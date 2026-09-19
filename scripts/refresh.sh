#!/bin/bash
#
# REFRESH - the daily data update. Safe to run from cron.
#
# WHAT IT DOES
#   1. ingest.daily   appends today's NAV for funds we already hold
#   2. meter.job      recomputes every meter from the new prices
#
# In that order, because a meter computed before the new price arrives is a
# meter that is one day stale.
#
# WHY A LOCK, AND WHY mkdir
#   cron will happily start a second copy while the first is still running.
#   Two ingests writing the same rows at once is the kind of thing that looks
#   fine for months and then corrupts a day of data.
#
#   macOS has no flock. Worse, `if ! flock ...` returns TRUE when the command
#   is missing, so a flock-based guard would decide a run was already in
#   progress and skip every single night, silently.
#
#   mkdir is atomic on every POSIX system and needs no extra tool.
#
# WHY ABSOLUTE PATHS
#   cron runs with almost no environment - no PATH, no shell profile, not even
#   the right working directory. Anything relative works when you test it by
#   hand and silently fails at 23:30.

set -euo pipefail

PROJECT="/Users/my_folder/ai-agent/finishh-club"
PYTHON="/Users/my_folder/ai-agent/venv/bin/python"
LOG_DIR="$PROJECT/logs"
LOCK_DIR="/tmp/finishh-refresh.lock"
STALE_MINUTES=120

mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/refresh-$(date +%Y-%m-%d).log"

# A crashed run would leave the lock behind forever. Anything older than the
# longest plausible run is treated as abandoned.
if [ -d "$LOCK_DIR" ] && [ -n "$(find "$LOCK_DIR" -maxdepth 0 -mmin +$STALE_MINUTES 2>/dev/null)" ]; then
    echo "$(date '+%F %T')  removing stale lock" >> "$LOG"
    rmdir "$LOCK_DIR" 2>/dev/null || true
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$(date '+%F %T')  another refresh is still running, skipping" >> "$LOG"
    exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

cd "$PROJECT"

{
    echo "=============================================================="
    echo "refresh started  $(date '+%F %T %Z')"
    echo "=============================================================="

    echo "--- ingest.daily ---"
    "$PYTHON" -m ingest.daily

    echo "--- meter.job ---"
    "$PYTHON" -m meter.job

    echo "refresh finished $(date '+%F %T %Z')"
    echo
} >> "$LOG" 2>&1

# keep two weeks of logs, no more
find "$LOG_DIR" -name "refresh-*.log" -mtime +14 -delete 2>/dev/null || true
