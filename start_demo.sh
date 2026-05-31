#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Please install Python 3.10 or newer, then run this script again."
  exit 1
fi

if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:8502 >/dev/null 2>&1; then
  echo "Port 8502 is already in use. Opening the existing demo page."
  if command -v open >/dev/null 2>&1; then
    open "http://localhost:8502"
  fi
  exit 0
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements.txt

if command -v open >/dev/null 2>&1; then
  (sleep 4 && open "http://localhost:8502") &
fi

streamlit run app/streamlit_app.py --server.port 8502
