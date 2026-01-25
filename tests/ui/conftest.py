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
    2. Patches custom MessageBox static methods to return immediately without user intervention
    3. Also patches QMessageBox for any code that might use it directly
    4. Does NOT patch QDialog.exec_() globally to allow tests to control dialog behavior

    Note: Tests should call accept() or reject() directly on dialogs instead of
    relying on exec() return values.
    """
    from src.services.first_run_detector import FirstRunDetector
    from src.ui.message_box import MessageBox
    from PyQt5.QtWidgets import QMessageBox

    # Patch is_first_run to always return False
    monkeypatch.setattr(FirstRunDetector, 'is_first_run', lambda self: False)

    # Patch should_show_tutorial to always return False
    monkeypatch.setattr(FirstRunDetector, 'should_show_tutorial', lambda self: False)

    # Patch custom MessageBox static methods (used by production code)
    monkeypatch.setattr(MessageBox, 'information', lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(MessageBox, 'warning', lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(MessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(MessageBox, 'critical', lambda *args, **kwargs: QMessageBox.Ok)

    # Also patch standard QMessageBox as fallback
    monkeypatch.setattr(QMessageBox, 'information', lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, 'warning', lambda *args, **kwargs: QMessageBox.Ok)
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)
    monkeypatch.setattr(QMessageBox, 'critical', lambda *args, **kwargs: QMessageBox.Ok)


@pytest.fixture(autouse=True)
def auto_close_dialogs(qtbot):
    """
    Auto-close any QDialog that appears during tests to prevent manual intervention.

    This is a safety net that ensures even if a dialog escapes mocking, it will
    automatically accept and close immediately, allowing tests to continue running
    without manual intervention.

    This fixture patches QDialog.exec_ globally for the duration of each test.
    """
    from PyQt5.QtWidgets import QDialog
    from PyQt5.QtCore import QTimer

    original_exec = QDialog.exec_

    def auto_exec(self):
        """Auto-accept dialog immediately and return."""
        QTimer.singleShot(0, self.accept)
        return original_exec(self)

    QDialog.exec_ = auto_exec
    yield
    QDialog.exec_ = original_exec


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
    """Mock DatabaseConnection for testing.

    This class wraps a sqlite3.Connection and provides both:
    1. DatabaseConnection-style interface (get_connection())
    2. Direct sqlite3.Connection interface (cursor(), execute(), etc.)

    This ensures compatibility with both types of database consumers.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        """Return underlying connection (DatabaseConnection interface)."""
        return self._conn

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def commit(self):
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self):
        """Roll back the current transaction."""
        self._conn.rollback()

    def cursor(self):
        """Return a cursor object (raw sqlite3.Connection interface)."""
        return self._conn.cursor()

    def execute(self, *args, **kwargs):
        """Execute SQL directly (raw sqlite3.Connection interface)."""
        return self._conn.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        """Execute SQL for multiple parameter sets."""
        return self._conn.executemany(*args, **kwargs)

    def executescript(self, *args, **kwargs):
        """Execute SQL script."""
        return self._conn.executescript(*args, **kwargs)

    @property
    def row_factory(self):
        """Get row factory."""
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, value):
        """Set row factory."""
        self._conn.row_factory = value


@pytest.fixture
def db_connection():
    """
    Create in-memory database wrapped in MockDatabaseConnection.

    This fixture provides a DatabaseConnection-compatible wrapper
    for UI tests that expect db_connection.get_connection().
    """
    from src.database.schema import DatabaseSchema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)

    mock_conn = MockDatabaseConnection(conn)
    yield mock_conn
    conn.close()
