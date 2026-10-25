"""Strict streaming multipart parsing without UploadFile's temporary-file spooling."""

import re

from fastapi import Request
from python_multipart import MultipartParser
from python_multipart.exceptions import MultipartParseError
from python_multipart.multipart import parse_options_header
from starlette.requests import ClientDisconnect

from language_lab.domain.catalog import UUID4
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.features.pronunciation.audio import MAX_ATTEMPT_BYTES


async def read_attempt(request: Request) -> tuple[str, bytes]:
    parts: dict[bytes, bytearray] = {}
    headers: dict[bytes, bytes] = {}
    header_name = bytearray()
    header_value = bytearray()
    current: bytes | None = None
    ended = False
    header_size = 0

    def begin():
        nonlocal current
        current = None
        headers.clear()

    def header_field(data, start, end):
        nonlocal header_size
        header_size += end - start
        if header_size > 8192:
            raise ValueError
        header_name.extend(data[start:end])

    def header_value_part(data, start, end):
        nonlocal header_size
        header_size += end - start
        if header_size > 8192:
            raise ValueError
        header_value.extend(data[start:end])

    def header_end():
        key = bytes(header_name).lower()
        if key in headers:
            raise ValueError
        headers[key] = bytes(header_value)
        header_name.clear()
        header_value.clear()

    def headers_finished():
        nonlocal current
        kind, options = parse_options_header(headers.get(b"content-disposition", b""))
        current = options.get(b"name")
        if kind != b"form-data" or current not in (b"itemId", b"recording") or current in parts:
            raise ValueError
        if (current == b"recording") != (b"filename" in options):
            raise ValueError
        parts[current] = bytearray()

    def data_part(data, start, end):
        if current is None:
            raise ValueError
        limit = MAX_ATTEMPT_BYTES if current == b"recording" else 36
        if len(parts[current]) + end - start > limit:
            code = (
                ErrorCode.PAYLOAD_TOO_LARGE
                if current == b"recording"
                else (ErrorCode.VALIDATION_FAILED)
            )
            raise AppError(code)
        parts[current].extend(data[start:end])

    def finished():
        nonlocal ended
        ended = True

    try:
        kind, options = parse_options_header(request.headers.get("content-type", ""))
        boundary = options.get(b"boundary", b"")
        if kind != b"multipart/form-data" or not boundary or len(boundary) > 200:
            raise ValueError
        parser = MultipartParser(
            boundary,
            callbacks={
                "on_part_begin": begin,
                "on_header_field": header_field,
                "on_header_value": header_value_part,
                "on_header_end": header_end,
                "on_headers_finished": headers_finished,
                "on_part_data": data_part,
                "on_end": finished,
            },
        )
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_ATTEMPT_BYTES + 16384:
                raise AppError(ErrorCode.PAYLOAD_TOO_LARGE)
            parser.write(chunk)
        parser.finalize()
        if not ended or set(parts) != {b"itemId", b"recording"} or not parts[b"recording"]:
            raise ValueError
        item_id = parts[b"itemId"].decode("ascii")
        if re.fullmatch(UUID4, item_id) is None:
            raise ValueError
        return item_id, bytes(parts[b"recording"])
    except ValueError, UnicodeError, MultipartParseError, ClientDisconnect:
        raise AppError(ErrorCode.VALIDATION_FAILED) from None
    finally:
        for part in parts.values():
            part.clear()
        parts.clear()
