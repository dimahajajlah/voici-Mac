#!/usr/bin/env bash
# One-time setup for Intel Macs. Run from this folder:  bash setup_mac.sh
set -e

# One dependency (monotonic-alignment-search) has no prebuilt Intel-Mac wheel, so pip compiles it.
# That needs Apple's command line tools (a C compiler).
if ! xcode-select -p >/dev/null 2>&1; then
  echo "Apple command line tools are missing. An install window will open - finish it, then re-run this script."
  xcode-select --install || true
  exit 1
fi

# Need Python 3.10-3.12 (3.11 recommended). Newer versions have no compatible torch for Intel Macs.
PY=""
for c in python3.11 python3.12 python3.10; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "No Python 3.10-3.12 found."
  echo "Install Python 3.11 from https://www.python.org/downloads/macos/ (or: brew install python@3.11), then re-run."
  exit 1
fi
echo "Using $($PY --version)"

$PY -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo
echo "Setup done. Test your install with:"
echo "  source .venv/bin/activate && python voiceclone.py --check"
