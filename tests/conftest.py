"""
Pytest configuration and shared fixtures.

Provides test database setup and cleanup for all tests.
"""

import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from src.database.schema import DatabaseSchema
from PyQt5.QtWidgets import QMessageBox


@pytest.fixture(scope="session", autouse=True)
def suppress_qt_messages():
    """
    Globally suppress QMessageBox dialogs during testing.

    This prevents "OK" dialogs from popping up and requiring user interaction.
    """
    # Store original methods
    original_information = QMessageBox.information
    original_warning = QMessageBox.warning
    original_critical = QMessageBox.critical

    # Replace with no-op functions
    QMessageBox.information = lambda *args, **kwargs: None
    QMessageBox.warning = lambda *args, **kwargs: None
    QMessageBox.critical = lambda *args, **kwargs: None

    yield

    # Restore original methods (cleanup)
    QMessageBox.information = original_information
    QMessageBox.warning = original_warning
    QMessageBox.critical = original_critical


@pytest.fixture(scope="function")
def test_db():
    """
    Create a temporary test database for each test function.

    This fixture provides complete test isolation by:
    1. Creating a new temporary database file
    2. Initializing the schema
    3. Yielding a connection to the test
    4. Cleaning up after the test
    """
    # Create a temporary database file
    temp_db = tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False)
    temp_db_path = temp_db.name
    temp_db.close()

    # Connect to the temporary database
    connection = sqlite3.connect(temp_db_path, check_same_thread=False)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row

    # Initialize schema
    DatabaseSchema.initialize_database(connection)
    connection.commit()

    yield connection

    # Cleanup
    connection.close()
    try:
        os.unlink(temp_db_path)
    except:
        pass


@pytest.fixture(scope="function")
def clean_test_db(test_db):
    """
    Provide a clean database that automatically rolls back after each test.

    This is useful for tests that need to verify state but don't want
    to affect other tests.
    """
    # Start a transaction
    test_db.execute("BEGIN")

    yield test_db

    # Rollback the transaction
    test_db.rollback()
