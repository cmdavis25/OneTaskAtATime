"""
Settings Data Access Object for OneTaskAtATime application.

Handles all database operations for application settings.
"""

import sqlite3
import json
from datetime import datetime
from typing import Any, Dict, Optional


class SettingsDAO:
    """Data Access Object for application settings."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize SettingsDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value by key.

        Args:
            key: Setting key
            default: Default value if setting not found

        Returns:
            Setting value converted to appropriate type, or default if not found
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT value, value_type FROM settings WHERE key = ?",
            (key,)
        )

        row = cursor.fetchone()
        if not row:
            return default

        value, value_type = row
        return self._convert_value(value, value_type)

    def set(self, key: str, value: Any, value_type: str, description: str = None) -> None:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Setting value
            value_type: Type of value ('string', 'integer', 'float', 'boolean', 'json')
            description: Optional description of setting
        """
        cursor = self.db.cursor()
        now = datetime.now()

        # Convert value to string for storage
        str_value = self._value_to_string(value, value_type)

        cursor.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, value_type, description, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (key, str_value, value_type, description, now.isoformat())
        )

        self.db.commit()

    def get_all(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        Returns:
            Dictionary of key-value pairs with values converted to appropriate types
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT key, value, value_type FROM settings")

        settings = {}
        for row in cursor.fetchall():
            key, value, value_type = row
            settings[key] = self._convert_value(value, value_type)

        return settings

    def delete(self, key: str) -> bool:
        """
        Delete a setting.

        Args:
            key: Setting key to delete

        Returns:
            True if setting was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM settings WHERE key = ?", (key,))
        self.db.commit()
        return cursor.rowcount > 0

    def _convert_value(self, value: str, value_type: str) -> Any:
        """
        Convert a string value to the appropriate Python type.

        Args:
            value: String value from database
            value_type: Type indicator

        Returns:
            Value converted to appropriate type
        """
        if value_type == 'integer':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes')
        elif value_type == 'json':
            return json.loads(value)
        else:  # string
            return value

    def _value_to_string(self, value: Any, value_type: str) -> str:
        """
        Convert a Python value to a string for storage.

        Args:
            value: Value to convert
            value_type: Type indicator

        Returns:
            String representation of value
        """
        if value_type == 'json':
            return json.dumps(value)
        elif value_type == 'boolean':
            return 'true' if value else 'false'
        else:
            return str(value)

    # Convenience methods for typed retrieval
    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting value."""
        value = self.get(key, default)
        return int(value) if value is not None else default

    def get_str(self, key: str, default: str = '') -> str:
        """Get a string setting value."""
        value = self.get(key, default)
        return str(value) if value is not None else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting value."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return bool(value) if value is not None else default

    def get_datetime(self, key: str, default: Optional[datetime] = None) -> Optional[datetime]:
        """Get a datetime setting value."""
        value = self.get(key, default)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value != 'null':
            try:
                return datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                return default
        return default
