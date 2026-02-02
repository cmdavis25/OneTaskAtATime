"""
Database Connection Module

Provides singleton SQLite database connection management for OneTaskAtATime.
"""

import sqlite3
import os
import sys
from pathlib import Path
from typing import Optional
from .schema import DatabaseSchema


class DatabaseConnection:
    """
    Singleton class managing SQLite database connection.

    Ensures only one connection instance exists throughout the application lifecycle.
    """

    _instance: Optional['DatabaseConnection'] = None
    _connection: Optional[sqlite3.Connection] = None
    _current_db_path: Optional[Path] = None

    def __new__(cls, custom_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, custom_path: Optional[str] = None):
        """Initialize database connection if not already connected.

        Args:
            custom_path: Optional custom database file path
        """
        if self._connection is None:
            self._connect(custom_path)

    def _connect(self, custom_path: Optional[str] = None):
        """
        Establish connection to SQLite database.

        Creates the database file in the appropriate directory:
        - When installed: %APPDATA%\\OneTaskAtATime\\
        - When running from source: project's resources directory
        - Or uses custom path if provided

        Enables foreign key constraints for referential integrity.

        Args:
            custom_path: Optional custom database file path
        """
        # Determine database path
        if custom_path:
            db_path = Path(custom_path)
        else:
            # Determine the appropriate data directory
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller bundle (installed application)
                # Use AppData directory for persistent, writable storage
                app_data = os.environ.get('APPDATA')
                if not app_data:
                    raise RuntimeError("APPDATA environment variable not found")
                data_dir = Path(app_data) / "OneTaskAtATime"
            else:
                # Running from source - use project's resources directory
                data_dir = Path(__file__).parent.parent.parent / "resources"

            # Ensure data directory exists
            data_dir.mkdir(exist_ok=True)

            # Database file path
            db_path = data_dir / "onetaskatatime.db"

        # Connect to database
        self._connection = sqlite3.connect(
            str(db_path),
            check_same_thread=False  # Allow usage across threads
        )

        # Store current database path
        self._current_db_path = db_path

        # Enable foreign key constraints
        self._connection.execute("PRAGMA foreign_keys = ON")

        # Use Row factory for dict-like access
        self._connection.row_factory = sqlite3.Row

        print(f"Database connected: {db_path}")

        # Initialize database schema if needed
        DatabaseSchema.initialize_database(self._connection)

        # Run migrations
        DatabaseSchema.migrate_to_elo_system(self._connection)
        DatabaseSchema.migrate_to_recurring_tasks(self._connection)
        DatabaseSchema.migrate_to_notification_system(self._connection)

    def get_connection(self) -> sqlite3.Connection:
        """
        Get the active database connection.

        Returns:
            sqlite3.Connection: Active database connection
        """
        if self._connection is None:
            self._connect()
        return self._connection

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            print("Database connection closed")

    def commit(self):
        """Commit current transaction."""
        if self._connection:
            self._connection.commit()

    def rollback(self):
        """Rollback current transaction."""
        if self._connection:
            self._connection.rollback()

    def get_current_database_path(self) -> Optional[str]:
        """
        Get the path to the currently connected database.

        Returns:
            Database file path as string, or None if not connected
        """
        return str(self._current_db_path) if self._current_db_path else None

    @staticmethod
    def validate_database_file(path: str) -> tuple[bool, str]:
        """
        Validate that a file is a valid OneTaskAtATime database.

        Args:
            path: Path to database file to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, "") if valid
            - (False, error_message) if invalid
        """
        db_file = Path(path)

        # Check file exists
        if not db_file.exists():
            return (False, "File does not exist")

        # Check file is readable
        if not os.access(path, os.R_OK):
            return (False, "File is not readable")

        # Try to open as SQLite database
        try:
            test_conn = sqlite3.connect(str(db_file))

            # Check for required tables
            cursor = test_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}

            required_tables = {'tasks', 'contexts', 'project_tags', 'settings'}
            missing_tables = required_tables - tables

            if missing_tables:
                test_conn.close()
                return (False, f"Missing required tables: {', '.join(missing_tables)}")

            test_conn.close()
            return (True, "")

        except sqlite3.DatabaseError as e:
            return (False, f"Invalid SQLite database: {str(e)}")
        except Exception as e:
            return (False, f"Error validating database: {str(e)}")

    def switch_database(self, new_path: str) -> tuple[bool, str]:
        """
        Switch to a different database file.

        Args:
            new_path: Path to the new database file

        Returns:
            Tuple of (success, message)
            - (True, success_message) if switch succeeded
            - (False, error_message) if switch failed
        """
        # Validate the new database first
        is_valid, error_msg = self.validate_database_file(new_path)
        if not is_valid:
            return (False, f"Invalid database: {error_msg}")

        # Close current connection
        if self._connection:
            self._connection.close()
            self._connection = None

        # Connect to new database
        try:
            self._connect(custom_path=new_path)
            return (True, f"Successfully switched to database: {new_path}")
        except Exception as e:
            # If connection fails, try to reconnect to previous database
            if self._current_db_path:
                try:
                    self._connect(custom_path=str(self._current_db_path))
                except:
                    pass  # If this also fails, we're in trouble
            return (False, f"Failed to switch database: {str(e)}")

    @classmethod
    def get_instance(cls) -> 'DatabaseConnection':
        """
        Get the singleton instance of DatabaseConnection.

        Returns:
            DatabaseConnection instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


# Convenience function for getting connection
def get_db() -> sqlite3.Connection:
    """
    Get the singleton database connection.

    Returns:
        sqlite3.Connection: Active database connection
    """
    return DatabaseConnection().get_connection()
