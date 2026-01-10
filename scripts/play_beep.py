#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from piscan.config import Config
from piscan.sound_player import SoundPlayer

try:
    config = Config()
    player = SoundPlayer(config)
    # Use computer_work_beep.mp3 for button press feedback
    sound_path = "/opt/piscan/sounds/computer_work_beep.mp3"
    
    # Manually trigger play_sound since _play_file is internal/renamed
    player._play_sound(sound_path, "button_feedback")
except Exception as e:
    print(f"Error playing sound: {e}")
