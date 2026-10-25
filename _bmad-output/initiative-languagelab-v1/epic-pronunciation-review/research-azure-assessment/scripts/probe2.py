import sys, io, wave, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from probe_assess import read_env, to_wav16k, assess
env = read_env(sys.argv[1]); d = Path(sys.argv[2]); out = Path(sys.argv[3])
k, r = env["AZURE_SPEECH_KEY"], env["AZURE_SPEECH_REGION"]
bon = to_wav16k((d / "fr-bonjour.wav").read_bytes())
sil = io.BytesIO()
with wave.open(sil, "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b"\0" * 32000 * 2)
for name, loc, wav, ref in [("bonjour-direct-frCA", "fr-CA", bon, "Bonjour"),
                            ("bonjour-frFR", "fr-FR", bon, "Bonjour"),
                            ("silence-enUS", "en-US", sil.getvalue(), "What's the weather like?")]:
    s, t, body = assess(r, k, loc, wav, ref)
    (out / f"{name}.json").write_text(body)
    print(name, s, f"{t:.2f}s", body[:300])
s, t, body = assess(r, "invalid", "en-US", bon, "x"); print("badkey", s, body[:200])
