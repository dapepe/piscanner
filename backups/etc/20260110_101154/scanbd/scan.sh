#!/bin/bash
# Piscan: scanbd action script
# Runs the same piscan Python pipeline used by CLI/service.

set -eo pipefail

PYTHON_BIN="/usr/bin/python3"
LOG_FILE_DEFAULT="/var/log/scanbd-scan.log"
LOG_FILE="${PISCAN_SCANBD_LOG:-$LOG_FILE_DEFAULT}"
CONFIG_PATH="${PISCAN_CONFIG:-/opt/piscan/config/config.yaml}"
SCAN_SCRIPT="/opt/piscan/scan.py"

# If /var/log isn't writable by the scanbd user, fall back
# to /tmp to avoid breaking button scans completely.
if ! touch "$LOG_FILE" 2>/dev/null; then
  LOG_FILE="/tmp/scanbd-scan.log"
  touch "$LOG_FILE" 2>/dev/null || true
fi

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') - $*" >> "$LOG_FILE" 2>/dev/null || logger -t "scanbd" "$*" || true
}

log "=== Scan button pressed - starting scan ==="
log "Config: $CONFIG_PATH"
log "scanbd: action=${SCANBD_ACTION:-unknown} device=${SCANBD_DEVICE:-unknown}"

if [ ! -x "$SCAN_SCRIPT" ]; then
  log "ERROR: Missing scan script: $SCAN_SCRIPT"
  exit 1
fi

if [ ! -x "$PYTHON_BIN" ]; then
  log "ERROR: Missing python binary: $PYTHON_BIN"
  exit 1
fi

# Run scan script (includes ZIP bundling + payload size logs)
# --debug prints key config (no secrets) into the scanbd log.
# -u forces unbuffered binary stdout/stderr so logs appear in real-time.
# We redirect directly to LOG_FILE to avoid bash buffering loop delays.
set +e
"$PYTHON_BIN" -u "$SCAN_SCRIPT" --config "$CONFIG_PATH" --debug >> "$LOG_FILE" 2>&1
rc=$?
set -e

if [ "$rc" -eq 0 ]; then
  log "✓ Scan completed successfully"
else
  log "ERROR: Scan failed (exit=$rc)"
fi

log "=== Scan complete ==="
exit "$rc"
