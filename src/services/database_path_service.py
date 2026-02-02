"""
Database Path Service

Handles persistence of custom database path using Windows Registry
with JSON file fallback for cross-platform compatibility.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


class DatabasePathService:
    """
    Service for persisting custom database path across application sessions.

    Uses Windows Registry on Windows platform, falls back to JSON config file
    for other platforms or if registry access fails.
    """

    REGISTRY_KEY = r"Software\OneTaskAtATime"
    REGISTRY_VALUE = "DatabasePath"
    CONFIG_FILENAME = "config.json"

    def __init__(self):
        """Initialize the database path service."""
        self.is_windows = sys.platform == 'win32'
        self.config_path = self._get_config_path()

    def _get_config_path(self) -> Path:
        """
        Get the path to the config file.

        Returns:
            Path to config.json
        """
        if getattr(sys, 'frozen', False):
            # Running as installed app
            app_data = os.environ.get('APPDATA')
            if not app_data:
                raise RuntimeError("APPDATA environment variable not found")
            config_dir = Path(app_data) / "OneTaskAtATime"
        else:
            # Running from source
            config_dir = Path(__file__).parent.parent.parent / "resources"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / self.CONFIG_FILENAME

    def save_database_path(self, path: str) -> bool:
        """
        Save custom database path to persistent storage.

        Args:
            path: Database file path to save

        Returns:
            True if successful, False otherwise
        """
        success = False

        # Try Windows Registry first
        if self.is_windows:
            if self._save_to_registry(path):
                logger.info(f"Saved database path to registry: {path}")
                success = True

        # Also save to JSON config file as backup
        if self._save_to_config_file(path):
            success = True

        return success

    def load_database_path(self) -> Optional[str]:
        """
        Load custom database path from persistent storage.

        Returns:
            Database path if found, None otherwise
        """
        # Try Windows Registry first
        if self.is_windows:
            path = self._load_from_registry()
            if path:
                logger.info(f"Loaded database path from registry: {path}")
                return path

        # Fallback to JSON config file
        return self._load_from_config_file()

    def clear_database_path(self) -> bool:
        """
        Clear saved database path from persistent storage.

        Returns:
            True if successful, False otherwise
        """
        success = True

        # Clear from registry
        if self.is_windows:
            if not self._clear_from_registry():
                success = False

        # Clear from config file
        if not self._clear_from_config_file():
            success = False

        if success:
            logger.info("Cleared saved database path")

        return success

    def _save_to_registry(self, path: str) -> bool:
        """Save path to Windows Registry."""
        try:
            import winreg

            # Create or open the registry key
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY)

            # Set the value
            winreg.SetValueEx(key, self.REGISTRY_VALUE, 0, winreg.REG_SZ, path)

            # Close the key
            winreg.CloseKey(key)

            return True

        except ImportError:
            logger.warning("winreg module not available")
            return False
        except Exception as e:
            logger.error(f"Error saving to registry: {e}")
            return False

    def _load_from_registry(self) -> Optional[str]:
        """Load path from Windows Registry."""
        try:
            import winreg

            # Open the registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY)

            # Read the value
            path, _ = winreg.QueryValueEx(key, self.REGISTRY_VALUE)

            # Close the key
            winreg.CloseKey(key)

            return path

        except ImportError:
            logger.warning("winreg module not available")
            return None
        except FileNotFoundError:
            # Key doesn't exist
            return None
        except Exception as e:
            logger.error(f"Error loading from registry: {e}")
            return None

    def _clear_from_registry(self) -> bool:
        """Clear path from Windows Registry."""
        try:
            import winreg

            # Open the registry key
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.REGISTRY_KEY, 0, winreg.KEY_WRITE)

            # Delete the value
            winreg.DeleteValue(key, self.REGISTRY_VALUE)

            # Close the key
            winreg.CloseKey(key)

            return True

        except ImportError:
            return False
        except FileNotFoundError:
            # Key doesn't exist - already clear
            return True
        except Exception as e:
            logger.error(f"Error clearing from registry: {e}")
            return False

    def _save_to_config_file(self, path: str) -> bool:
        """Save path to JSON config file."""
        try:
            config = self._load_config_file()
            config['database_path'] = path

            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved database path to config file: {path}")
            return True

        except Exception as e:
            logger.error(f"Error saving to config file: {e}")
            return False

    def _load_from_config_file(self) -> Optional[str]:
        """Load path from JSON config file."""
        try:
            config = self._load_config_file()
            path = config.get('database_path')

            if path:
                logger.info(f"Loaded database path from config file: {path}")

            return path

        except Exception as e:
            logger.error(f"Error loading from config file: {e}")
            return None

    def _clear_from_config_file(self) -> bool:
        """Clear path from JSON config file."""
        try:
            config = self._load_config_file()

            if 'database_path' in config:
                del config['database_path']

                with open(self.config_path, 'w') as f:
                    json.dump(config, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Error clearing from config file: {e}")
            return False

    def _load_config_file(self) -> dict:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Config file is corrupted, returning empty config")
            return {}
        except Exception as e:
            logger.error(f"Error reading config file: {e}")
            return {}
