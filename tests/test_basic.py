"""
Basic tests to verify Phase 0 setup.

Tests the skeleton application and database connection.
"""

import pytest
from database.connection import DatabaseConnection, get_db
import sqlite3


class TestDatabaseConnection:
    """Test database connection functionality."""

    def test_singleton_pattern(self):
        """Test that DatabaseConnection implements singleton pattern."""
        conn1 = DatabaseConnection()
        conn2 = DatabaseConnection()
        assert conn1 is conn2, "DatabaseConnection should be a singleton"

    def test_get_connection(self):
        """Test that get_connection returns a valid SQLite connection."""
        db = get_db()
        assert isinstance(db, sqlite3.Connection), "Should return SQLite connection"

    def test_foreign_keys_enabled(self):
        """Test that foreign key constraints are enabled."""
        db = get_db()
        cursor = db.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1, "Foreign keys should be enabled"


class TestApplicationSetup:
    """Test basic application setup."""

    def test_imports(self):
        """Test that main modules can be imported."""
        try:
            from ui.main_window import MainWindow
            assert MainWindow is not None
        except ImportError as e:
            pytest.fail(f"Failed to import MainWindow: {e}")

    def test_main_module(self):
        """Test that main module exists and has main function."""
        import main
        assert hasattr(main, 'main'), "main.py should have a main() function"
