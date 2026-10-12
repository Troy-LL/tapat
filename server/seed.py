"""Create a demo quiz (code DEMO01) with three sample students."""
import os
import time

import db
from app import import_rows

QUIZ = "DEMO01"
FORM = "https://docs.google.com/forms/d/e/1FAIpQLSdemo/viewform"


def main():
    db.init()
    with db.connect() as c:
        for t in ("events", "responses", "sessions"):
            c.execute(f"DELETE FROM {t} WHERE quiz=?", (QUIZ,))
        c.execute("DELETE FROM quizzes WHERE code=?", (QUIZ,))
        c.execute("INSERT INTO quizzes(code, token, title, form_url, created) VALUES (?,?,?,?,?)",
                  (QUIZ, "demo-token", "INTE301 Quiz 2", FORM, time.time() - 3600))
        t0 = time.time() - 1200
        rows = []
        a, b = "student.a@school.edu", "student.b@school.edu"
        for sid, email in (("s-a", a), ("s-b", b)):
            c.execute("INSERT INTO sessions(id, token, quiz, email, created) VALUES (?,?,?,?,?)",
                      (sid, "seed-" + sid, QUIZ, email, t0))
        for i in range(0, 600, 10):  # Student A: clean run
            rows.append((QUIZ, "s-a", a, "heartbeat", "", t0 + i))
        rows.append((QUIZ, "s-a", a, "submitted", "formResponse", t0 + 600))
        t1 = t0 + 30  # Student B: left the exam, ChatGPT blocked, Word opened, silent gap
        for i in list(range(0, 200, 10)) + list(range(260, 700, 10)):
            rows.append((QUIZ, "s-b", b, "heartbeat", "", t1 + i))
        rows += [
            (QUIZ, "s-b", b, "focus_lost", "Chrome lost focus", t1 + 95),
            (QUIZ, "s-b", b, "tab_switch", "new tab", t1 + 120),
            (QUIZ, "s-b", b, "blocked_url", "chatgpt.com", t1 + 124),
            (QUIZ, "s-b", b, "app_opened", "Microsoft Word", t1 + 300),
            (QUIZ, "s-b", b, "tab_switch", "returned to exam", t1 + 330),
            (QUIZ, "s-b", b, "submitted", "formResponse", t1 + 700),
        ]
        # Student D: wifi dropped for about 90 seconds; the extension queued a
        # focus change and the heartbeats, then sent them when back online.
        d = "student.d@school.edu"
        c.execute("INSERT INTO sessions(id, token, quiz, email, created) VALUES (?,?,?,?,?)",
                  ("s-d", "seed-s-d", QUIZ, d, t0))
        t2 = t0 + 60
        back_online = t2 + 345
        for i in list(range(0, 250, 10)) + [340] + list(range(350, 640, 10)):
            rows.append((QUIZ, "s-d", d, "heartbeat", "4 heartbeats while offline" if i == 340 else "", t2 + i))
        rows.append((QUIZ, "s-d", d, "focus_lost", "Chrome lost focus", t2 + 300))
        rows.append((QUIZ, "s-d", d, "submitted", "formResponse", t2 + 640))

        def received(sid, ts):
            # Queued while offline -> received when the wifi came back.
            return back_online + 2 if sid == "s-d" and t2 + 250 < ts <= back_online else ts + 0.3

        rows = [(q, sid, n, who, t, det, ts, received(sid, ts)) for n, (q, sid, who, t, det, ts) in enumerate(rows)]
        c.executemany("INSERT INTO events(quiz, session_id, seq, student, type, detail, ts, received) "
                      "VALUES (?,?,?,?,?,?,?,?)", rows)
    # Student C is in the Form CSV but never ran Tapat (took it in incognito).
    import_rows(QUIZ, open(os.path.join(os.path.dirname(__file__), "sample_responses.csv")).read())
    print(f"seeded quiz {QUIZ}")


if __name__ == "__main__":
    main()
