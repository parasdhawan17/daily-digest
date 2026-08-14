#!/usr/bin/env bash
# Local dev server using project venv (macOS system Python is PEP 668–managed).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -x ".venv/bin/python3" ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/python3 scripts/dev_server.py
