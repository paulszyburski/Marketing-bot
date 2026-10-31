#!/bin/bash
set -euo pipefail

readonly PROJECT_DIR="/home/paul/Projects/Marketing-bot"

cd "$PROJECT_DIR"
exec env PYTHONPATH="$PROJECT_DIR/src" \
    "$PROJECT_DIR/.venv/bin/python" -m automation.main
