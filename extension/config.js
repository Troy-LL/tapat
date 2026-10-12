// Shared settings for the Tapat extension.
// Default hosted server. Change it after deploying (see docs/deploy.md);
// a start link from any server also works, since it carries its own address.
const DEFAULT_SERVER = "https://tapat-xrg5.onrender.com";
const HEARTBEAT_SECONDS = 10;

// Sites blocked while an exam session is active. These are RE2 regexes on the
// full URL. Google Forms (docs.google.com/forms/...) must never match.
const BLOCK_LIST = [
  { label: "chatgpt.com", regex: "^https?://([a-z0-9-]+\\.)*(chatgpt\\.com|chat\\.openai\\.com)/" },
  { label: "gemini.google.com", regex: "^https?://gemini\\.google\\.com/" },
  { label: "claude.ai", regex: "^https?://([a-z0-9-]+\\.)*claude\\.ai/" },
  { label: "Word Online / office.com", regex: "^https?://([a-z0-9-]+\\.)*(office\\.com|officeapps\\.live\\.com)/" },
  { label: "Google Docs", regex: "^https?://docs\\.google\\.com/document/" },
  { label: "PDF file", regex: "^[^?#]*\\.pdf([?#].*)?$" }
];

// Start links look like https://<server>/q/<CODE>?t=<quiz token>
function parseStartLink(text) {
  let url;
  try { url = new URL(text.trim()); } catch (e) { return null; }
  const m = url.pathname.match(/^\/q\/([A-Za-z0-9]+)\/?$/);
  const token = url.searchParams.get("t");
  if (!m || !token) return null;
  return { server: url.origin, code: m[1].toUpperCase(), token };
}

if (typeof module !== "undefined") module.exports = { BLOCK_LIST, parseStartLink, DEFAULT_SERVER };
