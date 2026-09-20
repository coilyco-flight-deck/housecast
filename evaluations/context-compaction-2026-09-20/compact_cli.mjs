// One compaction of a message list per invocation. JSON on stdin, JSON on stdout.
// mode jev    scores with Jev through Agent Proxy's /v1/systemone shim
// mode rule   drops every unpinned result to its head, no model
// mode random drops the counts given, chosen at random among the unpinned calls
// The library under test is imported from `lib`, never vendored here.
import { pathToFileURL } from 'node:url';

let raw = '';
for await (const chunk of process.stdin) raw += chunk;
const { lib, mode, messages, options = {}, baseUrl, seed = 7, counts = {} } = JSON.parse(raw);
const L = await import(pathToFileURL(`${lib}/dist/index.js`).href);
const resolved = L.resolveOptions(options);

function mulberry32(a) {
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function stats(before, after, decisions, extra) {
  const count = (reason) => decisions.filter((d) => d.reason === reason).length;
  return {
    messagesBefore: before.length,
    messagesAfter: after.length,
    charsBefore: before.reduce((s, m) => s + L.messageChars(m), 0),
    charsAfter: after.reduce((s, m) => s + L.messageChars(m), 0),
    calls: decisions.length,
    pinned: count('pinned'),
    kept: count('kept'),
    resultsDropped: count('result_dropped'),
    callsDropped: count('call_dropped'),
    ...extra,
  };
}

function decideAll(calls, answerFor) {
  return calls.map((call) => L.decideCall(call, answerFor(call), resolved));
}

let out;
if (mode === 'jev') {
  const asker = new L.JevClient({ apiKey: 'held-by-agent-proxy', baseUrl, model: 'jev-latest' });
  const r = await L.compact(messages, asker, options);
  out = { messages: r.messages, decisions: r.decisions, stats: r.stats };
} else {
  const calls = L.collectToolCalls(messages, resolved.preserveRecentMessages);
  let decisions;
  if (mode === 'rule') {
    decisions = decideAll(calls, () => ({ keepCall: 1, keepResult: 0 }));
  } else if (mode === 'random') {
    const rand = mulberry32(seed);
    const order = calls.filter((c) => !c.pinned).map((c) => c.id);
    for (let i = order.length - 1; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [order[i], order[j]] = [order[j], order[i]];
    }
    const callDrops = new Set(order.slice(0, counts.callsDropped ?? 0));
    const resultDrops = new Set(
      order.slice(counts.callsDropped ?? 0, (counts.callsDropped ?? 0) + (counts.resultsDropped ?? 0)),
    );
    decisions = decideAll(calls, (c) =>
      callDrops.has(c.id)
        ? { keepCall: 0, keepResult: 0 }
        : resultDrops.has(c.id)
          ? { keepCall: 1, keepResult: 0 }
          : { keepCall: 1, keepResult: 1 },
    );
  } else {
    throw new Error(`unknown mode ${mode}`);
  }
  const after = L.applyDecisions(messages, decisions, calls, resolved.truncateHeadChars);
  out = { messages: after, decisions, stats: stats(messages, after, decisions, { requests: 0 }) };
}
process.stdout.write(JSON.stringify(out));
