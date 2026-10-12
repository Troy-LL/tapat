const target = decodeURIComponent(location.hash.slice(1));
let host = target;
try { host = new URL(target).hostname + new URL(target).pathname.slice(0, 40); } catch (e) {}
document.getElementById("site").textContent = host || "blocked site";
chrome.runtime.sendMessage({ kind: "blocked", url: host });
document.getElementById("back").onclick = async () => {
  const s = await chrome.runtime.sendMessage({ kind: "status" });
  if (s && s.examTabId) chrome.tabs.update(s.examTabId, { active: true });
  history.length > 1 ? history.back() : window.close();
};
