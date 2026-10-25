"""Story 7.2 Attempt fixtures and proposed boundary contracts, with no live externals.

The Assessment wire shape is an explicit scaffold choice shared with browser tests.
New production imports resolve inside observed operations, so collection works in RED.
"""

import io
import json
import uuid
import wave
from fractions import Fraction
from pathlib import Path
from typing import Any

import av
from pydantic import TypeAdapter

from language_lab.domain.errors import AppError, ErrorCode
from tests.fakes.speech import FakeSpeech
from tests.support.anki_state import item_note, managed_collection
from tests.support.audio import MediaRig
from tests.support.captures import MANIFEST
from tests.support.duplicates import vocabulary
from tests.support.items import note_type_of, stored_fields

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "azure-assessment"
ATTEMPT_API = "/api/pronunciation/en/attempt"
MAX_ATTEMPT_BYTES = 5 * 1024 * 1024  # AD-14: same binary MB convention as managed audio
MAX_ATTEMPT_SECONDS = 30
EN_REPLY = "single-en-US-taught-vs-thought.json"
FR_REPLY = "single-fr-CA-bonsoir-vs-bonjour.json"
SILENCE_REPLY = "silence-enUS.json"
MP4_SAMPLE = "en-weather.mp4-aac.mp4"
WEBM_SAMPLE = "en-weather.webm-opus.webm"


def sample(name: str = MP4_SAMPLE) -> bytes:
    return (FIXTURES / name).read_bytes()


def response_fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def assessment_wire(*, locale: str = "en-US") -> dict[str, Any]:
    """Known values transcribed independently from the two real Azure response fixtures."""
    if locale == "fr-CA":
        return {
            "locale": locale,
            "overall": 10.6,
            "accuracy": 53.0,
            "fluency": 0.0,
            "completeness": 0.0,
            "prosody": None,
            "words": [
                {
                    "text": "bonjour",
                    "score": 53.0,
                    "errorType": "Mispronunciation",
                    "phonemes": [],
                    "positions": {"start": 17.0, "middle": 0.0, "end": 0.0},
                }
            ],
        }
    return {
        "locale": locale,
        "overall": 79.2,
        "accuracy": 89.0,
        "fluency": 100.0,
        "completeness": 100.0,
        "prosody": 53.4,
        "words": [
            {
                "text": "thought",
                "score": 89.0,
                "errorType": "None",
                "phonemes": [
                    {"symbol": "θ", "score": 59.0},
                    {"symbol": "ɔ", "score": 89.0},
                    {"symbol": "t", "score": 99.0},
                ],
                "positions": None,
            }
        ],
    }


def wav_bytes(seconds: int = 1) -> bytes:
    """A known PCM WAV for the Azure adapter contract, without depending on the converter."""
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\0\0" * 16_000 * seconds)
    return output.getvalue()


def wav_properties(data: bytes) -> dict[str, Any]:
    with wave.open(io.BytesIO(data), "rb") as audio:
        frames = audio.readframes(audio.getnframes())
        return {
            "sampleRate": audio.getframerate(),
            "channels": audio.getnchannels(),
            "sampleWidth": audio.getsampwidth(),
            "compression": audio.getcomptype(),
            "frames": audio.getnframes(),
            "nonSilent": any(frames),
        }


async def converted_properties(data: bytes) -> dict[str, Any]:
    """Proposed sync converter to_wav(bytes) -> bytes; import and parse inside settle()."""
    from language_lab.features.pronunciation.audio import to_wav

    return wav_properties(to_wav(data))


def overlong_webm() -> bytes:
    """31-second compressed Opus upload: small bytes, excessive decoded duration.

    Frame planes are populated directly, never through numpy. Nothing touches disk.
    """
    output = io.BytesIO()
    with av.open(output, "w", format="webm") as container:
        stream = container.add_stream("libopus", rate=48_000, layout="mono")
        for i in range(31 * 50):
            frame = av.AudioFrame(format="s16", layout="mono", samples=960)
            frame.sample_rate = 48_000
            frame.pts = i * 960
            frame.time_base = Fraction(1, 48_000)
            frame.planes[0].update(bytes(frame.planes[0].buffer_size))
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)
    return output.getvalue()


async def assess_with(speech: Any, locale: str, target: str, wav: bytes) -> Any:
    """Proposed Speech.assess(locale, target, wav) -> Assessment | None."""
    return await speech.assess(locale, target, wav)


async def assess_wire(replay: Any, *, locale: str, target: str) -> Any:
    """Real Azure adapter over the existing offline HTTP replay; no live subscription."""
    from language_lab.adapters.azure import AzureSpeech
    from tests.support.audio import AZURE_KEY, AZURE_REGION

    speech = AzureSpeech(AZURE_KEY, AZURE_REGION, transport=replay.transport)
    try:
        assessment = await assess_with(speech, locale, target, wav_bytes())
        return None if assessment is None else assessment.wire()
    finally:
        await speech.aclose()


class AttemptSpeech(FakeSpeech):
    """Test-owned extension of the existing Speech fake until the port grows assess()."""

    def __init__(self) -> None:
        super().__init__()
        self.assessments: list[dict[str, Any]] = []
        self.assessment_error = False

    async def assess(self, locale: str, target: str, wav: bytes) -> Any:
        self.assessments.append({"locale": locale, "target": target, "wav": wav})
        if self.assessment_error:
            raise AppError(ErrorCode.ASSESSMENT_FAILED)
        from language_lab.domain.pronunciation import Assessment

        return TypeAdapter(Assessment).validate_python(assessment_wire(locale=locale))


def attempt_rig(*, target: str = "thought") -> tuple[MediaRig, str]:
    """A real guarded adapter over an existing Anki collection; no precondition HTTP call."""
    collection = managed_collection(MANIFEST)
    item_id = str(uuid.uuid4())
    wire = vocabulary(target)
    item_note(collection, MANIFEST, note_type_of("en", wire), item_id, stored_fields(wire, item_id))
    return MediaRig(collection), item_id


def attempt_parts(item_id: str, recording: bytes | None = None, *, webm: bool = False):
    return {
        "itemId": (None, item_id),
        "recording": (
            "attempt.webm" if webm else "attempt.mp4",
            sample(WEBM_SAMPLE if webm else MP4_SAMPLE) if recording is None else recording,
            "audio/webm" if webm else "audio/mp4",
        ),
    }
