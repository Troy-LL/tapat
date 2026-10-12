// Shared settings for the Tapat extension.
const TAPAT_SERVER = "http://localhost:8000";
const HEARTBEAT_SECONDS = 10;
// Sites blocked while an exam session is active (regex on the full URL).
const BLOCK_LIST = [
  { label: "chatgpt.com", regex: "^https?://([a-z0-9-]+\\.)*(chatgpt\\.com|chat\\.openai\\.com)/" },
  { label: "gemini.google.com", regex: "^https?://gemini\\.google\\.com/" },
  { label: "claude.ai", regex: "^https?://([a-z0-9-]+\\.)*claude\\.ai/" },
  { label: "Word Online / office.com", regex: "^https?://([a-z0-9-]+\\.)*(office\\.com|officeapps\\.live\\.com)/" },
  { label: "Google Docs", regex: "^https?://docs\\.google\\.com/document/" },
  { label: "PDF file", regex: "^[^?#]*\\.pdf([?#].*)?$" }
];
