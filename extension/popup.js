const $ = (id) => document.getElementById(id);

chrome.storage.local.get(["server", "lastEmail"]).then(({ server, lastEmail }) => {
  $("server").value = server || DEFAULT_SERVER;
  if (lastEmail) $("email").value = lastEmail;
});

$("save").onclick = async () => {
  await chrome.storage.local.set({ server: $("server").value.trim().replace(/\/$/, "") });
  $("save").textContent = "Saved";
};

// The free server sleeps when idle and can take about a minute to wake.
async function waitForServer(server) {
  const until = Date.now() + 120000;
  let first = true;
  for (;;) {
    try {
      const res = await fetch(`${server}/health`, { cache: "no-store" });
      if (res.ok) return true;
    } catch (e) { /* still waking */ }
    if (first) { $("state").hidden = false; $("state").textContent = "Server waking up… this can take a minute."; first = false; }
    if (Date.now() > until) return false;
    await new Promise(r => setTimeout(r, 3000));
  }
}

$("go").onclick = async () => {
  const email = $("email").value.trim();
  let link = $("link").value.trim();
  $("err").textContent = "";
  // A bare code like Q7K2PM?t=... is accepted with the saved server.
  if (link && !/^https?:/.test(link)) link = `${$("server").value.trim().replace(/\/$/, "")}/q/${link.replace(/^\/?q\//, "")}`;
  const parsed = parseStartLink(link);
  if (!parsed) return ($("err").textContent = "Paste the start link from your professor.");
  if (!/^\S+@\S+\.\S+$/.test(email)) return ($("err").textContent = "Enter your school email.");
  $("go").disabled = true;
  const up = await waitForServer(parsed.server);
  $("go").disabled = false;
  $("state").hidden = true;
  if (!up) return ($("err").textContent = "The Tapat server did not answer. Try again in a minute.");
  await chrome.storage.local.set({ lastEmail: email });
  const url = chrome.runtime.getURL(`exam.html?email=${encodeURIComponent(email)}&link=${encodeURIComponent(link)}`);
  chrome.tabs.create({ url });
  window.close();
};

// Queue status: shown while events are waiting to be sent.
async function showQueue() {
  const q = await chrome.runtime.sendMessage({ kind: "queue" });
  const el = $("queue");
  if (q && q.queued > 0 && q.offline) {
    el.hidden = false;
    el.textContent = `Offline, ${q.queued} events queued. They will send when you are back online.`;
  } else el.hidden = true;
}
showQueue();
setInterval(showQueue, 2000);
