#!/usr/bin/env python3
"""Test script to verify scanner auto-detection works after device changes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from piscan.config import Config
from piscan.scanner import Scanner
from piscan.uploader import Uploader

def test_auto_detection():
    """Test scanner auto-detection."""
    print("=== Testing Scanner Auto-Detection ===")

    # Create config with no device specified (forces auto-detection)
    config = Config()
    config._config['scanner']['device'] = ''

    uploader = Uploader(config)
    scanner = Scanner(config, uploader)

    print(f"✓ Auto-detected device: {scanner.device}")
    print(f"✓ Scanner test result: {scanner.test_scanner()}")

    # Simulate device change (what happens when scanner is power-cycled)
    print("\n=== Simulating Device Change ===")
    old_device = scanner.device
    scanner.device = "canon_dr:libusb:001:002"  # Fake old device path

    print(f"Simulated device change: {old_device} -> {scanner.device}")

    # Test again - should re-detect
    test_result = scanner.test_scanner()
    print(f"✓ After device change, test result: {test_result}")
    print(f"✓ Re-detected device: {scanner.device}")

    if scanner.device != old_device and test_result:
        print("\n🎉 SUCCESS: Auto-detection correctly handled device change!")
        return True
    else:
        print("\n❌ FAILED: Auto-detection did not handle device change properly")
        return False

if __name__ == '__main__':
    success = test_auto_detection()
    sys.exit(0 if success else 1)