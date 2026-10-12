// Tapat service worker: session start, blocking, focus logging, submit
// detection, heartbeat, and an event queue that survives a sleeping server.
importScripts("config.js");

const store = chrome.storage.local;

async function getSession() {
  const { session } = await store.get("session");
  return session || null;
}

// ---------- event queue ----------
// Every event is written to chrome.storage.local first, with its own client
// time and a per-session sequence number, then sent in order. If the student
// has no wifi, or the free server is still waking up, events stay queued and
// are retried with backoff (on a timer, on a chrome alarm, and when the
// browser comes back online). The server ignores a (session, seq) it already
// has, so a resend can never double count.
let flushing = false;
let retryTimer = null;
// Queue writes go through one chain so two events can't overwrite each other.
let lock = Promise.resolve();
function locked(fn) {
  const run = lock.then(fn);
  lock = run.catch(() => {});
  return run;
}

function enqueue(type, detail = "") {
  return locked(() => addToQueue(type, detail));
}

async function addToQueue(type, detail) {
  const s = await getSession();
  if (!s || !s.active) return;
  const { queue = [], backoff = 0, seq = 0 } = await store.get(["queue", "backoff", "seq"]);
  const now = Date.now() / 1000;
  let nextSeq = seq;
  const last = queue[queue.length - 1];
  const offline = backoff > 0 || !navigator.onLine;
  if (type === "heartbeat" && offline && queue.length > 1 && last.body.type === "heartbeat" && last.body.session_id === s.id) {
    // Offline: fold heartbeats into one summary instead of piling them up.
    last.beats = (last.beats || 1) + 1;
    last.body.ts = now;
    last.body.detail = `${last.beats} heartbeats while offline`;
  } else {
    nextSeq = seq + 1;
    queue.push({ server: s.server, body: {
      session_id: s.id, session_token: s.token, seq: nextSeq, student: s.email, type, detail, ts: now
    } });
  }
  await store.set({ queue, seq: nextSeq });
  flush();
}

async function flush() {
  if (flushing) return;
  flushing = true;
  try {
    for (;;) {
      const { queue = [], backoff = 0 } = await store.get(["queue", "backoff"]);
      if (!queue.length) { await store.set({ backoff: 0 }); chrome.alarms.clear("flush"); break; }
      const item = queue[0];
      let res = null;
      if (navigator.onLine) {
        try {
          res = await fetch(`${item.server}/events`, {
            method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(item.body)
          });
        } catch (e) { res = null; }
      }
      if (res && (res.ok || (res.status >= 400 && res.status < 500))) {
        // Sent (or a duplicate), or rejected for good (bad token): drop it, keep order.
        await locked(async () => {
          const { queue: q2 = [] } = await store.get("queue");
          q2.shift();
          await store.set({ queue: q2, backoff: 0 });
        });
        continue;
      }
      // Offline, asleep or unreachable: wait 2, 4, 8 ... up to 60 seconds.
      const next = Math.min(backoff ? backoff * 2 : 2, 60);
      await store.set({ backoff: next });
      clearTimeout(retryTimer);
      retryTimer = setTimeout(flush, next * 1000);
      // The alarm survives the service worker being shut down.
      chrome.alarms.create("flush", { periodInMinutes: 0.5 });
      break;
    }
  } finally {
    flushing = false;
  }
}

self.addEventListener("online", () => { store.set({ backoff: 0 }).then(flush); });

// ---------- server calls with wake-up retries ----------
async function fetchRetry(url, options, totalSeconds = 120) {
  const until = Date.now() + totalSeconds * 1000;
  let wait = 2;
  for (;;) {
    try {
      const res = await fetch(url, options);
      if (res.status < 500) return res;
    } catch (e) { /* asleep or offline */ }
    if (Date.now() > until) throw new Error("Server did not answer");
    await new Promise(r => setTimeout(r, wait * 1000));
    wait = Math.min(wait * 2, 15);
  }
}

// ---------- blocking ----------
async function enableBlocking() {
  const rules = BLOCK_LIST.map((b, i) => ({
    id: i + 1, priority: 1, action: { type: "block" },
    condition: { regexFilter: b.regex, resourceTypes: ["main_frame", "sub_frame"] }
  }));
  const old = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: old.map(r => r.id), addRules: rules });
}

async function disableBlocking() {
  const old = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: old.map(r => r.id) });
}

// A blocked page fails with ERR_BLOCKED_BY_CLIENT; log it and show our page.
chrome.webNavigation.onErrorOccurred.addListener(async (d) => {
  const s = await getSession();
  if (!s || !s.active || d.error !== "net::ERR_BLOCKED_BY_CLIENT") return;
  let shown = d.url;
  try { const u = new URL(d.url); shown = u.hostname + u.pathname.slice(0, 40); } catch (e) {}
  enqueue("blocked_url", shown);
  if (d.frameId === 0) {
    chrome.tabs.update(d.tabId, { url: chrome.runtime.getURL("blocked.html") + "#" + encodeURIComponent(shown) });
  }
});

// ---------- session ----------
async function startSession({ email, link }) {
  const parsed = parseStartLink(link);
  if (!parsed) return { ok: false, error: "That start link is not valid." };
  let res;
  try {
    res = await fetchRetry(`${parsed.server}/api/start`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: parsed.code, token: parsed.token, email })
    });
  } catch (e) {
    return { ok: false, error: "The Tapat server did not answer. Check your internet and try again." };
  }
  const data = await res.json();
  if (!res.ok) return { ok: false, error: data.error || "Could not start the quiz." };
  const session = {
    id: data.session_id, token: data.session_token, email: email.trim().toLowerCase(), server: parsed.server,
    quiz: data.quiz, title: data.title, formUrl: data.form_url, active: true
  };
  await store.set({ session, seq: 0, examTabId: null });
  await enableBlocking();
  chrome.alarms.create("heartbeat", { periodInMinutes: HEARTBEAT_SECONDS / 60 });
  enqueue("heartbeat", "session started");
  return { ok: true, session };
}

async function endSession(reason) {
  await enqueue("submitted", reason);
  await locked(async () => {
    const s = await getSession();
    if (s) await store.set({ session: { ...s, active: false } });
  });
  chrome.alarms.clear("heartbeat");
  await disableBlocking();
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.kind === "start") { startSession(msg).then(reply); return true; }
  if (msg.kind === "examTab") {
    store.set({ examTabId: sender.tab.id });
  }
  if (msg.kind === "status") { store.get("examTabId").then(({ examTabId }) => reply({ examTabId })); return true; }
  if (msg.kind === "queue") {
    store.get(["queue", "backoff"]).then(({ queue = [], backoff = 0 }) =>
      reply({ queued: queue.length, offline: !navigator.onLine || backoff > 0 }));
    return true;
  }
});

chrome.alarms.onAlarm.addListener(a => {
  if (a.name === "heartbeat") enqueue("heartbeat");
  if (a.name === "flush") flush();
});
chrome.runtime.onStartup.addListener(flush);

// Chrome itself lost focus (another app or window in front).
chrome.windows.onFocusChanged.addListener((windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) enqueue("focus_lost", "Chrome lost focus");
});

// Leaving the exam tab.
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const s = await getSession();
  const { examTabId = null } = await store.get("examTabId");
  if (s && s.active && examTabId !== null && tabId !== examTabId) {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    let where = "other tab";
    try {
      if (tab && tab.url) {
        const u = new URL(tab.url);
        where = u.protocol === "chrome-extension:" ? "Tapat page" : (u.hostname || where);
      }
    } catch (e) {}
    enqueue("tab_switch", where);
  }
});
chrome.tabs.onCreated.addListener(() => enqueue("tab_switch", "new tab"));

// Closing the exam tab without submitting ends the session, so the block list
// does not stay on after the quiz. It is logged so the professor can see it.
chrome.tabs.onRemoved.addListener(async (tabId) => {
  const s = await getSession();
  const { examTabId = null } = await store.get("examTabId");
  if (!s || !s.active || tabId !== examTabId) return;
  await enqueue("tab_switch", "closed the exam tab before submitting");
  await locked(async () => {
    const cur = await getSession();
    if (cur) await store.set({ session: { ...cur, active: false } });
  });
  chrome.alarms.clear("heartbeat");
  await disableBlocking();
});

// The embedded Form frame lands on .../formResponse after submit.
chrome.webNavigation.onCompleted.addListener(async (d) => {
  const s = await getSession();
  const { examTabId = null } = await store.get("examTabId");
  if (s && s.active && d.tabId === examTabId && d.url.includes("formResponse")) endSession("formResponse");
}, { url: [{ hostEquals: "docs.google.com" }] });
