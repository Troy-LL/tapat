// Run with: node --test extension/tests
// The block list must catch Google Docs but never the Google Form itself.
const test = require("node:test");
const assert = require("node:assert");
const { BLOCK_LIST, parseStartLink } = require("../config.js");

const blocked = (url) => BLOCK_LIST.some((b) => new RegExp(b.regex).test(url));

test("Google Docs documents are blocked", () => {
  assert.ok(blocked("https://docs.google.com/document/d/1abc/edit"));
});

test("Google Forms are never blocked", () => {
  for (const url of [
    "https://docs.google.com/forms/d/e/1FAIpQLSf/viewform?embedded=true",
    "https://docs.google.com/forms/d/e/1FAIpQLSf/formResponse",
    "https://docs.google.com/forms/d/e/1FAIpQLSf/viewform?usp=pp_url&entry.1=report.pdf",
  ]) assert.ok(!blocked(url), url);
});

test("listed sites are blocked", () => {
  for (const url of [
    "https://chatgpt.com/", "https://chat.openai.com/c/1", "https://gemini.google.com/app",
    "https://claude.ai/new", "https://www.office.com/launch/word", "https://example.com/notes/lesson1.pdf",
  ]) assert.ok(blocked(url), url);
});

test("unlisted sites stay open", () => {
  assert.ok(!blocked("https://www.google.com/search?q=api+gateway"));
});

test("start links parse", () => {
  assert.deepStrictEqual(parseStartLink("https://tapat-xrg5.onrender.com/q/q7k2pm?t=abc"),
    { server: "https://tapat-xrg5.onrender.com", code: "Q7K2PM", token: "abc" });
  assert.strictEqual(parseStartLink("https://tapat-xrg5.onrender.com/q/Q7K2PM"), null);
  assert.strictEqual(parseStartLink("not a link"), null);
});
