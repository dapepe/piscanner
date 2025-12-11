# Canon DR-F120 Button Setup Guide

Complete guide for configuring the Canon DR-F120 physical scan button to trigger ADF Duplex scans automatically.

## Overview

This setup allows you to:
- Press the **green START button** on your Canon DR-F120 scanner
- Automatically scan both sides of documents (ADF Duplex mode)
- Upload scanned documents to your configured API endpoint
- Everything runs automatically on system startup

---

## System Components

### 1. **scanbd** - Scanner Button Daemon
- Monitors scanner hardware buttons
- Detects button press events
- Triggers configured actions

### 2. **piscan** - Scanner Control Server  
- HTTP API server on port 5000
- Handles scan requests
- Manages scanning, blank page detection, and uploading

### 3. **SANE** - Scanner Access Now Easy
- Provides scanner hardware access
- Uses network backend to coordinate with scanbd

---

## Configuration Files

| File | Purpose |
|------|---------|
| `/etc/scanbd/scanbd.conf` | scanbd main configuration - defines button actions |
| `/etc/scanbd/scan.sh` | Script executed when START button is pressed |
| `/etc/sane.d/dll.conf` | SANE backends for normal apps (uses `net` backend) |
| `/etc/sane.d/net.conf` | Network connection to scanbd |
| `/etc/scanbd/sane.d/dll.conf` | Real backends used by scanbd (includes `canon_dr`) |
| `/etc/udev/rules.d/90-canon-scanner.rules` | USB device permissions |
| `/opt/piscan/config/config.yaml` | Piscan scanner and API configuration |
| `/etc/systemd/system/piscan.service` | Auto-start service for piscan |

---

## How It Works

```
┌─────────────────┐
│  Press GREEN    │
│  START Button   │
└────────┬────────┘
         │
         v
┌─────────────────┐
│    scanbd       │  Monitors button via SANE
│  (detects press)│
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│  /etc/scanbd/scan.sh            │
│  curl POST                      │
│  {"source": "ADF Duplex"}       │
│  -> http://localhost:5000/scan  │
└────────┬────────────────────────┘
         │
         v
┌─────────────────┐
│  piscan server  │  HTTP API server
│  (port 5000)    │
└────────┬────────┘
         │
         v
┌─────────────────────────────────┐
│  1. Scan with scanimage         │
│     - Device: net:localhost:     │
│       canon_dr                   │
│     - Source: ADF Duplex         │
│     - Resolution: 300 DPI        │
│     - Mode: Color                │
│                                  │
│  2. Detect & remove blank pages  │
│                                  │
│  3. Upload to API                │
│     scan.haider.vc/difo/api/...  │
└──────────────────────────────────┘
```

---

## scanbd Configuration

**File:** `/etc/scanbd/scanbd.conf`

```c
global {
    debug   = true
    debug-level = 7
    
    user    = saned
    group   = scanner
    
    saned   = "/usr/sbin/saned"
    saned_opt  = {}
    saned_env  = { "SANE_CONFIG_DIR=/etc/scanbd/sane.d" }
    
    scriptdir = /etc/scanbd
    timeout = 500
    pidfile = "/var/run/scanbd.pid"
    
    environment {
        device = "SCANBD_DEVICE"
        action = "SCANBD_ACTION"
    }
    
    multiple_actions = true
    
    # Trigger on START button (green button)
    action scan {
        filter = "^start$"            # Button name from SANE
        numerical-trigger {
            from-value = 0            # Button released
            to-value   = 1            # Button pressed
        }
        desc   = "Scan button (green start button)"
        script = "/etc/scanbd/scan.sh"
    }
}

device canon_dr {
    filter = "^canon_dr.*"
    desc = "Canon DR-F120"
}
```

**Key Points:**
- `filter = "^start$"` - Matches the START button specifically
- `numerical-trigger` - Triggers on button press (0→1 transition)
- `script = "/etc/scanbd/scan.sh"` - Script to execute

---

## Button Trigger Script

**File:** `/etc/scanbd/scan.sh`

```bash
#!/bin/bash
# Piscan: Trigger ADF Duplex scan when button is pressed

# Log the event
logger -t "scanbd" "Scan button pressed (action: $SCANBD_ACTION, device: $SCANBD_DEVICE) - triggering ADF Duplex scan"

# Trigger piscan ADF Duplex scan
curl -X POST -H "Content-Type: application/json" \
     -d '{"source": "ADF Duplex"}' \
     "http://localhost:5000/scan" \
     2>&1 | logger -t "scanbd"

logger -t "scanbd" "Scan trigger sent to piscan"
```

**Permissions:**
```bash
chmod +x /etc/scanbd/scan.sh
```

---

## Piscan Configuration

**File:** `/opt/piscan/config/config.yaml`

```yaml
scanner:
  device: "net:localhost:canon_dr"  # Stable device identifier
  resolution: 300
  mode: "Color"
  source: "ADF Duplex"              # Default scan mode
  format: "png"

api:
  workspace: "difo"
  url: "https://scan.haider.vc"
  token: "your-api-token-here"
  timeout: 60

processing:
  skip_blank: true
  blank_threshold: 0.03
  white_threshold: 250

server:
  host: "0.0.0.0"
  port: 5000
  debug: false

logging:
  level: "INFO"
  file: "/var/log/piscan.log"
  max_size: 10485760
  backup_count: 5
```

---

## Auto-Start Services

Both services are configured to start automatically on boot.

### piscan Service

**File:** `/etc/systemd/system/piscan.service`

```ini
[Unit]
Description=Piscan Scanner Server
After=network.target scanbd.service
Requires=scanbd.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/piscan
ExecStart=/usr/bin/python3 -m piscan.cli server
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Commands:**
```bash
# Enable auto-start
sudo systemctl enable piscan

# Start/stop/restart
sudo systemctl start piscan
sudo systemctl stop piscan
sudo systemctl restart piscan

# Check status
sudo systemctl status piscan

# View logs
sudo journalctl -u piscan -f
```

### scanbd Service

scanbd is automatically enabled by the setup script.

**Commands:**
```bash
# Check status
sudo systemctl status scanbd

# Restart
sudo systemctl restart scanbd

# View logs
sudo journalctl -u scanbd -f
```

---

## Testing the Setup

### 1. **Check Services Are Running**

```bash
sudo systemctl status scanbd
sudo systemctl status piscan
```

Both should show `Active: active (running)`.

### 2. **Test Button Detection**

Monitor scanbd logs while pressing the button:

```bash
sudo journalctl -u scanbd -f | grep -E "start|scan.sh"
```

Press the green START button. You should see:
```
scanbd: trigger action for start for device canon_dr:libusb:001:XXX with script /etc/scanbd/scan.sh
scanbd: waiting for child: /etc/scanbd/scan.sh
```

### 3. **Test Complete Workflow**

1. **Monitor logs:**
   ```bash
   # Terminal 1 - scanbd logs
   sudo journalctl -u scanbd -f
   
   # Terminal 2 - piscan logs  
   sudo journalctl -u piscan -f
   ```

2. **Load paper** in the ADF (both sides will be scanned)

3. **Press the green START button**

4. **Watch the process:**
   - scanbd detects button press
   - Triggers /etc/scanbd/scan.sh
   - Script calls piscan API
   - Piscan scans documents (ADF Duplex)
   - Removes blank pages
   - Uploads to API

### 4. **Manual API Test**

Test the API directly without using the button:

```bash
curl -X POST http://localhost:5000/scan \
     -H "Content-Type: application/json" \
     -d '{"source": "ADF Duplex"}'
```

---

## Troubleshooting

### Button Press Not Detected

**Check if scanbd is running:**
```bash
sudo systemctl status scanbd
ps aux | grep scanbd
```

**Test button detection manually:**
```bash
# Stop the service
sudo systemctl stop scanbd

# Run in foreground with debug output
sudo scanbd -f -d7

# Press button and watch output
# Press Ctrl+C to stop
```

**Check button values:**
```bash
watch -n 0.5 'scanimage -d net:localhost:canon_dr -A 2>&1 | grep -A 1 "start"'
```

Press button and watch for value change from `[no]` to `[yes]`.

### Scan Triggered But Fails

**Check piscan logs:**
```bash
tail -50 /var/log/piscan.log
```

**Common issues:**
- No paper in ADF
- Scanner device changed (USB number)
- API credentials incorrect

**Test scanner directly:**
```bash
scanimage -d net:localhost:canon_dr \
          --source "ADF Duplex" \
          --resolution 300 \
          --mode Color \
          --format=png \
          --batch=/tmp/test_%03d.png
```

### Services Not Starting After Reboot

**Check service status:**
```bash
sudo systemctl status piscan
sudo systemctl status scanbd
```

**Re-enable if needed:**
```bash
sudo systemctl enable piscan
sudo systemctl enable scanbd
```

**Check logs for errors:**
```bash
sudo journalctl -u piscan --since today
sudo journalctl -u scanbd --since today
```

### USB Device Number Changes

The configuration uses stable identifiers that work regardless of USB device number changes:

**Piscan config uses:** `net:localhost:canon_dr`  
**NOT:** `canon_dr:libusb:001:004` (which would change)

**If you need to verify:**
```bash
# Check what scanimage sees
scanimage -L

# Should show: net:localhost:canon_dr:libusb:001:XXX
```

---

## Available Scanner Buttons

The Canon DR-F120 has multiple buttons that can be configured:

| Button Name | Description | Current Config |
|-------------|-------------|----------------|
| `start` | Big green button / small 1 button | ✅ Configured for ADF Duplex scan |
| `stop` | Small orange button / small 2 button | ❌ Not configured |
| `button-3` | Small 3 button | ❌ Not configured |
| `newfile` | New File button | ❌ Not configured |
| `countonly` | Count Only button | ❌ Not configured |
| `bypassmode` | Bypass Mode button | ❌ Not configured |

### Adding More Button Actions

To configure additional buttons, edit `/etc/scanbd/scanbd.conf`:

```c
# Example: Configure STOP button
action stop_scan {
    filter = "^stop$"
    numerical-trigger {
        from-value = 0
        to-value   = 1
    }
    desc   = "Stop button"
    script = "/etc/scanbd/stop.sh"
}
```

Then create `/etc/scanbd/stop.sh` with your desired action.

---

## Monitoring and Logs

### System Logs

**scanbd logs:**
```bash
# Follow in real-time
sudo journalctl -u scanbd -f

# Last 50 lines
sudo journalctl -u scanbd -n 50

# Since specific time
sudo journalctl -u scanbd --since "1 hour ago"
```

**piscan logs:**
```bash
# Follow in real-time
sudo journalctl -u piscan -f

# Application log file
tail -f /var/log/piscan.log

# Last 100 lines
tail -100 /var/log/piscan.log
```

### HTTP API Endpoints

Test piscan API directly:

```bash
# Health check
curl http://localhost:5000/health

# Scanner status
curl http://localhost:5000/status | python3 -m json.tool

# Scanner info
curl http://localhost:5000/scanner/info | python3 -m json.tool

# Configuration
curl http://localhost:5000/config | python3 -m json.tool
```

---

## Summary: What Was Configured

✅ **scanbd daemon** - Monitors scanner hardware buttons  
✅ **Button action** - Green START button triggers ADF Duplex scan  
✅ **Trigger script** - `/etc/scanbd/scan.sh` calls piscan API  
✅ **piscan service** - Auto-starts on boot, provides HTTP API  
✅ **Stable device names** - Works across reboots and power cycles  
✅ **Auto-start** - Everything starts automatically on system boot  
✅ **Logging** - Comprehensive logs for troubleshooting  

---

## Quick Reference

**Start/restart services:**
```bash
sudo systemctl restart scanbd
sudo systemctl restart piscan
```

**Check if working:**
```bash
sudo systemctl status scanbd piscan
curl http://localhost:5000/health
```

**Watch logs:**
```bash
sudo journalctl -u scanbd -u piscan -f
```

**Test button:**
1. Load paper in ADF
2. Press green START button
3. Watch logs for activity

---

## Next Steps

1. ✅ Services are running and enabled
2. ✅ Button triggers ADF Duplex scans
3. ✅ Scans upload to API automatically
4. ✅ Everything survives reboots

**You're all set! Just press the button to scan!** 🟢
