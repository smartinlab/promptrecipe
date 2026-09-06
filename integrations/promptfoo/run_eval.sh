#!/usr/bin/env bash
# Run the eval against the repository's own interpreter.
#
# promptfoo spawns `python3` from PATH, which on macOS is the system 3.9 —
# below this project's 3.11 floor. Pointing it at the repo venv is the whole
# job of this script.
set -euo pipefail
cd "$(dirname "$0")"

VENV="$(cd ../.. && pwd)/.venv/bin/python"
if [ -z "${PROMPTFOO_PYTHON:-}" ] && [ -x "$VENV" ]; then
  export PROMPTFOO_PYTHON="$VENV"
fi

echo "python: ${PROMPTFOO_PYTHON:-python3 (from PATH)}"
exec npx promptfoo eval "$@"
