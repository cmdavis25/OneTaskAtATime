"""
First Run Detector for OneTaskAtATime.

Detects and manages first-run state for onboarding.
"""

import sqlite3
from typing import Optional


class FirstRunDetector:
    """
    Service for detecting and managing first-run state.

    Uses settings database to track whether onboarding has been completed.
    """

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize the First Run Detector.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db_connection = db_connection

    def is_first_run(self) -> bool:
        """
        Check if this is the first app launch.

        Returns:
            True if onboarding has not been completed
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            "SELECT value FROM settings WHERE key = 'onboarding_completed'"
        )

        result = cursor.fetchone()

        if not result:
            return True

        return result[0].lower() in ('false', '0', 'no')

    def mark_onboarding_complete(self):
        """Mark onboarding as completed in settings."""
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, value_type, description)
            VALUES ('onboarding_completed', 'true', 'boolean',
                   'Whether first-run onboarding has been completed')
            """
        )

        self.db_connection.commit()

    def should_show_tutorial(self) -> bool:
        """
        Check if tutorial should be shown.

        Returns:
            True if tutorial has not been shown before
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            "SELECT value FROM settings WHERE key = 'tutorial_shown'"
        )

        result = cursor.fetchone()

        if not result:
            return True

        return result[0].lower() in ('false', '0', 'no')

    def mark_tutorial_shown(self):
        """Mark tutorial as shown in settings."""
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, value_type, description)
            VALUES ('tutorial_shown', 'true', 'boolean',
                   'Whether interactive tutorial has been shown')
            """
        )

        self.db_connection.commit()

    def reset_onboarding(self):
        """Reset onboarding state (for testing or re-running tutorial)."""
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            UPDATE settings
            SET value = 'false'
            WHERE key IN ('onboarding_completed', 'tutorial_shown')
            """
        )

        self.db_connection.commit()
