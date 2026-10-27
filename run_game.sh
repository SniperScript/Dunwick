#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python"
PARENT_VENV_PYTHON="$SCRIPT_DIR/../.venv/bin/python"

if [ -x "$VENV_PYTHON" ]; then
    exec "$VENV_PYTHON" "$SCRIPT_DIR/main.py" "$@"
elif [ -x "$PARENT_VENV_PYTHON" ]; then
    exec "$PARENT_VENV_PYTHON" "$SCRIPT_DIR/main.py" "$@"
else
    exec python3 "$SCRIPT_DIR/main.py" "$@"
fi
