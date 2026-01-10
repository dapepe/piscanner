#!/bin/bash
# Poll scanner button status
DEVICE="canon_dr:libusb:003:003"
echo "Polling button status for $DEVICE..."

for i in {1..20}; do
    scanimage -d "$DEVICE" -A | grep -E "start|stop|button-3"
    sleep 1
done
