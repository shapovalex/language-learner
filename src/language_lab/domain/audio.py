"""Reference audio values and bounded MP3 validation; bytes are never transformed."""

import hashlib
from dataclasses import dataclass

from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent

MAX_AUDIO_BYTES = 5 * 1024 * 1024


@dataclass(frozen=True)
class Voice:
    name: str
    locale: str
    display_name: str


def validate_mp3(data: bytes) -> None:
    """Require complete MPEG Layer III frames, allowing ID3 metadata at either end."""
    if len(data) > MAX_AUDIO_BYTES:
        raise AppError(ErrorCode.PAYLOAD_TOO_LARGE)
    position = 0
    if data.startswith(b"ID3"):
        if len(data) < 10 or any(b & 128 for b in data[6:10]):
            raise AppError(ErrorCode.VALIDATION_FAILED)
        size = sum(b << shift for b, shift in zip(data[6:10], (21, 14, 7, 0), strict=True))
        position = 10 + size + (10 if data[5] & 16 else 0)
    frames = 0
    while position < len(data):
        if len(data) - position == 128 and data[position : position + 3] == b"TAG":
            position += 128
            break
        header = data[position : position + 4]
        if len(header) != 4 or header[0] != 255 or header[1] & 224 != 224:
            raise AppError(ErrorCode.VALIDATION_FAILED)
        version, layer = (header[1] >> 3) & 3, (header[1] >> 1) & 3
        rate, frequency = header[2] >> 4, (header[2] >> 2) & 3
        if (
            version == 1
            or layer != 1
            or rate in (0, 15)
            or frequency == 3
            or header[3] & 3 == 2  # reserved MPEG emphasis value
        ):
            raise AppError(ErrorCode.VALIDATION_FAILED)
        rates = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)
        if version != 3:
            rates = (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)
        sample_rate = (44100, 48000, 32000)[frequency] // {3: 1, 2: 2, 0: 4}[version]
        length = (144 if version == 3 else 72) * rates[rate] * 1000 // sample_rate
        length += (header[2] >> 1) & 1
        position += length
        frames += 1
    if not frames or position != len(data):
        raise AppError(ErrorCode.VALIDATION_FAILED)


def audio_upload(intent: AudioIntent, data: bytes | None) -> bytes | None:
    """The bytes a Save stores: `replace` needs a valid MP3, `keep` and `remove` take no file.
    Raises `AppError(VALIDATION_FAILED | PAYLOAD_TOO_LARGE)`.
    """
    if intent is AudioIntent.REPLACE:
        if data is None:
            raise AppError(ErrorCode.VALIDATION_FAILED)
        validate_mp3(data)
        return data
    if data is not None:
        raise AppError(ErrorCode.VALIDATION_FAILED)
    return None


def media_name(prefix: str, item_id: str, data: bytes) -> str:
    """The managed media name of `data` for an Item (AD-7):
    `<prefix lowercased>_<ItemId>_<sha256[:12]>.mp3`. Anki lowercases the names it stores
    (spike 2.2), so a lowercase name comes back unchanged.
    """
    return f"{prefix.lower()}_{item_id}_{hashlib.sha256(data).hexdigest()[:12]}.mp3"
