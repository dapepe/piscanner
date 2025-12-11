"""Sound notification player for piscan."""

import os
import subprocess
from typing import Optional

try:
    from .logger import Logger
except ImportError:
    # Simple logger fallback
    import os
    _debug_enabled = os.environ.get('PISCAN_DEBUG', '').lower() in ('1', 'true', 'yes')
    
    class Logger:
        def info(self, msg, *args):
            if _debug_enabled:
                print(f"INFO: {msg % args if args else msg}")
        def error(self, msg, *args):
            if _debug_enabled:
                print(f"ERROR: {msg % args if args else msg}")
        def debug(self, msg, *args):
            if _debug_enabled:
                print(f"DEBUG: {msg % args if args else msg}")
        def warning(self, msg, *args):
            if _debug_enabled:
                print(f"WARNING: {msg % args if args else msg}")


class SoundPlayer:
    """Plays sound notifications using available audio players."""
    
    def __init__(self, config):
        """Initialize sound player.
        
        Args:
            config: Configuration object
        """
        self.config = config
        self.logger = Logger()
        self.enabled = config.sound_enabled
        self.player = self._detect_player()
        
        if self.enabled and not self.player:
            self.logger.warning("Sound notifications enabled but no audio player found")
            self.enabled = False
    
    def _detect_player(self) -> Optional[str]:
        """Detect available audio player.
        
        Returns:
            Path to audio player command or None
        """
        # Try different audio players in order of preference
        players = [
            'aplay',      # ALSA player (most common on Raspberry Pi)
            'paplay',     # PulseAudio player
            'mpg123',     # MP3 player
            'ffplay',     # FFmpeg player
            'cvlc',       # VLC (command line)
            'mplayer'     # MPlayer
        ]
        
        for player in players:
            try:
                result = subprocess.run(
                    ['which', player],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self.logger.debug(f"Found audio player: {player}")
                    return player
            except Exception as e:
                self.logger.debug(f"Error checking for {player}: {e}")
        
        return None
    
    def play_success(self) -> None:
        """Play success sound."""
        if not self.enabled:
            return
        
        sound_file = self.config.success_sound
        self._play_sound(sound_file, "success")
    
    def play_error(self) -> None:
        """Play error sound."""
        if not self.enabled:
            return
        
        sound_file = self.config.error_sound
        self._play_sound(sound_file, "error")
    
    def _play_sound(self, sound_file: str, sound_type: str) -> None:
        """Play a sound file.
        
        Args:
            sound_file: Path to sound file
            sound_type: Type of sound (for logging)
        """
        if not sound_file or not os.path.exists(sound_file):
            self.logger.warning(f"{sound_type} sound file not found: {sound_file}")
            return
        
        try:
            # Build command based on player
            if self.player == 'aplay':
                # aplay is for WAV files, try to use it anyway
                cmd = ['aplay', '-q', sound_file]
            elif self.player == 'paplay':
                # PulseAudio player
                volume_fraction = self.config.sound_volume / 100.0
                cmd = ['paplay', f'--volume={int(volume_fraction * 65536)}', sound_file]
            elif self.player == 'mpg123':
                # mpg123 for MP3/OGG
                cmd = ['mpg123', '-q', sound_file]
            elif self.player == 'ffplay':
                # ffplay (FFmpeg)
                volume_db = -30 + (self.config.sound_volume / 100.0 * 30)
                cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', 
                       '-af', f'volume={volume_db}dB', sound_file]
            elif self.player == 'cvlc':
                # VLC command line
                gain = self.config.sound_volume / 100.0 * 2
                cmd = ['cvlc', '--play-and-exit', '--quiet', f'--gain={gain}', sound_file]
            elif self.player == 'mplayer':
                # MPlayer
                cmd = ['mplayer', '-really-quiet', '-volume', str(self.config.sound_volume), sound_file]
            else:
                self.logger.warning(f"Unknown player: {self.player}")
                return
            
            # Play sound in background (non-blocking)
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            self.logger.debug(f"Playing {sound_type} sound: {sound_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to play {sound_type} sound: {e}")
    
    def test_sound(self) -> dict:
        """Test sound playback.
        
        Returns:
            Dictionary with test results
        """
        result = {
            'enabled': self.enabled,
            'player': self.player,
            'success_sound': self.config.success_sound,
            'error_sound': self.config.error_sound,
            'volume': self.config.sound_volume
        }
        
        if not self.enabled:
            result['status'] = 'disabled'
            result['message'] = 'Sound notifications are disabled in config'
            return result
        
        if not self.player:
            result['status'] = 'no_player'
            result['message'] = 'No audio player found'
            return result
        
        # Check if sound files exist
        if not os.path.exists(self.config.success_sound):
            result['status'] = 'missing_file'
            result['message'] = f'Success sound file not found: {self.config.success_sound}'
            return result
        
        if not os.path.exists(self.config.error_sound):
            result['status'] = 'missing_file'
            result['message'] = f'Error sound file not found: {self.config.error_sound}'
            return result
        
        result['status'] = 'ready'
        result['message'] = 'Sound player is ready'
        
        return result
