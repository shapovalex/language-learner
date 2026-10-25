"""Story 7.2 RED: PyAV decodes both native browser encodings in memory, without numpy."""

import sys

import pytest

from tests.support.aio import settle
from tests.support.assessment import MP4_SAMPLE, WEBM_SAMPLE, converted_properties, sample


@pytest.mark.p0
@pytest.mark.parametrize("recording", [MP4_SAMPLE, WEBM_SAMPLE], ids=["ios-mp4-aac", "webm-opus"])
def test_native_recording_becomes_16khz_mono_pcm_without_numpy(recording, monkeypatch):
    """[P0] AC-6 both native codecs become nonempty 16 kHz mono s16 PCM WAV in memory."""
    monkeypatch.setitem(sys.modules, "numpy", None)

    result = settle(converted_properties(sample(recording)))
    properties = {} if isinstance(result, Exception) else result

    assert properties.get("sampleRate") == 16_000
    assert properties["channels"] == 1
    assert properties["sampleWidth"] == 2
    assert properties["compression"] == "NONE"
    assert 0 < properties["frames"] <= 30 * 16_000
    assert properties["nonSilent"] is True


@pytest.mark.parametrize("seconds", [1, 30])
def test_duration_limit_includes_exact_thirty_seconds(seconds):
    from language_lab.features.pronunciation.audio import to_wav
    from tests.support.assessment import wav_bytes, wav_properties

    assert wav_properties(to_wav(wav_bytes(seconds)))["frames"] == seconds * 16_000


@pytest.mark.parametrize("recording", [b"", b"corrupt recording", b"RIFF\0\0\0\0WAVE"])
def test_invalid_audio_has_a_fixed_validation_error(recording):
    from language_lab.domain.errors import AppError, ErrorCode
    from language_lab.features.pronunciation.audio import to_wav

    with pytest.raises(AppError) as raised:
        to_wav(recording)
    assert raised.value.code == ErrorCode.VALIDATION_FAILED


def test_resampling_stereo_at_48khz_flushes_the_last_samples():
    import io
    import wave

    from language_lab.features.pronunciation.audio import to_wav
    from tests.support.assessment import wav_properties

    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(48_000)
        wav.writeframes(b"\x01\x20\x01\x10" * 48_000)
    properties = wav_properties(to_wav(output.getvalue()))
    assert properties["frames"] == 16_000
    assert properties["channels"] == 1
    assert properties["nonSilent"]
