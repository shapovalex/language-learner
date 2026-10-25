"""Probe Azure scripted pronunciation assessment (REST short audio) with PyAV conversion.

usage: probe_assess.py <env file> <audio dir> <out dir>
Encodes each sample to AAC/mp4 (iOS MediaRecorder) and Opus/webm (Chrome), decodes it back
with PyAV to 16 kHz mono PCM WAV in memory, and calls Azure. Never prints the key.
"""

import base64
import io
import json
import sys
import time
import wave
from pathlib import Path

import av
import httpx


def read_env(path):
    out = {}
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def encode(src: Path, container: str, codec: str, rate: int) -> bytes:
    buf = io.BytesIO()
    with av.open(str(src)) as inp, av.open(buf, "w", format=container) as out:
        stream = out.add_stream(codec, rate=rate, layout="mono")
        resampler = av.AudioResampler(format=stream.format.name, layout="mono", rate=rate)
        for frame in inp.decode(audio=0):
            for f in resampler.resample(frame):
                for p in stream.encode(f):
                    out.mux(p)
        for f in resampler.resample(None):
            for p in stream.encode(f):
                out.mux(p)
        for p in stream.encode(None):
            out.mux(p)
    return buf.getvalue()


def to_wav16k(data: bytes) -> bytes:
    pcm = bytearray()
    with av.open(io.BytesIO(data)) as inp:
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        for frame in inp.decode(audio=0):
            for f in resampler.resample(frame):
                pcm += bytes(f.planes[0])[: f.samples * 2]
        for f in resampler.resample(None):
            pcm += bytes(f.planes[0])[: f.samples * 2]
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(bytes(pcm))
    return out.getvalue()


def assess(region, key, locale, wav, reference, **extra):
    cfg = {"ReferenceText": reference, "GradingSystem": "HundredMark",
           "Granularity": "Phoneme", "Dimension": "Comprehensive", "EnableMiscue": True}
    cfg.update(extra)
    header = base64.b64encode(json.dumps(cfg).encode()).decode()
    url = (f"https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/"
           f"cognitiveservices/v1?language={locale}&format=detailed")
    t = time.monotonic()
    r = httpx.post(url, content=wav, timeout=30, headers={
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
        "Accept": "application/json",
        "Pronunciation-Assessment": header,
    })
    return r.status_code, time.monotonic() - t, r.text


CASES = [
    # name, file, locale, reference, extra config
    ("en-correct", "en-weather.wav", "en-US", "What's the weather like?",
     {"PhonemeAlphabet": "IPA", "EnableProsodyAssessment": True}),
    ("en-miscue", "en-weather.wav", "en-US", "What is the weather like today?",
     {"PhonemeAlphabet": "IPA", "EnableProsodyAssessment": True}),
    ("frCA-lunettes", "fr-lunettes.wav", "fr-CA", "Bonjour lunettes, adieu fillettes.", {}),
    ("frCA-bonjour", "fr-bonjour.wav", "fr-CA", "Bonjour", {}),
    ("frCA-lunettes-prosody-ipa", "fr-lunettes.wav", "fr-CA", "Bonjour lunettes, adieu fillettes.",
     {"PhonemeAlphabet": "IPA", "EnableProsodyAssessment": True}),
    ("frCA-wrongtext", "fr-lunettes.wav", "fr-CA", "Bonsoir lunettes, adieu fillettes.", {}),
]


def main():
    env_file, audio_dir, out_dir = map(Path, sys.argv[1:4])
    env = read_env(env_file)
    key, region = env["AZURE_SPEECH_KEY"], env["AZURE_SPEECH_REGION"]
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fname, locale, ref, extra in CASES:
        src = audio_dir / fname
        for label, (container, codec, rate) in {"mp4-aac": ("mp4", "aac", 48000),
                                                "webm-opus": ("webm", "libopus", 48000)}.items():
            if label == "webm-opus" and not name.endswith(("correct", "lunettes")):
                continue
            try:
                blob = encode(src, container, codec, rate)
                (out_dir / f"{fname.rsplit('.', 1)[0]}.{label}.{container}").write_bytes(blob)
                t = time.monotonic()
                wav = to_wav16k(blob)
                conv = time.monotonic() - t
            except Exception as e:  # noqa: BLE001
                print(f"{name} {label}: conversion failed: {type(e).__name__}: {e}")
                continue
            status, secs, body = assess(region, key, locale, wav, ref, **extra)
            (out_dir / f"{name}.{label}.json").write_text(body)
            print(f"{name} {label}: blob={len(blob)}B wav={len(wav)}B conv={conv:.2f}s "
                  f"http={status} {secs:.2f}s body={len(body)}B")


if __name__ == "__main__":
    main()
