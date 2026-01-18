"""
Unit tests for SettingsDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime

from src.database.schema import DatabaseSchema
from src.database.settings_dao import SettingsDAO


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db_connection(temp_db):
    """Create a database connection for testing."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def settings_dao(db_connection):
    """Create a SettingsDAO instance for testing."""
    return SettingsDAO(db_connection)


class TestSettingsDAO:
    """Tests for SettingsDAO class."""

    # Basic get/set tests

    def test_set_and_get_string(self, settings_dao):
        """Test setting and getting a string value."""
        settings_dao.set("test_key", "test_value", "string")

        result = settings_dao.get("test_key")

        assert result == "test_value"

    def test_set_and_get_integer(self, settings_dao):
        """Test setting and getting an integer value."""
        settings_dao.set("max_items", 100, "integer")

        result = settings_dao.get("max_items")

        assert result == 100
        assert isinstance(result, int)

    def test_set_and_get_float(self, settings_dao):
        """Test setting and getting a float value."""
        settings_dao.set("threshold", 0.75, "float")

        result = settings_dao.get("threshold")

        assert result == 0.75
        assert isinstance(result, float)

    def test_set_and_get_boolean_true(self, settings_dao):
        """Test setting and getting a boolean true value."""
        settings_dao.set("enabled", True, "boolean")

        result = settings_dao.get("enabled")

        assert result is True
        assert isinstance(result, bool)

    def test_set_and_get_boolean_false(self, settings_dao):
        """Test setting and getting a boolean false value."""
        settings_dao.set("disabled", False, "boolean")

        result = settings_dao.get("disabled")

        assert result is False
        assert isinstance(result, bool)

    def test_set_and_get_json(self, settings_dao):
        """Test setting and getting a JSON value."""
        data = {"name": "test", "values": [1, 2, 3], "nested": {"key": "value"}}
        settings_dao.set("complex_data", data, "json")

        result = settings_dao.get("complex_data")

        assert result == data
        assert result["name"] == "test"
        assert result["values"] == [1, 2, 3]
        assert result["nested"]["key"] == "value"

    def test_get_nonexistent_returns_default(self, settings_dao):
        """Test that getting a nonexistent key returns the default value."""
        result = settings_dao.get("nonexistent", default="default_value")

        assert result == "default_value"

    def test_get_nonexistent_returns_none(self, settings_dao):
        """Test that getting a nonexistent key returns None if no default."""
        result = settings_dao.get("nonexistent")

        assert result is None

    def test_set_with_description(self, settings_dao, db_connection):
        """Test setting a value with a description."""
        settings_dao.set("documented_key", "value", "string", "This is a documented setting")

        cursor = db_connection.cursor()
        cursor.execute("SELECT description FROM settings WHERE key = ?", ("documented_key",))
        row = cursor.fetchone()

        assert row[0] == "This is a documented setting"

    def test_set_overwrites_existing(self, settings_dao):
        """Test that setting an existing key overwrites the value."""
        settings_dao.set("overwrite_test", "original", "string")
        settings_dao.set("overwrite_test", "updated", "string")

        result = settings_dao.get("overwrite_test")

        assert result == "updated"

    # Convenience method tests

    def test_get_int(self, settings_dao):
        """Test get_int convenience method."""
        settings_dao.set("count", 42, "integer")

        result = settings_dao.get_int("count")

        assert result == 42
        assert isinstance(result, int)

    def test_get_int_default(self, settings_dao):
        """Test get_int with default value."""
        result = settings_dao.get_int("nonexistent", default=10)

        assert result == 10

    def test_get_str(self, settings_dao):
        """Test get_str convenience method."""
        settings_dao.set("name", "Alice", "string")

        result = settings_dao.get_str("name")

        assert result == "Alice"
        assert isinstance(result, str)

    def test_get_str_default(self, settings_dao):
        """Test get_str with default value."""
        result = settings_dao.get_str("nonexistent", default="default")

        assert result == "default"

    def test_get_bool(self, settings_dao):
        """Test get_bool convenience method."""
        settings_dao.set("active", True, "boolean")

        result = settings_dao.get_bool("active")

        assert result is True
        assert isinstance(result, bool)

    def test_get_bool_default(self, settings_dao):
        """Test get_bool with default value."""
        result = settings_dao.get_bool("nonexistent", default=True)

        assert result is True

    def test_get_bool_from_string(self, settings_dao):
        """Test get_bool handles string values."""
        settings_dao.set("string_bool", "true", "string")

        result = settings_dao.get_bool("string_bool")

        assert result is True

    def test_get_float(self, settings_dao):
        """Test get_float convenience method."""
        settings_dao.set("ratio", 0.5, "float")

        result = settings_dao.get_float("ratio")

        assert result == 0.5
        assert isinstance(result, float)

    def test_get_float_default(self, settings_dao):
        """Test get_float with default value."""
        result = settings_dao.get_float("nonexistent", default=1.5)

        assert result == 1.5

    def test_get_datetime(self, settings_dao):
        """Test get_datetime convenience method."""
        now = datetime.now()
        settings_dao.set("timestamp", now.isoformat(), "string")

        result = settings_dao.get_datetime("timestamp")

        assert result is not None
        assert isinstance(result, datetime)
        # Compare with some tolerance for microseconds
        assert abs((result - now).total_seconds()) < 1

    def test_get_datetime_default(self, settings_dao):
        """Test get_datetime with default value."""
        default_dt = datetime(2020, 1, 1)
        result = settings_dao.get_datetime("nonexistent", default=default_dt)

        assert result == default_dt

    def test_get_datetime_invalid_returns_default(self, settings_dao):
        """Test get_datetime returns default for invalid datetime string."""
        settings_dao.set("bad_date", "not-a-date", "string")
        default_dt = datetime(2020, 1, 1)

        result = settings_dao.get_datetime("bad_date", default=default_dt)

        assert result == default_dt

    # get_all tests

    def test_get_all(self, settings_dao):
        """Test getting all settings as a dictionary."""
        settings_dao.set("key1", "value1", "string")
        settings_dao.set("key2", 42, "integer")
        settings_dao.set("key3", True, "boolean")

        all_settings = settings_dao.get_all()

        assert len(all_settings) >= 3  # May have default settings
        assert all_settings["key1"] == "value1"
        assert all_settings["key2"] == 42
        assert all_settings["key3"] is True

    def test_get_all_empty(self, settings_dao, db_connection):
        """Test getting all settings when empty."""
        # Clear any default settings
        cursor = db_connection.cursor()
        cursor.execute("DELETE FROM settings")
        db_connection.commit()

        all_settings = settings_dao.get_all()

        assert all_settings == {}

    # delete tests

    def test_delete(self, settings_dao):
        """Test deleting a setting."""
        settings_dao.set("to_delete", "value", "string")

        result = settings_dao.delete("to_delete")

        assert result is True
        assert settings_dao.get("to_delete") is None

    def test_delete_nonexistent(self, settings_dao):
        """Test deleting a nonexistent setting."""
        result = settings_dao.delete("nonexistent")

        assert result is False

    # Type conversion edge cases

    def test_boolean_conversion_with_actual_booleans(self, settings_dao):
        """Test boolean conversion with actual boolean values."""
        # When storing actual Python booleans, the conversion works correctly
        settings_dao.set("bool_true", True, "boolean")
        settings_dao.set("bool_false", False, "boolean")

        assert settings_dao.get("bool_true") is True
        assert settings_dao.get("bool_false") is False

    def test_boolean_storage_stores_normalized_values(self, settings_dao, db_connection):
        """Test that booleans are stored as normalized 'true'/'false' strings."""
        settings_dao.set("test_bool", True, "boolean")

        cursor = db_connection.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("test_bool",))
        row = cursor.fetchone()

        assert row[0] == "true"

        settings_dao.set("test_bool_f", False, "boolean")
        cursor.execute("SELECT value FROM settings WHERE key = ?", ("test_bool_f",))
        row = cursor.fetchone()

        assert row[0] == "false"

    def test_json_empty_list(self, settings_dao):
        """Test JSON with empty list."""
        settings_dao.set("empty_list", [], "json")

        result = settings_dao.get("empty_list")

        assert result == []

    def test_json_empty_dict(self, settings_dao):
        """Test JSON with empty dict."""
        settings_dao.set("empty_dict", {}, "json")

        result = settings_dao.get("empty_dict")

        assert result == {}
