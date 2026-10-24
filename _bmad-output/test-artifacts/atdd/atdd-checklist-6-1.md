---
runScope: "story"
runKey: "story-6-1"
workflowStatus: "completed"
stepsCompleted: ["step-01-preflight-and-context", "step-02-generation-mode", "step-03-test-strategy", "step-04-generate-tests", "step-04c-aggregate", "step-05-validate-and-complete"]
lastStep: "step-05-validate-and-complete"
lastSaved: "2026-10-24"
storyId: "6.1"
storyKey: "6-1"
storyFile: ""
storySource: "_bmad-output/initiative-languagelab-v1/epic-reference-audio/tickets.toml (entry 1)"
atddChecklistPath: "_bmad-output/test-artifacts/atdd/atdd-checklist-6-1.md"
generatedTestFiles:
  - "tests/api/test_reference_audio.py"
  - "tests/e2e/test_draft_audio.py"
  - "tests/integration/test_anki_audio_save.py"
  - "tests/integration/test_azure_speech.py"
inputDocuments:
  - "AGENTS.md"
  - "_bmad/config.toml"
  - "_bmad-output/initiative-languagelab-v1/tickets.toml"
  - "_bmad-output/initiative-languagelab-v1/epic-reference-audio/tickets.toml (entry 1)"
  - "_bmad-output/initiative-languagelab-v1/epic-reference-audio/epic-reference-audio.md"
  - "_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md"
  - "_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md"
  - "_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md"
  - "pyproject.toml"
  - "tests/conftest.py"
  - "tests/README.md"
  - ".agents/skills/bmod-tea/knowledge/data-factories.md"
  - ".agents/skills/bmod-tea/knowledge/component-tdd.md"
  - ".agents/skills/bmod-tea/knowledge/test-quality.md"
  - ".agents/skills/bmod-tea/knowledge/test-healing-patterns.md"
  - ".agents/skills/bmod-tea/knowledge/test-levels-framework.md"
  - ".agents/skills/bmod-tea/knowledge/test-priorities-matrix.md"
  - ".agents/skills/bmod-tea/knowledge/ci-burn-in.md"
acceptanceCriteria:
  - {"id": "AC-1", "idSource": "generated", "text": "Speech synthesis uses the Azure REST adapter with server-side credentials and returns MP3 bytes for the selected locale Voice and Target text."}
  - {"id": "AC-2", "idSource": "generated", "text": "The available Voice list comes from the current Azure catalog and contains only Voices for the requested en-US or fr-CA locale."}
  - {"id": "AC-3", "idSource": "generated", "text": "Each browser persists en-US and fr-CA Voice preferences independently under the AD-13 local-storage keys."}
  - {"id": "AC-4", "idSource": "generated", "text": "POST /api/audio/preview returns a memory-only MP3 Preview without any Anki writes or server-side Preview state."}
  - {"id": "AC-5", "idSource": "generated", "text": "Explicit Preview offers Keep current or Use preview; keeping discards the candidate and ordinary audio=keep Save remains available."}
  - {"id": "AC-6", "idSource": "generated", "text": "After Use preview, multipart Save with audio=replace stores and plays back the exact previewed MP3 bytes without synthesizing again."}
  - {"id": "AC-7", "idSource": "generated", "text": "The backend computes the managed media filename from Prefix, ItemId and the first twelve hex characters of SHA-256 of the received bytes."}
  - {"id": "AC-8", "idSource": "generated", "text": "One shared Anki lock covers storing new media before adding the note and placing its four Cards in the correct Study and Pronunciation decks."}
  - {"id": "AC-9", "idSource": "generated", "text": "GET /api/media/{name} serves saved managed MP3 bytes and rejects non-managed or out-of-Prefix names."}
  - {"id": "AC-10", "idSource": "generated", "text": "Item detail reads expose the saved audio reference for later existing-Item playback."}
  - {"id": "AC-11", "idSource": "generated", "text": "A failed binary multipart Save visibly retains the Draft edits and accepted Preview so retry saves the same candidate."}
  - {"id": "AC-12", "idSource": "generated", "text": "Changing Voice does not automatically synthesize or write Anki; Preview is always an explicit action."}
  - {"id": "AC-13", "idSource": "generated", "text": "A failed Voice-list load shows a recoverable inline error and Try again loads the locale Voices without losing Draft edits."}
  - {"id": "AC-14", "idSource": "generated", "text": "A failed TTS Preview shows a recoverable inline error and retains Draft edits and the prior candidate until an explicit successful retry."}
  - {"id": "AC-15", "idSource": "generated", "text": "A media-store or note-write failure stops later Save steps and preserves the prior note and audio until the note write succeeds."}
  - {"id": "AC-16", "idSource": "generated", "text": "Audio API failures use the existing error envelope and never expose Azure credentials, Target text or MP3 content in browser responses or request logs."}
  - {"id": "AC-17", "idSource": "generated", "text": "Editing Target text after accepting a Preview warns or invalidates the stale candidate so it cannot be mistaken for matching audio."}
---

# ATDD Checklist: Story 6.1 — Preview and save Reference audio from a Draft

## Preflight

Create mode inferred from the explicit story request. Approved high-risk ticket entry 1 in epic 6 is the story source; no leaf story file exists. The registry assigns generated ids in source order from the description and verification clause, supplemented by binding AD-4/5/6/7/13/14/15 and the epic's explicit stale-candidate assumption. No pre-existing checklist for this story.

Stack detection: backend (Python manifest), with a static browser client and Python Playwright. pytest configuration, conftest, local virtual environment and existing API, adapter and browser test infrastructure are available. No epic-6 or system test design was found in test-design/ or the legacy test-artifacts root. Priorities derive from the high-risk byte-integrity, Prefix-isolation and failure-retention contracts.

Playwright-utils and Pact flags are true, but package and runner gates are closed: no package.json, JavaScript Playwright runner or Pact artifacts. Only the seven core/backend knowledge fragments listed in inputDocuments apply. Backend generation mode does not require browser recording. Python browser coverage remains necessary because this story explicitly promises phone and desktop behavior.

Scope: Draft Preview/Save and read/playback contracts. Existing-Item replacement/removal completion belongs to 6.2, refactoring to 6.3, released-wheel human acceptance to 6.4. Follow adopted AD-6 over older broad failure promises: preserve prior values until note-write success, then tolerate repairable partial leftovers without compensation.

## Contract assumptions

Architectural contracts fix POST /api/audio/preview, multipart item plus audioFile, audio=replace and GET /api/media/{name}. Builder-defined Voice-list shape, adapter method signatures, absent/unavailable stored-Voice fallback and saved-reference field shape will be proposed consistently by the workers and recorded here; these are scaffold contracts, not already implemented APIs. Use role/label selectors from EXPERIENCE.md and established Draft helpers. No Azure credentials, real Anki or paid provider calls may be used.

## Generation mode

AI generation from the approved ticket, architecture, UX and existing Python tests. No recording: the new audio UI and routes are not implemented and the backend stack mandates AI generation.

## Test strategy

Primary level: API plus adapter integration. One primary red-phase leaf per declared criterion; no parametrized expansion. Worker A owns AC-1, AC-2, AC-4, AC-6, AC-7, AC-8, AC-9, AC-10, AC-15, AC-16. Worker B owns AC-3, AC-5, AC-11, AC-12, AC-13, AC-14, AC-17. Python Playwright is retained for the story's explicit UI promises despite manifest-based backend detection.

P0: AC-4/6/7/8/9/11/15/16 (byte integrity, writes, isolation, retained edits and secrets). P1: AC-1/2/3/5/10/12/13/14/17. Each first assertion isolates the promised result; transition tests actually perform the transition. No fake passing assertions, unconditional failures or tests asserting the absence of production behavior. API setup responses stay opaque before the criterion assertion. Missing future modules/methods must resolve inside an observed action so a direct criterion assertion owns the failure; record any Python browser limitation honestly.

Scaffolds use reasoned module skips (pytest equivalent of test.skip) until task activation. Temporary activation in validation confirms RED and restores skips before commit. Reuse existing collection, locks, codec, settings, HTTP replay and Draft screen helpers. New synthetic Azure HTTP fixtures must be explicitly labelled documented-contract examples, never claimed as captured real Azure recordings. Real Azure fixture capture is a green-phase/released-wheel evidence task.

Additional branches for green phase: both locales and Categories at phone/tablet/desktop widths; invalid/missing/stale/foreign Voice, escaped SSML, absent/unavailable preference fallback; empty/oversized/malformed binary uploads; no auto-play and Blob URL cleanup on navigation; Setup gate and Prefix guard on media writes; same-hash existing-media behavior and post-note failures in 6.2; live-provider fixture comparison and device evidence in 6.4.

## Execution mode

Config auto, capability probing enabled. Tool inspection confirms subagent launch capability; no dedicated agent-team runtime. Resolved mode: subagent. The skill explicitly dispatches API/adapter and browser workers in parallel. Node-only Playwright-utils/Pact mandates are inapplicable because packages and runners are absent.

## Generated scaffolds and coverage

17 primary leaves: 6 API, 4 adapter integration, 7 browser. All carry reasoned module skips;
activate only the current task. No component/unit files are needed for this primary mapping.
Each criterion has exactly one leaf, with its id in the first docstring line (Python title
adaptation). Secondary branches remain green-phase work rather than duplicate skipped leaves.

| Criterion | Primary scaffold |
| --- | --- |
| AC-1 | `tests/integration/test_azure_speech.py::test_synthesis_returns_the_azure_mp3_and_escapes_ssml` |
| AC-2 | `tests/integration/test_azure_speech.py::test_each_voice_read_filters_the_new_current_catalog` |
| AC-3 | `tests/e2e/test_draft_audio.py::test_locale_voice_preferences_survive_new_drafts_and_are_browser_local` |
| AC-4 | `tests/api/test_reference_audio.py::test_preview_returns_memory_only_mp3_without_anki_writes` |
| AC-5 | `tests/e2e/test_draft_audio.py::test_keep_current_discards_the_preview_and_save_uses_the_keep_intent` |
| AC-6 | `tests/api/test_reference_audio.py::test_save_uploads_the_exact_preview_and_playback_returns_the_same_bytes` |
| AC-7 | `tests/api/test_reference_audio.py::test_save_computes_the_managed_name_from_received_bytes` |
| AC-8 | `tests/integration/test_anki_audio_save.py::test_one_lock_stores_media_before_the_note_and_four_card_placements` |
| AC-9 | `tests/api/test_reference_audio.py::test_media_route_plays_managed_audio_and_refuses_foreign_names` |
| AC-10 | `tests/api/test_reference_audio.py::test_item_detail_exposes_the_saved_reference_filename` |
| AC-11 | `tests/e2e/test_draft_audio.py::test_failed_binary_save_retains_the_candidate_and_retry_sends_the_same_bytes` |
| AC-12 | `tests/e2e/test_draft_audio.py::test_changing_voice_keeps_the_candidate_until_an_explicit_new_preview` |
| AC-13 | `tests/e2e/test_draft_audio.py::test_voice_catalog_failure_can_retry_without_losing_draft_edits` |
| AC-14 | `tests/e2e/test_draft_audio.py::test_failed_preview_retains_the_prior_clip_and_explicit_retry_can_replace_it` |
| AC-15 | `tests/integration/test_anki_audio_save.py::test_failed_note_write_retains_previous_values_and_stops_cleanup` |
| AC-16 | `tests/api/test_reference_audio.py::test_failed_audio_request_has_a_safe_envelope_and_content_free_logs` |
| AC-17 | `tests/e2e/test_draft_audio.py::test_target_edit_warns_that_the_accepted_candidate_no_longer_matches` |

Generated file sizes:

- `tests/api/test_reference_audio.py`: 218 lines.
- `tests/e2e/test_draft_audio.py`: 268 lines.
- `tests/integration/test_anki_audio_save.py`: 91 lines.
- `tests/integration/test_azure_speech.py`: 84 lines.

## Supporting factories, fixtures and mocks

- `tests/support/audio.py`: known binary clips, per-test UUID callers, preview request and
  multipart factories with overrides, independently computed expected AD-7 names, allowed-host
  app client, and `MediaRig`. The rig composes the real guarded/gated Anki adapter and shared
  observed lock with a byte-aware external HTTP double; it implements no product Save logic.
- `tests/support/azure.py`: httpx MockTransport replay and calls into the future real Azure
  adapter. Two catalog responses exercise freshness across a provider change.
- `tests/fakes/speech.py`: proposed in-memory Speech fake, to align with the new port during
  implementation. Future Voice imports resolve inside methods, so skipped collection works.
- `tests/support/audio_screen.py`: per-page API doubles, accessible locators, actual native
  player's Blob-byte inspection, and MIME-aware multipart capture. Every page/context is
  created and cleaned by existing pytest-playwright fixtures. Collections and media maps are
  per-test objects; no external cleanup or credentials are required.
- `tests/fixtures/azure/catalog-example.json`: synthetic mixed-locale provider schema.
  `preview.mp3` and `second-preview.mp3`: locally generated valid 24 kHz mono silent MP3s.
  Their README identifies provenance, Microsoft sources and pending real-provider comparison.

Three mocked boundaries: Speech at API level, Azure REST at adapter level, and AnkiConnect
via the collection/media replay. Browser doubles cover Voice GET, Preview POST and multipart
Save POST and return the standard AD-15 error envelope on failure. No live provider calls,
new dependencies, authentication flows or fixture registrations.

## Proposed contracts and UI selectors

- `GET /api/audio/voices?locale=en-US` → `{voices:[{name,locale,displayName}]}`; `name`
  corresponds to Azure ShortName. Only en-US/fr-CA are in scope. Fallback for missing or
  unavailable stored Voices remains a builder decision.
- `POST /api/audio/preview` JSON `{language,voice,target}` → `audio/mpeg` bytes with
  `Cache-Control: no-store`; browser keeps a Blob and server retains no Preview session.
- Existing `POST /api/items/{lang}` takes multipart `item` JSON with `audio=replace` plus
  `audioFile`; ignore client filenames and compute the AD-7 name from received bytes.
  Existing `audio=keep` remains supported without an audioFile.
- `GET /api/media/{name}` returns managed audio bytes and refuses invalid or foreign Prefix
  names before media retrieval. `GET /api/items/{lang}/{itemId}` adds `audio: filename|null`
  as saved read metadata. Keep ItemContent independent of transport metadata.
- Proposed Python interfaces: `AzureSpeech(key, region, transport=...)`, `voices(locale)`,
  `synthesize(locale, voice, target)`, `aclose()`; `create_app(..., speech=...)`;
  `save_item(..., audio=AudioIntent.REPLACE, audio_bytes=...)`. Align port/fake/adapter
  together. Remove test helper signature compatibility detection after wiring exists.
- No data-testid attributes required. Scope to accessible region `Reference audio`, Voice
  combobox, explicit Preview, Keep current, Use preview, and Play audio preview. The native
  audio element has no implicit ARIA role, so its tag is used only for byte probes. Audio
  region naming, Preview action, TTS Try again and Draft stale warning are proposed scaffold
  choices; the builder may select equivalent behavior and update the affected contract.
- Preferences use only `languagelab.voice.en-US` and `languagelab.voice.fr-CA`. A Draft,
  ItemId, text and Blob must not enter storage or history.state. Two browser contexts test
  preference independence without pinning the unspecified initial fallback.

## Implementation checklist

- [ ] AC-1: add domain Voice/Speech, a matching fake and the httpx Azure REST adapter with
  server credentials, escaped SSML and MP3 output; close its client in app lifespan.
- [ ] AC-2: fetch Azure's current catalog and filter exact locale on each read. Add the
  voices route and normalize ShortName/Locale/DisplayName for the client.
- [ ] AC-3: implement voice-pref.js as the only localStorage owner, with independent locale
  keys; keep Draft/Preview in screen memory. Revisit unavailable preference fallback.
- [ ] AC-4: add Audio service/Preview route returning binary no-store responses; synthesize
  outside the Anki lock, with zero Anki writes and no retained server Preview state.
- [ ] AC-5: add explicit audio comparison controls to Draft; Keep current discards the
  candidate and preserves ordinary keep Save, without writing Anki during comparison.
- [ ] AC-6: carry the accepted Blob through shared api.js multipart Save; store and return
  precisely those bytes, with no re-synthesis or lossy conversion.
- [ ] AC-7: compute SHA-256 from the uploaded bytes, derive Prefix/ItemId/hash media names,
  ignore supplied filenames and write exactly `[sound:<name>]` to the Audio field.
- [ ] AC-8: extend the AnkiStore port/fake/adapter use case under one shared lock: store
  media, write note, then move new ord-0/1/2 Cards to Study; ord-3 stays Pronunciation.
- [ ] AC-9: expose guarded read-only media playback; reject non-managed and foreign Prefix
  names before retrieval, return MP3 bytes and keep reads independent of the write gate.
- [ ] AC-10: decode saved Audio references and expose the read metadata required by 6.2;
  preserve existing Item content/list/duplicate contracts and reads without audio.
- [ ] AC-11: extend shared api.js binary handling with the existing envelope; retain edits,
  accepted Blob and ItemId after Save failure, then retry with identical multipart audio.
- [ ] AC-12: Voice changes update preference only; make Preview the sole synthesis trigger.
- [ ] AC-13: show inline Voice-list failure and Try again without losing Draft edits.
- [ ] AC-14: show inline TTS failure; keep the prior candidate and edits until explicit retry
  succeeds and the user accepts the new candidate.
- [ ] AC-15: stop on media-store/note-write failure without compensation; keep prior values
  until note-write success, tolerate orphan media and retain existing Setup repair behavior.
- [ ] AC-16: use AD-15 codes and content-free messages/logs; never return/log the Azure key,
  Target text, audio bytes or base64. Include credentials/body/header leak checks.
- [ ] AC-17: track the Target used for the candidate; warn or invalidate after Target edits.
  The scaffold chooses the documented warning; equivalent invalidation is allowed by epic.

Green-phase expansions: both locales/Categories and responsive widths; actual Play interaction
and no autoplay; Blob URL revocation on reject/replace/unmount; missing/foreign/stale Voices;
SSML/locale/voice validation, empty/oversized/malformed uploads; media-store failure before note,
Setup-required and out-of-Prefix writes; missing media; binary API network errors. Existing-Item
replacement/remove and same-hash/post-note cleanup completion belong to 6.2. Capture sanitized
real Azure and Anki media replies and device/wheel evidence in implementation/6.4; synthetic
fixtures do not satisfy that evidence. No human acceptance record is closed by this run.

Implementation sizing remains the approved high-risk story; this ATDD run does not estimate
implementation hours. Refactor only after active tests pass; retain existing Item Save/Delete,
Draft generation and Setup/media repair regressions.

## Activation and downstream handoff

There is no leaf story file to update. Pass `epic-reference-audio/tickets.toml` entry 1,
this checklist and generatedTestFiles to the implementation workflow. Remove the module skip
only while implementing its file, or replace it with equivalent reasoned per-test skips so
only the current task is active. Confirm RED, implement minimal behavior, confirm GREEN,
then refactor and commit passing tests. Update scaffold contracts if the builder records a
compatible alternative. Story completion is separate from ATDD completion.

```sh
.venv/bin/pytest tests/api/test_reference_audio.py tests/integration/test_azure_speech.py tests/integration/test_anki_audio_save.py tests/e2e/test_draft_audio.py -q
.venv/bin/pytest tests/e2e/test_draft_audio.py --headed -q
PWDEBUG=1 .venv/bin/pytest tests/e2e/test_draft_audio.py -k failed_binary_save
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

## Validation limits

Python sync Playwright cannot put the complete journey inside JavaScript's outer promise
matcher. The six new-control journeys currently stop at missing Voice/Preview controls before
later state assertions. The Voice-error journey can directly fail at its inline alert assertion.
Re-observe every later transition during implementation; current RED is not evidence that
those later controls/handlers already work. API/adapter actions directly assert missing status,
bytes, saved reference, media name, write sequence or error code; no placeholder failures.

Memory-only server behavior is supported by no-store/absence-of-writes and no session design,
not a complete heap/disk audit. Browser bytes are checked at the actual Blob player and outgoing
multipart boundary; browser doubles do not prove real Azure or Anki behavior.


## Validation and completion — 2026-10-24

- Registry and static leaf validation passed: 17 generated ids, exactly one primary leaf
  per id; 8 P0 and 9 P1. Both worker registries match the persisted registry exactly.
- Initial normal collection: 17 skipped, no errors. Final normal run with relevant Save
  and Draft regressions: **45 passed, 17 skipped**, no failures or errors (3.35 seconds).
- Temporary activation: **17 failed, 0 passed, 0 skipped, 0 errors** (6.61 seconds).
  A temporary pytest plugin removed collected skip markers without editing source. Its
  browser timeout was 2 seconds for probing missing controls; normal suite timeouts remain.
- API Preview/error first fail at 405 versus 200/502; media playback at 404 versus 200;
  saved reference/name/bytes are absent. Azure adapter imports and the audio_bytes Save
  extension are missing and observed inside actions, so assertions own adapter RED.
  Six browser journeys fail at the missing Voice selector; Voice-list error directly
  fails at the missing inline alert. Later transitions remain unobserved as noted above.
- Ruff check and format check passed across the repository (318 Python files); diff
  whitespace check passed. Both binary fixtures decode as 24 kHz MP3 with 3456 and 5760
  samples respectively. Existing upstream Starlette/httpx deprecation warnings remain.
- Machine-readable criterion mapping and compact execution evidence:
  `atdd-validation-6-1.json`. Raw local traces/JUnit are under ignored test-results/;
  pytest-playwright resets that directory between browser runs. Durable evidence is the
  compact validation artifact. Worker temporary source copies are not release evidence.
- Proposed TTS upstream-failure status is **502**, consistent with existing LLM failure
  handling and browser doubles. AD-15 already defines the fixed tts_failed message.

ATDD scaffolding is complete; Story 6.1 implementation remains pending. Next: bmad-build
with this checklist and epic-reference-audio/tickets.toml entry 1. The invoked ATDD
workflow is committed directly to main and pushed per AGENTS.md; no PR is required here.
