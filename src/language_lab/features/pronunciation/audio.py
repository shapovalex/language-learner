"""Bounded, in-memory native recording decode. No subprocess, filesystem or numpy."""

import io
import wave
from fractions import Fraction

import av

from language_lab.domain.errors import AppError, ErrorCode

MAX_ATTEMPT_BYTES = 5 * 1024 * 1024
MAX_ATTEMPT_SECONDS = 30
SAMPLE_RATE = 16_000


def to_wav(data: bytes) -> bytes:
    if len(data) > MAX_ATTEMPT_BYTES:
        raise AppError(ErrorCode.PAYLOAD_TOO_LARGE)
    try:
        with io.BytesIO(data) as source, io.BytesIO() as output:
            with av.open(source, mode="r") as container, wave.open(output, "wb") as wav:
                if len(container.streams.audio) != 1:
                    raise ValueError
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(SAMPLE_RATE)
                resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
                duration = Fraction(0)
                samples = 0

                def write(frames):
                    nonlocal samples
                    for frame in frames:
                        samples += frame.samples
                        if samples > MAX_ATTEMPT_SECONDS * SAMPLE_RATE:
                            raise ValueError
                        wav.writeframesraw(bytes(frame.planes[0])[: frame.samples * 2])

                for frame in container.decode(audio=0):
                    duration += Fraction(frame.samples, frame.sample_rate)
                    if duration > MAX_ATTEMPT_SECONDS:
                        raise ValueError
                    write(resampler.resample(frame))
                write(resampler.resample(None))
                if not samples:
                    raise ValueError
            return output.getvalue()
    except av.FFmpegError, ValueError, EOFError, OSError:
        raise AppError(ErrorCode.VALIDATION_FAILED) from None
