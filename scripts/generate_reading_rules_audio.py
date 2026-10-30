"""Dev tool: generate the bundled audio of the French reading rules deck.

Usage: LANGUAGE_LAB_DEV=1 uv run python scripts/generate_reading_rules_audio.py

Reads src/language_lab/data/french_reading_rules/rules.json, synthesizes every example word
with Azure `fr-CA-SylvieNeural` (the keys come from the dev `.env`), and writes
`audio/<key>-<n>.mp3` beside it plus `audio/index.json` (`{file: word}`), removing any other
file there. Run it after changing an example word, then commit the audio. Setup never calls
Azure: it stores these files as they are.
"""

import asyncio
import json
import sys
from pathlib import Path

from language_lab.adapters.azure import AzureSpeech
from language_lab.domain.reading_rules import audio_file
from language_lab.settings import load_settings

DATA = Path(__file__).resolve().parent.parent / "src/language_lab/data/french_reading_rules"
LOCALE, VOICE = "fr-CA", "fr-CA-SylvieNeural"
INDEX = "index.json"


async def generate() -> int:
    settings = load_settings()
    rules = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    audio = DATA / "audio"
    audio.mkdir(exist_ok=True)
    wanted = {
        audio_file(rule["key"], n): word
        for rule in rules
        for n, word in enumerate(rule["examples"], 1)
    }
    speech = AzureSpeech(settings.azure_speech_key.get_secret_value(), settings.azure_speech_region)
    try:
        for name, word in wanted.items():
            (audio / name).write_bytes(await speech.synthesize(LOCALE, VOICE, word))
            print(f"{name}: {word}")
    finally:
        await speech.aclose()
    index = json.dumps(wanted, ensure_ascii=False, indent=2) + "\n"
    (audio / INDEX).write_text(index, encoding="utf-8")
    for stale in audio.iterdir():
        if stale.name not in wanted and stale.name != INDEX:
            stale.unlink()
            print(f"removed {stale.name}")
    print(f"{len(wanted)} files written")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(generate()))
