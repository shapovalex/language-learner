---
runScope: "story"
runKey: "story-7-2"
workflowStatus: "completed"
stepsCompleted: ["step-01-preflight-and-context", "step-02-generation-mode", "step-03-test-strategy", "step-04-generate-tests", "step-04c-aggregate", "step-05-validate-and-complete"]
lastStep: "step-05-validate-and-complete"
lastSaved: "2026-10-25"
storyId: "7.2"
storyKey: "7-2"
storyFile: ""
storySource: "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/tickets.toml (entry 2)"
atddChecklistPath: "_bmad-output/test-artifacts/atdd/atdd-checklist-7-2.md"
generatedTestFiles: ["tests/api/test_pronunciation_attempt.py", "tests/integration/test_attempt_audio.py", "tests/integration/test_azure_assessment.py", "tests/e2e/test_pronunciation_attempt.py"]
inputDocuments: ["AGENTS.md", "_bmad/config.toml", "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/tickets.toml", "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/epic-pronunciation-review.md", "_bmad-output/initiative-languagelab-v1/epic-pronunciation-review/research-azure-assessment/findings.md", "_bmad-output/initiative-languagelab-v1/architecture-languagelab/architecture-languagelab.md", "_bmad-output/initiative-languagelab-v1/prd-languagelab/prd-languagelab.md", "_bmad-output/initiative-languagelab-v1/prd-languagelab/addendum.md", "_bmad-output/initiative-languagelab-v1/ux-languagelab/EXPERIENCE.md", "pyproject.toml", "tests/README.md", "tests/conftest.py", "tests/e2e/conftest.py", ".agents/skills/bmod-tea/knowledge/data-factories.md", ".agents/skills/bmod-tea/knowledge/component-tdd.md", ".agents/skills/bmod-tea/knowledge/test-quality.md", ".agents/skills/bmod-tea/knowledge/test-healing-patterns.md", ".agents/skills/bmod-tea/knowledge/test-levels-framework.md", ".agents/skills/bmod-tea/knowledge/test-priorities-matrix.md", ".agents/skills/bmod-tea/knowledge/ci-burn-in.md", "tests/support/pronunciation_screen.py", "tests/support/azure.py", "tests/support/audio.py", "tests/support/anki_state.py", "tests/fixtures/azure-assessment/manifest.json", "_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-Review.dc.html", "_bmad-output/initiative-languagelab-v1/ux-languagelab/mockups/S-iPadReview.dc.html"]
acceptanceCriteria: [{"id": "AC-1", "idSource": "generated", "text": "Recording uses MediaRecorder and shows the Listening pill and a live level meter."}, {"id": "AC-2", "idSource": "generated", "text": "Microphone denial or unavailability shows the mic-blocked warning; Reference still plays and the Card remains unanswered."}, {"id": "AC-3", "idSource": "generated", "text": "The recorder auto-stops at 30 seconds and submits the Attempt."}, {"id": "AC-4", "idSource": "generated", "text": "Attempt uploads above the 5 MB cap are refused before assessment."}, {"id": "AC-5", "idSource": "generated", "text": "One Attempt request reads Target text from Anki by itemId, assesses that trusted text and never writes Anki."}, {"id": "AC-6", "idSource": "generated", "text": "Native MP4/AAC and WebM/Opus recordings convert in memory with PyAV, without numpy, to 16 kHz mono PCM WAV."}, {"id": "AC-7", "idSource": "generated", "text": "Azure scripted assessment uses REST and returns en-US flat NBest overall, word, IPA phoneme and prosody scores."}, {"id": "AC-8", "idSource": "generated", "text": "fr-CA Assessment retains overall and word scores and start/middle/end positions computed from phoneme order, without phoneme labels or prosody."}, {"id": "AC-9", "idSource": "generated", "text": "HTTP 200 all-Omission Azure feedback is a nothing-heard result rather than a usable Assessment or provider failure."}, {"id": "AC-10", "idSource": "generated", "text": "Nothing heard shows Couldn't hear that Attempt / Record again closer to the microphone. and Record again, keeping the Card unanswered and Rating disabled."}, {"id": "AC-11", "idSource": "generated", "text": "The latest en-US Assessment renders the score ring, sub-scores, word pills and a selectable weak-word panel with IPA and non-color feedback cues."}, {"id": "AC-12", "idSource": "generated", "text": "fr-CA feedback renders only overall/word/position feedback and the Prosody isn't available. note, never a named French sound."}, {"id": "AC-13", "idSource": "generated", "text": "Unlimited Try again retries start recording immediately; Reference is disabled while recording and Checking… is shown while assessing."}, {"id": "AC-14", "idSource": "generated", "text": "Ratings start disabled, enable after one usable Assessment on the Card, stay enabled during later assessments, and no score selects or suggests a Rating."}, {"id": "AC-15", "idSource": "generated", "text": "Assessment failure shows Record again / Exit and the specified error copy with the Card current and unanswered and no Rating preselected."}, {"id": "AC-16", "idSource": "generated", "text": "After a Rating or leaving review the recording Blob and Assessment are dropped and microphone tracks and object URLs are released."}, {"id": "AC-17", "idSource": "generated", "text": "Uploads whose decoded duration exceeds 30 seconds are refused before Azure assessment."}, {"id": "AC-18", "idSource": "generated", "text": "Attempt success and failure logs contain no audio, scores or Target text."}]
---

# ATDD Checklist: Story 7.2 — Record Attempts and show Azure feedback per locale

## Preflight

Create mode inferred from the explicit story request. Approved ticket entry 2 is the source;
there is no leaf story file. Prerequisite 7.1 is implemented on main. Working tree was clean.
No epic-7 or system test design exists under test-design/ or the legacy artifacts root.
Priorities derive from the high-risk ticket, AD-14/AD-15 and FR-31–FR-35.

Stack: backend manifest with a static browser client and Python pytest-playwright. Browser
coverage is required by this story. No Node runner or package.json exists; playwright-utils
and Pact flags are true but package/runner/relevance gates are closed. No contract tests.
The seven core/backend knowledge fragments are listed in inputDocuments.

Criterion ids are generated in source order from ticket description, then verify clause.
Existing privacy middleware and scheduling remain regression coverage; new tests exercise
the Attempt-specific path. This run covers exactly story-7-2.

## Generation mode

AI generation from approved requirements, implemented 7.1 patterns and real probe fixtures.
No recording session is needed for the backend stack; new controls do not exist yet.

## Test strategy

Exactly one primary scaffold per criterion, with native-format parametrization for AC-6.
Transition criteria exercise the transition. First assertions isolate the promised value;
setup responses remain opaque until that assertion. New leaves stay explicitly skipped
until story implementation. Secondary branches belong to green-phase automation.

| Criterion | Level | Priority |
| --- | --- | --- |
| AC-1 | e2e | P1 |
| AC-2 | e2e | P0 |
| AC-3 | e2e | P0 |
| AC-4 | api | P0 |
| AC-5 | api | P0 |
| AC-6 | integration | P0 |
| AC-7 | integration | P0 |
| AC-8 | integration | P0 |
| AC-9 | integration | P0 |
| AC-10 | e2e | P0 |
| AC-11 | e2e | P1 |
| AC-12 | e2e | P0 |
| AC-13 | e2e | P1 |
| AC-14 | e2e | P0 |
| AC-15 | e2e | P0 |
| AC-16 | e2e | P0 |
| AC-17 | api | P0 |
| AC-18 | api | P0 |

## Execution and generated scaffolds

Requested mode auto, capability probe enabled. The harness supports subagents but no separate
agent-team interface; resolved subagent mode. Step 4 explicitly authorizes parallel API and
browser workers. Both worker registries match the saved registry exactly. No library deviations:
Python runner/package gates are closed. Both worker outputs are valid RED-phase JSON.

18 functions, 20 parametrized cases: 4 API, 5 integration, 11 browser. Every new test module
has a reasoned skip until its implementation task is activated. Exactly one function per
criterion; AC-6 has MP4 and WebM cases, AC-16 has Rating and navigation disposal cases.
Five probe fixtures are byte-exact copies with SHA-256 and source paths in manifest.json.

| Criterion | Primary scaffold |
| --- | --- |
| AC-1 | `tests/e2e/test_pronunciation_attempt.py::test_recording_shows_listening_and_a_live_level_meter` |
| AC-2 | `tests/e2e/test_pronunciation_attempt.py::test_denied_microphone_warns_without_answering_and_reference_still_plays` |
| AC-3 | `tests/e2e/test_pronunciation_attempt.py::test_recording_autostops_at_thirty_seconds_and_uploads_the_native_blob` |
| AC-4 | `tests/api/test_pronunciation_attempt.py::test_oversize_attempt_is_refused_before_assessment` |
| AC-5 | `tests/api/test_pronunciation_attempt.py::test_attempt_uses_the_target_read_from_anki_and_never_writes_it` |
| AC-6 | `tests/integration/test_attempt_audio.py::test_native_recording_becomes_16khz_mono_pcm_without_numpy` |
| AC-7 | `tests/integration/test_azure_assessment.py::test_english_flat_nbest_reply_keeps_ipa_and_prosody` |
| AC-8 | `tests/integration/test_azure_assessment.py::test_french_empty_phoneme_labels_become_positions_only` |
| AC-9 | `tests/integration/test_azure_assessment.py::test_success_with_every_word_omitted_is_nothing_heard` |
| AC-10 | `tests/e2e/test_pronunciation_attempt.py::test_nothing_heard_warns_and_does_not_unlock_rating` |
| AC-11 | `tests/e2e/test_pronunciation_attempt.py::test_english_feedback_shows_latest_score_and_selectable_word_detail` |
| AC-12 | `tests/e2e/test_pronunciation_attempt.py::test_french_feedback_shows_positions_without_naming_a_sound` |
| AC-13 | `tests/e2e/test_pronunciation_attempt.py::test_try_again_records_immediately_and_reference_is_disabled_until_assessing` |
| AC-14 | `tests/e2e/test_pronunciation_attempt.py::test_rating_unlocks_after_assessment_and_stays_enabled_during_the_next` |
| AC-15 | `tests/e2e/test_pronunciation_attempt.py::test_assessment_failure_offers_record_again_or_exit_without_answering` |
| AC-16 | `tests/e2e/test_pronunciation_attempt.py::test_rating_or_leaving_releases_recording_and_clears_assessment` |
| AC-17 | `tests/api/test_pronunciation_attempt.py::test_overlong_decoded_attempt_is_refused_before_azure` |
| AC-18 | `tests/api/test_pronunciation_attempt.py::test_attempt_success_and_failure_logs_exclude_audio_scores_and_target` |

## Proposed contracts

These are scaffold choices for new code, amendable together with the tests; no production
code is introduced in this run.

- `POST /api/pronunciation/{lang}/attempt`: multipart `itemId` and `recording`, no client
  Target; 200 `{assessment, nothingHeard}`; nothing heard is `{assessment: null,
  nothingHeard: true}`. Oversize: 413 `payload_too_large`; decoded >30 s: 422
  `validation_failed`; provider failure: 503 `assessment_failed`, all via AD-15.
- `Speech.assess(locale, target, wav) -> Assessment | None`; the Azure adapter uses the
  regional STT REST endpoint, escaped/base64 JSON assessment header, IPA/prosody for English
  only. None means all-Omission. The injected replay must cover the new STT host too.
- `domain.pronunciation.Assessment` supports Pydantic TypeAdapter validation and `.wire()`.
  Fields: locale, overall, accuracy, fluency, completeness, nullable prosody, words. Each
  word: text, score, errorType, phonemes[{symbol,score}], nullable positions{start,middle,end}.
  French phonemes are empty, prosody null; English positions null.
- French aggregation scaffold choice (documents do not prescribe the formula): index i of n
  goes to `min(2, floor(3*i/n))`, minimum score per bucket. Scores [100,17,0,0,0] yield
  start17/middle0/end0. Builder defines empty buckets and expands short-word boundaries.
- `features.pronunciation.audio.to_wav(bytes) -> bytes`: in-memory PyAV conversion,
  16 kHz mono s16 WAV, no numpy or external ffmpeg process.
- Accessible browser controls: Record / Listening… tap to stop / Try again / Checking…;
  meter named Microphone level with changing value; label Overall score; sub-score labels
  Accuracy, Fluency, Completeness, Prosody; region Word feedback; word buttons named by word.
  Warning and error copy is pinned to EXPERIENCE.md and ticket entry 2.

## Supporting infrastructure

`tests/support/assessment.py` supplies the real guarded Anki adapter rig, test-owned Speech
extension, WAV inspection, a 31-second compressed Opus upload, and lazy observed imports.
`tests/support/attempt_screen.py` composes ReviewApi with per-page Attempt outcomes and a
multipart observer. `fake_microphone.js` supplies real AudioContext streams and deterministic
MediaRecorder events containing copied MP4/WebM bytes. It records scalar stream/URL lifecycle
counts and controls analyser levels; the real screen owns all actions and state changes.
Browser doubles do not call Azure. No runtime test reads fixtures from planning documents.

## Implementation checklist and task activation

- [ ] AC-4/5/17/18: add the multipart Attempt route, read the Item through the scoped AnkiStore,
  validate size and decoded duration, invoke injected Speech, return AD-15 envelopes; no
  Anki write, disk persistence, Target/audio/score logging or client-supplied reference text.
- [ ] AC-6: implement bounded PyAV conversion and flush the resampler; keep numpy absent.
- [ ] AC-7/8/9: extend Speech, its fake and AzureSpeech together; normalize real flat NBest
  replies in domain Assessment, apply French position shaping and all-Omission detection.
- [ ] AC-1/2/3: add recording, mic-blocked handling, live level meter, 30-second auto-stop
  and client size guard; release microphone resources on every stop/error/leave path.
- [ ] AC-10/11/12: render the nothing-heard warning, latest score ring/subscores/word pills,
  weakest word and selectable details with non-color cues; no French sound names.
- [ ] AC-13/14/15: retry immediately without Reference autoplay; disable Reference during
  recording; Checking during assessment; unlock Ratings only after a usable result on this
  Card and retain that eligibility during later attempts; scores never select a Rating.
  Assessment failure offers Record again / Exit and preserves the unanswered Card.
- [ ] AC-16: clear the Blob and Assessment after successful Rating and unmount, stop tracks,
  revoke created URLs, ignore late results from a previous Card/screen, reset the next gate.
- [ ] Adapt existing 7.1 Rating browser tests to establish a usable Attempt before Rating;
  retain their scheduler, retry, next-Card and Rating-failure assertions.

Remove the module skip only for the current task, observe RED, implement, observe GREEN,
then refactor. No leaf story file exists, so hand off ticket entry 2, this checklist and
`generatedTestFiles` to bmad-build. Do not mark the story implemented from these scaffolds.

```sh
uv run pytest tests/api/test_pronunciation_attempt.py tests/integration/test_attempt_audio.py tests/integration/test_azure_assessment.py tests/e2e/test_pronunciation_attempt.py -q
uv run pytest tests/e2e/test_pronunciation_attempt.py --browser webkit -q
uv run ruff check src tests
uv run ruff format --check src tests
```

## Green-phase expansion and validation limits

Expand locale/lang mismatch and unknown Item cases; all-Omission HTTP mapping; Azure 401,
429, timeout, malformed/empty reply, provider message redaction; exact 5 MB and 30-second
boundaries, corrupt/unrecognized recordings, stereo/non-16kHz inputs; short French words and
empty buckets; lower phoneme scores on otherwise good words; silence/failure after an earlier
usable Assessment; stopping Reference on Record; size cap in the browser; disconnect/abort
cleanup and stale in-flight replies on navigation; score ring color stability and boundary
feedback steps 59/60/79/80; release-wheel tests and live device acceptance in 7.4.

Every browser test asserts `observe_journey(journey) is None` around the complete sequence.
The helper returns a failed navigation, locator or exact UI assertion as an exception value
without retrying or swallowing it; this is the synchronous equivalent of an outer promise
assertion. Missing Record controls still prevent reaching later transitions, which must be
re-observed after implementation. The microphone double proves screen API use and lifecycle, not browser
encoding or real Safari permission. Native codec conversion is covered separately. Heap Blob
and Assessment reachability cannot be proven through UI: inspect closure cleanup during build
and perform released-device acceptance. URL/track/visible-state checks alone do not prove
complete memory erasure. No production debug state is added to claim it.

## Checklist applicability

Primary level: E2E for recording and feedback interactions, with API and integration for
trusted inputs, upload limits, provider shaping and codec conversion. Component/unit additions
are N/A for these primary scaffolds; no component harness is installed. Python's pyproject.toml,
conftest and pytest-playwright satisfy the framework prerequisites; Node configuration,
TypeScript, faker and JS merged fixtures are N/A. UUID factories isolate Items and Cards;
recorded provider values are intentionally fixed requirements. No data-testid additions are
needed; accessible role/name/label contracts are listed above. No login/auth fixtures apply.

Setup/action/outcome are separated in each test, with one criterion concern per function and
exact outcome assertions. Temporary worker files use mandated /tmp names with run identity;
retained results are consolidated in atdd-validation-7-2.json. No recording CLI session was
opened. Playwright browsers and streams used during validation are closed by their fixtures.
Implementation effort is not estimated here; the source ticket classifies the story high risk.

## Validation and completion — 2026-10-25

- Registry/static validation: 18 primary functions for 18 generated ids, one id per function;
  15 P0 and 3 P1 functions, 20 cases including the native-format and disposal parameters.
- Normal run: **20 skipped**, no collection errors. Each skip names story/task activation.
- Scratch activation: **20 failed, 0 passed, 0 errors**. API/integration failures reach their
  exact first assertions: missing trusted Target, 405 instead of 413/422/[200,503], absent
  sample rate/overall/positions, or missing assess() instead of the all-Omission None result.
- Browser refinements were activated again: **11 failed** at the complete journey's outer
  assertion, which observes the missing Record control. Later feedback, gate and cleanup
  transitions remain unobserved until implementation; this RED run does not prove them.
- Regressions: unit/API/integration **919 passed, 9 skipped** (the new backend cases);
  existing pronunciation review, navigation and Item audio browser checks **81 passed**.
  Total existing tests passing: **1,000**.
- Fixture sanity: both native clips decode to 2.03 seconds; generated long Opus is 31 seconds
  and 14,642 bytes. Independently exercised microphone setup, meter reads, recorder events,
  exact payload bytes, track shutdown and URL revocation for MP4 and WebM; no page errors.
- Ruff lint/format passed across src/tests; git diff whitespace check passed. Parent validation
  sorted one local helper import and added the synchronous outer journey assertion.
- Retained machine-readable mapping and execution evidence: `atdd-validation-7-2.json`.

ATDD is complete; story implementation remains pending. Next workflow: bmad-build using
entry 2 and this checklist. Repository instruction: commit this ATDD work on main and push.
