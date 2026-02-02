"""
Centralized Logging Service for OneTaskAtATime application.

Provides rotating file-based logging with configurable settings.
Implements singleton pattern for application-wide logging management.
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from typing import Optional


class LoggingService:
    """
    Singleton service for application-wide logging.

    Features:
    - Rotating file handlers to prevent excessive disk usage
    - Automatic log cleanup based on retention policy
    - Configurable log levels and file sizes
    - Platform-aware log directory (AppData on Windows, project logs/ for development)
    """

    _instance: Optional['LoggingService'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize the logging service (singleton pattern)."""
        # Only initialize once
        if not LoggingService._initialized:
            self.log_dir = None
            self.logger = None
            self.file_handler = None
            self.console_handler = None

    @classmethod
    def initialize(
        cls,
        enabled: bool = True,
        level: str = "INFO",
        retention_days: int = 30,
        max_file_size_mb: int = 10
    ) -> 'LoggingService':
        """
        Initialize the logging service with configuration.

        Args:
            enabled: Whether logging is enabled
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            retention_days: Number of days to retain log files
            max_file_size_mb: Maximum size of each log file in MB

        Returns:
            Initialized LoggingService instance
        """
        instance = cls()

        if LoggingService._initialized:
            return instance

        # Determine log directory
        instance.log_dir = instance._get_log_directory()
        instance.log_dir.mkdir(parents=True, exist_ok=True)

        # Set up root logger
        instance.logger = logging.getLogger()
        instance.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

        # Clear any existing handlers
        instance.logger.handlers.clear()

        if enabled:
            # Add file handler with rotation
            log_file = instance.log_dir / instance._get_log_filename()
            max_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes

            instance.file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=5,  # Keep 5 backup files
                encoding='utf-8'
            )

            # Set formatter
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            instance.file_handler.setFormatter(formatter)
            instance.logger.addHandler(instance.file_handler)

        # Always add console handler for development
        instance.console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        instance.console_handler.setFormatter(console_formatter)
        instance.logger.addHandler(instance.console_handler)

        # Clean up old log files
        if enabled:
            instance._cleanup_old_logs(retention_days)

        LoggingService._initialized = True
        instance.logger.info("Logging service initialized")
        instance.logger.info(f"Log directory: {instance.log_dir}")

        return instance

    def _get_log_directory(self) -> Path:
        """
        Get the appropriate log directory based on execution context.

        Returns:
            Path to log directory
        """
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller bundle (installed application)
            app_data = os.environ.get('APPDATA')
            if not app_data:
                raise RuntimeError("APPDATA environment variable not found")
            return Path(app_data) / "OneTaskAtATime" / "logs"
        else:
            # Running from source - use project's logs directory
            return Path(__file__).parent.parent.parent / "logs"

    def _get_log_filename(self) -> str:
        """
        Generate log filename with current date.

        Returns:
            Log filename in format: onetaskatatime_YYYYMMDD.log
        """
        today = datetime.now().strftime("%Y%m%d")
        return f"onetaskatatime_{today}.log"

    def _cleanup_old_logs(self, retention_days: int) -> None:
        """
        Remove log files older than retention period.

        Args:
            retention_days: Number of days to retain log files
        """
        if not self.log_dir or not self.log_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=retention_days)

        for log_file in self.log_dir.glob("onetaskatatime_*.log*"):
            try:
                # Get file modification time
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)

                if mtime < cutoff_date:
                    log_file.unlink()
                    self.logger.debug(f"Deleted old log file: {log_file.name}")

            except Exception as e:
                self.logger.warning(f"Error cleaning up log file {log_file.name}: {e}")

    @classmethod
    def get_logger(cls, name: str = None) -> logging.Logger:
        """
        Get a logger instance.

        Args:
            name: Logger name (typically __name__ from calling module)

        Returns:
            Logger instance
        """
        if not LoggingService._initialized:
            # Initialize with defaults if not yet initialized
            cls.initialize()

        if name:
            return logging.getLogger(name)
        return logging.getLogger()

    @classmethod
    def cleanup(cls) -> None:
        """
        Clean up logging resources.

        Call this method when the application is shutting down.
        """
        instance = cls()

        if not LoggingService._initialized:
            return

        if instance.logger:
            instance.logger.info("Shutting down logging service")

        # Close and remove handlers
        if instance.file_handler:
            instance.file_handler.close()
            instance.logger.removeHandler(instance.file_handler)
            instance.file_handler = None

        if instance.console_handler:
            instance.console_handler.close()
            instance.logger.removeHandler(instance.console_handler)
            instance.console_handler = None

        # Reset logging
        logging.shutdown()
        LoggingService._initialized = False

    @classmethod
    def shutdown(cls) -> None:
        """
        Shutdown the logging service.

        Alias for cleanup() method for backward compatibility.
        """
        cls.cleanup()

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if logging service is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return LoggingService._initialized
