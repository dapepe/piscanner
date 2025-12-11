# Scanning Logs - How to Monitor Your Canon DR-F120

## Quick View: Last Scan

```bash
tail -20 /var/log/scanbd-scan.log
```

## Watch Scans in Real-Time

```bash
tail -f /var/log/scanbd-scan.log
```

---

## Log Locations

### **Scan Button Activity** 
**File:** `/var/log/scanbd-scan.log`

Shows:
- When button was pressed
- Scan progress
- Number of pages scanned
- Upload status
- Any errors

**Example output:**
```
2025-12-11 10:36:02 - === Scan button pressed - starting ADF Duplex scan ===
2025-12-11 10:36:02 - Device: canon_dr:libusb:001:004
2025-12-11 10:36:02 - Scan directory: /tmp/scan-2025-12-11-103602
2025-12-11 10:36:02 - Starting scan (ADF Duplex, 300 DPI, Color)...
2025-12-11 10:36:19 - ✓ Scanned 2 pages
2025-12-11 10:36:19 - Uploading to https://scan.haider.vc/difo/api/document/
2025-12-11 10:36:31 - ✓ Upload successful
2025-12-11 10:36:31 - === Scan complete ===
```

---

### **scanbd Daemon Logs** 
**Command:** `sudo journalctl -u scanbd -f`

Shows:
- Button detection events
- Device monitoring
- Script execution
- Low-level scanner events

---

### **piscan Service Logs** 
**Command:** `sudo journalctl -u piscan -f`  
**File:** `/var/log/piscan.log`

Shows:
- HTTP API requests
- Scanner operations (if using API)
- Service status

---

## Common Log Commands

### View last scan
```bash
tail -20 /var/log/scanbd-scan.log
```

### Watch scans live
```bash
tail -f /var/log/scanbd-scan.log
```

### Check for errors
```bash
grep ERROR /var/log/scanbd-scan.log
```

### View today's scans
```bash
grep "$(date +%Y-%m-%d)" /var/log/scanbd-scan.log
```

### Count scans today
```bash
grep -c "Scan button pressed" /var/log/scanbd-scan.log | grep "$(date +%Y-%m-%d)"
```

### View all logs together
```bash
tail -f /var/log/scanbd-scan.log & sudo journalctl -u scanbd -f
```

### Search system logs for scan activity
```bash
sudo journalctl --since today | grep -i "scan\|upload"
```

---

## Log Rotation

The scan log will grow over time. To manage it:

```bash
# View log size
ls -lh /var/log/scanbd-scan.log

# Manually clear (if needed)
sudo truncate -s 0 /var/log/scanbd-scan.log

# Or move to backup
sudo mv /var/log/scanbd-scan.log /var/log/scanbd-scan.log.bak
sudo touch /var/log/scanbd-scan.log
sudo chmod 666 /var/log/scanbd-scan.log
```

---

## Troubleshooting with Logs

### No logs appearing?
```bash
# Check if log file exists
ls -l /var/log/scanbd-scan.log

# Check permissions
sudo chmod 666 /var/log/scanbd-scan.log

# Restart scanbd
sudo systemctl restart scanbd
```

### Scan fails?
```bash
# Look for ERROR in logs
grep ERROR /var/log/scanbd-scan.log | tail -5

# Check last scan attempt
tail -30 /var/log/scanbd-scan.log
```

### Button not responding?
```bash
# Check scanbd status
sudo systemctl status scanbd

# Watch for button presses
sudo journalctl -u scanbd -f | grep "trigger action"
```

---

## Summary

**Primary log for button scans:** `/var/log/scanbd-scan.log`

**Quick command:**
```bash
tail -f /var/log/scanbd-scan.log
```

Press the button and watch your scans happen in real-time! 🟢
