#!/usr/bin/env python3
import time
import subprocess
import re
import sys

def get_options():
    try:
        # Use first available device
        cmd = ['scanimage', '-A']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return result.stdout
    except Exception as e:
        print(f"Error reading options: {e}")
        return ""

def parse_buttons(output):
    # Match lines like:
    #   --start[=(yes|no)] [no]
    #   --button-3[=(yes|no)] [no]
    #   --scan[=(yes|no)] [no]
    buttons = {}
    for line in output.splitlines():
        # Look for button-like options
        if any(x in line for x in ['button', 'start', 'stop', 'scan']):
            # Clean up the line to extract value
            # Example: "    --start[=(yes|no)] [no]" -> key="start", val="no"
            match = re.search(r'--([\w-]+).*?\[(.*?)\]', line)
            if match:
                key = match.group(1)
                val = match.group(2)
                buttons[key] = val
    return buttons

print("Watching scanner buttons via scanimage -A (Ctrl+C to stop)...")
print("Press scanner buttons now.")

last_buttons = {}

try:
    while True:
        raw = get_options()
        current = parse_buttons(raw)
        
        if not last_buttons:
            print(f"Initial state: {current}")
            last_buttons = current
        else:
            # Diff
            for key, val in current.items():
                old_val = last_buttons.get(key)
                if old_val != val:
                    print(f"CHANGE DETECTED: {key} changed from '{old_val}' to '{val}'")
            last_buttons = current
            
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopped.")
