#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -x .venv/bin/python ]; then
    echo "Desktop environment is missing. Run:"
    echo "  uv venv --python 3.13 .venv"
    echo "  uv pip install --python .venv/bin/python -r requirements-desktop.txt"
    exit 1
fi

exec .venv/bin/python main.py
