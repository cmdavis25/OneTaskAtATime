"""
Unit tests for ContextDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from src.database.schema import DatabaseSchema
from src.database.context_dao import ContextDAO
from src.models import Context


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
def context_dao(db_connection):
    """Create a ContextDAO instance for testing."""
    return ContextDAO(db_connection)


class TestContextDAO:
    """Tests for ContextDAO class."""

    def test_create_context(self, context_dao):
        """Test creating a context."""
        context = Context(name="@computer", description="Tasks requiring a computer")
        created = context_dao.create(context)

        assert created.id is not None
        assert created.name == "@computer"
        assert created.description == "Tasks requiring a computer"
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_create_context_with_existing_id_raises_error(self, context_dao):
        """Test that creating a context with an ID raises an error."""
        context = Context(name="@phone", id=1)

        with pytest.raises(ValueError, match="Cannot create context that already has an id"):
            context_dao.create(context)

    def test_create_duplicate_name_raises_error(self, context_dao):
        """Test that duplicate context names raise an error."""
        context_dao.create(Context(name="@computer"))

        with pytest.raises(sqlite3.IntegrityError):
            context_dao.create(Context(name="@computer"))

    def test_get_by_id(self, context_dao):
        """Test retrieving a context by ID."""
        created = context_dao.create(Context(name="@home"))
        retrieved = context_dao.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "@home"

    def test_get_by_id_not_found(self, context_dao):
        """Test retrieving a non-existent context."""
        context = context_dao.get_by_id(9999)
        assert context is None

    def test_get_by_name(self, context_dao):
        """Test retrieving a context by name."""
        context_dao.create(Context(name="@office"))
        retrieved = context_dao.get_by_name("@office")

        assert retrieved is not None
        assert retrieved.name == "@office"

    def test_get_by_name_not_found(self, context_dao):
        """Test retrieving a non-existent context by name."""
        context = context_dao.get_by_name("@nonexistent")
        assert context is None

    def test_get_all(self, context_dao):
        """Test retrieving all contexts."""
        context_dao.create(Context(name="@computer"))
        context_dao.create(Context(name="@phone"))
        context_dao.create(Context(name="@errands"))

        contexts = context_dao.get_all()

        assert len(contexts) == 3
        # Should be sorted by name
        assert contexts[0].name == "@computer"
        assert contexts[1].name == "@errands"
        assert contexts[2].name == "@phone"

    def test_update_context(self, context_dao):
        """Test updating a context."""
        context = context_dao.create(Context(name="@computer"))

        context.name = "@laptop"
        context.description = "Tasks on laptop"
        updated = context_dao.update(context)

        assert updated.name == "@laptop"
        assert updated.description == "Tasks on laptop"

        # Verify in database
        retrieved = context_dao.get_by_id(context.id)
        assert retrieved.name == "@laptop"

    def test_update_context_without_id_raises_error(self, context_dao):
        """Test that updating a context without an ID raises an error."""
        context = Context(name="@phone")

        with pytest.raises(ValueError, match="Cannot update context without an id"):
            context_dao.update(context)

    def test_update_to_duplicate_name_raises_error(self, context_dao):
        """Test that updating to a duplicate name raises an error."""
        context_dao.create(Context(name="@computer"))
        context2 = context_dao.create(Context(name="@phone"))

        context2.name = "@computer"
        with pytest.raises(sqlite3.IntegrityError):
            context_dao.update(context2)

    def test_delete_context(self, context_dao):
        """Test deleting a context."""
        context = context_dao.create(Context(name="@computer"))

        result = context_dao.delete(context.id)
        assert result is True

        # Verify deleted
        retrieved = context_dao.get_by_id(context.id)
        assert retrieved is None

    def test_delete_nonexistent_context(self, context_dao):
        """Test deleting a non-existent context."""
        result = context_dao.delete(9999)
        assert result is False

    def test_context_string_representation(self, context_dao):
        """Test Context string methods."""
        context = Context(name="@computer", description="Computer tasks")

        assert str(context) == "@computer"
        assert "Context" in repr(context)
        assert "@computer" in repr(context)
