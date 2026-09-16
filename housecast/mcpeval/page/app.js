// The flow. No visual value is decided here: everything is a class the token
// file resolves, so a rebrand never reaches this file.
"use strict";

const $ = (id) => document.getElementById(id);
const api = async (path, body) => {
  const options = body
    ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }
    : {};
  const response = await fetch(path, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok && response.status !== 409) throw new Error(payload.detail || response.statusText);
  return payload;
};

const state = {
  task: null, defs: null, baselineRun: null, lastRun: null,
  parentProse: "", blindToken: null, step: "task",
};

function step(name) {
  state.step = name;
  const order = ["task", "run", "read", "edit", "rerun", "decide"];
  const at = order.indexOf(name);
  document.querySelectorAll("#rail li").forEach((li) => {
    const i = order.indexOf(li.dataset.step);
    li.dataset.on = String(i === at);
    li.dataset.done = String(i < at);
  });
}

async function boot() {
  const s = await api("/api/state");
  $("env").textContent = `subject ${s.subject.version} · model ${s.model.name}`;
  $("task").innerHTML = s.tasks
    .map((t) => `<option value="${t.slug}">${t.title} · ${t.prompts} prompts</option>`)
    .join("");
  const t = s.tasks[0];
  if (t) $("cap").textContent = t.capability;
  refreshDefs(s);
  state.defs = $("defs").value || null;
  step("task");
}

function refreshDefs(s) {
  if (!s.definitions.length) {
    $("defs").innerHTML = `<option value="">no definition set yet — capture a baseline</option>`;
    return;
  }
  $("defs").innerHTML = s.definitions
    .map((d) => `<option value="${d.digest}">${d.label || d.digest} · ${d.authored_by}</option>`)
    .join("");
  if (state.defs) $("defs").value = state.defs;
}

$("baseline").onclick = async () => {
  const d = await api("/api/baseline", {});
  state.defs = d.digest;
  refreshDefs(await api("/api/state"));
  $("defs").value = d.digest;
  loadEditor(d);
};

$("defs").onchange = () => { state.defs = $("defs").value || null; };

$("task").onchange = async () => {
  const t = await api(`/api/task/${$("task").value}`);
  $("cap").textContent = t.capability;
};

$("go").onclick = async () => {
  const task = $("task").value;
  const defs = $("defs").value;
  state.defs = defs || state.defs;
  $("go").disabled = true;
  $("bar").classList.remove("hidden");
  step("run");
  const started = await api("/api/run", { task, definitions: defs, concurrency: 8 });
  poll(started.pending, started.total);
};

// A run is launched and left. The interface polls rather than blocking, because
// a design that blocks on a running suite has spent the hour on idling.
function poll(pending, total) {
  const tick = async () => {
    const s = await api("/api/state");
    const mine = s.live.find((l) => l.run_id === pending);
    if (!mine) return;
    $("progress").textContent = `${mine.done} of ${total} prompts`;
    $("bar").firstElementChild.style.width = `${(mine.done / total) * 100}%`;
    if (mine.error) {
      $("progress").textContent = mine.error;
      $("go").disabled = false;
      return;
    }
    if (mine.finished) {
      $("go").disabled = false;
      $("bar").classList.add("hidden");
      $("progress").textContent = "";
      await showRun(mine.finished);
      return;
    }
    setTimeout(tick, 700);
  };
  tick();
}

async function showRun(runId) {
  const d = await api(`/api/run/${runId}`);
  if (!state.baselineRun) state.baselineRun = runId;
  else state.lastRun = runId;
  $("p-run").classList.remove("hidden");
  $("run-meta").textContent =
    `${d.run.run_id} · ${d.run.label || d.run.definitions} · ${d.run.seconds}s · ` +
    `${d.run.scored} scored, ${d.run.errored} transport-errored`;
  const q = d.queue;
  $("run-tally").innerHTML = tally([
    ["mean score", d.run.mean === null ? "—" : d.run.mean.toFixed(2), ""],
    ["needing a read", String(q.rows.length), q.rows.length ? "bad" : "good"],
    ["passing, hidden", String(q.hidden), "good"],
  ]);
  $("budget").textContent =
    `${q.rows.length} rows × ${q.minutes_per_result} min = ${q.minutes.toFixed(0)} minutes of the hour. ` +
    `${q.hidden} passing rows are not shown.`;
  $("queue").innerHTML = q.rows.map(row).join("");
  document.querySelectorAll(".qrow").forEach((el) => {
    el.onclick = () => expand(el, d);
  });
  step("read");
  if (state.defs) loadEditor(await api(`/api/definitions/${state.defs}`));
  if (state.baselineRun && state.lastRun) compare();
}

const tally = (items) =>
  items.map(([k, n, c]) => `<div><span class="n ${c}">${n}</span><span class="k">${k}</span></div>`).join("");

const row = (r) => `
  <div class="qrow" data-reason="${r.reason}" data-id="${r.prompt_id}">
    <span class="id">${r.prompt_id}</span>
    <span class="why">${r.reason}</span>
    <span class="head">${esc(r.headline)}</span>
    <span class="sc">${r.score === null ? "—" : r.score.toFixed(2)}</span>
  </div>`;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

function expand(el, d) {
  const open = el.nextElementSibling && el.nextElementSibling.classList.contains("detail");
  if (open) { el.nextElementSibling.remove(); return; }
  const p = d.prompts.find((x) => x.prompt_id === el.dataset.id);
  if (!p) return;
  const node = document.createElement("div");
  node.className = "detail";
  node.innerHTML = `
    <p>${esc(p.prompt)}</p>
    <div class="calls">${p.calls.map((c) => `<div data-err="${c.is_error}">${esc(c.name)}(${esc(JSON.stringify(c.arguments))}) → ${esc((c.result || "").slice(0, 160))}</div>`).join("")}</div>
    <div class="checks">${p.grade.checks.map((c) => `<span class="chk" data-ok="${c.passed}">${c.name}: ${esc(c.detail)}</span>`).join("")}</div>
    <p class="meta" style="margin-top:var(--space-2)">answer: ${esc((p.answer || "(none)").slice(0, 400))}</p>`;
  el.after(node);
}

function loadEditor(d) {
  state.defs = d.digest;
  $("p-edit").classList.remove("hidden");
  $("edit-meta").textContent = `${d.digest} · ${d.authored_by}${d.parent ? ` · from ${d.parent}` : ""}`;
  $("tool").innerHTML = d.tools.map((t) => `<option value="${t.name}">${t.name}</option>`).join("");
  state.tools = d.tools;
  pickTool();
}

function pickTool() {
  const t = (state.tools || []).find((x) => x.name === $("tool").value);
  if (!t) return;
  state.parentProse = t.description;
  $("prose").value = t.description;
  validate();
}
$("tool").onchange = pickTool;
$("revert").onclick = () => { $("prose").value = state.parentProse; validate(); };

let timer = null;
$("prose").oninput = () => { clearTimeout(timer); timer = setTimeout(validate, 250); };

async function validate() {
  const v = await api("/api/validate", {
    parent: state.defs, tool: $("tool").value, description: $("prose").value,
  });
  const notes = [];
  if (v.unchanged) notes.push(["this is the prose already under test", true]);
  (v.notes || []).forEach((n) => notes.push([n, false]));
  if (!notes.length && v.ok) notes.push([`reads clean · new version would be ${v.digest}`, true]);
  $("notes").innerHTML = notes
    .map(([text, ok]) => `<span class="note" data-ok="${ok}">${esc(text)}</span>`)
    .join("");
  $("save").disabled = Boolean(v.unchanged) || !v.ok;
  step("edit");
}

$("save").onclick = async () => {
  const d = await api("/api/edit", {
    parent: state.defs, tool: $("tool").value, description: $("prose").value,
    author: "human:tester", label: $("label").value || "edit",
  });
  refreshDefs(await api("/api/state"));
  $("defs").value = d.digest;
  state.defs = d.digest;
  step("rerun");
  $("go").click();
};

async function compare() {
  const blind = await api(`/api/compare?before=${state.baselineRun}&after=${state.lastRun}`);
  $("p-compare").classList.remove("hidden");
  if (blind.refused) {
    $("cmp-body").innerHTML = `<p class="refused">${esc(blind.refused)}</p>`;
    return;
  }
  state.blindToken = blind.blind.token;
  $("cmp-meta").textContent = `${blind.task} · ${blind.deltas.length} prompts paired`;
  $("cmp-body").innerHTML = `
    <p>${esc(blind.blind.note)}</p>
    <div class="strip">${blind.deltas.map((d) => `<span class="cell" data-dir="blind" title="${d.prompt_id}">${d.prompt_id.replace(/^p/, "")}</span>`).join("")}</div>
    <div class="row">
      <span class="meta">arm A mean ${mean(blind.deltas, "arm_a")} · arm B mean ${mean(blind.deltas, "arm_b")}</span>
    </div>
    <div class="row" style="margin-top:var(--space-2)">
      <span class="meta">your judgement, before the labels:</span>
      <button data-v="a" class="ghost">A is better</button>
      <button data-v="b" class="ghost">B is better</button>
      <button data-v="same" class="quiet">no difference I can see</button>
    </div>`;
  $("cmp-body").querySelectorAll("button[data-v]").forEach((b) => {
    b.onclick = () => reveal(b.dataset.v);
  });
  step("decide");
}

const mean = (deltas, key) =>
  (deltas.reduce((a, d) => a + (d[key] || 0), 0) / Math.max(deltas.length, 1)).toFixed(2);

async function reveal(verdict) {
  const r = await api("/api/compare/judge", { token: state.blindToken, verdict });
  const rows = r.deltas.map((d) => {
    const label = d.delta === null ? "" : (d.delta > 0 ? "+" : "") + d.delta.toFixed(2);
    return `<span class="cell" data-dir="${d.direction}" title="${d.prompt_id} ${label}">${d.prompt_id.replace(/^p/, "")}</span>`;
  }).join("");
  const power = r.underpowered
    ? `p=${r.p_value.toFixed(3)} — this many moved prompts cannot support a conclusion. Accumulate across iterations rather than reading harder.`
    : `p=${r.p_value.toFixed(3)} — clears 0.05 on an exact two-tailed sign test.`;
  $("cmp-body").innerHTML = `
    <p class="meta">you judged <b>${esc(verdict)}</b> · arm A was the <b>${esc(r.arm_a_was)}</b> arm</p>
    <div class="tally">${tally([
      ["improved", String(r.improved), "good"],
      ["regressed", String(r.regressed), "bad"],
      ["held", String(r.held), "flat"],
      ["paired", String(r.deltas.length), ""],
    ])}</div>
    <div class="strip">${rows}</div>
    <p class="meta">${esc(power)}</p>
    ${r.past_threshold.length ? `<p class="refused">past the ${r.rule.regression_threshold} regression threshold: ${r.past_threshold.join(", ")}</p>` : ""}
    <div class="verdict" data-decision="${r.decision}">
      <span class="word">${esc(r.decision)}</span>
      <p>By the declared rule: ${r.rule.require_net_improvement ? "net improvement required" : "no net requirement"}, no prompt regressing past ${r.rule.regression_threshold}. The rule decides, not the p-value.</p>
    </div>
    <span class="budget" style="margin-top:var(--space-3)">${r.queue.rows.length} rows still worth reading · ${r.queue.minutes.toFixed(0)} minutes</span>`;
}

boot();
