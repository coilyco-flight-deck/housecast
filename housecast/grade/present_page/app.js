"use strict";

/* The room's client. Polls GET /api/state and renders only the keys the
   current payload holds - see docs/presenting.md for what each state adds. */

var POLL_MS = 1500;
var STATE_URL = "/api/state";
var VOTE_URL = "/api/vote";
var ADVANCE_URL = "/api/control/advance";
var BACK_URL = "/api/control/back";
var DEVICE_KEY = "housecast-present-device";

/* A random token the browser mints for itself, wrapped in try/catch since
   localStorage can throw in a private window or with site data blocked. */
function readDevice() {
  var fallback = null;
  function mint() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return "d-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
  try {
    var existing = window.localStorage.getItem(DEVICE_KEY);
    if (existing) return existing;
    fallback = mint();
    window.localStorage.setItem(DEVICE_KEY, fallback);
    return fallback;
  } catch (err) {
    return fallback || mint();
  }
}
var DEVICE = readDevice();

/* The header authorizes control, never a cookie: read once from the URL. */
var PRESENTER_TOKEN = new URLSearchParams(window.location.search).get("presenter");
var isPresenter = Boolean(PRESENTER_TOKEN);

var el = {
  deckName: document.getElementById("deck-name"),
  progress: document.getElementById("progress"),
  commitments: document.getElementById("commitments"),
  commitmentsList: document.getElementById("commitments-list"),
  emptyState: document.getElementById("empty-state"),
  caseBlock: document.getElementById("case-block"),
  prompt: document.getElementById("prompt"),
  response: document.getElementById("response"),
  voteBlock: document.getElementById("vote-block"),
  votePass: document.getElementById("vote-pass"),
  voteFail: document.getElementById("vote-fail"),
  voteSay: document.getElementById("vote-say"),
  splitBlock: document.getElementById("split-block"),
  splitPassFill: document.getElementById("split-pass-fill"),
  splitFailFill: document.getElementById("split-fail-fill"),
  splitPassCount: document.getElementById("split-pass-count"),
  splitFailCount: document.getElementById("split-fail-count"),
  revealBlock: document.getElementById("reveal-block"),
  verdictChip: document.getElementById("verdict-chip"),
  critiqueBlock: document.getElementById("critique-block"),
  critiqueText: document.getElementById("critique-text"),
  banner: document.getElementById("banner"),
  bannerText: document.getElementById("banner-text"),
  presenter: document.getElementById("presenter"),
  ctlBack: document.getElementById("ctl-back"),
  ctlAdvance: document.getElementById("ctl-advance")
};

/* UI memory only: the server never echoes a vote back. */
var myVote = { round: null, choice: null };

/* k-note's own registers ("warn"/"error"), never grant/cost, so a
   connection banner can never be mistaken for a round's verdict. */
function showBanner(text, tone) {
  el.bannerText.textContent = text;
  el.banner.classList.remove("k-note--refuse", "k-note--cost");
  el.banner.classList.add(tone === "error" ? "k-note--cost" : "k-note--refuse");
  el.banner.hidden = false;
}
function hideBanner() {
  el.banner.hidden = true;
  el.bannerText.textContent = "";
}

function hideAll() {
  el.emptyState.hidden = true;
  el.caseBlock.hidden = true;
  el.voteBlock.hidden = true;
  el.splitBlock.hidden = true;
  el.revealBlock.hidden = true;
}

/* Checked against the response rather than trusted: a highlight that
   silently misses a moved span is worse than one that plainly did not. */
function responseMarkup(text, evidence) {
  if (!evidence) return document.createTextNode(text);
  var found = text.toLowerCase().indexOf(evidence.toLowerCase());
  if (found < 0) return document.createTextNode(text);
  var frag = document.createDocumentFragment();
  frag.appendChild(document.createTextNode(text.slice(0, found)));
  var mark = document.createElement("mark");
  mark.textContent = text.slice(found, found + evidence.length);
  frag.appendChild(mark);
  frag.appendChild(document.createTextNode(text.slice(found + evidence.length)));
  return frag;
}

function draw(payload) {
  el.deckName.textContent = payload.deck || "housecast";
  el.progress.textContent = "round " + (payload.round + 1) + " of " + payload.rounds + " — " + payload.state;

  var commitments = payload.commitments || [];
  el.commitments.hidden = commitments.length === 0;
  el.commitmentsList.replaceChildren();
  commitments.forEach(function (line) {
    var li = document.createElement("li");
    li.textContent = line;
    el.commitmentsList.appendChild(li);
  });

  hideAll();

  var hasCase = "prompt" in payload && "response" in payload;
  if (!hasCase) {
    el.emptyState.hidden = false;
    return;
  }

  el.caseBlock.hidden = false;
  el.prompt.textContent = payload.prompt;
  var evidence = payload.reveal ? payload.reveal.evidence : "";
  el.response.textContent = "";
  el.response.appendChild(responseMarkup(payload.response, evidence));

  if (myVote.round !== payload.round) myVote = { round: payload.round, choice: null };

  if (payload.state === "open") {
    el.voteBlock.hidden = false;
    var count = typeof payload.votes_cast === "number" ? payload.votes_cast : 0;
    el.votePass.disabled = false;
    el.voteFail.disabled = false;
    el.votePass.setAttribute("aria-pressed", String(myVote.choice === "pass"));
    el.voteFail.setAttribute("aria-pressed", String(myVote.choice === "fail"));
    el.voteSay.textContent = myVote.choice
      ? "your vote is in — " + count + " cast so far, change it any time"
      : count + " cast so far";
  }

  if (payload.split) {
    el.splitBlock.hidden = false;
    var pass = payload.split.pass || 0;
    var fail = payload.split.fail || 0;
    var total = pass + fail;
    el.splitPassCount.textContent = String(pass);
    el.splitFailCount.textContent = String(fail);
    el.splitPassFill.style.width = (total ? (100 * pass) / total : 0) + "%";
    el.splitFailFill.style.width = (total ? (100 * fail) / total : 0) + "%";
  }

  if (payload.reveal) {
    el.revealBlock.hidden = false;
    el.verdictChip.textContent = payload.reveal.label;
    var passed = payload.reveal.label === "pass";
    el.verdictChip.classList.toggle("k-chip--grant", passed);
    el.verdictChip.classList.toggle("k-chip--cost", !passed);
    el.critiqueBlock.classList.toggle("k-note--grant", passed);
    el.critiqueBlock.classList.toggle("k-note--cost", !passed);
    if (payload.reveal.critique) {
      el.critiqueBlock.hidden = false;
      el.critiqueText.textContent = payload.reveal.critique;
    } else {
      el.critiqueBlock.hidden = true;
    }
  }
}

function castVote(choice) {
  el.votePass.disabled = true;
  el.voteFail.disabled = true;
  fetch(VOTE_URL, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ device: DEVICE, choice: choice })
  })
    .then(function (r) {
      if (r.status === 409) {
        return r.json().then(function (body) {
          showBanner(body.detail || "voting is not open on this round", "error");
        });
      }
      if (!r.ok) throw new Error("vote failed");
      hideBanner();
      myVote.choice = choice;
    })
    .catch(function () {
      showBanner("that vote did not reach the room. Try again.", "error");
    })
    .finally(function () {
      el.votePass.disabled = false;
      el.voteFail.disabled = false;
    });
}
el.votePass.addEventListener("click", function () { castVote("pass"); });
el.voteFail.addEventListener("click", function () { castVote("fail"); });

function control(url) {
  fetch(url, { method: "POST", headers: { "X-Control-Token": PRESENTER_TOKEN } })
    .then(function (r) {
      if (r.status === 403) {
        showBanner("the control token does not match", "error");
        return;
      }
      if (!r.ok) throw new Error("control failed");
      hideBanner();
      return r.json().then(draw);
    })
    .catch(function () {
      showBanner("that control did not reach the room", "error");
    });
}

if (isPresenter) {
  el.presenter.hidden = false;
  el.ctlAdvance.addEventListener("click", function () { control(ADVANCE_URL); });
  el.ctlBack.addEventListener("click", function () { control(BACK_URL); });
  window.addEventListener("keydown", function (event) {
    if (event.key === "ArrowRight") control(ADVANCE_URL);
    if (event.key === "ArrowLeft") control(BACK_URL);
  });
}

function poll() {
  fetch(STATE_URL, { headers: { accept: "application/json" } })
    .then(function (r) {
      if (!r.ok) throw new Error("state fetch failed");
      return r.json();
    })
    .then(function (payload) {
      hideBanner();
      draw(payload);
    })
    .catch(function () {
      showBanner("connection to the room lost, retrying…", "warn");
    });
}

poll();
setInterval(poll, POLL_MS);
