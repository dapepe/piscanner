"""Logging system for piscan."""

import logging
import logging.handlers
import os
from typing import Optional


class Logger:
    """Centralized logging system for piscan."""
    
    _instance = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize logger."""
        if self._logger is None:
            self._setup_logger()
    
    def _setup_logger(self, config: Optional[object] = None):
        """Setup the logger with configuration.
        
        Args:
            config: Configuration object
        """
        # Import here to avoid circular imports
        if config is None:
            try:
                import importlib
                config_module = importlib.import_module('.config', package='piscan')
                config = config_module.Config()
            except ImportError:
                # Fallback defaults if config import fails
                config = type('Config', (), {
                    'log_level': 'INFO',
                    'log_file': '/tmp/piscan.log',
                    'log_max_size': 10485760,
                    'log_backup_count': 5
                })()
        
        self._logger = logging.getLogger('piscan')
        log_level = getattr(config, 'log_level', 'INFO')
        self._logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear existing handlers
        self._logger.handlers.clear()
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # File handler with rotation
        log_file = getattr(config, 'log_file', None)
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=getattr(config, 'log_max_size', 10485760),
                backupCount=getattr(config, 'log_backup_count', 5)
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
    
    def get_logger(self) -> logging.Logger:
        """Get the configured logger.
        
        Returns:
            Logger instance
        """
        if self._logger is None:
            self._setup_logger()
        return self._logger  # type: ignore
    
    def debug(self, message: str, *args, **kwargs):
        """Log debug message."""
        if self._logger:
            self._logger.debug(message, *args, **kwargs)
    
    def info(self, message: str, *args, **kwargs):
        """Log info message."""
        if self._logger:
            self._logger.info(message, *args, **kwargs)
    
    def warning(self, message: str, *args, **kwargs):
        """Log warning message."""
        if self._logger:
            self._logger.warning(message, *args, **kwargs)
    
    def error(self, message: str, *args, **kwargs):
        """Log error message."""
        if self._logger:
            self._logger.error(message, *args, **kwargs)
    
    def critical(self, message: str, *args, **kwargs):
        """Log critical message."""
        if self._logger:
            self._logger.critical(message, *args, **kwargs)
    
    def exception(self, message: str, *args, **kwargs):
        """Log exception with traceback."""
        if self._logger:
            self._logger.exception(message, *args, **kwargs)


# Global logger instance
logger = Logger()