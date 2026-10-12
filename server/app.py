"""Tapat teacher server: receives monitor events and shows the dashboard."""
import csv
import io
import os
import sqlite3
import time
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, File, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("TAPAT_DB", os.path.join(os.path.dirname(__file__), "tapat.db"))
SILENT_GAP = 25  # seconds without a heartbeat before "Monitor silent"
EVENT_TYPES = {"tab_switch", "focus_lost", "blocked_url", "app_opened", "heartbeat", "submitted"}

app = FastAPI(title="Tapat")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY, session_id TEXT, student TEXT,
            type TEXT, detail TEXT, ts REAL)"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS responses(
            email TEXT PRIMARY KEY, submitted_at TEXT)"""
    )
    return conn


class Event(BaseModel):
    session_id: str
    student: str
    type: str
    detail: str = ""
    ts: float | None = None


@app.post("/events")
def post_event(ev: Event):
    if ev.type not in EVENT_TYPES:
        return {"ok": False, "error": f"unknown type {ev.type}"}
    with db() as conn:
        conn.execute(
            "INSERT INTO events(session_id, student, type, detail, ts) VALUES (?,?,?,?,?)",
            (ev.session_id, ev.student.strip().lower(), ev.type, ev.detail[:300], ev.ts or time.time()),
        )
    return {"ok": True}


@app.get("/sessions/{session_id}")
def session_state(session_id: str):
    """Polled by the desktop watcher; 'closed' once the Form is submitted."""
    with db() as conn:
        row = conn.execute(
            "SELECT 1 FROM events WHERE session_id=? AND type='submitted' LIMIT 1", (session_id,)
        ).fetchone()
        known = conn.execute("SELECT 1 FROM events WHERE session_id=? LIMIT 1", (session_id,)).fetchone()
    return {"session_id": session_id, "state": "closed" if row else ("open" if known else "unknown")}


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    """Import the Google Form responses CSV. Needs 'Collect email addresses' on."""
    text = (await file.read()).decode("utf-8-sig")
    count = import_rows(text)
    return RedirectResponse(f"/dashboard?imported={count}", status_code=303)


def import_rows(text: str) -> int:
    reader = csv.DictReader(io.StringIO(text))
    email_col = next((c for c in (reader.fieldnames or []) if "email" in c.lower()), None)
    if not email_col:
        return 0
    ts_col = next((c for c in reader.fieldnames if "timestamp" in c.lower()), None)
    n = 0
    with db() as conn:
        for r in reader:
            email = (r.get(email_col) or "").strip().lower()
            if email:
                conn.execute(
                    "INSERT OR REPLACE INTO responses(email, submitted_at) VALUES (?,?)",
                    (email, r.get(ts_col, "") if ts_col else ""),
                )
                n += 1
    return n


def summarize(now: float | None = None):
    now = now or time.time()
    with db() as conn:
        events = conn.execute("SELECT * FROM events ORDER BY ts").fetchall()
        responses = {r["email"]: r["submitted_at"] for r in conn.execute("SELECT * FROM responses")}
    students: dict[str, dict] = {}
    for e in events:
        s = students.setdefault(e["student"], {
            "email": e["student"], "counts": {t: 0 for t in EVENT_TYPES}, "timeline": [],
            "last_beat": None, "first": e["ts"], "submitted": False, "silent_gaps": 0,
        })
        if e["type"] == "heartbeat":
            if s["last_beat"] and e["ts"] - s["last_beat"] > SILENT_GAP:
                s["silent_gaps"] += 1
                s["timeline"].append((s["last_beat"], "monitor_silent", f"no heartbeat for {int(e['ts'] - s['last_beat'])}s"))
            s["last_beat"] = e["ts"]
        else:
            s["timeline"].append((e["ts"], e["type"], e["detail"]))
        s["counts"][e["type"]] += 1
        if e["type"] == "submitted":
            s["submitted"] = True
    rows = []
    for s in students.values():
        flags = []
        if s["counts"]["blocked_url"]:
            flags.append("Blocked site")
        if s["counts"]["app_opened"]:
            flags.append("App opened")
        if s["counts"]["tab_switch"] + s["counts"]["focus_lost"] >= 3:
            flags.append("Left exam")
        live_gap = (not s["submitted"]) and s["last_beat"] and now - s["last_beat"] > SILENT_GAP
        if s["silent_gaps"] or live_gap:
            flags.append("Monitor silent")
        s["flags"] = flags
        s["in_form"] = s["email"] in responses
        rows.append(s)
    for email, at in responses.items():
        if email not in students:
            rows.append({"email": email, "counts": {t: 0 for t in EVENT_TYPES}, "timeline": [],
                         "flags": ["No session"], "submitted": True, "in_form": True, "first": None})
    return sorted(rows, key=lambda r: r["email"])


def fmt(ts):
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S") if ts else "-"


CSS = """
body{font-family:Inter,Segoe UI,Helvetica,Arial,sans-serif;margin:0;background:#f5f7fb;color:#111}
header{background:#1F3A8A;color:#fff;padding:18px 28px;display:flex;justify-content:space-between;align-items:center}
header h1{margin:0;font-size:22px}header span{opacity:.8;font-size:13px}
main{padding:20px 28px}
.bar{display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap}
.bar a{padding:6px 12px;border-radius:16px;background:#e3e8f5;color:#1F3A8A;text-decoration:none;font-size:13px}
.bar a.on{background:#1F3A8A;color:#fff}
form.imp{margin-left:auto;font-size:13px}
table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px #0001}
th,td{padding:10px 12px;text-align:left;font-size:13px;border-bottom:1px solid #eef}
th{background:#eef2fb;color:#1F3A8A}
.flag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;margin:1px;background:#fde2e2;color:#9b1c1c}
.flag.No{background:#1F3A8A;color:#fff}.clean{color:#127a3a;font-weight:600}
details summary{cursor:pointer;color:#1F3A8A}
ol.tl{margin:6px 0;padding-left:18px;font-size:12px;color:#333}
"""


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(flag: str = Query("all"), q: str = Query(""), imported: int | None = None):
    rows = summarize()
    if q:
        rows = [r for r in rows if q.lower() in r["email"]]
    if flag == "flagged":
        rows = [r for r in rows if r["flags"]]
    elif flag == "clean":
        rows = [r for r in rows if not r["flags"]]
    elif flag == "nosession":
        rows = [r for r in rows if "No session" in r["flags"]]
    tabs = "".join(
        f'<a class="{"on" if flag == k else ""}" href="/dashboard?flag={k}">{v}</a>'
        for k, v in [("all", "All"), ("flagged", "Flagged"), ("clean", "Clean"), ("nosession", "No session")]
    )
    body = []
    for r in rows:
        c = r["counts"]
        flags = "".join(f'<span class="flag {escape(f.split()[0])}">{escape(f)}</span>' for f in r["flags"]) or '<span class="clean">Clean</span>'
        tl = "".join(f"<li>{fmt(t)} · <b>{escape(k)}</b> {escape(d)}</li>" for t, k, d in r["timeline"])
        tl_html = f"<details><summary>{len(r['timeline'])} events</summary><ol class='tl'>{tl}</ol></details>" if tl else "-"
        body.append(
            f"<tr><td>{escape(r['email'])}</td><td>{fmt(r['first'])}</td><td>{c['tab_switch']}</td><td>{c['focus_lost']}</td>"
            f"<td>{c['blocked_url']}</td><td>{c['app_opened']}</td><td>{'Yes' if r['submitted'] else 'No'}</td>"
            f"<td>{flags}</td><td>{tl_html}</td></tr>"
        )
    note = f"<p>Imported {imported} Form responses.</p>" if imported is not None else ""
    return f"""<!doctype html><html><head><meta charset=utf-8><title>Tapat dashboard</title><style>{CSS}</style></head>
<body><header><h1>Tapat · Teacher dashboard</h1><span>{len(rows)} students</span></header><main>{note}
<div class="bar">{tabs}<form method=get action=/dashboard><input name=q placeholder="Search email" value="{escape(q)}"></form>
<form class=imp method=post action=/import enctype=multipart/form-data>Form responses CSV: <input type=file name=file accept=.csv> <button>Import</button></form></div>
<table><tr><th>Student</th><th>Started</th><th>Tab switches</th><th>Focus lost</th><th>Blocked</th><th>Apps</th><th>Submitted</th><th>Flags</th><th>Timeline</th></tr>
{''.join(body) or '<tr><td colspan=9>No sessions yet.</td></tr>'}</table></main></body></html>"""
