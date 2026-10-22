---
title: 'Tracer: save a Capture from the Captures screen'
type: 'feature'
ticket: '1'
created: '2026-10-22'
status: 'built'
baseline_revision: 'aed70b9e62f45a60ce61fa804a8deb221a801b77'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-3-1.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** You can't save a Capture yet. The Captures screen shows only its heading, and neither the AnkiStore nor the API can create a Capture note.

**Approach:** Cut one slice through every layer: `AnkiStore.create_capture` (port, AnkiConnect adapter and fake), `POST /api/captures`, and the compose box on the Captures screen. Make the 29 red-phase ATDD cases from commit aed70b9 pass.

## Boundaries & Constraints

**Always:**
- Hold the Anki lock once for the whole create. Send every Anki call through `client.invoke`, so the Prefix guard and the setup gate both apply.
- The CaptureId lookup sends only `note_query(manifest, "<Prefix> Capture")`, then `notesInfo`. It matches `decode_field(CaptureId).strip()` in Python. Neither the CaptureId nor the text ever goes into a query (AD-4).
- Write every field through `encode_field`. Write `CreatedAt` as `YYYY-MM-DDTHH:MM:SSZ` in UTC.
- The server sets `created_at` (`datetime.now(UTC)`, no microseconds). Text is stored exactly as typed.
- The browser generates the CaptureId with `crypto.randomUUID()`, once per composition.

**Never:**
- Write through `invoke_setup`, or add a `nid:` scope to the query builder.
- Build an error message from upstream text (AD-15).
- Show the Captures list (entry 2), detail, or delete. Add Capture search.
- Report a Capture as saved when the save failed.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| New Capture | Unknown UUIDv4, text | `addNote` to `<Prefix>::Captures` with `allowDuplicate: true`, then `suspend` its cards; 201 `{captureId, text, createdAt}` | — |
| Retry | CaptureId already stored (plain or in editor markup) | The stored Capture, decoded; no write; 201 | — |
| Same text, other id | Another Capture has this Text | A second note (allowDuplicate) | — |
| Blank text / bad id | `""`, whitespace, missing; uppercase, v1, unhyphenated, non-UUID, missing id | 422 `validation_failed`; store not called | Envelope only |
| Gated Anki | SetupState not `ready` | 409 `setup_required`; no write | Gate raises before addNote |
| Anki failing | Down, or `addNote` errors | 503 `anki_unavailable`; no `suspend` | — |
| Suspend fails | `addNote` ok, `suspend` errors | `anki_unavailable`; the note is left unsuspended (tolerated AD-6 leftover, fixed by Setup repair) | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/captures.py` (new) -- `Capture(capture_id: str, text: str, created_at: datetime)`, a frozen dataclass in the style of `domain/sync.py`.
- `src/language_lab/ports/anki_store.py` -- add `create_capture(capture_id, text, created_at) -> Capture` and its docstring. Update the module docstring's list of use cases.
- `src/language_lab/adapters/anki/store.py` -- `AnkiConnectStore`. Reuse `_require_manifest`, `self._lock.hold()`, `note_query`, `encode_field`/`decode_field`, `SCHEMA_VERSION_FIELD`, and `manifest.card_deck(name, 0)` for the deck. AnkiConnect answers `{}` for a deleted note; skip it, as `setup_gate.read_note_versions` does. The new note's card ids come from `notesInfo([new_id])[0]["cards"]`. Reject malformed replies with `AppError(ANKI_UNAVAILABLE)`. The guard already permits `addNote` (managed deck and model) and `suspend` (cards of managed notes). The gate computes an unknown state on demand. Don't change guard.py, setup_gate.py or query.py.
- `src/language_lab/features/captures/{__init__,service,routes}.py` (new) -- mirror `features/setup/routes.py`. `CaptureService(anki)` stamps `created_at`. `captures_router(service)` serves POST `/api/captures`, status 201, and takes a pydantic body with camelCase aliases.
  - Validation in pydantic: `captureId` must fullmatch the lowercase UUIDv4 regex (as `guard._UUID4`), and `text` must be non-blank after strip. A failure becomes `RequestValidationError`, which `app._on_validation_error` already turns into the 422 envelope.
  - The response is `{captureId, text, createdAt}`.
- `src/language_lab/app.py` -- `app.include_router(captures_router(CaptureService(anki_store)))` next to setup's. The `AppError` → status map already covers 409/503.
- `tests/fakes/anki_store.py` -- `captures: dict[str, Capture]`. `create_capture` is create-or-noop and raises `anki_busy`/`anki_unavailable` like the other methods. Update the class docstring.
- `src/language_lab/static/api.js` -- `createCapture(captureId, text)` posting JSON, in the style of `applySetup`.
- `src/language_lab/static/screens/captures.js` -- the compose box. Import `setDirty` from `../router.js` (check how router is imported, e.g. in `main.js`).
- `src/language_lab/static/router.js` -- `describeLoss`: kind `"capture"` → "This Capture isn't saved.".
- `src/language_lab/static/css/studio.css` -- textarea styling per DESIGN.md text-field: 2px `--color-border-input`, accent on focus, padding 12px 14px, label above in `--font-size-label`. Reuse `.button .button-primary` and `.inline-alert-error`.
- Tests (already written, skipped): `tests/integration/test_anki_captures.py`, `tests/api/test_captures.py`, `tests/e2e/test_captures_compose.py`. Fixtures are in `tests/support/anki_state.py` (done; don't change).

## Tasks & Acceptance

**Execution:**
- [x] `domain/captures.py`, `ports/anki_store.py`, `adapters/anki/store.py`, `tests/fakes/anki_store.py` -- add create_capture with lookup → found ? return : addNote → notesInfo cards → suspend. Then un-skip `tests/integration/test_anki_captures.py` -- AC-1..5.
- [x] `features/captures/*`, `app.py` -- the service, the route and the wiring. Then un-skip `tests/api/test_captures.py` -- AC-6..8.
- [x] `tests/api/test_captures.py` -- add these secondary cases from the checklist:
  - A retry with the same id and different text returns the first text.
  - `create_app` without an injected store has the route.
  - A fake with `available=False` gives 503.
- [x] `tests/integration/test_anki_captures.py` -- add a secondary case: a failing `suspend` is `anki_unavailable`, and a retry then writes nothing.
- [x] `static/api.js`, `static/screens/captures.js`, `static/router.js`, `static/css/studio.css` -- the compose box. Then un-skip `tests/e2e/test_captures_compose.py` -- AC-9..15.

**Acceptance Criteria:**
- Given the 29 ATDD cases plus the added secondary cases, when they run un-skipped, then all pass.
- Given the full suite, when `make test` and `uv run ruff check` run, then both are clean.
- Given the compose box on phone, tablet and desktop widths, then it fits without horizontal scroll, and the textarea text is at least 16px.

## Implementation Notes

- On a successful Save the box is cleared (and `setDirty(null)`) only when it still holds the text that was sent. Text typed while the Save was in flight is a new composition: it stays, keeps the screen dirty, and gets the new CaptureId. The AC-11 E2E test needed this (it types the next composition right after the response).
- The inline alert's Try again is `button button-destructive`, per DESIGN.md Inline alert; Save is `button button-primary`.
- The "create_app without an injected store has the route" case is behavioural: FastAPI here wraps included routers (`_IncludedRouter`), so `app.routes` doesn't list `/api/captures`. The test points `ANKI_CONNECT_URL` at a closed port and expects 503 `anki_unavailable`.
- Added: `tests/unit/test_anki_store_port.py` now lists `create_capture` in the port's method set, plus a signature test. Also an E2E width test (phone/tablet/desktop: no horizontal scroll, textarea font >= 16px).
- The route keeps its own copy of the lowercase UUIDv4 regex rather than importing `guard._UUID4`, so the feature doesn't import an adapter (AD-1).

## Plan Change Log

## Review Triage Log

### Pass 1 (quick) — high 0 · medium 2 · low 4 · false 1 · maybe-false 0

| # | Finding | Verdict | Route | Evidence |
|---|---------|---------|-------|----------|
| 1 | `captures.js` `onInput` → `render()` re-inserts the `role="alert"` node on every keystroke | medium | patch | `render()` calls `alertSlot.replaceChildren(alert)` with a new node whenever `state.error` is set; each insertion is announced again |
| 2 | Try again removes its own focused button; a failed retry leaves focus on `<body>` | medium | patch | `submit()` sets `state.error = null`, then `render()` empties `alertSlot`; only the success path calls `box.focus()` |
| 3 | Try again is enabled for blank text, but `submit()` silently returns | low | patch | `again.disabled = state.busy` vs `if (state.busy \|\| !text.trim()) return`; a direct one-line correction |
| 4 | Text typed while a Save is in flight keeps the saved prefix under a new CaptureId, so the next Save stores it twice | low | reject | Real but rare (typing in the sub-second Save window, then saving again). The alternative clears what the user typed. The fix would add prefix-stripping logic. The deviation was needed for AC-11 and is recorded in Implementation Notes |
| 5 | `_find_capture`: one Capture note with a missing or non-string `CaptureId` makes every create 503; `findNotes` ids aren't checked to be ints | low | reject | A note type missing `CaptureId` fails the manifest diff, so the gate is not `ready` first. AnkiConnect always returns string field values. Non-int ids make `notesInfo` fail as `anki_unavailable` anyway. The plan asks for malformed replies to be rejected |
| 6 | `.compose-card > .button-primary` full width on desktop deviates from the mockup | false | reject | Both `S-Captures.dc.html` and `S-CapturesDesk.dc.html` put Save Capture as a stretched child of a flex-column section: full width in both |
| 7 | Unused `compose-alert-button` class | low | patch | No CSS rule or test refers to it; a direct deletion |

## Design Notes

Screen state is `{captureId, busy, error}`.
- **Input:** `setDirty(text.trim() ? {kind: "capture", count: 1, target: ""} : null)`. Save is disabled when the text is blank or `busy`.
- **Save and Try again** both send the current text with the composition's `captureId`. Each new attempt clears the inline alert.
- **Success:** clear the box, `setDirty(null)`, make a new `captureId`, and focus the box.
- **Failure:** keep the text, and show `role="alert"` at the box.
  - `anki_unavailable` has the title "Not saved — Anki isn't reachable", the EXPERIENCE.md body, and a Try again button.
  - Any other code has the title "Not saved", the `ApiError` message (or the network fallback), and Try again.
- **Unmount:** guard late responses with a `mounted` flag, as `setup.js` does.

Known, accepted tracer risk: suppose a Save times out after Anki stored the note, and the user edits the text before Try again. The retry returns the first text (AD-20 noop).

## Verification

**Commands:**
- `uv run pytest tests/integration/test_anki_captures.py tests/api/test_captures.py tests/e2e/test_captures_compose.py` -- expected: all pass
- `make test` -- expected: green
- `uv run ruff check && uv run ruff format --check` -- expected: clean
