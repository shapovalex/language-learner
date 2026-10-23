---
title: 'OpenRouter Draft generation'
type: 'feature'
ticket: '2'
created: '2026-10-22'
status: 'built'
baseline_revision: 'bc3ed4f4c5d84c0c68281ea75c0252254cb69701'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/test-artifacts/atdd/atdd-checklist-4-2.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A Draft can only be written by hand. The ticket's core value, a schema-checked Russian Draft from OpenRouter, doesn't exist yet.

**Approach:**
- Add the per-Category generated-fields models and `strict_json_schema()` to `domain/items.py`.
- Add an `Llm` port, an `OpenRouterLlm` adapter (A4 call, one retry on invalid output) and a `FakeLlm`.
- Add `POST /api/drafts/generate`, which issues the ItemId like the blank Draft.
- In the Make an Item pane, add the Generation context field and "Generate Draft". It opens the Draft editor with a loading state, then fills it, or shows the EXPERIENCE.md error with Try again.
- Add the "Evaluating a model" docs section.

## Boundaries & Constraints

**Always:**
- Target is input. The model never returns or changes it (decided with the user, 2026-10-22).
- The Generation context goes to the model only. It is never in the response, the Save, Anki, logs, the URL, `history.state` or storage (FR-16, AD-13, AD-15).
- The adapter logs nothing: no prompt, Target, context, key or reply.
- `provider` is exactly `{require_parameters: true}`, with no other privacy or routing keys (NFR-8).
- Only invalid output retries, and only once. A transport, status or non-JSON body failure is `llm_failed` at once.
- Port, adapter and fake share one exact `generate` signature (AD-1).
- `run_live_server` injects `FakeLlm()`, so no test reaches OpenRouter.
- Follow the ATDD checklist's "Defaults taken" and "Decision taken with the user": wire shapes, copy, status codes.

**Never:**
- No duplicate check or Item read (entry 3). No per-field regenerate (epic-maintain-items).
- No template or CSS changes under `adapters/anki/templates/`.
- No change to the blank Draft path's behaviour.
- Don't edit test assertions. Only remove the skip markers.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Generate | valid `{language, category, target, generationContext?}` | 201 `{itemId, ...ItemContent}`, with Target as given, nulls as `""` and mnemonic `""`. No Anki call | — |
| Bad input | blank/missing Target, unknown Language/Category, non-string context, non-object/non-JSON body | model not called | 422 `validation_failed` |
| Invalid reply | not JSON, fails the model, refusal, no choices | retried once with the identical body | 2nd invalid → 502 `llm_invalid_output` |
| Failed request | refused, timeout, non-2xx, non-JSON body, empty `OPENROUTER_MODELS` | no retry | 502 `llm_failed` |
| Screen loading | Generate Draft clicked | `/captures/<id>/new`, skeleton "Writing your Draft…" (`role=status`), not dirty | — |
| Screen failure | 502 or another code | alert with the code's copy and Try again (same request). No form, not dirty | — |
| Left while loading | back/Discard during the request | a late reply is ignored | — |

</frozen-after-approval>

## Code Map

- `src/language_lab/domain/items.py` -- reuse the `_Required`/`_Alternatives` validators and the `_Content` config (camelCase, frozen). Add the generated models with `extra="forbid"` and no defaults, plus `generated_model(category)`, `strict_json_schema(category)` and `.to_content(target)`. Post-process Pydantic's schema: drop `title`/`default`, inline any `$defs`, and set `additionalProperties: false` and `required` = all keys. Keep the alias type `GeneratedFields` for the port's return annotation.
- `src/language_lab/ports/sync_requester.py` -- the Protocol style for the new `ports/llm.py`.
- `src/language_lab/adapters/anki/client.py` -- the pattern for an httpx `AsyncClient(transport=, timeout=)` and `aclose`. The new adapter is `adapters/openrouter/__init__.py` exporting `OpenRouterLlm`. It needs its own timeout, e.g. 60 s.
- `src/language_lab/features/drafts/{routes,service}.py` -- `DraftService(llm)`. `generate()` issues `uuid4` and returns `{itemId, **content}`. The route takes a Pydantic body: `language: Language`, `category: Category`, `target` (non-blank), `generationContext: str = ""`, strict str.
- `src/language_lab/app.py` -- `create_app(..., llm=None)`. Build `OpenRouterLlm(settings.openrouter_api_key.get_secret_value(), settings.openrouter_models)` and close it in the lifespan. `_APP_ERROR_STATUS` gets `LLM_FAILED`/`LLM_INVALID_OUTPUT` → 502. The request log already logs no body.
- `tests/fakes/` -- add `llm.py` (`FakeLlm`, see the checklist).
- `tests/support/live_server.py:58` -- add `llm=FakeLlm()`.
- `src/language_lab/static/api.js` -- `generateDraft(body)` JSON POST, beside `blankDraft`.
- `src/language_lab/static/screens/make-item.js`:
  - In the pane: the context textarea under the pickers (`choice.context`), and Primary "Generate Draft" + link "Write it myself", one shared disabled reason, with `onGenerate`.
  - In the editor: "Clear" in the Vocabulary Example field.
  - A `generatingScreen(draft, {onRetry})` with the back link + skeleton or alert + Try again.
- `src/language_lab/static/screens/captures.js`:
  - `freshChoice` gets `context: ""`.
  - `onGenerate` sets `draft` with `values: null` and `generation: {request, busy, error}`, navigates to `/new`, then fills `values` from the reply (via `blankValues` + reply keys, alternatives joined by `\n`).
  - `renderEditor` shows the generating screen while `values` is null.
  - `syncDirty` marks the draft dirty only once `values` exists.
  - Guard late replies with `draft !== pending || !mounted`.
- `src/language_lab/static/css/studio.css` -- the pane's actions row (Primary + link), the context field and the Example Clear. No phone overflow.
- `docs/configuration.md` -- `## Evaluating a model` after the keys table.
- Tests (red, skipped): `tests/unit/test_{draft_generation_domain,llm_port,docs_model_evaluation}.py`, `tests/integration/test_openrouter_llm.py`, `tests/api/test_drafts_generate.py`, `tests/e2e/test_generate_draft.py`. Support: `tests/support/{drafts,openrouter,items_screen}.py`.

## Tasks & Acceptance

**Execution:**
- [ ] `domain/items.py` -- generated models, `generated_model`, `strict_json_schema`, `to_content` -- AC-1 to AC-4.
- [ ] `ports/llm.py`, `adapters/openrouter/__init__.py`, `tests/fakes/llm.py`:
  - The port, the adapter and the fake.
  - The adapter's system prompt asks for one contextual primary meaning, no dictionary dump, and one example for Vocabulary (FR-14).
  - Covers AC-5 to AC-9.
- [ ] `features/drafts/{routes,service}.py`, `app.py`, `tests/support/live_server.py` -- the route, the wiring, the 502 mapping and the fake injection -- AC-10 to AC-13.
- [ ] `static/api.js`, `static/screens/{make-item,captures}.js`, `static/css/studio.css` -- the pane, the loading/error/Try again states, the filled editor and Clear -- AC-14 to AC-17.
- [ ] `docs/configuration.md` -- the "Evaluating a model" section with the fixture table -- AC-18.
- [ ] Remove the skip markers from the six red files and run them green. Add a P1 test that `create_app(settings)` with no `llm` builds `OpenRouterLlm`.

**Acceptance Criteria:**
- Given the ATDD checklist's AC-1 to AC-18, when `make test` runs, then every test in the six story files passes, with no skips.
- Given `tests/e2e/test_make_an_item.py`, when it runs, then it still passes: the blank Draft path is unchanged.
- Given a generation in flight, when the user goes back to the Capture, then no unsaved-changes prompt shows, and the late reply opens no editor.

## Implementation Notes

- Implemented directly in the planning session, not by a subagent: the investigation was already in context, as in story 4.1.
- `domain/items.py`:
  - The generated models are `GeneratedVocabulary`/`GeneratedSentence` on a `_Generated` base, with `GeneratedFields` as the port's return type.
  - `_strict()` drops `title`/`default`, turns a nullable `anyOf` into a `type` list, and closes every object.
  - The current models emit no `$defs`, so there is no inlining code.
- The `OpenRouterLlm` adapter:
  - It has a 60 s timeout and sends the key in its client's default headers.
  - An empty `OPENROUTER_MODELS` is `llm_failed` with no request.
  - A non-object JSON body is `llm_failed`.
  - `aclose()` is closed in the app lifespan.
- The route body is a strict Pydantic model. `language`/`category` are non-strict so the enums parse from JSON strings.
- On screen:
  - A generated Draft is the story 4.1 `draft` object, with `values: null` and `generation` set until the reply.
  - The generating screen keeps the back link at every width, because it has no Discard.
- Docs: the closing sentence of the keys section now says Generate Draft calls OpenRouter.
- Added P1 tests:
  - `create_app` wiring (API).
  - Empty models (integration).
  - Leaving while loading, and leaving after a failure (E2E).
  - The Generation context is used once (E2E, from review).
- Ruff's isort removed the blank lines left by the skip markers. No assertions changed.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick, 2026-10-22):** high 0, medium 1, low 3, false 2, maybe-false 0.

| # | Finding | Verdict | Route | Evidence / action |
|---|---------|---------|-------|-------------------|
| 1 | Clear also shows on blank Vocabulary Drafts, against "No change to the blank Draft path's behaviour" | false | reject | The blank path's behaviour is unchanged: it issues the ItemId, starts blank and saves the same, and `test_make_an_item.py` passes. EXPERIENCE.md puts "Example" + "Clear" on the Draft editor, which both paths share. |
| 2 | The Generation context is still in the pane after Save to the same Capture, so the next Draft re-sends it | medium | patch | Confirmed: `update()` returns early for the same Capture, so `choice` isn't reset. Fixed: `choice.context` is cleared when a reply arrives. New E2E test `test_the_generation_context_is_used_once`. |
| 3 | The docs fixture criteria "Target unchanged" / "must come back exactly" can't fail | low | patch | Confirmed: `to_content(target)` always uses the input. Reworded: the model never writes the Target. |
| 4 | `_strict` doesn't inline `$defs` as the Code Map said | false | reject | `strict_json_schema` for both Categories emits no `$defs` or `$ref`. The Code Map said to inline any `$defs`, and there are none. |
| 5 | OpenRouter client not closed if the Anki client's close raises | low | patch | Confirmed: both closes were in the same `finally`. Nested in `try/finally`, like the surrounding code. |
| 6 | The loading screen renders twice on the first ask; focus goes to the title, not Try again, after a failure | low | patch | Confirmed. `generate()` now renders only when not already busy (Try again), and a failure focuses Try again. |

Verification after the patches: `make test` 898 passed; ruff clean.

## Design Notes

**One Draft object, two phases.** A generated Draft exists in memory from the click, so the `/new` route and `update()` stay as in story 4.1 (`draft?.captureId === id`). `values === null` means "not filled yet": the editor renders the generating screen, and `syncDirty` treats it as clean. That matches the checklist: no Draft exists until a reply arrives. Try again re-sends `draft.generation.request` unchanged, so the second request equals the first.

**Schema post-processing.** OpenRouter's strict mode dislikes `title`, `default` and `$ref`. Building the schema by hand from `model_fields` would drift from the validator. Walking Pydantic's `model_json_schema(by_alias=True)` and stripping or inlining keeps one source (AD-11).

## Verification

**Commands:**
- `uv run pytest tests/unit/test_draft_generation_domain.py tests/unit/test_llm_port.py tests/unit/test_docs_model_evaluation.py tests/integration/test_openrouter_llm.py tests/api/test_drafts_generate.py tests/e2e/test_generate_draft.py tests/e2e/test_make_an_item.py` -- expected: all pass, none skipped.
- `make test` -- expected: green.
- `uv run ruff check && uv run ruff format --check` -- expected: clean.
