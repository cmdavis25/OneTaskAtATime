"""
Database Connection Module

Provides singleton SQLite database connection management for OneTaskAtATime.
"""

import sqlite3
import os
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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database connection if not already connected."""
        if self._connection is None:
            self._connect()

    def _connect(self):
        """
        Establish connection to SQLite database.

        Creates the database file in the resources directory if it doesn't exist.
        Enables foreign key constraints for referential integrity.
        """
        # Ensure resources directory exists
        resources_dir = Path(__file__).parent.parent.parent / "resources"
        resources_dir.mkdir(exist_ok=True)

        # Database file path
        db_path = resources_dir / "onetaskatatime.db"

        # Connect to database
        self._connection = sqlite3.connect(
            str(db_path),
            check_same_thread=False  # Allow usage across threads
        )

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


# Convenience function for getting connection
def get_db() -> sqlite3.Connection:
    """
    Get the singleton database connection.

    Returns:
        sqlite3.Connection: Active database connection
    """
    return DatabaseConnection().get_connection()
