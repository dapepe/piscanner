#!/usr/bin/env python3
"""Test piscan sound notifications.

This script validates sound configuration and plays the configured sounds.

Examples:
  python3 testsound.py --check
  python3 testsound.py --success
  python3 testsound.py --error
  python3 testsound.py --success --config /opt/piscan/config/config.yaml
"""

import argparse
import os
import sys

# Ensure local imports work when run from anywhere
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from piscan.config import Config
from piscan.sound_player import SoundPlayer


def main() -> int:
    parser = argparse.ArgumentParser(description="Test piscan sound playback")
    parser.add_argument(
        "--config",
        default=os.environ.get("PISCAN_CONFIG", os.path.join(SCRIPT_DIR, "config", "config.yaml")),
        help="Path to config.yaml (default: PISCAN_CONFIG or ./config/config.yaml)",
    )

    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument("--check", action="store_true", help="Print detected sound status")
    action.add_argument("--success", action="store_true", help="Play configured success sound")
    action.add_argument("--error", action="store_true", help="Play configured error sound")

    parser.add_argument(
        "--blocking",
        action="store_true",
        help="Play sound synchronously (useful for service hooks)",
    )

    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the relevant sound config values",
    )

    parser.add_argument(
        "--device",
        default=None,
        help="Override audio device (for aplay: e.g. plughw:1,0)",
    )

    parser.add_argument(
        "--list-alsa",
        action="store_true",
        help="List ALSA playback devices (aplay -l)",
    )

    args = parser.parse_args()

    if args.list_alsa:
        import subprocess

        subprocess.run(["aplay", "-l"])
        return 0

    if args.blocking:
        os.environ['PISCAN_SOUND_BLOCKING'] = '1'

    config = Config(args.config)

    # Optional per-run override
    if args.device is not None:
        config.set('sound.device', args.device)

    sound_player = SoundPlayer(config)

    if args.print_config:
        print(f"config_path: {getattr(config, 'config_path', args.config)}")
        print(f"sound.enabled: {config.sound_enabled}")
        print(f"sound.success_sound: {config.success_sound} (exists={os.path.exists(config.success_sound)})")
        print(f"sound.error_sound: {config.error_sound} (exists={os.path.exists(config.error_sound)})")
        print(f"sound.volume: {config.sound_volume}")
        print(f"sound.device: {getattr(config, 'sound_device', '')}")
        print(f"detected_player: {sound_player.player}")
        print()

    # Default action: --check
    if not (args.check or args.success or args.error):
        args.check = True

    if args.check:
        result = sound_player.test_sound()
        print(result)
        return 0 if result.get("status") == "ready" else 1

    if args.success:
        sound_player.play_success()
        print("Triggered success sound")
        return 0

    if args.error:
        sound_player.play_error()
        print("Triggered error sound")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
