// Shown after the service worker sees a blocked navigation (it already logged it).
document.getElementById("site").textContent = decodeURIComponent(location.hash.slice(1)) || "blocked site";
document.getElementById("back").onclick = async () => {
  const s = await chrome.runtime.sendMessage({ kind: "status" });
  if (s && s.examTabId) chrome.tabs.update(s.examTabId, { active: true });
  window.close();
};
