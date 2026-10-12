"""Database access: Postgres when DATABASE_URL is set, SQLite otherwise.

Render's free disk is wiped on every deploy and restart, so the hosted
server keeps its data in a free Postgres database (Neon or Supabase).
Locally, a SQLite file is enough.
"""
import os
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
SQLITE_PATH = os.environ.get("TAPAT_DB", os.path.join(os.path.dirname(__file__), "tapat.db"))
IS_PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS quizzes(
        code TEXT PRIMARY KEY, token TEXT NOT NULL, title TEXT NOT NULL, form_url TEXT NOT NULL,
        created DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS sessions(
        id TEXT PRIMARY KEY, token TEXT NOT NULL, quiz TEXT NOT NULL, email TEXT NOT NULL,
        created DOUBLE PRECISION)""",
    """CREATE TABLE IF NOT EXISTS events(
        id {pk}, quiz TEXT, session_id TEXT, seq INTEGER, student TEXT,
        type TEXT, detail TEXT, ts DOUBLE PRECISION, received DOUBLE PRECISION,
        UNIQUE (session_id, seq))""",
    """CREATE TABLE IF NOT EXISTS responses(
        quiz TEXT, email TEXT, submitted_at TEXT, PRIMARY KEY (quiz, email))""",
    "CREATE INDEX IF NOT EXISTS events_quiz ON events(quiz)",
    "CREATE INDEX IF NOT EXISTS events_session ON events(session_id)",
]


class Conn:
    """Small wrapper so the app writes one SQL dialect (`?` placeholders)."""

    def __init__(self):
        if IS_PG:
            import psycopg
            from psycopg.rows import dict_row
            self.raw = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        else:
            self.raw = sqlite3.connect(SQLITE_PATH)
            self.raw.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        if IS_PG:
            sql = sql.replace("?", "%s")
        cur = self.raw.cursor()
        cur.execute(sql, params)
        return cur

    def executemany(self, sql, rows):
        if IS_PG:
            sql = sql.replace("?", "%s")
        self.raw.cursor().executemany(sql, rows)

    def __enter__(self):
        return self

    def __exit__(self, exc, *_):
        if exc:
            self.raw.rollback()
        else:
            self.raw.commit()
        self.raw.close()


def connect() -> Conn:
    return Conn()


def init():
    pk = "SERIAL PRIMARY KEY" if IS_PG else "INTEGER PRIMARY KEY"
    with connect() as c:
        for stmt in SCHEMA:
            c.execute(stmt.format(pk=pk))
