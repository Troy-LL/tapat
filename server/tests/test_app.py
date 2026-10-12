import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TAPAT_DB"] = "/tmp/tapat_test.db"
os.environ["ADMIN_PASSWORD"] = "test-only-password"
os.environ.pop("DATABASE_URL", None)
if os.path.exists("/tmp/tapat_test.db"):
    os.remove("/tmp/tapat_test.db")

from fastapi.testclient import TestClient  # noqa: E402

import app as tapat  # noqa: E402
import auth  # noqa: E402

c = TestClient(tapat.app)
QUIZ = tapat.create_quiz("Test quiz", "https://docs.google.com/forms/d/e/x/viewform")
TOKEN = tapat.get_quiz(QUIZ)["token"]


def start(email="a@x.edu", token=None):
    return c.post("/api/start", json={"code": QUIZ, "token": token or TOKEN, "email": email})


SEQ = {}


def ev(sess, t, detail="", ts=None, seq=None):
    if seq is None:
        seq = SEQ[sess["session_id"]] = SEQ.get(sess["session_id"], 0) + 1
    return c.post("/events", json={"session_id": sess["session_id"], "session_token": sess["session_token"],
                                   "type": t, "detail": detail, "ts": ts, "seq": seq})


A = start().json()


def login(client):
    return client.post("/admin/login", data={"password": "test-only-password"}, follow_redirects=False)


def test_start_needs_quiz_token():
    assert start(token="wrong").status_code == 403
    assert A["form_url"].endswith("/viewform") and A["session_token"]


def test_event_and_summary():
    assert ev(A, "blocked_url", "chatgpt.com").json()["ok"]
    row = [r for r in tapat.summarize(QUIZ) if r["email"] == "a@x.edu"][0]
    assert "Blocked site" in row["flags"]


def test_cannot_fake_events_for_classmate():
    forged = dict(A, session_token="guess")
    assert ev(forged, "heartbeat").status_code == 403
    # The email in the body is ignored; the session's own email is used.
    r = c.post("/events", json={"session_id": A["session_id"], "session_token": A["session_token"],
                                "student": "victim@x.edu", "type": "tab_switch", "seq": 999})
    assert r.status_code == 200
    assert "victim@x.edu" not in [r["email"] for r in tapat.summarize(QUIZ)]


def test_rejects_unknown_type():
    assert ev(A, "bogus").status_code == 400


def test_start_page_needs_token():
    assert c.get(f"/q/{QUIZ}?t={TOKEN}").status_code == 200
    assert c.get(f"/q/{QUIZ}?t=nope").status_code == 404


def test_session_closes_on_submit():
    s = start("c@x.edu").json()
    assert c.get("/sessions/unknown").json()["state"] == "unknown"
    assert c.get(f"/sessions/{s['session_id']}").json()["state"] == "open"
    ev(s, "submitted")
    assert c.get(f"/sessions/{s['session_id']}").json()["state"] == "closed"


def test_monitor_silent():
    s = start("b@x.edu").json()
    now = time.time()
    ev(s, "heartbeat", ts=now - 100)
    ev(s, "heartbeat", ts=now - 60)
    row = [r for r in tapat.summarize(QUIZ) if r["email"] == "b@x.edu"][0]
    assert "Monitor silent" in row["flags"]


def test_admin_requires_login():
    fresh = TestClient(tapat.app)
    r = fresh.get("/admin", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/login"
    assert fresh.get(f"/admin/quiz/{QUIZ}", follow_redirects=False).status_code == 303
    assert fresh.post(f"/admin/quiz/{QUIZ}/delete", data={"confirm": "DELETE"}, follow_redirects=False).status_code == 303


def test_forged_cookie_rejected():
    assert not auth.valid_cookie("9999999999.abc.deadbeef")
    fresh = TestClient(tapat.app)
    fresh.cookies.set(auth.COOKIE, "9999999999.abc.deadbeef")
    assert fresh.get("/admin", follow_redirects=False).status_code == 303


def test_login_rate_limited():
    auth._fails.clear()
    fresh = TestClient(tapat.app)
    for _ in range(auth.FAIL_LIMIT):
        r = fresh.post("/admin/login", data={"password": "nope"}, follow_redirects=False)
        assert "error=1" in r.headers["location"]
    r = login(fresh)  # even the right password is refused while locked out
    assert "error=rate" in r.headers["location"]
    auth._fails.clear()


def test_no_password_means_no_login(monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    assert not auth.check_password("")


def test_admin_create_quiz_and_page():
    auth._fails.clear()
    a = TestClient(tapat.app)
    assert login(a).headers["location"] == "/admin"
    r = a.post("/admin/quiz", data={"title": "Quiz 9", "form_url": "https://docs.google.com/forms/d/e/y/viewform"},
               follow_redirects=False)
    code = r.headers["location"].rsplit("/", 1)[1]
    html = a.get(f"/admin/quiz/{code}").text
    assert f"/q/{code}?t={tapat.get_quiz(code)['token']}" in html
    for label in ("Copy start link", "Import responses", "Delete logs", "Type DELETE"):
        assert label in html
    bad = a.post("/admin/quiz", data={"title": "x", "form_url": "https://example.com"}, follow_redirects=False)
    assert bad.status_code == 400


def test_csv_no_session_and_delete_logs():
    auth._fails.clear()
    a = TestClient(tapat.app)
    login(a)
    csv = "Timestamp,Email Address\n1,a@x.edu\n2,ghost@x.edu\n"
    a.post(f"/admin/quiz/{QUIZ}/import", files={"file": ("r.csv", csv, "text/csv")}, follow_redirects=False)
    rows = {r["email"]: r for r in tapat.summarize(QUIZ)}
    assert rows["ghost@x.edu"]["flags"] == ["No session"]
    assert "No session" not in rows["a@x.edu"]["flags"]
    assert a.post(f"/admin/quiz/{QUIZ}/delete", data={"confirm": "nope"}).status_code == 400
    a.post(f"/admin/quiz/{QUIZ}/delete", data={"confirm": "DELETE"}, follow_redirects=False)
    assert tapat.summarize(QUIZ) == []
    assert ev(A, "heartbeat").status_code == 403  # sessions were deleted too


def test_resend_is_deduped_by_session_and_seq():
    s = start("dup@x.edu").json()
    assert ev(s, "tab_switch", "new tab", seq=1).json()["duplicate"] is False
    assert ev(s, "tab_switch", "new tab", seq=1).json()["duplicate"] is True
    row = [r for r in tapat.summarize(QUIZ) if r["email"] == "dup@x.edu"][0]
    assert row["counts"]["tab_switch"] == 1


def test_queued_events_keep_client_time_and_order():
    s = start("order@x.edu").json()
    t = time.time() - 300
    # Sent out of order (as a retry might), each with its own client time.
    ev(s, "submitted", "formResponse", ts=t + 30, seq=3)
    ev(s, "focus_lost", "Chrome lost focus", ts=t + 10, seq=1)
    ev(s, "blocked_url", "chatgpt.com", ts=t + 20, seq=2)
    row = [r for r in tapat.summarize(QUIZ) if r["email"] == "order@x.edu"][0]
    assert [k for _, k, _ in row["timeline"]] == ["focus_lost", "blocked_url", "submitted"]
    with tapat.db.connect() as conn:
        got = conn.execute("SELECT ts, received FROM events WHERE session_id=? AND seq=1", (s["session_id"],)).fetchone()
    assert abs(got["ts"] - (t + 10)) < 0.01 and got["received"] > got["ts"] + 200


def test_offline_gap_synced_later_is_not_monitor_silent():
    s = start("offline@x.edu").json()
    t = time.time() - 600
    for i in range(0, 60, 10):
        ev(s, "heartbeat", ts=t + i)
    # Wifi drops for 90s. The queued summary heartbeat arrives late, then live beats resume.
    ev(s, "heartbeat", "9 heartbeats while offline", ts=t + 150)
    for i in range(160, 200, 10):
        ev(s, "heartbeat", ts=t + i)
    ev(s, "submitted", ts=t + 200)
    row = [r for r in tapat.summarize(QUIZ) if r["email"] == "offline@x.edu"][0]
    assert "Offline gap, synced later" in row["flags"]
    assert "Monitor silent" not in row["flags"]


def test_delete_quiz_removes_everything():
    auth._fails.clear()
    a = TestClient(tapat.app)
    login(a)
    code = tapat.create_quiz("Doomed", "https://docs.google.com/forms/d/e/z/viewform")
    tok = tapat.get_quiz(code)["token"]
    s = c.post("/api/start", json={"code": code, "token": tok, "email": "d@x.edu"}).json()
    ev(s, "heartbeat")
    a.post(f"/admin/quiz/{code}/import", files={"file": ("r.csv", "Email Address\nz@x.edu\n", "text/csv")})
    assert a.post(f"/admin/quiz/{code}/delete-quiz", data={"confirm": "nope"}).status_code == 400
    assert TestClient(tapat.app).post(f"/admin/quiz/{code}/delete-quiz", data={"confirm": "DELETE"},
                                      follow_redirects=False).headers["location"] == "/admin/login"
    r = a.post(f"/admin/quiz/{code}/delete-quiz", data={"confirm": "DELETE"}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    assert tapat.get_quiz(code) is None
    with tapat.db.connect() as conn:
        for table in ("events", "sessions", "responses"):
            assert conn.execute(f"SELECT COUNT(*) AS n FROM {table} WHERE quiz=?", (code,)).fetchone()["n"] == 0
    assert c.post("/api/start", json={"code": code, "token": tok, "email": "d@x.edu"}).status_code == 403
    assert "Doomed" not in a.get("/admin").text
