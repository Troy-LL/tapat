"""Tapat desktop watcher: logs which watched apps come to the front.

Only app names are sent, never window titles. Exits when the exam
session is closed on the server (the student submitted the Form).
"""
import argparse
import json
import platform
import subprocess
import sys
import time
import urllib.request

DEFAULT_APPS = ["Microsoft Word", "WINWORD", "Notes", "Notepad", "Preview", "Acrobat", "AcroRd32"]


def frontmost_app() -> str | None:
    system = platform.system()
    if system == "Darwin":
        out = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get name of first process whose frontmost is true'],
            capture_output=True, text=True,
        )
        return out.stdout.strip() or None
    if system == "Windows":
        import psutil
        import win32gui
        import win32process
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            return psutil.Process(pid).name().removesuffix(".exe")
        except psutil.Error:
            return None
    return None


def matches(app: str, watched: list[str]) -> str | None:
    for name in watched:
        if name.lower() in app.lower():
            return name
    return None


def post(server, body):
    req = urllib.request.Request(f"{server}/events", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=3).read()


def session_state(server, session_id) -> str:
    with urllib.request.urlopen(f"{server}/sessions/{session_id}", timeout=3) as r:
        return json.load(r)["state"]


def main(argv=None):
    p = argparse.ArgumentParser(description="Tapat desktop watcher")
    p.add_argument("--email", required=True)
    p.add_argument("--session", required=True, help="session id from the exam page")
    p.add_argument("--token", required=True, help="session token from the exam page")
    p.add_argument("--server", default="https://tapat.onrender.com")
    p.add_argument("--apps", default=",".join(DEFAULT_APPS), help="comma-separated app names to watch")
    a = p.parse_args(argv)
    watched = [x.strip() for x in a.apps.split(",") if x.strip()]
    last = None
    tick = 0
    print(f"Tapat watcher running for {a.email}. Watching: {', '.join(watched)}")
    while True:
        app = frontmost_app()
        hit = matches(app, watched) if app else None
        if hit and hit != last:
            try:
                post(a.server, {"session_id": a.session, "session_token": a.token, "student": a.email, "type": "app_opened",
                                "detail": hit, "ts": time.time()})
            except OSError:
                pass
        last = hit
        tick += 1
        if tick % 5 == 0:
            try:
                if session_state(a.server, a.session) == "closed":
                    print("Session closed. Watcher exiting.")
                    return 0
            except OSError:
                pass
        time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
