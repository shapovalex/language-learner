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
// same Rating (AD-20). Ratings have no hotkeys and, until story 7.2 adds Attempts, no gate.
//
// The session end is sent when the screen unmounts, when the page is hidden or goes away
// (`pagehide`, as a beacon), and when the queue is empty. A page shown again after being hidden
// starts a new session if Cards remain. Nothing about a session is stored.

import {
  errorMessage,
  getPronunciationQueue,
  isApiError,
  mediaUrl,
  rateCard,
  sessionBeacon,
  sessionSignal,
} from "../api.js";
import { categoryName, languageName } from "../catalog.js";
import { alertBox, element, skeleton, tryAgain } from "../dom.js";
import { releasePlayer } from "../reference-audio.js";

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

  const screen = element("div", "review-screen");
  const heading = element("h1", "review-title", `${language} Pronunciation`);
  const body = element("div", "review-body");
  screen.append(heading, body);
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
    if (card.audio) {
      const reference = element("button", "button review-reference");
      reference.type = "button";
      reference.setAttribute("aria-label", REFERENCE);
      reference.append(speakerIcon(), element("span", null, "Reference"));
      reference.addEventListener("click", () => playReference(card));
      const actions = element("div", "review-actions");
      actions.append(reference);
      section.append(actions);
    }
    return section;
  }

  function ratingRow(card) {
    const section = element("section", "review-rating");
    section.setAttribute("aria-label", "Rating");
    const buttons = element("div", "review-rating-buttons");
    for (const [rating, label] of RATINGS) {
      const button = element("button", "button review-rating-button", label);
      button.type = "button";
      button.addEventListener("click", () => {
        if (busy) return;
        submit({ cardId: card.cardId, reps: card.reps, rating });
      });
      buttons.append(button);
    }
    section.append(element("p", "review-prompt", PROMPT), buttons);
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
    const focusName = focused?.classList.contains("review-rating-button")
      ? focused.textContent
      : null;
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
    nodes.push(ratingRow(card));
    const layout = element("div", "review-layout");
    layout.append(...nodes);
    body.replaceChildren(layout);
    if (focused) {
      const buttons = [...layout.querySelectorAll(".review-rating-button")];
      (buttons.find((button) => button.textContent === focusName) ?? buttons[0])?.focus();
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
    await load();
  }

  function onVisibility() {
    if (document.visibilityState === "hidden") {
      if (inSession) endSession();
    } else if (queue?.cards.length && !inSession) {
      startSession();
    }
  }

  function onPageHide() {
    if (inSession) endSession(true);
  }

  document.addEventListener("visibilitychange", onVisibility);
  window.addEventListener("pagehide", onPageHide);
  load();

  return () => {
    mounted = false;
    document.removeEventListener("visibilitychange", onVisibility);
    window.removeEventListener("pagehide", onPageHide);
    if (inSession) endSession();
    dropPlayer();
    root.replaceChildren();
  };
}
