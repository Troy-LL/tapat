const params = new URLSearchParams(location.search);
const email = params.get("email");
let form = params.get("form") || "";
document.getElementById("who").textContent = email;

function embedUrl(u) {
  const url = new URL(u);
  url.searchParams.set("embedded", "true");
  return url.toString();
}

document.getElementById("agree").onclick = async () => {
  const session = await chrome.runtime.sendMessage({ kind: "start", email, formUrl: form });
  document.getElementById("who").textContent = `${email} · session ${session.id}`;
  chrome.runtime.sendMessage({ kind: "examTab" });
  document.getElementById("consent").hidden = true;
  const frame = document.getElementById("form");
  frame.src = embedUrl(form);
  frame.hidden = false;
};
