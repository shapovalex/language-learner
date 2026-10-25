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

MAX_HEADER_BYTES = 8192  # all part header names and values, together
MAX_BOUNDARY_BYTES = 200
UUID_LENGTH = 36  # the itemId part's limit
STREAM_SLACK_BYTES = 16384  # multipart framing allowed beyond the recording


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

    def header_bytes(target: bytearray):
        def on_bytes(data, start, end):
            nonlocal header_size
            header_size += end - start
            if header_size > MAX_HEADER_BYTES:
                raise ValueError
            target.extend(data[start:end])

        return on_bytes

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
        recording = current == b"recording"
        if len(parts[current]) + end - start > (MAX_ATTEMPT_BYTES if recording else UUID_LENGTH):
            raise AppError(
                ErrorCode.PAYLOAD_TOO_LARGE if recording else ErrorCode.VALIDATION_FAILED
            )
        parts[current].extend(data[start:end])

    def finished():
        nonlocal ended
        ended = True

    try:
        kind, options = parse_options_header(request.headers.get("content-type", ""))
        boundary = options.get(b"boundary", b"")
        if kind != b"multipart/form-data" or not boundary or len(boundary) > MAX_BOUNDARY_BYTES:
            raise ValueError
        parser = MultipartParser(
            boundary,
            callbacks={
                "on_part_begin": begin,
                "on_header_field": header_bytes(header_name),
                "on_header_value": header_bytes(header_value),
                "on_header_end": header_end,
                "on_headers_finished": headers_finished,
                "on_part_data": data_part,
                "on_end": finished,
            },
        )
        total = 0
        async for chunk in request.stream():
            total += len(chunk)
            if total > MAX_ATTEMPT_BYTES + STREAM_SLACK_BYTES:
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
