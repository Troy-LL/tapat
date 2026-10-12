import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ["TAPAT_DB"] = "/tmp/tapat_test.db"
if os.path.exists("/tmp/tapat_test.db"):
    os.remove("/tmp/tapat_test.db")
from fastapi.testclient import TestClient
import app as tapat

c = TestClient(tapat.app)

def ev(t, detail="", ts=None, sid="x1", who="a@x.edu"):
    return c.post("/events", json={"session_id": sid, "student": who, "type": t, "detail": detail, "ts": ts}).json()

def test_post_and_dashboard():
    assert ev("blocked_url", "chatgpt.com")["ok"]
    html = c.get("/dashboard").text
    assert "a@x.edu" in html and "Blocked site" in html

def test_rejects_unknown_type():
    assert not ev("bogus")["ok"]

def test_session_closes_on_submit():
    assert c.get("/sessions/x2").json()["state"] == "unknown"
    ev("heartbeat", sid="x2")
    assert c.get("/sessions/x2").json()["state"] == "open"
    ev("submitted", sid="x2")
    assert c.get("/sessions/x2").json()["state"] == "closed"

def test_monitor_silent():
    now = time.time()
    ev("heartbeat", ts=now - 100, sid="s3", who="b@x.edu")
    ev("heartbeat", ts=now - 60, sid="s3", who="b@x.edu")
    row = [r for r in tapat.summarize() if r["email"] == "b@x.edu"][0]
    assert "Monitor silent" in row["flags"]

def test_csv_no_session():
    csv = "Timestamp,Email Address\n1,a@x.edu\n2,ghost@x.edu\n"
    r = c.post("/import", files={"file": ("r.csv", csv, "text/csv")}, follow_redirects=False)
    assert r.status_code == 303
    rows = {r["email"]: r for r in tapat.summarize()}
    assert rows["ghost@x.edu"]["flags"] == ["No session"]
    assert "No session" not in rows["a@x.edu"]["flags"]
