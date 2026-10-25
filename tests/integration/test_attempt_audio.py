"""Story 7.2 RED: PyAV decodes both native browser encodings in memory, without numpy."""

import sys

import pytest

from tests.support.aio import settle
from tests.support.assessment import MP4_SAMPLE, WEBM_SAMPLE, converted_properties, sample

pytestmark = pytest.mark.skip(reason="Story 7.2 RED scaffold: activate with Attempt transcoding")


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
