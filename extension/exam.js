const params = new URLSearchParams(location.search);
const email = params.get("email");
const link = params.get("link") || "";
document.getElementById("who").textContent = email;

function embedUrl(u) {
  const url = new URL(u);
  url.searchParams.set("embedded", "true");
  return url.toString();
}

document.getElementById("agree").onclick = async (e) => {
  e.target.disabled = true;
  const state = document.getElementById("state");
  state.hidden = false;
  state.textContent = "Starting… if the server is waking up, this can take a minute.";
  const res = await chrome.runtime.sendMessage({ kind: "start", email, link });
  state.hidden = true;
  if (!res || !res.ok) {
    e.target.disabled = false;
    document.getElementById("err").textContent = (res && res.error) || "Could not start the quiz.";
    return;
  }
  chrome.runtime.sendMessage({ kind: "examTab" });
  document.title = res.session.title;
  document.getElementById("who").textContent = `${email} · ${res.session.title}`;
  const w = document.getElementById("watch");
  w.hidden = false;
  w.onclick = async () => {
    const s = res.session;
    await navigator.clipboard.writeText(
      `python watcher.py --email ${s.email} --session ${s.id} --token ${s.token} --server ${s.server}`);
    w.textContent = "Copied";
  };
  document.getElementById("consent").hidden = true;
  const frame = document.getElementById("form");
  frame.src = embedUrl(res.session.formUrl);
  frame.hidden = false;
};
