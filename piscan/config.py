"""Configuration management for piscan."""

import os
import yaml
from typing import Dict, Any, Optional


class Config:
    """Configuration manager for piscan."""
    
    DEFAULT_CONFIG = {
        "scanner": {
            "device": "",  # Auto-detect if empty
            "resolution": 300,
            "mode": "Color",
            "source": "Auto",  # Auto, ADF, Flatbed
            "format": "png",
            "color_correction": "none"  # none, swap_rb, swap_rg, swap_gb, rotate_left, rotate_right, bgr_to_rgb
        },
        "api": {
            "workspace": "default",
            "url": "http://localhost:8080",
            "token": "",
            "timeout": 30
        },
        "storage": {
            "temp_dir": "/tmp",
            "failed_dir": "/tmp/failed",
            "keep_failed": True,
            "temp_retention_hours": 168,  # Delete temp scan dirs older than this (7 days)
            "failed_retention_days": 30  # Delete failed jobs older than this
        },
        "processing": {
            "skip_blank": True,
            "blank_threshold": 0.03,  # 3% non-white pixels threshold
            "white_threshold": 250  # Pixel brightness > 250 considered white
        },
        "server": {
            "host": "0.0.0.0",
            "port": 5000,
            "debug": False
        },
        "logging": {
            "level": "INFO",
            "file": "/var/log/piscan.log",
            "max_size": 10485760,  # 10MB
            "backup_count": 5
        },
        "sound": {
            "enabled": False,  # Enable sound notifications
            "success_sound": "/usr/share/sounds/freedesktop/stereo/complete.oga",  # Sound file for successful upload
            "error_sound": "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",  # Sound file for errors
            "volume": 70,  # Volume percentage (0-100)
            "device": ""  # Optional ALSA/Pulse output device (e.g. "plughw:1,0" for USB)
        },
        "upload": {
            "compression": "individual",  # individual, zip
            "image_quality": 90,  # JPEG quality (1-100)
            "optimize_png": True,  # Optimize PNG files
            "zip_bundle_size": 0,  # Max files per ZIP bundle (0 = unlimited)
            "zip_bundle_max_bytes": 0,  # Max ZIP payload bytes per bundle (0 = unlimited)
            "zip_compression_level": 6,  # ZIP compression level (1-9, 9 = best compression)
            "auto_jpeg_threshold": 0,  # Auto-convert to JPEG if page count exceeds this (0 = disabled)
            "auto_jpeg_page_size_bytes": 0,  # Auto-convert large pages to JPEG (0 = disabled)
            "max_image_dimension": 0  # Max dimension for images (0 = unlimited, reduces size for large docs)
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            config_path: Path to YAML config file
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config = self.DEFAULT_CONFIG.copy()
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        # Allow explicit override (useful for systemd/scanbd environments)
        env_path = os.environ.get("PISCAN_CONFIG")
        if env_path and os.path.exists(env_path):
            return env_path

        # Check common locations.
        # NOTE: system services often run with CWD=/, so include the canonical
        # /opt/piscan path to ensure the same config is used everywhere.
        paths = [
            "/opt/piscan/config/config.yaml",  # Canonical install location
            "./config/config.yaml",  # Local config directory (recommended)
            os.path.expanduser("~/.piscan/config.yaml"),  # User home directory
            "/etc/piscan/config.yaml",  # System-wide
            "./config.yaml"  # Legacy location
        ]
        for path in paths:
            if os.path.exists(path):
                return path
        return paths[0]  # Return first path as default
    
    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                self._merge_config(self._config, user_config)
            except Exception as e:
                print(f"Warning: Failed to load config from {self.config_path}: {e}")
    
    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Recursively merge configuration dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., 'scanner.resolution')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """Set configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., 'scanner.resolution')
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to YAML file.
        
        Args:
            path: Optional path to save to (defaults to config_path)
        """
        save_path = path or self.config_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        with open(save_path, 'w') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)
    
    @property
    def scanner_device(self) -> str:
        """Get scanner device string."""
        return self.get('scanner.device')
    
    @property
    def scanner_resolution(self) -> int:
        """Get scanner resolution DPI."""
        return self.get('scanner.resolution')
    
    @property
    def scanner_mode(self) -> str:
        """Get scanner color mode."""
        return self.get('scanner.mode')
    
    @property
    def scanner_source(self) -> str:
        """Get scanner source."""
        return self.get('scanner.source')
    
    @property
    def scanner_format(self) -> str:
        """Get scanner output format."""
        return self.get('scanner.format')
    
    @property
    def scanner_color_correction(self) -> str:
        """Get scanner color correction mode."""
        return self.get('scanner.color_correction', 'none')
    
    @property
    def api_workspace(self) -> str:
        """Get API workspace."""
        return self.get('api.workspace')
    
    @property
    def api_url(self) -> str:
        """Get API base URL."""
        return self.get('api.url')
    
    @property
    def api_token(self) -> str:
        """Get API authentication token."""
        return self.get('api.token')
    
    @property
    def api_timeout(self) -> int:
        """Get API request timeout."""
        return self.get('api.timeout')
    
    @property
    def temp_dir(self) -> str:
        """Get temporary directory path."""
        return self.get('storage.temp_dir')
    
    @property
    def failed_dir(self) -> str:
        """Get failed jobs directory path."""
        return self.get('storage.failed_dir')
    
    @property
    def keep_failed(self) -> bool:
        """Whether to keep failed jobs."""
        return self.get('storage.keep_failed')
    
    @property
    def skip_blank(self) -> bool:
        """Whether to skip blank pages."""
        return self.get('processing.skip_blank')
    
    @property
    def blank_threshold(self) -> float:
        """Get blank page threshold."""
        return self.get('processing.blank_threshold')
    
    @property
    def white_threshold(self) -> int:
        """Get white pixel threshold."""
        return self.get('processing.white_threshold')
    
    @property
    def server_host(self) -> str:
        """Get server host."""
        return self.get('server.host')
    
    @property
    def server_port(self) -> int:
        """Get server port."""
        return self.get('server.port')
    
    @property
    def server_debug(self) -> bool:
        """Get server debug mode."""
        return self.get('server.debug')
    
    @property
    def log_level(self) -> str:
        """Get log level."""
        return self.get('logging.level')
    
    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self.get('logging.file')
    
    @property
    def log_max_size(self) -> int:
        """Get maximum log file size."""
        return self.get('logging.max_size')
    
    @property
    def sound_enabled(self) -> bool:
        """Whether sound notifications are enabled."""
        return self.get('sound.enabled', False)
    
    @property
    def success_sound(self) -> str:
        """Get success sound file path."""
        return self.get('sound.success_sound', '/usr/share/sounds/freedesktop/stereo/complete.oga')
    
    @property
    def error_sound(self) -> str:
        """Get error sound file path."""
        return self.get('sound.error_sound', '/usr/share/sounds/freedesktop/stereo/dialog-error.oga')
    
    @property
    def sound_volume(self) -> int:
        """Get sound volume (0-100)."""
        return self.get('sound.volume', 70)

    @property
    def sound_device(self) -> str:
        """Optional audio output device string."""
        return self.get('sound.device', '')
    
    @property
    def log_backup_count(self) -> int:
        """Get log backup count."""
        return self.get('logging.backup_count')

    @property
    def temp_retention_hours(self) -> int:
        """Max age (hours) to keep temp scan dirs."""
        return int(self.get('storage.temp_retention_hours', 168))

    @property
    def failed_retention_days(self) -> int:
        """Max age (days) to keep failed scan dirs."""
        return int(self.get('storage.failed_retention_days', 30))
    
    @property
    def upload_compression(self) -> str:
        """Get upload compression mode."""
        return self.get('upload.compression', 'individual')
    
    @property
    def upload_image_quality(self) -> int:
        """Get upload image quality."""
        return self.get('upload.image_quality', 90)
    
    @property
    def upload_optimize_png(self) -> bool:
        """Whether to optimize PNG files."""
        return self.get('upload.optimize_png', True)

    @property
    def upload_zip_bundle_size(self) -> int:
        """Get max files per ZIP bundle (0 = unlimited)."""
        return int(self.get('upload.zip_bundle_size', 0))

    @property
    def upload_zip_bundle_max_bytes(self) -> int:
        """Max ZIP payload bytes per bundle (0 = unlimited)."""
        return int(self.get('upload.zip_bundle_max_bytes', 0))

    @property
    def upload_zip_compression_level(self) -> int:
        """Get ZIP compression level (1-9, 9 = best)."""
        return self.get('upload.zip_compression_level', 6)

    @property
    def upload_auto_jpeg_threshold(self) -> int:
        """Get auto-JPEG conversion threshold (0 = disabled)."""
        return int(self.get('upload.auto_jpeg_threshold', 0))

    @property
    def upload_auto_jpeg_page_size_bytes(self) -> int:
        """Auto-convert large pages to JPEG (0 = disabled)."""
        return int(self.get('upload.auto_jpeg_page_size_bytes', 0))

    @property
    def upload_max_image_dimension(self) -> int:
        """Get max image dimension (0 = unlimited)."""
        return self.get('upload.max_image_dimension', 0)