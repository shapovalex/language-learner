// A Language's Pronunciation screen (S-Review, S-iPadReview; FR-30, FR-31, FR-34, FR-36; AD-13).
// params.lang is "en" or "fr".
//
// Every mount reads GET /api/pronunciation/<lang>/queue (a skeleton in the Target card
// meanwhile) and shows the first Card: its Category, the "N due · M new" chip, the Target text,
// Reference (only when the Card has Reference audio) and the four Rating buttons. Only then is
// the session start sent, never awaited and with no Sync UI (FR-36, AD-17). Reference never
// autoplays: /api/media/<name> is requested on the first tap only (FR-31). A Rating posts the
// Card's cardId and reps; once Anki confirms, the queue is read again for the next Card and the
// chip. A failed Rating keeps the Card current with an inline alert whose Try again resends the
// same Rating (AD-20). One usable Assessment unlocks neutral Ratings for this Card.
//
// The session end is sent when the screen unmounts, when the page is hidden or goes away
// (`pagehide`, as a beacon), and when the queue is empty. A page shown again after being hidden
// starts a new session if Cards remain. Nothing about a session is stored.

import {
  assessAttempt,
  errorMessage,
  getPronunciationQueue,
  isApiError,
  mediaUrl,
  rateCard,
  sessionBeacon,
  sessionSignal,
} from "../api.js";
import { AttemptRecorder } from "../attempt-recorder.js";
import { categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import { releasePlayer } from "../reference-audio.js";
import { navigate } from "../router.js";

const RATINGS = [
  ["again", "Again"],
  ["hard", "Hard"],
  ["good", "Good"],
  ["easy", "Easy"],
];
const PROMPT = "How did that feel? You decide.";
const RATING_FAILED = "Rating not saved — Anki isn't reachable.";
const EMPTY_BODY = "No new or due Pronounce Cards right now.";
const REFERENCE = "Play reference audio";
const SVG = "http://www.w3.org/2000/svg";

function speakerIcon() {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.classList.add("review-reference-icon");
  const path = document.createElementNS(SVG, "path");
  path.setAttribute(
    "d",
    "M4 9v6h4l5 4V5L8 9H4zm12.5 3a4.5 4.5 0 0 0-2.5-4v8a4.5 4.5 0 0 0 2.5-4zM14 3.2v2.1a7 7 0 0 1 0 13.4v2.1a9 9 0 0 0 0-17.6z",
  );
  svg.append(path);
  return svg;
}

export function mount(root, params) {
  const { lang } = params;
  const language = languageName(lang);
  let mounted = true;
  let seq = 0;
  let queue = null; // the latest read: {due, new, cards}
  let readError = null; // the latest read's failure
  let busy = false; // a Rating or the read after it is in flight
  let failed = null; // {body, error}: the Rating that failed, for Try again
  let inSession = false; // a session start was sent and no end since
  let player = null; // the current Card's Reference <audio>, made on the first tap
  let playerFor = null; // the cardId that player belongs to
  let eligible = false;
  let assessment = null;
  let selectedWord = 0;
  let attemptState = "idle";
  let attemptWarning = null;
  let attemptSeq = 0;
  let recorder = null;
  let attemptRequest = null;

  const screen = element("div", "review-screen");
  const heading = element("h1", "review-title", `${language} Pronunciation`);
  const body = element("div", "review-body");
  const announcement = element("p", "sr-only");
  announcement.setAttribute("aria-live", "polite");
  screen.append(heading, body, announcement);
  root.replaceChildren(screen);

  function startSession() {
    if (inSession) return;
    inSession = true;
    sessionSignal(lang, "start");
  }

  function endSession(beacon = false) {
    // An empty queue ends a session even if none was started: the end is idempotent
    inSession = false;
    if (beacon) sessionBeacon(lang, "end");
    else sessionSignal(lang, "end");
  }

  function dropPlayer() {
    if (player) releasePlayer(player);
    player = null;
    playerFor = null;
  }

  function playReference(card) {
    if (attemptState === "recording" || attemptState === "permission") return;
    if (playerFor !== card.cardId) {
      dropPlayer();
      player = element("audio");
      player.preload = "auto";
      player.src = mediaUrl(card.audio);
      playerFor = card.cardId;
    } else {
      player.currentTime = 0;
    }
    player.play()?.catch?.(() => {});
  }

  function targetCard(card) {
    const section = element("section", "review-card");
    section.setAttribute("aria-label", "Card");
    const head = element("div", "review-card-head");
    const count = `${queue.due} due · ${queue.new} new`;
    const chip = element("span", "chip review-count", count);
    chip.setAttribute("aria-label", `${queue.due} due, ${queue.new} new`);
    head.append(element("span", "review-category", categoryName(card.category)), chip);
    const target = element("p", "review-target", card.target);
    target.lang = lang;
    section.append(head, target);
    const actions = element("div", "review-actions");
    if (card.audio) {
      const reference = element("button", "button review-reference");
      reference.type = "button";
      reference.setAttribute("aria-label", REFERENCE);
      reference.dataset.control = "reference";
      reference.disabled = attemptState === "recording" || attemptState === "permission";
      reference.append(speakerIcon(), element("span", null, "Reference"));
      reference.addEventListener("click", () => playReference(card));
      actions.append(reference);
    }
    const labels = {
      idle: "Record", permission: "Opening microphone…", recording: "Listening… tap to stop",
      assessing: "Checking…", result: "Try again",
    };
    if (!attemptWarning || attemptWarning === "mic") {
      const record = action(labels[attemptState] ?? "Record", "record", () => {
        if (attemptState === "recording") recorder?.stop();
        else startRecording(card);
      });
      record.classList.add("review-record");
      if (attemptState === "recording") record.classList.add("review-listening");
      record.disabled = busy || attemptState === "assessing" || attemptState === "permission";
      actions.append(record);
    }
    section.append(actions);
    if (attemptState === "recording") {
      const meter = element("meter", "review-meter");
      meter.min = 0;
      meter.max = 1;
      meter.value = 0;
      meter.setAttribute("aria-label", "Microphone level");
      section.append(meter);
    }
    if (attemptWarning) section.append(attemptAlert(card));
    return section;
  }

  function action(label, control, callback) {
    const button = element("button", "button", label);
    button.type = "button";
    button.dataset.control = control;
    button.addEventListener("click", callback);
    return button;
  }

  function discardAttempt(resetEligibility = false) {
    ++attemptSeq;
    attemptRequest?.abort();
    attemptRequest = null;
    recorder?.dispose();
    recorder = null;
    assessment = null;
    selectedWord = 0;
    attemptWarning = null;
    attemptState = "idle";
    announcement.textContent = "";
    if (resetEligibility) eligible = false;
  }

  function startRecording(card) {
    if (busy || ["recording", "permission", "assessing"].includes(attemptState)) return;
    discardAttempt();
    dropPlayer();
    const token = attemptSeq;
    const current = () => mounted && token === attemptSeq;
    attemptState = "permission";
    render();
    recorder = new AttemptRecorder({
      recording: () => {
        if (!current()) return;
        attemptState = "recording";
        render();
        body.querySelector('[data-control="record"]')?.focus();
      },
      level: value => {
        if (!current()) return;
        const meter = body.querySelector("meter");
        if (meter) meter.value = value;
      },
      stopping: () => {
        if (!current()) return;
        attemptState = "assessing";
        render();
      },
      complete: blob => {
        if (!current()) return;
        recorder = null;
        attemptState = "assessing";
        render();
        attemptRequest = new AbortController();
        // The helper owns the upload body. The screen keeps neither Blob nor FormData.
        const pending = assessAttempt(lang, card.itemId, blob, attemptRequest.signal);
        blob = null;
        pending.then(result => {
          if (!current()) return;
          attemptRequest = null;
          assessment = result.assessment;
          attemptWarning = result.nothingHeard ? "nothing" : null;
          attemptState = "result";
          if (assessment) {
            eligible = true;
            selectedWord = assessment.words.reduce((weakest, word, index, words) =>
              word.score < words[weakest].score ? index : weakest, 0);
            announcement.textContent = `Overall score ${assessment.overall}. Weakest word: ${assessment.words[selectedWord].text}.`;
          }
          render();
          body.querySelector('[data-control="record"]')?.focus();
        }).catch(() => {
          if (!current()) return;
          attemptRequest = null;
          attemptWarning = "failed";
          attemptState = "result";
          render();
          body.querySelector('[data-control="record"]')?.focus();
        });
      },
      error: reason => {
        if (!current()) return;
        recorder = null;
        attemptState = "idle";
        attemptWarning = reason === "size" ? "size" : "mic";
        render();
        body.querySelector('[data-control="record"]')?.focus();
      },
    });
    recorder.start();
  }

  function attemptAlert(card) {
    const copy = {
      mic: ["LanguageLab can't hear you", "Allow microphone access for this site in Safari, then reload the page."],
      nothing: ["Couldn't hear that Attempt", "Record again closer to the microphone."],
      failed: ["Couldn't assess that Attempt", "This Card isn't answered yet. Record again, or leave and come back later."],
      size: ["Recording is too large", "Record again with a shorter Attempt."],
    };
    const [title, message] = copy[attemptWarning];
    const alert = alertBox("review-alert", element("strong", null, title), element("p", null, message));
    if (attemptWarning !== "failed") {
      alert.className = "inline-alert-warning review-alert";
    }
    if (attemptWarning !== "mic") {
      alert.append(action("Record again", "record", () => startRecording(card)));
    }
    if (attemptWarning === "failed") {
      alert.append(action("Exit", "exit", () => navigate(`/${lang}/items`)));
    }
    return alert;
  }

  function feedbackClass(score) {
    return score === null ? "feedback-empty" : score >= 80 ? "feedback-good" : score >= 60 ? "feedback-fair" : "feedback-poor";
  }

  function scoresCard() {
    const section = element("section", "review-scores review-card");
    section.setAttribute("aria-label", "Assessment");
    const ring = element("div", "review-score-ring", String(assessment.overall));
    ring.setAttribute("aria-label", "Overall score");
    ring.style.setProperty("--score", `${assessment.overall}%`);
    section.append(ring);
    const scores = element("div", "review-subscores");
    for (const label of ["Accuracy", "Fluency", "Completeness", "Prosody"]) {
      const value = assessment[label.toLowerCase()];
      if (value === null || (lang === "fr" && label === "Prosody")) continue;
      const row = element("div", "review-subscore");
      const number = element("span", null, String(value));
      number.setAttribute("aria-label", label);
      row.append(element("span", null, label), number);
      scores.append(row);
    }
    section.append(scores);
    const pills = element("div", "review-word-pills");
    assessment.words.forEach((word, index) => {
      const pill = action(word.text, `word-${index}`, () => {
        selectedWord = index;
        render();
      });
      pill.className = `button review-word-pill ${feedbackClass(word.score)}`;
      pill.lang = assessment.locale;
      pill.setAttribute("aria-pressed", String(index === selectedWord));
      pills.append(pill);
    });
    section.append(pills);
    const word = assessment.words[selectedWord];
    const detail = element("section", "review-word-detail");
    detail.lang = assessment.locale;
    detail.setAttribute("aria-label", "Word feedback");
    const error = word.errorType === "Mispronunciation" ? "mispronounced" : word.errorType === "None" ? "no pronunciation error" : word.errorType.toLowerCase();
    detail.append(element("h2", null, `${word.text} · ${word.score} · ${error}`));
    const units = element("div", "review-position-strip");
    if (lang === "fr") {
      detail.append(element("p", null, "Where in the word"));
      for (const position of ["start", "middle", "end"]) {
        const value = word.positions?.[position] ?? null;
        const cell = element("div", `review-position ${feedbackClass(value)}`);
        cell.append(element("span", null, position), element("span", null, value === null ? "—" : String(value)));
        units.append(cell);
      }
      section.append(element("p", "review-feedback-note", "French feedback covers the overall score, words and where in a word a sound slipped. Prosody isn't available."));
    } else {
      for (const phoneme of word.phonemes) {
        const pill = element("span", `review-phoneme ${feedbackClass(phoneme.score)}`);
        pill.append(element("span", null, phoneme.symbol), element("span", null, String(phoneme.score)));
        units.append(pill);
      }
    }
    detail.append(units);
    section.append(detail);
    return section;
  }

  function ratingRow(card) {
    const section = element("section", "review-rating");
    section.setAttribute("aria-label", "Rating");
    const buttons = element("div", "review-rating-buttons");
    for (const [rating, label] of RATINGS) {
      const button = element("button", "button review-rating-button", label);
      button.type = "button";
      button.dataset.control = `rating-${rating}`;
      button.disabled = !eligible;
      button.addEventListener("click", () => {
        if (busy || !eligible) return;
        submit({ cardId: card.cardId, reps: card.reps, rating });
      });
      buttons.append(button);
    }
    section.append(element("p", "review-prompt", PROMPT), buttons);
    if (!eligible) section.append(element("p", "review-prompt", "Record an Attempt to enable Rating."));
    if (busy) section.setAttribute("aria-busy", "true");
    return section;
  }

  function render() {
    if (readError) {
      body.replaceChildren(
        alertBox(
          "review-alert",
          element("p", "review-alert-body", errorMessage(readError)),
          tryAgain(() => load()),
        ),
      );
      return;
    }
    const card = queue.cards[0];
    if (!card) {
      dropPlayer();
      const empty = element("div", "review-empty");
      empty.append(
        element("p", "review-empty-title", `Nothing to practice in ${language}`),
        element("p", "review-empty-body", EMPTY_BODY),
      );
      body.replaceChildren(empty);
      return;
    }
    if (playerFor !== null && playerFor !== card.cardId) dropPlayer();
    // Focus inside the review survives the re-render: on the same Rating, else the first one
    const focused = body.contains(document.activeElement) ? document.activeElement : null;
    const focusName = focused?.dataset.control;
    const left = element("div", "review-main-column");
    const nodes = [targetCard(card)];
    if (failed) {
      const message = isApiError(failed.error, "setup_required")
        ? `Rating not saved — ${errorMessage(failed.error)}`
        : RATING_FAILED;
      nodes.push(
        alertBox(
          "review-alert",
          element("p", "review-alert-body", message),
          tryAgain(() => {
            if (!busy) submit(failed.body);
          }),
        ),
      );
    }
    left.append(...nodes);
    const layout = element("div", "review-layout");
    layout.append(left);
    if (assessment) layout.append(scoresCard());
    layout.append(ratingRow(card));
    body.replaceChildren(layout);
    if (focused) {
      const buttons = [...layout.querySelectorAll("button:not(:disabled)")];
      (buttons.find(button => button.dataset.control === focusName) ??
        buttons.find(button => button.dataset.control === "record"))?.focus();
    }
  }

  async function load() {
    const token = ++seq;
    const first = queue === null;
    if (first || readError) {
      const card = element("section", "review-card");
      card.append(skeleton(`Loading ${language} Pronunciation…`));
      body.replaceChildren(card);
    }
    let next = null;
    let error = null;
    try {
      next = await getPronunciationQueue(lang);
    } catch (caught) {
      error = caught;
    }
    if (!mounted || token !== seq) return;
    busy = false;
    readError = error;
    if (next) {
      if (queue?.cards[0]?.cardId !== next.cards[0]?.cardId) discardAttempt(true);
      queue = next;
      failed = null;
    }
    render();
    if (!next) return;
    // The first Card is on screen before the session's Sync is asked for (FR-36)
    if (next.cards.length) {
      // A page hidden by now starts its session when shown again (onVisibility)
      if (first && document.visibilityState !== "hidden") startSession();
    } else if (first || inSession) {
      endSession();
    }
  }

  async function submit(rating) {
    busy = true;
    failed = null;
    render();
    try {
      await rateCard(lang, rating);
    } catch (error) {
      if (!mounted) return;
      if (isApiError(error, "not_found")) {
        // The Card left the queue in Anki since the read: show what is queued now
        await load();
        return;
      }
      busy = false;
      failed = { body: rating, error };
      render();
      return;
    }
    if (!mounted) return;
    discardAttempt(true);
    await load();
  }

  function onVisibility() {
    if (document.visibilityState === "hidden") {
      discardAttempt();
      if (queue) render();
      if (inSession) endSession();
    } else if (queue?.cards.length && !inSession) {
      startSession();
    }
  }

  function onPageHide() {
    discardAttempt(true);
    if (inSession) endSession(true);
  }

  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("pagehide", onPageHide);
  load();

  return () => {
    mounted = false;
    discardAttempt(true);
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("pagehide", onPageHide);
    if (inSession) endSession();
    dropPlayer();
    root.replaceChildren();
  };
}
