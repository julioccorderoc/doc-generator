#!/usr/bin/env bash
# Pre-sync the Python virtual environment so subsequent uv run calls skip installation.
# Run once per session before the first generation call. Idempotent — safe to re-run.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
uv sync --directory "$SCRIPT_DIR" --quiet 2>/dev/null
