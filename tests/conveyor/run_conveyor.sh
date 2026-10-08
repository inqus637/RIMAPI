#!/usr/bin/env bash
# RIMAPI autonomous test conveyor — full cycle runner.
#
# Boots RimWorld through Steam when needed, waits for the RIMAPI server on
# localhost:8765 (the smoke suite polls it itself), runs the smoke suite,
# and optionally closes the game afterwards.
#
# Usage:
#   ./run_conveyor.sh          run tests (launches RimWorld if not running)
#   ./run_conveyor.sh --quit   close RimWorld after the tests finish
set -euo pipefail

APP_ID=294100
SMOKE_TEST="$(dirname "$0")/smoke_test.py"

if ! pgrep -x RimWorldLinux >/dev/null; then
    echo "[conveyor] launching RimWorld via steam steam://rungameid/${APP_ID}"
    setsid steam "steam://rungameid/${APP_ID}" >/dev/null 2>&1 &
fi

echo "[conveyor] running smoke suite (server wait is built in, up to 180s)"
status=0
python3 "$SMOKE_TEST" || status=$?

if [[ "${1:-}" == "--quit" ]]; then
    pkill -x RimWorldLinux || true
    echo "[conveyor] RimWorld closed"
fi

exit "$status"
