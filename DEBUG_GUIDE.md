# PiScan Scanner & Button Debug Guide

This guide provides a summary of the scanner integration, the recent robustness improvements, and step-by-step instructions for troubleshooting issues with the Canon DR-F120 scanner and physical buttons.

## System Overview

The system consists of three main components that work together:

1.  **PiScan Application**: The core Python application (`scan.py`) that performs the scanning and uploading.
2.  **scanbd (Scanner Button Daemon)**: A background service that listens for physical button presses on the scanner.
3.  **Scanner Health Monitor**: A custom service (`piscan-scanner-monitor`) that checks connectivity and ensures services recover after power cycles.

### How it Works (The "Detach and Restart" Strategy)

Scanning and listening for buttons are mutually exclusive operations (only one process can access the USB device at a time). To handle this:

1.  **Idle State**: `scanbd` runs in the background, holding the scanner lock, waiting for button presses.
2.  **Button Press**:
    *   `scanbd` triggers `/etc/scanbd/scan.sh`.
    *   The script plays an **immediate feedback sound**.
    *   It spawns a background process and exits (to release `scanbd`).
3.  **Scan Sequence**:
    *   The background process **stops** `scanbd` and the `monitor` service.
    *   It runs the actual scan (`scan.py`) which now has exclusive access to the scanner.
    *   Upon completion, it **restarts** `scanbd` and the `monitor` service.

## Recent Improvements

*   **Robust Auto-Detection**: PiScan now finds the Canon DR-F120 regardless of which USB port it is plugged into (e.g., `libusb:001:004` vs `libusb:001:005`).
*   **Power-Cycle Recovery**: The health monitor detects when the scanner is turned off and on, automatically restarting `scanbd` so buttons work without a reboot.
*   **Service Wrapper**: `scanbd` is now run via a wrapper (`/usr/local/bin/scanbd-wrapper.sh`) to ensure correct environment variables for device detection.
*   **Dual Button Functions**:
    *   **Start (Green)**: Scans all pages (ADF Duplex).
    *   **Stop/Cancel (Orange)**: Scans a **single page** only.

---

## Troubleshooting & Debugging

### 1. The "One-Click" Diagnostic Tool

We have created a script that checks hardware connection, SANE detection, service status, and recent logs.

```bash
sudo /opt/piscan/check_button.sh
```

Run this first. If everything looks "Green" / "RUNNING" / "DETECTED", but it still fails, check the "Live Monitor" section at the end of the script output while pressing a button.

### 2. Common Issues & Solutions

#### Scanner not detected / "No devices found"
*   **Check Hardware**: Ensure USB cable is connected and scanner is powered on (Blue light).
*   **Check Permissions**: `ls -l /dev/bus/usb/003/XXX` (should be owned by `root:saned` or `root:scanner`).
*   **Test SANE**:
    ```bash
    scanimage -L
    ```
    *If `scanbd` is running, you should see `net:localhost:...`. If stopped, you should see `canon_dr:...` directly.*

#### Buttons not working (No beep, no scan)
1.  **Is scanbd running?**
    ```bash
    systemctl status scanbd
    ```
2.  **Did the scanner address change?** (e.g. unplugged/replugged)
    The monitor service should handle this, but you can force a refresh:
    ```bash
    sudo systemctl restart scanbd
    ```
3.  **Check logs for trigger**:
    ```bash
    tail -f /var/log/syslog | grep scanbd
    ```
    Press the button. You should see messages like `checking option start...` or `trigger action...`.

#### Scan starts but fails immediately ("Device busy" / "Invalid argument")
This usually means `scanbd` failed to stop fast enough, or the monitor service restarted it too early.
*   **Check scan logs**:
    ```bash
    tail -n 50 /var/log/scanbd-scan.log
    ```

### 3. Manual Service Control

If the system gets stuck, you can reset the entire stack:

```bash
# Stop everything
sudo systemctl stop scanbd piscan-scanner-monitor

# (Optional) Test scanner manually here: scanimage -L

# Start everything back up
sudo systemctl start scanbd piscan-scanner-monitor
```

### 4. Configuration Files

*   **Main Config**: `/opt/piscan/config/config.yaml`
*   **Button Actions**: `/etc/scanbd/scanner.d/piscan.conf`
*   **Action Script**: `/etc/scanbd/scan.sh`
*   **Daemon Config**: `/etc/scanbd/scanbd.conf`
*   **Backups**: `/opt/piscan/backups/etc/`

### 5. Sound Issues

If you don't hear the beep:
1.  Run the test script manually:
    ```bash
    /opt/piscan/scripts/play_beep.py
    ```
2.  Check if audio player is installed (`aplay`, `mpg123`, `ffplay`).
3.  Check volume settings in `config.yaml`.
