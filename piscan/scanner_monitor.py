#!/usr/bin/env python3
"""Scanner health monitoring service for PiScan.

This service monitors scanner connectivity and restarts scanbd when the scanner
reconnects after being power-cycled.
"""

import sys
import os
import time
import subprocess
import signal
from typing import Optional

# Add piscan to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from piscan.logger import Logger


class ScannerHealthMonitor:
    """Monitors scanner health and manages scanbd service."""

    def __init__(self, check_interval: int = 30):
        """Initialize health monitor.

        Args:
            check_interval: Seconds between health checks
        """
        self.check_interval = check_interval
        self.logger = Logger()
        self.running = False
        self.last_scanner_status = None
        self.scanbd_was_restarted = False

    def _scanner_is_available(self) -> bool:
        """Check if scanner is currently available.

        Returns:
            True if scanner is accessible
        """
        try:
            # Try to list scanners - if scanner is available, it should appear
            result = subprocess.run([
                'scanimage', '-L'
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                output = result.stdout.lower()
                # Look for Canon scanner in output
                if 'canon' in output and ('dr-f120' in output or 'scanner' in output):
                    return True

            return False

        except Exception as e:
            self.logger.debug(f"Scanner availability check failed: {e}")
            return False

    def _scanbd_is_running(self) -> bool:
        """Check if scanbd service is running.

        Returns:
            True if scanbd is active
        """
        try:
            result = subprocess.run([
                'systemctl', 'is-active', 'scanbd'
            ], capture_output=True, text=True, timeout=5)

            return result.returncode == 0 and result.stdout.strip() == 'active'

        except Exception:
            return False

    def _restart_scanbd(self) -> bool:
        """Restart scanbd service.

        Returns:
            True if restart was successful
        """
        try:
            self.logger.info("Restarting scanbd service due to scanner reconnection...")

            result = subprocess.run([
                'systemctl', 'restart', 'scanbd'
            ], capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                self.logger.info("scanbd restarted successfully")
                time.sleep(2)  # Give scanbd time to initialize
                return True
            else:
                self.logger.error(f"Failed to restart scanbd: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error restarting scanbd: {e}")
            return False

    def _check_and_manage_scanbd(self, scanner_available: bool):
        """Check scanbd status and restart if needed.

        Args:
            scanner_available: Whether scanner is currently available
        """
        scanbd_running = self._scanbd_is_running()

        # Only restart scanbd if scanner has been unavailable for multiple checks
        # This prevents restarting when there are temporary connection issues
        if scanner_available and not scanbd_running and self.last_scanner_status is False:
            self.logger.info("Scanner reconnected after being unavailable, restarting scanbd...")
            if self._restart_scanbd():
                self.scanbd_was_restarted = True
            else:
                self.logger.warning("Failed to restart scanbd after scanner reconnection")

        # If scanner becomes unavailable while scanbd is running, it might be a temporary issue
        # Don't restart scanbd immediately, wait for scanner to be unavailable for longer

    def run_monitoring_loop(self):
        """Main monitoring loop."""
        self.logger.info(f"Starting scanner health monitoring (check interval: {self.check_interval}s)")
        self.running = True

        try:
            while self.running:
                scanner_available = self._scanner_is_available()

                if scanner_available != self.last_scanner_status:
                    status_change = "available" if scanner_available else "unavailable"
                    self.logger.info(f"Scanner status changed to: {status_change}")
                    self.last_scanner_status = scanner_available

                    # Manage scanbd based on scanner status
                    self._check_and_manage_scanbd(scanner_available)

                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Scanner health monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Scanner health monitoring error: {e}")
        finally:
            self.running = False

    def stop(self):
        """Stop the monitoring service."""
        self.logger.info("Stopping scanner health monitoring...")
        self.running = False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Scanner Health Monitor for PiScan')
    parser.add_argument('--interval', type=int, default=30,
                       help='Check interval in seconds (default: 30)')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (fork to background)')

    args = parser.parse_args()

    monitor = ScannerHealthMonitor(check_interval=args.interval)

    def signal_handler(signum, frame):
        monitor.stop()

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if args.daemon:
        # Fork to background
        if os.fork() > 0:
            sys.exit(0)

        os.setsid()
        if os.fork() > 0:
            sys.exit(0)

        # Redirect stdio
        sys.stdout.flush()
        sys.stderr.flush()
        with open('/dev/null', 'r') as null_read:
            with open('/dev/null', 'w') as null_write:
                os.dup2(null_read.fileno(), sys.stdin.fileno())
                os.dup2(null_write.fileno(), sys.stdout.fileno())
                os.dup2(null_write.fileno(), sys.stderr.fileno())

    monitor.run_monitoring_loop()


if __name__ == '__main__':
    main()