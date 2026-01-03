#!/usr/bin/env python3
"""Cron-friendly cleanup for piscan temp/failed scan dirs.

This script removes:
- temp scan directories older than `storage.temp_retention_hours`
- failed scan directories older than `storage.failed_retention_days`

It is safe to run frequently.

Usage:
  PISCAN_CONFIG=/opt/piscan/config/config.yaml PYTHONPATH=/opt/piscan \
    python3 /opt/piscan/scripts/cleanup_temp.py
"""

import os
import sys

# Ensure local imports work if cron runs from /
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SCRIPT_DIR)

from piscan.config import Config
from piscan.file_manager import FileManager


def main() -> int:
    config_path = os.environ.get("PISCAN_CONFIG", "/opt/piscan/config/config.yaml")
    config = Config(config_path)

    fm = FileManager(config)

    # Cleanup temp scan dirs (including scanbd /tmp/scan-*)
    fm.cleanup_old_temp_jobs(config.temp_retention_hours)

    # Cleanup old failed jobs
    fm.cleanup_old_failed_jobs(config.failed_retention_days)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
