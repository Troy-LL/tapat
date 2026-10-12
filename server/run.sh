#!/usr/bin/env bash
# Start Tapat locally on http://localhost:8000 (add --seed for demo data).
# The admin password comes from ADMIN_PASSWORD. If it is not set, a random
# one is made for this run and printed below.
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
if [ -z "$ADMIN_PASSWORD" ]; then
  export ADMIN_PASSWORD="$(.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(9))')"
  echo "Admin password for this run: $ADMIN_PASSWORD"
fi
[ "$1" = "--seed" ] && .venv/bin/python seed.py
exec .venv/bin/uvicorn app:app --host 127.0.0.1 --port "${PORT:-8000}"
