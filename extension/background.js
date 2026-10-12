// Tapat service worker: blocking, focus logging, submit detection, heartbeat.
importScripts("config.js");

async function getSession() {
  const { session } = await chrome.storage.local.get("session");
  return session || null;
}

async function send(type, detail = "") {
  const s = await getSession();
  if (!s || !s.active) return;
  const body = { session_id: s.id, student: s.email, type, detail, ts: Date.now() / 1000 };
  try {
    await fetch(`${TAPAT_SERVER}/events`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
  } catch (e) {
    // Server unreachable: the missing heartbeats show up as "Monitor silent".
  }
}

async function enableBlocking() {
  const blockPage = chrome.runtime.getURL("blocked.html");
  const rules = BLOCK_LIST.map((b, i) => ({
    id: i + 1,
    priority: 1,
    action: { type: "redirect", redirect: { regexSubstitution: `${blockPage}#\\0` } },
    condition: { regexFilter: b.regex, resourceTypes: ["main_frame", "sub_frame"] }
  }));
  const old = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({
    removeRuleIds: old.map(r => r.id), addRules: rules
  });
}

async function disableBlocking() {
  const old = await chrome.declarativeNetRequest.getDynamicRules();
  await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: old.map(r => r.id) });
}

async function startSession(email, formUrl) {
  const session = {
    id: crypto.randomUUID(), email: email.trim().toLowerCase(), formUrl, active: true, examTabId: null
  };
  await chrome.storage.local.set({ session });
  await enableBlocking();
  chrome.alarms.create("heartbeat", { periodInMinutes: HEARTBEAT_SECONDS / 60 });
  await send("heartbeat", "session started");
  return session;
}

async function endSession(reason) {
  await send("submitted", reason);
  const s = await getSession();
  if (s) await chrome.storage.local.set({ session: { ...s, active: false } });
  chrome.alarms.clear("heartbeat");
  await disableBlocking();
}

chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg.kind === "start") {
    startSession(msg.email, msg.formUrl).then(reply);
    return true;
  }
  if (msg.kind === "examTab") {
    getSession().then(s => s && chrome.storage.local.set({ session: { ...s, examTabId: sender.tab.id } }));
  }
  if (msg.kind === "blocked") send("blocked_url", msg.url);
  if (msg.kind === "status") { getSession().then(reply); return true; }
});

chrome.alarms.onAlarm.addListener(a => { if (a.name === "heartbeat") send("heartbeat"); });

// Chrome itself lost focus (another app or window in front).
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) send("focus_lost", "Chrome lost focus");
});

// Leaving the exam tab.
chrome.tabs.onActivated.addListener(async ({ tabId }) => {
  const s = await getSession();
  if (s && s.active && s.examTabId !== null && tabId !== s.examTabId) {
    const tab = await chrome.tabs.get(tabId).catch(() => null);
    send("tab_switch", tab && tab.url ? new URL(tab.url).hostname : "other tab");
  }
});
chrome.tabs.onCreated.addListener(() => send("tab_switch", "new tab"));

// The embedded Form frame lands on .../formResponse after submit.
chrome.webNavigation.onCompleted.addListener(async (d) => {
  const s = await getSession();
  if (s && s.active && d.tabId === s.examTabId && d.url.includes("formResponse")) {
    endSession("formResponse");
  }
}, { url: [{ hostEquals: "docs.google.com" }] });
