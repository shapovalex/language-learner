# Azure pronunciation assessment probe (2026-10-25)

Real calls to Azure Speech (`eastus`) scripted pronunciation assessment, REST short-audio endpoint, from the dev machine with the key in the repo `.env`. Done before epic 7 inception to settle the source of 7.2's fixtures.

## How

`scripts/probe_assess.py`, `probe2.py`, and `probe3.py` (run with `uv run python -I <script> .env <audio dir> <out dir>`):

1. Encode each sample with PyAV (`av==19.0.1`, the wheel's pin) to AAC in MP4 (what iOS Safari MediaRecorder sends) and Opus in WebM (Chrome).
2. Decode that blob back with PyAV to 16 kHz mono s16 WAV in memory.
3. `POST https://{region}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language={locale}&format=detailed` with `Content-Type: audio/wav; codecs=audio/pcm; samplerate=16000` and a base64 JSON `Pronunciation-Assessment` header: `ReferenceText`, `GradingSystem: HundredMark`, `Granularity: Phoneme`, `Dimension: Comprehensive`, `EnableMiscue: true`, and for en-US `PhonemeAlphabet: IPA`, `EnableProsodyAssessment: true`.

## Findings

- **PyAV conversion works for both MP4/AAC and WebM/Opus** with no ffmpeg install, in under 10 ms per clip. `AudioFrame.to_ndarray()` needs numpy, which is not a dependency: take the PCM with `bytes(frame.planes[0])[: frame.samples * 2]` from an `AudioResampler(format="s16", layout="mono", rate=16000)`.
- **Latency:** 0.3–0.9 s per assessment (one 2.6 s outlier).
- **REST reply shape:** the scores are flat on `NBest[0]` (`AccuracyScore`, `FluencyScore`, `CompletenessScore`, `ProsodyScore`, `PronScore`) and on each `Words[]` item (`AccuracyScore`, `ErrorType`), with `Syllables[]` and `Phonemes[]` (`Phoneme`, `AccuracyScore`). This is not the SDK's nested `PronunciationAssessment` object. Prosody feedback per word is under `Words[].Feedback.Prosody` (`Break`, `Intonation`).
- **en-US:** IPA phonemes and syllables (`θ ɔ t`, `wɛð ɚ`), a `ProsodyScore`, and per-word prosody feedback. Prosody on a single word is low and noisy (64 for a clean TTS "thought").
- **fr-CA:** `Phoneme` and `Syllable` labels come back as **empty strings**, even when IPA is requested, but each phoneme keeps its `AccuracyScore` in order. So start, middle, and end positions can be computed from the phoneme index, and no French sound can be named (AD-14 holds without filtering). `ProsodyScore` is absent even when prosody is requested.
- **Wrong words:** reading "bonjour" against "bonsoir" gives the word `ErrorType: Mispronunciation` at 36, with the end phonemes at 0 (position "end"). A word not said gives `ErrorType: Omission`. Azure's `ErrorType` stays `None` for a weak but recognized word ("taught" read as "thought": 89, `θ` at 59), so the "mispronounced" step in the UI is LanguageLab's own threshold on word or phoneme scores.
- **Nothing heard is not an error:** silence, and one quiet Lingua Libre clip, return **HTTP 200** `RecognitionStatus: Success` with `DisplayText: "."`, every word `Omission`, and all scores 0. It needs its own handling, not the Assessment-failed path.
- **Bad key:** HTTP 401 with an empty body.
- Single-word Targets (Vocabulary) assess fine with clear audio in both locales.

## Files

- `responses/*.json`: the raw Azure replies, named `<case>.<encoding>.json`. They hold no key or account data.
- `samples/`: the encoded MP4 and WebM inputs, and Azure TTS MP3s (Sylvie fr-CA, Andrew en-US) used as clear single-word speakers.

## Sources of the input audio

- `en-weather.*`: "What's the weather like?", `whatstheweatherlike.wav` from Azure-Samples/cognitive-services-speech-sdk (MIT).
- `fr-lunettes.*`: "Bonjour lunettes, adieu fillettes", Wikimedia Commons `LL-Q150 (fra)-LoquaxFR-bonjour lunettes, adieu fillettes.wav` (Lingua Libre, CC BY-SA 4.0, speaker LoquaxFR).
- `fr-bonjour.*`: "Bonjour", Wikimedia Commons `LL-Q150 (fra)-Platinium12-Mbalatsara (Bonjour).wav` (Lingua Libre, CC BY-SA 4.0, speaker Platinium12). Azure did not hear it (see above).
- `tts-*.mp3`: synthesized by Azure TTS with the project key.

A sample copied into `tests/fixtures/` keeps its source and license line in that folder's README.
