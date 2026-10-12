"""Fill the database with three sample students for demos and screenshots."""
import os
import time

from app import EVENT_TYPES, db, import_rows

def main():
    with db() as conn:
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM responses")
        t0 = time.time() - 1200
        rows = []
        # Student A: clean run
        for i in range(0, 600, 10):
            rows.append(("s-a", "student.a@school.edu", "heartbeat", "", t0 + i))
        rows.append(("s-a", "student.a@school.edu", "submitted", "formResponse", t0 + 600))
        # Student B: tabs, ChatGPT block, Word, silent gap
        b = t0 + 30
        for i in list(range(0, 200, 10)) + list(range(260, 700, 10)):
            rows.append(("s-b", "student.b@school.edu", "heartbeat", "", b + i))
        rows += [
            ("s-b", "student.b@school.edu", "focus_lost", "Chrome lost focus", b + 95),
            ("s-b", "student.b@school.edu", "tab_switch", "new tab", b + 120),
            ("s-b", "student.b@school.edu", "blocked_url", "chatgpt.com", b + 124),
            ("s-b", "student.b@school.edu", "app_opened", "Microsoft Word", b + 300),
            ("s-b", "student.b@school.edu", "tab_switch", "returned to exam", b + 330),
            ("s-b", "student.b@school.edu", "submitted", "formResponse", b + 700),
        ]
        conn.executemany("INSERT INTO events(session_id, student, type, detail, ts) VALUES (?,?,?,?,?)", rows)
    # Student C: in the Form CSV but never ran Tapat (incognito)
    import_rows(open(os.path.join(os.path.dirname(__file__), "sample_responses.csv")).read())
    print("seeded")

if __name__ == "__main__":
    main()
