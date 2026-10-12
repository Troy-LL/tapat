"""Tapat server: receives monitor events and serves the professor's admin pages."""
import csv
import os
import io
import hmac
import secrets
import time
from datetime import datetime, timedelta, timezone
from html import escape

from fastapi import Cookie, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import auth
import db

SILENT_GAP = 25  # seconds without a heartbeat before "Monitor silent"
EVENT_TYPES = {"tab_switch", "focus_lost", "blocked_url", "app_opened", "heartbeat", "submitted"}
MANILA = timezone(timedelta(hours=8))
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

app = FastAPI(title="Tapat")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])
db.init()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")


# ---------- student and extension API ----------

class StartRequest(BaseModel):
    code: str
    token: str
    email: str


class Event(BaseModel):
    session_id: str
    session_token: str
    type: str
    seq: int  # per-session counter from the extension; resends are ignored
    student: str = ""  # informational; the server uses the email bound to the session
    detail: str = ""
    ts: float | None = None  # client time when it happened, kept even if sent much later


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/start")
def start_session(req: StartRequest):
    """Start link (quiz code + quiz token) plus email -> a session token for this student only."""
    q = get_quiz(req.code)
    if not q or not hmac.compare_digest(req.token.encode(), q["token"].encode()):
        return JSONResponse({"ok": False, "error": "Start link is not valid"}, status_code=403)
    email = req.email.strip().lower()
    if "@" not in email:
        return JSONResponse({"ok": False, "error": "Enter your school email"}, status_code=400)
    sid, tok = secrets.token_hex(12), secrets.token_urlsafe(24)
    with db.connect() as c:
        c.execute("INSERT INTO sessions(id, token, quiz, email, created) VALUES (?,?,?,?,?)",
                  (sid, tok, q["code"], email, time.time()))
    return {"ok": True, "session_id": sid, "session_token": tok, "form_url": q["form_url"],
            "title": q["title"], "quiz": q["code"]}


def get_session(sid: str, token: str):
    with db.connect() as c:
        s = c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if s and hmac.compare_digest(token.encode(), s["token"].encode()):
        return s
    return None


@app.post("/events")
def post_event(ev: Event):
    if ev.type not in EVENT_TYPES:
        return JSONResponse({"ok": False, "error": f"unknown type {ev.type}"}, status_code=400)
    s = get_session(ev.session_id, ev.session_token)
    if not s:
        return JSONResponse({"ok": False, "error": "bad session token"}, status_code=403)
    now = time.time()
    with db.connect() as c:
        cur = c.execute(
            "INSERT INTO events(quiz, session_id, seq, student, type, detail, ts, received) VALUES (?,?,?,?,?,?,?,?) "
            "ON CONFLICT (session_id, seq) DO NOTHING",
            (s["quiz"], s["id"], ev.seq, s["email"], ev.type, ev.detail[:300], ev.ts or now, now),
        )
    return {"ok": True, "duplicate": cur.rowcount == 0}


@app.get("/sessions/{session_id}")
def session_state(session_id: str):
    """Polled by the desktop watcher; 'closed' once the Form is submitted."""
    with db.connect() as c:
        done = c.execute("SELECT 1 FROM events WHERE session_id=? AND type='submitted' LIMIT 1", (session_id,)).fetchone()
        known = c.execute("SELECT 1 FROM sessions WHERE id=?", (session_id,)).fetchone()
    return {"session_id": session_id, "state": "closed" if done else ("open" if known else "unknown")}


@app.get("/q/{code}", response_class=HTMLResponse)
def student_start(code: str, request: Request, t: str = ""):
    q = get_quiz(code)
    if not q or not hmac.compare_digest(t.encode(), q["token"].encode()):
        return page("Quiz not found", "<div class=card><h2>This start link is not valid.</h2>"
                    "<p>Ask your professor for the link again.</p></div>", 404)
    body = f"""<div class=card style="max-width:620px"><h2>{escape(q['title'])}</h2>
<p>This quiz is taken through the Tapat Chrome extension.</p>
<ol><li>Install the Tapat extension your professor shared.</li>
<li>Copy this page's address from the address bar.</li>
<li>Click the Tapat icon, paste the link under <b>Start link</b>, enter your school email, and click <b>Open exam</b>.</li></ol>
<p class=muted>Use the same email you will use in the Google Form.</p></div>"""
    return page(q["title"], body)


# ---------- data ----------

def get_quiz(code: str):
    with db.connect() as c:
        return c.execute("SELECT * FROM quizzes WHERE code=?", (code.upper(),)).fetchone()


def new_code() -> str:
    while True:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        if not get_quiz(code):
            return code


def create_quiz(title: str, form_url: str) -> str:
    code = new_code()
    with db.connect() as c:
        c.execute("INSERT INTO quizzes(code, token, title, form_url, created) VALUES (?,?,?,?,?)",
                  (code, secrets.token_urlsafe(9), title.strip() or "Quiz", form_url.strip(), time.time()))
    return code


def import_rows(quiz: str, text: str) -> int:
    """Read the Google Form responses CSV. Needs 'Collect email addresses' on."""
    reader = csv.DictReader(io.StringIO(text))
    email_col = next((h for h in (reader.fieldnames or []) if "email" in h.lower()), None)
    if not email_col:
        return 0
    ts_col = next((h for h in reader.fieldnames if "timestamp" in h.lower()), None)
    n = 0
    with db.connect() as c:
        for r in reader:
            email = (r.get(email_col) or "").strip().lower()
            if email:
                c.execute(
                    "INSERT INTO responses(quiz, email, submitted_at) VALUES (?,?,?) "
                    "ON CONFLICT (quiz, email) DO UPDATE SET submitted_at = excluded.submitted_at",
                    (quiz, email, r.get(ts_col, "") if ts_col else ""),
                )
                n += 1
    return n


def delete_logs(quiz: str):
    with db.connect() as c:
        c.execute("DELETE FROM events WHERE quiz=?", (quiz,))
        c.execute("DELETE FROM responses WHERE quiz=?", (quiz,))
        c.execute("DELETE FROM sessions WHERE quiz=?", (quiz,))


def summarize(quiz: str, now: float | None = None):
    now = now or time.time()
    with db.connect() as c:
        events = c.execute("SELECT * FROM events WHERE quiz=? ORDER BY ts, seq", (quiz,)).fetchall()
        responses = {r["email"]: r["submitted_at"] for r in c.execute("SELECT * FROM responses WHERE quiz=?", (quiz,))}
    students: dict[str, dict] = {}
    for e in events:
        s = students.setdefault(e["student"], {
            "email": e["student"], "counts": {t: 0 for t in EVENT_TYPES}, "timeline": [],
            "last_beat": None, "first": e["ts"], "submitted": False, "silent_gaps": 0, "offline_gaps": 0, "late_since_beat": False, "n_events": 0,
        })
        s["last"] = e["ts"]
        late = (e["received"] or e["ts"]) - e["ts"] > SILENT_GAP
        if e["type"] == "heartbeat":
            if s["last_beat"] and e["ts"] - s["last_beat"] > SILENT_GAP:
                gap = int(e["ts"] - s["last_beat"])
                # A gap closed by events that arrived late was the student being
                # offline: the extension queued everything and sent it afterward.
                if late or s["late_since_beat"]:
                    s["offline_gaps"] += 1
                    s["timeline"].append((s["last_beat"], "offline_gap", f"offline for {gap}s, synced later"))
                else:
                    s["silent_gaps"] += 1
                    s["timeline"].append((s["last_beat"], "monitor_silent", f"no heartbeat for {gap}s"))
            s["last_beat"] = e["ts"]
            s["late_since_beat"] = False
        else:
            s["timeline"].append((e["ts"], e["type"], e["detail"]))
            s["n_events"] += 1
            s["late_since_beat"] = s.get("late_since_beat") or late
        s["counts"][e["type"]] += 1
        if e["type"] == "submitted":
            s["submitted"] = True
    rows = []
    for s in students.values():
        s["timeline"].sort(key=lambda item: item[0])
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
        elif s["offline_gaps"]:
            flags.append("Offline gap, synced later")
        s["flags"] = flags
        rows.append(s)
    for email in responses:
        if email not in students:
            rows.append({"email": email, "counts": {t: 0 for t in EVENT_TYPES}, "timeline": [],
                         "flags": ["No session"], "submitted": True, "first": None, "last": None, "n_events": 0})
    return sorted(rows, key=lambda r: r["email"])


# ---------- HTML ----------

def fmt(ts, full=False):
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts, MANILA).strftime("%b %d, %I:%M:%S %p" if full else "%I:%M:%S %p")


ACCENT = "#1F3A8A"
CSS = """
*{box-sizing:border-box}
body{font-family:Inter,Segoe UI,Helvetica,Arial,sans-serif;margin:0;background:#fff;color:#14161a}
header{background:#1F3A8A;color:#fff;padding:12px 24px;display:flex;justify-content:space-between;align-items:center}
header .brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:18px;color:#fff;text-decoration:none}
header .brand img{height:28px;width:28px;border-radius:6px;background:#fff}
header nav a{color:#fff;font-size:13px;margin-left:16px;opacity:.9}
main{padding:24px;max-width:1100px;margin:0 auto}
h2{font-size:16px;margin:0 0 10px;color:#14161a}
section{border:1px solid #e3e6ee;border-radius:8px;padding:16px 18px;margin-bottom:18px}
button,.btn{background:#1F3A8A;color:#fff;border:0;border-radius:6px;padding:8px 14px;font-size:14px;cursor:pointer;font-family:inherit}
button.danger{background:#b91c1c}button:disabled{opacity:.45;cursor:not-allowed}
input[type=text],input[type=url],input[type=password]{padding:8px 10px;border:1px solid #c9cedb;border-radius:6px;font-size:14px;font-family:inherit}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.link{flex:1;min-width:280px;font-family:Consolas,monospace;font-size:13px;background:#f4f6fa}
.muted{color:#5b6170;font-size:13px}.err{color:#b91c1c}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 12px;text-align:left;font-size:14px;border-bottom:1px solid #eceff4}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#5b6170}
tr.student{cursor:pointer}tr.student:hover{background:#f6f8fc}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600}
.chip.ok{background:#eceef2;color:#4a505c}.chip.silent{background:#fdf0d5;color:#8a5a00}.chip.offline{background:#f3ecdc;color:#6e5a2e}.chip.none{background:#fde2e2;color:#a61b1b}
.notes{color:#5b6170;font-size:12px}
tr.tl td{background:#fafbfd;padding:6px 12px 12px 28px}tr.tl ol{margin:0;padding-left:18px;font-size:13px}
.login{max-width:360px;margin:72px auto}
.list a{color:#1F3A8A}
"""


def page(title, body, status=200, nav=""):
    html = f"""<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content="width=device-width">
<title>{escape(title)} · Tapat</title><style>{CSS}</style></head>
<body><header><a class=brand href="/admin"><img src="/static/mark.png" alt="">Tapat</a><nav>{nav}</nav></header>
<main>{body}</main></body></html>"""
    return HTMLResponse(html, status_code=status)


ADMIN_NAV = '<a href="/admin">All quizzes</a><a href="/admin/logout">Log out</a>'


def require_admin(cookie):
    if not auth.valid_cookie(cookie):
        raise HTTPException(303, headers={"Location": "/admin/login"})


def start_link(request: Request, quiz) -> str:
    return str(request.base_url).rstrip("/") + f"/q/{quiz['code']}?t={quiz['token']}"


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/admin")


@app.get("/admin/login", response_class=HTMLResponse)
def login_page(error: str = ""):
    msg = {"1": "Wrong password.", "rate": "Too many tries. Wait 10 minutes and try again."}.get(error, "")
    if not auth.admin_password():
        msg = "ADMIN_PASSWORD is not set on the server."
    err = f"<p class=err>{msg}</p>" if msg else ""
    return page("Log in", f"""<section class=login><h2>Professor log in</h2>{err}
<form method=post action=/admin/login><p><input type=password name=password placeholder="Admin password" autofocus style="width:100%"></p>
<button>Log in</button></form></section>""")


@app.post("/admin/login")
def login(request: Request, password: str = Form("")):
    # Behind Render's proxy the real address is the last X-Forwarded-For entry.
    fwd = request.headers.get("x-forwarded-for", "")
    ip = fwd.split(",")[-1].strip() if fwd else (request.client.host if request.client else "?")
    if auth.too_many_tries(ip):
        return RedirectResponse("/admin/login?error=rate", status_code=303)
    if not auth.check_password(password):
        auth.record_fail(ip)
        return RedirectResponse("/admin/login?error=1", status_code=303)
    auth.clear_fails(ip)
    r = RedirectResponse("/admin", status_code=303)
    r.set_cookie(auth.COOKIE, auth.make_cookie(), max_age=auth.MAX_AGE, httponly=True, samesite="lax",
                 secure=request.url.scheme == "https")
    return r


@app.get("/admin/logout")
def logout():
    r = RedirectResponse("/admin/login", status_code=303)
    r.delete_cookie(auth.COOKIE)
    return r


@app.get("/admin", response_class=HTMLResponse)
def admin_home(tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    with db.connect() as c:
        quizzes = c.execute("SELECT * FROM quizzes ORDER BY created DESC").fetchall()
        counts = {r["quiz"]: r["n"] for r in c.execute("SELECT quiz, COUNT(*) AS n FROM sessions GROUP BY quiz")}
    rows = "".join(
        f"<tr><td><a href='/admin/quiz/{q['code']}'>{escape(q['title'])}</a></td>"
        f"<td>{counts.get(q['code'], 0)}</td><td>{fmt(q['created'], True)}</td></tr>" for q in quizzes
    ) or "<tr><td colspan=3 class=muted>No quizzes yet.</td></tr>"
    body = f"""<section><h2>New quiz</h2>
<form method=post action=/admin/quiz class=row><input type=text name=title placeholder="Quiz title" required style="width:220px">
<input type=url name=form_url placeholder="Google Form link" required style="flex:1;min-width:280px"><button>Create quiz</button></form>
<p class=muted>Turn on Collect email addresses in the Form first. Tapat matches students by email.</p></section>
<section class=list><h2>Quizzes</h2><table><tr><th>Quiz</th><th>Sessions</th><th>Created (Manila)</th></tr>{rows}</table></section>"""
    return page("Admin", body, nav=ADMIN_NAV)


@app.post("/admin/quiz")
def admin_create(title: str = Form(...), form_url: str = Form(...), tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    if not form_url.strip().startswith("https://docs.google.com/forms/"):
        raise HTTPException(400, "Paste a Google Forms link (https://docs.google.com/forms/...)")
    code = create_quiz(title, form_url)
    return RedirectResponse(f"/admin/quiz/{code}", status_code=303)


def status_chip(flags):
    if "No session" in flags:
        return '<span class="chip none">No session</span>'
    if "Monitor silent" in flags:
        return '<span class="chip silent">Monitor silent</span>'
    if "Offline gap, synced later" in flags:
        return '<span class="chip offline">Offline gap, synced later</span>'
    return '<span class="chip ok">OK</span>'


@app.get("/admin/quiz/{code}", response_class=HTMLResponse)
def admin_quiz(code: str, request: Request, imported: int | None = None, deleted: int = 0,
               tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    quiz = get_quiz(code)
    if not quiz:
        raise HTTPException(404, "No quiz with that code")
    code = quiz["code"]
    trs = []
    for i, r in enumerate(summarize(code)):
        notes = ", ".join(f for f in r["flags"] if f not in ("No session", "Monitor silent", "Offline gap, synced later"))
        tl = "".join(f"<li>{fmt(t)} · <b>{escape(k)}</b> {escape(d)}</li>" for t, k, d in r["timeline"]) \
            or "<li class=muted>No events. This student submitted the Form without Tapat.</li>"
        trs.append(
            f"<tr class=student onclick=\"document.getElementById('tl{i}').hidden^=1\"><td>{escape(r['email'])}</td>"
            f"<td>{r['n_events']}</td><td>{fmt(r['last'])}</td><td>{status_chip(r['flags'])}</td>"
            f"<td class=notes>{escape(notes)}</td></tr><tr class=tl id=tl{i} hidden><td colspan=5><ol>{tl}</ol></td></tr>"
        )
    link = start_link(request, quiz)
    msg = ""
    if imported is not None:
        msg = f"<p class=muted>Imported {imported} responses.</p>"
    if deleted:
        msg = "<p class=muted>All logs for this quiz were deleted.</p>"
    body = f"""<h1 style="font-size:22px;margin:0 0 16px">{escape(quiz['title'])}</h1>
<section><h2>Start link</h2><div class=row><input class=link id=link type=text readonly value="{escape(link)}">
<button id=copy onclick="navigator.clipboard.writeText(document.getElementById('link').value).then(()=>{{this.textContent='Copied';setTimeout(()=>this.textContent='Copy start link',2000)}})">Copy start link</button></div>
<p class=muted>Send this link to the class. Students paste it into the Tapat extension.</p></section>
<section><h2>Students</h2><table><tr><th>Email</th><th>Events</th><th>Last event (Manila)</th><th>Status</th><th>Notes</th></tr>
{''.join(trs) or '<tr><td colspan=5 class=muted>No students yet.</td></tr>'}</table>
<p class=muted>Click a row to see its timeline.</p></section>
<section><h2>Import responses</h2>{msg}
<form method=post action="/admin/quiz/{code}/import" enctype=multipart/form-data class=row>
<input type=file name=file accept=.csv required><button>Import responses</button></form>
<p class=muted>Upload the Form's responses CSV after the quiz. Anyone who submitted without Tapat shows as No session.</p></section>
<section><h2>Delete logs</h2><form method=post action="/admin/quiz/{code}/delete" class=row>
<input type=text name=confirm placeholder="Type DELETE" autocomplete=off oninput="this.form.querySelector('button').disabled=this.value!=='DELETE'">
<button class=danger disabled>Delete logs</button></form>
<p class=muted>Removes every event, session and imported response for this quiz. Do this after grading.</p></section>
<section><h2>Delete quiz</h2><form method=post action="/admin/quiz/{code}/delete-quiz" class=row>
<input type=text name=confirm placeholder="Type DELETE" autocomplete=off oninput="this.form.querySelector('button').disabled=this.value!=='DELETE'">
<button class=danger disabled>Delete quiz</button></form>
<p class=muted>Removes this quiz, its start link and all of its logs. Students can no longer start it.</p></section>"""
    return page(quiz["title"], body, nav=ADMIN_NAV)


@app.post("/admin/quiz/{code}/import")
async def admin_import(code: str, file: UploadFile = File(...), tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    n = import_rows(code.upper(), (await file.read()).decode("utf-8-sig"))
    return RedirectResponse(f"/admin/quiz/{code.upper()}?imported={n}", status_code=303)


@app.post("/admin/quiz/{code}/delete")
def admin_delete(code: str, confirm: str = Form(""), tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    if confirm != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm")
    delete_logs(code.upper())
    return RedirectResponse(f"/admin/quiz/{code.upper()}?deleted=1", status_code=303)


@app.post("/admin/quiz/{code}/delete-quiz")
def admin_delete_quiz(code: str, confirm: str = Form(""), tapat_admin: str | None = Cookie(None)):
    require_admin(tapat_admin)
    if confirm != "DELETE":
        raise HTTPException(400, "Type DELETE to confirm")
    code = code.upper()
    delete_logs(code)
    with db.connect() as c:
        c.execute("DELETE FROM quizzes WHERE code=?", (code,))
    return RedirectResponse("/admin", status_code=303)
