import sys, json, httpx
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from probe_assess import read_env, to_wav16k, assess
env = read_env(sys.argv[1]); out = Path(sys.argv[2])
k, r = env["AZURE_SPEECH_KEY"], env["AZURE_SPEECH_REGION"]
def tts(loc, voice, text):
    ssml = f"<speak version='1.0' xml:lang='{loc}'><voice name='{voice}'>{text}</voice></speak>"
    resp = httpx.post(f"https://{r}.tts.speech.microsoft.com/cognitiveservices/v1", content=ssml.encode(),
        headers={"Ocp-Apim-Subscription-Key": k, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3", "User-Agent": "probe"}, timeout=30)
    resp.raise_for_status(); return resp.content
for loc, voice, said, ref in [("fr-CA", "fr-CA-SylvieNeural", "bonjour", "bonjour"),
                              ("fr-CA", "fr-CA-SylvieNeural", "bonsoir", "bonjour"),
                              ("en-US", "en-US-AndrewNeural", "thought", "thought"),
                              ("en-US", "en-US-AndrewNeural", "taught", "thought")]:
    mp3 = tts(loc, voice, said)
    (out / f"tts-{loc}-{said}.mp3").write_bytes(mp3)
    extra = {"PhonemeAlphabet": "IPA", "EnableProsodyAssessment": True} if loc == "en-US" else {}
    s, t, body = assess(r, k, loc, to_wav16k(mp3), ref, **extra)
    (out / f"single-{loc}-{said}-vs-{ref}.json").write_text(body)
    nb = json.loads(body)["NBest"][0]; w = nb["Words"][0]
    print(loc, said, "vs", ref, s, {x: nb.get(x) for x in ("AccuracyScore","PronScore","ProsodyScore")},
          w["ErrorType"], [(p["Phoneme"], p["AccuracyScore"]) for p in w.get("Phonemes", [])])
