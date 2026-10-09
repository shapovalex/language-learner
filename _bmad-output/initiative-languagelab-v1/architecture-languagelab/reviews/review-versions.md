# Review: Versions and Reality Check of the LanguageLab Architecture Spine

- **Target:** `../architecture-languagelab.md` (draft, 2026-10-08), with `../.memlog.md`
- **Date:** 2026-10-08
- **Lens:** were the committed decisions checked against live sources, or asserted from training data?
- **Method:** live queries made today: PyPI JSON API, GitHub releases API, endoflife.date, the AnkiConnect README on git.sr.ht, OpenRouter docs and Microsoft Learn. Local runs on this Mac (arm64, macOS 26.6.2, uv 0.12.23) tested PyAV, `uvx --from` and pydantic-settings directly.

## Verdict

**PASS with minor gaps.** Every pinned version in the Stack table matches the latest release published today. Each named technology still exists and fits. Running the code locally confirmed the riskiest claims: PyAV converts AAC/mp4 to WAV on Python 3.14 arm64, `uvx --from` accepts a wheel path and a wheel URL, and pydantic-settings reads an explicit env-file path. Nothing in the spine is outdated.

The gaps are of two kinds:
- the memlog records no evidence for about a third of the checked claims;
- a few implementation constraints that bear on AD-11, AD-14 and AD-18 are not stated anywhere (findings F1–F4).

## 1. Stack table vs. live sources

| Stack entry | Spine | Live latest (source, upload date) | Status |
| --- | --- | --- | --- |
| Python | 3.14 | 3.14.8, released 2026-09-30 (endoflife.date); 3.15 not yet GA | OK |
| FastAPI | 0.143.0 | 0.143.0 (PyPI, **2026-10-08**, published today) | OK; see F5 |
| uvicorn | 0.54.0 | 0.54.0 (2026-09-25) | OK |
| Pydantic | 2.14.0 | 2.14.0 (**2026-10-08**, published today; pydantic-core 2.50.0) | OK; see F5 |
| pydantic-settings | 2.15.0 | 2.15.0 (2026-08-07), requires pydantic>=2.7 | OK |
| httpx | 0.28.1 | 0.28.1 (2024-12-06), still the latest | OK (stable but old; no 1.0 yet) |
| av (PyAV) | 19.0.1 | 19.0.1 (2026-10-03), requires Python >=3.12 | OK; see §2 |
| pytest | 9.1.1 | 9.1.1 (2026-06-19) | OK |
| ruff | 0.16.10 | 0.16.10 (2026-10-01) | OK |
| uv | 0.12.24 | 0.12.24 (PyPI 2026-10-08, GitHub release 2026-10-08T20:06Z) | OK. The local machine has 0.12.23 |
| AnkiConnect | API version 6 | README examples all use `"version": 6`; latest tagged release 23.10.29.0, last repo commit 2025-12-03 | OK; see §3 |
| actions/checkout | v7 | v7.0.1 (2026-07-20) | OK |
| astral-sh/setup-uv | v10 | v10.2.0 (2026-09-21) | OK |
| softprops/action-gh-release | v3 | v3.0.3 (2026-08-30) | OK |
| **python-multipart** | *absent* | 0.0.32 (2026-06-04) | **Missing (F1)** |

FastAPI 0.143.0 declares `pydantic>=2.9.0` and `starlette>=0.46.0`, so it is compatible with Pydantic 2.14.0 and with pydantic-settings 2.15.0.

## 2. PyAV 19.0.1: wheels and codecs (checked by running it)

- **Wheels.** The release ships `av-19.0.1-cp312-abi3-macosx_14_0_arm64.whl`, a stable-ABI wheel that covers CPython 3.14. It also ships `cp314t` wheels for free-threaded Python only. Python 3.14 on arm64 therefore installs a binary wheel and needs no compiler.
  - Constraint: the wheel requires **macOS 14 or later** on the Mac Mini. The spine does not state this (F6).
- **Bundled FFmpeg.** It reports FFmpeg 9.0.2. The `aac` decoder and the `pcm_s16le` encoder are both available.
- **End-to-end run.** `uv run --python 3.14 --with av==19.0.1` on Python 3.14.8 arm64 performed the full conversion entirely in memory:
  - input: an AAC `.m4a` (MP4 container) made with `say` and `afconvert`;
  - steps: `av.open(BytesIO)` → decode → `AudioResampler(s16, mono, 16000)` → `wav` muxer with `pcm_s16le`;
  - output: a valid RIFF/WAVE file, `pcm_s16le`, 16000 Hz, 1 channel.

  This confirms the AD-14 Attempt path and that AD-2 holds (nothing touches disk).
- **Not tested.** No real iOS Safari `audio/mp4` recording was used. The memlog records that Safari MediaRecorder produces AAC in MP4. The fragmented MP4 that Safari emits should be tested with a real device sample when the pronunciation epic is built (low risk).

## 3. AnkiConnect, API version 6

Checked against the README at https://git.sr.ht/~foosoft/anki-connect/blob/master/README.md, fetched today (109 KB). The README has a `#### \`<action>\`` section for every action the spine or memlog relies on:

`answerCards`, `changeDeck`, `storeMediaFile`, `sync`, `saveDeckConfig`, `getDeckConfig`, `deleteMediaFile`, `getMediaFilesNames`, `findCards`, `cardsInfo`, `notesInfo`, `addNote`, `updateNoteFields`, `deleteNotes`, `suspend`, `createModel`, `updateModelTemplates`, `updateModelStyling`, `modelFieldAdd`, `createDeck`, `cloneDeckConfigId`, `setDeckConfigId`, `multi`.

Relevant details:
- **`answerCards`.** "Ease is between 1 (Again) and 4 (Easy)". This matches the Rating → ease 1–4 convention.
- **`changeDeck`.** It "moves cards … creating the deck if it doesn't exist yet". This supports AD-6 step 3.
- **`storeMediaFile`.**
  - It takes base64 `data`, a `path` or a `url`. AD-2 rules out on-disk temp files, so the adapter must send base64 `data`. This is consistent with AD-14, whose no-base64 rule covers only the LanguageLab API.
  - `deleteExisting` defaults to true. That is harmless with content-hashed names (AD-7).
- **`saveDeckConfig`.** It saves a whole config group, so the adapter has to read it with `getDeckConfig`, change it and write it back. The bury keys come from Anki's deck-config JSON, which is not documented in the README. Confirm them against a live Anki during the Setup epic.
- **Stale wording.** The README still says it is "compatible with the latest stable (2.1.x) releases of Anki", although Anki now uses 2x.xx version numbers. The add-on is still maintained (last commit 2025-12). This is low risk, but nobody has confirmed that the add-on works with the specific Anki version installed on the Mac Mini (F6).

## 4. OpenRouter

- **`models` fallback array.** Current. See https://openrouter.ai/docs/guides/routing/model-fallbacks.
  - The docs say "Provide an array of model IDs in priority order". If the first model errors, OpenRouter tries the next.
  - No maximum length is stated. The model that actually ran is reported in the response `model` field.
  - The separate Anthropic-style `fallbacks` parameter is capped at 3 and cannot be combined with `models`. The spine uses `models`, which is correct.
- **`provider.require_parameters`.** Current; default `false`. See https://openrouter.ai/docs/features/provider-routing. With `true`, OpenRouter routes only to providers that support every parameter in the request.
- **Structured outputs.** Current. See https://openrouter.ai/docs/features/structured-outputs.
  - The format is `response_format: {type: "json_schema", json_schema: {name, strict: true, schema}}`.
  - The docs explicitly recommend `require_parameters: true`.
  - Support is determined "per endpoint, not just per model" and "can change over time".
- **Unconfirmed: fallback behavior.** The docs do not say whether a `models` entry with no endpoint that supports structured outputs (under `require_parameters`) counts as an error that moves on to the next model, or fails the whole request. Test this once with a deliberately unsupported first model.
- **Strict-schema fit with Pydantic (F2).** In strict mode, providers that follow OpenAI's rules require:
  - `additionalProperties: false` on every object;
  - every property listed in `required`;
  - no unsupported keywords such as `default`, and for some providers no `minLength`/`format`.

  Pydantic's `model_json_schema()` does not produce this by default. Optional or defaulted fields drop out of `required`, and `additionalProperties` is omitted unless `extra="forbid"` is set. AD-11 says "Its JSON Schema (strict)" but does not say who makes the schema strict-compatible.

## 5. Azure Speech REST

Source: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short, updated 2026-06-05.

- **Short-audio endpoint.** `https://<resource>.cognitiveservices.azure.com/stt/speech/recognition/conversation/cognitiveservices/v1?language=<locale>`.
- **`Pronunciation-Assessment` header.** Still current: base64-encoded JSON with these parameters:
  - `ReferenceText`, `GradingSystem`, `Granularity`, `Dimension`, `EnableMiscue`;
  - **`EnableProsodyAssessment`**, which returns `ProsodyScore`. **REST does support prosody.**
- **Audio format.** WAV PCM 16 kHz mono with `Content-type: audio/wav; codecs=audio/pcm; samplerate=16000`, or OGG Opus. This matches the PyAV output in §2.
- **Length limits.** At most 60 s of audio per request, and "for pronunciation assessment, the audio duration should be no more than 30 seconds". The how-to page says ">30 s use continuous mode", which is SDK only. This confirms AD-14's 30 s auto-stop.
- **Prosody locale.** The how-to page (updated 2026-07-03) says "Prosody assessment is only available in the en-US locale". This matches AD-14.
- **fr-CA.** It is listed in the pronunciation-assessment language table (33 locales). The spine does not state this explicitly, but it holds.
- **Doc framing.** Microsoft's docs say to use REST short audio "only in cases where you can't use the Speech SDK". The REST API is not deprecated. AD-14 has a reason for REST (it avoids the SDK's native GStreamer dependency), so this is acceptable.

Text to speech: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech, ms.date 2026-05-21.

- **Voices list.** `GET https://<resource>.cognitiveservices.azure.com/tts/cognitiveservices/voices/list`, or the regional `https://<region>.tts.speech.microsoft.com/cognitiveservices/voices/list`. Current.
- **Synthesis.** `POST …/cognitiveservices/v1` with an SSML body. MP3 output formats such as `audio-24khz-48kbitrate-mono-mp3` and `audio-48khz-96kbitrate-mono-mp3` are current. A `User-Agent` header is listed as required.
- **Not decided: endpoint form.** The spine and settings do not say whether to use the resource-domain endpoint or the regional one. Bearer tokens are scoped to their issuing host, and `Ocp-Apim-Subscription-Key` works with every endpoint form. It is an adapter-level decision, but `.env.example` will need either `AZURE_SPEECH_REGION` or `AZURE_SPEECH_ENDPOINT`.

## 6. `uvx --from` with a wheel (checked by running it)

- **Local wheel path.** Works. A demo package was built with `uv build --wheel` (uv_build backend), then `uvx --from /abs/path/demo_lab-0.1.0-py3-none-any.whl demo-lab` installed it and ran its console script.
- **Wheel URL.** Works. `uvx --from https://files.pythonhosted.org/.../pyjokes-0.8.3-py3-none-any.whl pyjoke` ran.
- **Not tested.** A GitHub release-asset URL redirects to objects.githubusercontent.com. That should work like any HTTPS URL but was not tried. A private repository would need auth.

## 7. pydantic-settings explicit env file (checked by running it)

With pydantic-settings 2.15.0, pydantic 2.14.0 and Python 3.14:

- `SettingsConfigDict(env_file=<absolute Path>)` loads the file.
- `env_file="~/.config/language-lab/.env"` is **tilde-expanded** (tested with an overridden `HOME`).
- A runtime override with `_env_file=` also works.
- **Constraint 1 (F3): extra keys fail startup.** The default is `extra="forbid"`. Any key in the `.env` file that is not a model field, such as `ANKI_PREFIX` when the model lacks it, raises `extra_forbidden` at startup. AD-18 should choose `extra="ignore"`, or deliberately keep `forbid` and say so.
- **Constraint 2 (F3): list format.** A `list[str]` field such as `OPENROUTER_MODELS` is parsed as **JSON**, so `OPENROUTER_MODELS=["a/b","c/d"]` works. A comma-separated value needs `NoDecode` plus a validator. `.env.example` must show the chosen format.

## 8. Memlog evidence coverage

The memlog has two `(version)` entries:
- Azure limits, Safari format, PyAV wheels;
- the PyPI versions plus the list of AnkiConnect actions.

The claims checked here break down as follows.

| Claim | In memlog with evidence? |
| --- | --- |
| PyPI versions (9 packages), Python 3.14.8 | Yes, dated 2026-10-08 |
| AnkiConnect actions (answerCards, changeDeck, storeMediaFile, sync, saveDeckConfig …) | Yes |
| Azure 30 s limit, WAV 16k mono, prosody en-US only | Yes ("verified on Microsoft Learn 2026-10") |
| PyAV arm64 wheels + bundled FFmpeg | Partly. No Python 3.14 (abi3) check, no macOS 14 minimum, no codec check |
| **REST supports `EnableProsodyAssessment`** | **No.** It says "prosody en-US only" but not that REST exposes it |
| **Azure TTS REST voices list endpoint** | **No** |
| **OpenRouter `models` + `require_parameters` + strict json_schema** | **No.** It appears only as the inherited constraint A4 |
| **GitHub Actions versions (checkout v7, setup-uv v10, action-gh-release v3)** | **No** |
| **`uvx --from <wheel path or URL>`** | **No.** Inherited constraint A1 only |
| **pydantic-settings explicit env file path** | **No** |
| httpx 0.28.1 still current | Yes (in the PyPI list) |

This review has now verified all six "No" items, and they hold. The memlog should still record them so the spine's provenance is complete (F4).

## Findings

| # | Severity | Finding | Suggested action (spine not edited) |
| --- | --- | --- | --- |
| F1 | Medium | **`python-multipart` is missing from the Stack.** FastAPI needs it for `multipart/form-data` (`UploadFile`/`Form`). The spine's convention uses multipart for the Save and Attempt uploads. Plain `fastapi` does not pull it in; only `fastapi[standard]` does. | Add `python-multipart 0.0.32` to the Stack, or pin `fastapi[standard]`. |
| F2 | Medium | **AD-11's strict-schema claim is unconfirmed against Pydantic's output.** Strict `json_schema` needs `additionalProperties:false` everywhere and every property in `required`; Pydantic's default schema does not produce this. Also unconfirmed: what `models` fallback does when a model has no endpoint that supports structured outputs. | Have the OpenRouter adapter (or `domain`) own the transform to a strict schema. Run one live probe of fallback under `require_parameters`. |
| F3 | Low | **AD-18 leaves two pydantic-settings behaviors open:** the default `extra="forbid"` fails startup on unknown `.env` keys, and `list[str]` env values must be JSON. | State `extra` and the format of `OPENROUTER_MODELS` in AD-18 or `.env.example`. |
| F4 | Low | **The memlog has no evidence entries** for REST prosody support, the TTS voices endpoint, the OpenRouter routing parameters, the GitHub Actions versions, `uvx --from` with a wheel, or the pydantic-settings env file. | Add `(version)` lines that cite this review's sources. |
| F5 | Info | **FastAPI 0.143.0 and Pydantic 2.14.0 were both published today** (the 0.143.0 minor bump and the 2.14 GA). They are compatible by declared ranges, but nobody has used them in practice yet. | Keep the pins but expect a patch release soon. Allow lockfile updates for patch versions. |
| F6 | Info | **Platform assumptions are unstated:** the PyAV wheel needs macOS ≥ 14 on the Mac Mini, and AnkiConnect is undated against the installed Anki version. Also untested: a real iOS Safari fMP4 sample, and a GitHub release-asset URL with `uvx`. | Add a note about the macOS minimum. Check these during the first epic's spike. |

## Sources

- PyPI JSON: `https://pypi.org/pypi/{fastapi,uvicorn,pydantic,pydantic-settings,httpx,av,pytest,ruff,uv,python-multipart}/json`, and `/pypi/av/19.0.1/json` for the wheel list
- GitHub releases API: actions/checkout, astral-sh/setup-uv, softprops/action-gh-release, astral-sh/uv, FooSoft/anki-connect
- https://endoflife.date/api/python.json
- https://git.sr.ht/~foosoft/anki-connect/blob/master/README.md and its log
- https://openrouter.ai/docs/guides/routing/model-fallbacks
- https://openrouter.ai/docs/features/provider-routing
- https://openrouter.ai/docs/features/structured-outputs
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-speech-to-text-short
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/rest-text-to-speech
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-pronunciation-assessment
- https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=pronunciation-assessment
- Local runs (scratchpad): PyAV AAC→WAV conversion, `uvx --from` with a wheel path and a wheel URL, pydantic-settings `env_file` with an absolute path and with `~`
