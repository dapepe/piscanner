#!/bin/bash
# PiScan Button Diagnostic Tool

LOG_FILE="/var/log/scanbd-scan.log"
SCANBD_LOG="/var/log/syslog" # Or journal

echo "=== PiScan Diagnostic Tool ==="
echo "Date: $(date)"

# 1. Check Hardware
echo -n "1. USB Device: "
if lsusb | grep -q "Canon.*DR-F120"; then
    echo "DETECTED"
    lsusb | grep "Canon.*DR-F120"
else
    echo "NOT FOUND"
    echo "   -> Check USB cable and power."
fi

# 2. Check SANE detection
echo -n "2. SANE Device: "
DEVICES=$(scanimage -L 2>/dev/null)
if echo "$DEVICES" | grep -q "Canon"; then
    echo "DETECTED"
    echo "$DEVICES" | grep "Canon"
else
    echo "NOT FOUND"
    echo "   -> Scanner not recognized by SANE."
fi

# 3. Check Service Status
echo -n "3. scanbd Service: "
if systemctl is-active --quiet scanbd; then
    echo "RUNNING"
else
    echo "STOPPED"
fi

echo -n "4. Monitor Service: "
if systemctl is-active --quiet piscan-scanner-monitor; then
    echo "RUNNING"
else
    echo "STOPPED"
fi

# 4. Check Logs for recent triggers
echo "5. Recent Button Events (Last 5):"
if [ -f "$LOG_FILE" ]; then
    grep "Scan button pressed" "$LOG_FILE" | tail -n 5 || echo "   No events found in $LOG_FILE"
else
    echo "   Log file not found: $LOG_FILE"
fi

echo "6. Recent Scan Errors (Last 5):"
if [ -f "$LOG_FILE" ]; then
    grep "ERROR" "$LOG_FILE" | tail -n 5 || echo "   No errors found"
else
    echo "   Log file not found"
fi

echo ""
echo "=== Live Monitor ==="
echo "Press CTRL+C to exit."
echo "Waiting for button press..."
echo "(Watch for 'Scan button pressed' below)"
tail -f "$LOG_FILE"
