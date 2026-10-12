#!/usr/bin/env bash
# Start the Tapat server on http://localhost:8000 (add --seed for demo data)
set -e
cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
[ "$1" = "--seed" ] && .venv/bin/python seed.py
exec .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
