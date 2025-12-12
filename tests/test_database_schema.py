"""
Unit tests for database schema creation and initialization.
"""

import pytest
import sqlite3
import tempfile
import os
from src.database.schema import DatabaseSchema
from src.database.connection import DatabaseConnection


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    yield path

    # Cleanup
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db_connection(temp_db):
    """Create a database connection for testing."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    yield conn
    conn.close()


class TestDatabaseSchema:
    """Tests for DatabaseSchema class."""

    def test_create_tables(self, db_connection):
        """Test that all tables are created successfully."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            'tasks', 'contexts', 'project_tags', 'task_project_tags',
            'dependencies', 'task_comparisons', 'postpone_history', 'settings'
        }

        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

    def test_create_indexes(self, db_connection):
        """Test that all indexes are created successfully."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}

        expected_indexes = {
            'idx_tasks_state', 'idx_tasks_due_date', 'idx_tasks_start_date',
            'idx_tasks_follow_up_date', 'idx_tasks_context_id', 'idx_tasks_base_priority',
            'idx_dependencies_blocked_task', 'idx_dependencies_blocking_task',
            'idx_comparisons_winner', 'idx_comparisons_loser',
            'idx_postpone_task_id', 'idx_task_project_tags_project'
        }

        assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"

    def test_default_settings(self, db_connection):
        """Test that default settings are inserted."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()
        cursor.execute("SELECT key FROM settings")
        settings_keys = {row[0] for row in cursor.fetchall()}

        expected_keys = {
            'comparison_decrement', 'someday_review_days', 'delegated_remind_days',
            'deferred_check_hours', 'theme', 'enable_notifications', 'score_epsilon'
        }

        assert expected_keys.issubset(settings_keys), f"Missing settings: {expected_keys - settings_keys}"

    def test_foreign_key_constraints_enabled(self, db_connection):
        """Test that foreign key constraints are enforced."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()

        # Try to insert a task with invalid context_id
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO tasks (title, context_id) VALUES (?, ?)",
                ("Test Task", 9999)
            )

    def test_task_state_constraint(self, db_connection):
        """Test that task state CHECK constraint is enforced."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()

        # Try to insert a task with invalid state
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO tasks (title, state) VALUES (?, ?)",
                ("Test Task", "invalid_state")
            )

    def test_task_priority_constraint(self, db_connection):
        """Test that task priority CHECK constraint is enforced."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()

        # Try to insert a task with invalid priority
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO tasks (title, base_priority) VALUES (?, ?)",
                ("Test Task", 5)
            )

    def test_schema_version(self, db_connection):
        """Test schema version management."""
        DatabaseSchema.initialize_database(db_connection)

        # Initially version should be 0 (not set yet)
        version = DatabaseSchema.get_schema_version(db_connection)
        assert version == 0

        # Set version
        DatabaseSchema.set_schema_version(db_connection, 1)
        version = DatabaseSchema.get_schema_version(db_connection)
        assert version == 1

    def test_unique_context_name(self, db_connection):
        """Test that context names must be unique."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO contexts (name) VALUES (?)", ("@computer",))

        # Try to insert duplicate
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO contexts (name) VALUES (?)", ("@computer",))

    def test_unique_project_tag_name(self, db_connection):
        """Test that project tag names must be unique."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO project_tags (name) VALUES (?)", ("Work",))

        # Try to insert duplicate
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("INSERT INTO project_tags (name) VALUES (?)", ("Work",))

    def test_dependency_self_reference_constraint(self, db_connection):
        """Test that dependencies cannot reference the same task."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()

        # Create a task
        cursor.execute("INSERT INTO tasks (title) VALUES (?)", ("Test Task",))
        task_id = cursor.lastrowid

        # Try to create self-dependency
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute(
                "INSERT INTO dependencies (blocked_task_id, blocking_task_id) VALUES (?, ?)",
                (task_id, task_id)
            )

    def test_cascade_delete_task_removes_associations(self, db_connection):
        """Test that deleting a task removes its associations."""
        DatabaseSchema.initialize_database(db_connection)

        cursor = db_connection.cursor()

        # Create task and project tag
        cursor.execute("INSERT INTO tasks (title) VALUES (?)", ("Test Task",))
        task_id = cursor.lastrowid
        cursor.execute("INSERT INTO project_tags (name) VALUES (?)", ("Work",))
        tag_id = cursor.lastrowid

        # Create association
        cursor.execute(
            "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
            (task_id, tag_id)
        )

        # Verify association exists
        cursor.execute("SELECT * FROM task_project_tags WHERE task_id = ?", (task_id,))
        assert cursor.fetchone() is not None

        # Delete task
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        # Verify association is gone
        cursor.execute("SELECT * FROM task_project_tags WHERE task_id = ?", (task_id,))
        assert cursor.fetchone() is None
