"""
Pytest configuration for UI tests.

This module provides common fixtures and setup for all UI tests,
including preventing the Welcome Wizard from appearing during test execution.
"""

import pytest
import sqlite3
from PyQt5.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """
    Create QApplication for test session.

    This is a session-scoped fixture to ensure only one QApplication
    instance exists for all UI tests.
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture(autouse=True)
def prevent_dialogs_from_blocking(monkeypatch):
    """
    Automatically prevent dialogs from blocking test execution.

    This fixture runs automatically for every test and:
    1. Patches FirstRunDetector to indicate onboarding is complete
    2. Prevents all QDialog.exec_() calls from blocking
    """
    from PyQt5.QtWidgets import QDialog
    from src.services.first_run_detector import FirstRunDetector

    # Patch is_first_run to always return False
    monkeypatch.setattr(FirstRunDetector, 'is_first_run', lambda self: False)

    # Patch should_show_tutorial to always return False
    monkeypatch.setattr(FirstRunDetector, 'should_show_tutorial', lambda self: False)

    # Prevent ALL dialogs from blocking by patching QDialog.exec_
    original_exec = QDialog.exec_

    def mock_exec(self):
        """Mock exec_ to prevent any dialog from blocking tests."""
        # Return Rejected (0) to simulate user canceling
        return 0

    monkeypatch.setattr(QDialog, 'exec_', mock_exec)


@pytest.fixture
def mark_onboarding_complete():
    """
    Helper fixture to mark onboarding as complete in a database connection.

    Use this fixture when you need to explicitly mark onboarding complete
    in a test database.

    Returns:
        Function that takes a database connection and marks onboarding complete
    """
    def _mark_complete(db_connection):
        """Mark onboarding complete in the given database."""
        if hasattr(db_connection, 'get_connection'):
            conn = db_connection.get_connection()
        else:
            conn = db_connection

        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, value_type, description)
            VALUES ('onboarding_completed', 'true', 'boolean',
                   'Whether first-run onboarding has been completed')
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, value_type, description)
            VALUES ('tutorial_shown', 'true', 'boolean',
                   'Whether interactive tutorial has been shown')
        """)
        conn.commit()

    return _mark_complete


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()
