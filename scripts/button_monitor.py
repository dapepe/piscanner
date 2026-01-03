#!/usr/bin/env python3
import time
import subprocess
import os
import sys
import logging
import signal

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger("piscan-monitor")

# Configuration
SCAN_SCRIPT = "/opt/piscan/scan.py"
CONFIG_PATH = "/opt/piscan/config/config.yaml"
POLL_INTERVAL = 0.5  # Check every 500ms
BUTTON_COOLDOWN = 2.0 # Ignore presses for 2s after a scan

# Signal handler for clean exit
def signal_handler(sig, frame):
    logger.info("Stopping button monitor...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def get_device_name():
    """Find the local scanner device (excluding network backends)."""
    try:
        # Use scanimage -L to find devices
        result = subprocess.run(['scanimage', '-L'], capture_output=True, text=True, timeout=5)
        for line in result.stdout.splitlines():
            # Example: device `canon_dr:libusb:003:003' is a CANON DR-F120 scanner
            if "device `" in line:
                dev = line.split("`")[1].split("'")[0]
                # Filter out network proxies if they exist
                if not dev.startswith("net:") and not dev.startswith("airscan") and not dev.startswith("hpaio"):
                    return dev
    except Exception as e:
        logger.error(f"Error finding device: {e}")
    return None

def check_button(device):
    """Check if start button is pressed."""
    try:
        # Query device options
        # We assume the device is available since we are the only one accessing it
        cmd = ['scanimage', '-d', device, '-A']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=2)
        
        # Look for button "yes" state
        # Matches: --start[=(yes|no)] [yes]
        # or: --button-3[=(yes|no)] [yes]
        output = result.stdout
        
        if "[yes]" in output:
            # Confirm it's a button option
            for line in output.splitlines():
                if "[yes]" in line and any(x in line for x in ['start', 'button', 'scan']):
                    return True
        return False
    except subprocess.TimeoutExpired:
        # Device might be busy or sleeping, just skip this poll
        return False
    except Exception as e:
        logger.error(f"Poll error: {e}")
        return False

def trigger_scan():
    """Run the main scan script."""
    logger.info("=== Button pressed! Starting scan... ===")
    try:
        # Run scan.py in subprocess, letting it log to stdout (which systemd captures)
        # We pass -u for unbuffered output
        cmd = [sys.executable, "-u", SCAN_SCRIPT, "--config", CONFIG_PATH]
        
        # We wait for it to finish so we don't poll during scanning
        subprocess.run(cmd, check=False)
        
        logger.info("=== Scan process finished ===")
    except Exception as e:
        logger.error(f"Failed to run scan script: {e}")

def main():
    logger.info("Piscan Button Monitor started")
    
    device = get_device_name()
    if not device:
        logger.error("No local scanner found! Retrying in 5s...")
        time.sleep(5)
        sys.exit(1) # Systemd will restart us
        
    logger.info(f"Monitoring device: {device}")
    
    while True:
        if check_button(device):
            trigger_scan()
            # Cooldown to prevent double-triggering
            time.sleep(BUTTON_COOLDOWN)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
