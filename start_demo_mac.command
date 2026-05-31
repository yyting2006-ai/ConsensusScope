#!/bin/bash

cd "$(dirname "$0")" || {
  echo "Failed to enter the demo folder."
  read -r -p "Press Enter to close..."
  exit 1
}

echo "Starting ConsensusScope..."
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found."
  echo "Please install Python 3.10 or newer from https://www.python.org/downloads/"
  echo "Then double-click this file again."
  echo
  read -r -p "Press Enter to close..."
  exit 1
fi

if command -v lsof >/dev/null 2>&1 && lsof -ti tcp:8502 >/dev/null 2>&1; then
  echo "ConsensusScope already appears to be running."
  echo "Opening http://localhost:8502 ..."
  open "http://localhost:8502"
  echo
  read -r -p "Press Enter to close..."
  exit 0
fi

if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv || {
    echo "Failed to create virtual environment."
    read -r -p "Press Enter to close..."
    exit 1
  }
fi

source ".venv/bin/activate" || {
  echo "Failed to activate virtual environment."
  read -r -p "Press Enter to close..."
  exit 1
}

echo "Installing dependencies..."
python -m pip install -U pip || {
  echo "Failed to update pip."
  read -r -p "Press Enter to close..."
  exit 1
}

python -m pip install -r requirements.txt || {
  echo "Failed to install dependencies."
  read -r -p "Press Enter to close..."
  exit 1
}

echo
echo "Launching demo at http://localhost:8502"
echo "Keep this Terminal window open while using the demo."
echo

(sleep 4 && open "http://localhost:8502") &
streamlit run app/streamlit_app.py --server.port 8502

echo
read -r -p "Press Enter to close..."
