"""Admin login: one password from ADMIN_PASSWORD, kept in a signed cookie."""
import hashlib
import hmac
import os
import secrets
import time

COOKIE = "tapat_admin"
MAX_AGE = 12 * 3600


def admin_password() -> str:
    # Set only in the environment (Render dashboard or run.sh), never in the repo.
    return os.environ.get("ADMIN_PASSWORD", "")


def _secret() -> bytes:
    key = os.environ.get("SECRET_KEY") or ("tapat:" + admin_password())
    return key.encode()


def check_password(given: str) -> bool:
    pw = admin_password()
    return bool(pw) and hmac.compare_digest(given.encode(), pw.encode())


def make_cookie() -> str:
    expires = str(int(time.time()) + MAX_AGE)
    nonce = secrets.token_hex(8)
    payload = f"{expires}.{nonce}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def valid_cookie(value: str | None) -> bool:
    if not value or value.count(".") != 2:
        return False
    expires, nonce, sig = value.split(".")
    good = hmac.new(_secret(), f"{expires}.{nonce}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good) and expires.isdigit() and int(expires) > time.time()


# Login rate limit: 5 failed tries per address per 10 minutes.
FAIL_LIMIT = 5
FAIL_WINDOW = 600
_fails: dict[str, list[float]] = {}


def too_many_tries(ip: str) -> bool:
    now = time.time()
    _fails[ip] = [t for t in _fails.get(ip, []) if now - t < FAIL_WINDOW]
    return len(_fails[ip]) >= FAIL_LIMIT


def record_fail(ip: str):
    _fails.setdefault(ip, []).append(time.time())


def clear_fails(ip: str):
    _fails.pop(ip, None)
