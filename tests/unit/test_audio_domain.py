"""Refactor sweep (epic reference audio): the one Save-audio rule and media name in
domain/audio.py, shared by the Save route, the Anki adapter and the fake store.

- **audio_upload.** `replace` needs a file that is a valid MP3 within `MAX_AUDIO_BYTES`
  (`PAYLOAD_TOO_LARGE` over it, `VALIDATION_FAILED` when it isn't an MP3); `keep` and `remove`
  refuse any file. The bytes stored are the bytes sent.
- **media_name.** `<Prefix>_<ItemId>_<sha256[:12]>.mp3`.
"""

import pytest

from language_lab.domain.audio import MAX_AUDIO_BYTES, audio_upload, media_name
from language_lab.domain.errors import AppError, ErrorCode
from language_lab.domain.items import AudioIntent
from tests.support.audio import MP3, SECOND_MP3, managed_name

ITEM_ID = "0b6f3c1e-8d2a-4f5b-9c7e-1a2b3c4d5e6f"


@pytest.mark.p0
def test_replace_with_a_valid_mp3_returns_the_same_bytes() -> None:
    assert audio_upload(AudioIntent.REPLACE, MP3) is MP3


@pytest.mark.p0
@pytest.mark.parametrize("intent", [AudioIntent.KEEP, AudioIntent.REMOVE])
def test_keep_and_remove_without_a_file_store_nothing(intent: AudioIntent) -> None:
    assert audio_upload(intent, None) is None


@pytest.mark.p0
@pytest.mark.parametrize(
    ("intent", "data"),
    [
        (AudioIntent.REPLACE, None),
        (AudioIntent.KEEP, MP3),
        (AudioIntent.REMOVE, MP3),
        (AudioIntent.REPLACE, b"not an mp3"),
        (AudioIntent.REPLACE, b""),
    ],
    ids=["replace-no-file", "keep-file", "remove-file", "replace-not-mp3", "replace-empty"],
)
def test_a_mismatched_or_invalid_upload_is_refused_422(
    intent: AudioIntent, data: bytes | None
) -> None:
    with pytest.raises(AppError) as raised:
        audio_upload(intent, data)
    assert raised.value.code is ErrorCode.VALIDATION_FAILED


@pytest.mark.p0
def test_replace_over_the_size_limit_is_refused_413() -> None:
    with pytest.raises(AppError) as raised:
        audio_upload(AudioIntent.REPLACE, MP3 + b"\0" * (MAX_AUDIO_BYTES + 1 - len(MP3)))
    assert raised.value.code is ErrorCode.PAYLOAD_TOO_LARGE


@pytest.mark.p1
@pytest.mark.parametrize("data", [MP3, SECOND_MP3], ids=["first", "second"])
def test_media_name_is_prefix_item_id_and_content_digest(data: bytes) -> None:
    name = media_name("LanguageLab", ITEM_ID, data)
    assert name == managed_name(ITEM_ID, data, prefix="LanguageLab")
    assert name.startswith(f"LanguageLab_{ITEM_ID}_") and name.endswith(".mp3")
    assert len(name.removeprefix(f"LanguageLab_{ITEM_ID}_").removesuffix(".mp3")) == 12
