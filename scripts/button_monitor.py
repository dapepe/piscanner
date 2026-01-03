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

# Add piscan module to path
sys.path.insert(0, "/opt/piscan")
from piscan.config import Config
from piscan.sound_player import SoundPlayer

# Configuration
SCAN_SCRIPT = "/opt/piscan/scan.py"
CONFIG_PATH = "/opt/piscan/config/config.yaml"
POLL_INTERVAL = 0.5  # Check every 500ms
BUTTON_COOLDOWN = 2.0 # Ignore presses for 2s after a scan

# Load config and sound player
config = Config(CONFIG_PATH)
sound_player = SoundPlayer(config)

# Map physical buttons to scan sources
# "start" is the main green button on Canon DR-F120
# "button-3" is the small "3" button (often used as secondary)
BUTTON_MAP = {
    "start": "ADF Duplex",    # Main button -> Duplex
    "button-3": "ADF Front",  # Button 3 -> Simplex
    "stop": "ADF Front",      # Fallback: Stop button -> Simplex (if user prefers)
}

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
    """Check if any button is pressed and return its name."""
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
            for line in output.splitlines():
                if "[yes]" in line:
                    # Extract option name: "    --start[=(yes|no)] [yes]" -> "start"
                    # Regex match would be cleaner but split works for simple cases
                    if "--" in line and "[" in line:
                        parts = line.split("--")[1].split("[")[0]
                        btn_name = parts.strip()
                        if btn_name in ['start', 'stop', 'button-3', 'scan', 'button-1', 'button-2']:
                            return btn_name
        return None
    except subprocess.TimeoutExpired:
        # Device might be busy or sleeping, just skip this poll
        return None
    except Exception as e:
        logger.error(f"Poll error: {e}")
        return None

def trigger_scan(button_name):
    """Run the main scan script with source based on button."""
    source = BUTTON_MAP.get(button_name, config.scanner_source)
    logger.info(f"=== Button '{button_name}' pressed! Starting scan (Source: {source})... ===")
    
    # Play acknowledgment sound immediately
    # We use a non-blocking "work" beep if available, or just the success sound as "start"
    # Assuming computer_work_beep.mp3 is available based on user feedback
    work_sound = "/opt/piscan/sounds/computer_work_beep.mp3"
    if os.path.exists(work_sound):
        # Manually play via aplay/mpg123 for speed, or use SoundPlayer private method
        # Let's use SoundPlayer public method if possible, but it only has success/error.
        # We'll stick to a quick ad-hoc play or verify if SoundPlayer exposes generic play.
        # It has _play_sound(file, type).
        sound_player._play_sound(work_sound, "start")
    
    try:
        # Run scan.py in subprocess
        # Override source via command line argument
        cmd = [sys.executable, "-u", SCAN_SCRIPT, "--config", CONFIG_PATH, "--source", source]
        
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
    logger.info(f"Button mapping: {BUTTON_MAP}")
    
    while True:
        btn = check_button(device)
        if btn:
            trigger_scan(btn)
            # Cooldown to prevent double-triggering
            time.sleep(BUTTON_COOLDOWN)
        
        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
