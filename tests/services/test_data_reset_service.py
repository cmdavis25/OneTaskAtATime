"""Unit tests for DataResetService."""
import pytest
import sqlite3
from datetime import datetime
from src.services.data_reset_service import DataResetService
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.database.task_dao import TaskDAO
from src.database.context_dao import ContextDAO
from src.database.project_tag_dao import ProjectTagDAO
from src.database.settings_dao import SettingsDAO
from src.models.context import Context
from src.models.project_tag import ProjectTag


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        pass  # Don't close - let test_db fixture handle it

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


@pytest.fixture
def db_connection(test_db):
    """Create a test database connection wrapper."""
    return MockDatabaseConnection(test_db)


@pytest.fixture
def reset_service(test_db):
    """Create DataResetService instance."""
    return DataResetService(test_db)


@pytest.fixture
def populated_database(db_connection):
    """Populate database with test data."""
    conn = db_connection.get_connection()

    # Create contexts
    context_dao = ContextDAO(conn)
    ctx1 = context_dao.create(Context(name="Work", description="Work context"))
    ctx2 = context_dao.create(Context(name="Home", description="Home context"))

    # Create project tags
    tag_dao = ProjectTagDAO(conn)
    tag1 = tag_dao.create(ProjectTag(name="Project A", description="First project"))
    tag2 = tag_dao.create(ProjectTag(name="Project B", description="Second project"))

    # Create tasks
    task_dao = TaskDAO(conn)
    task1 = Task(
        title="Task 1",
        description="First task",
        state=TaskState.ACTIVE,
        base_priority=Priority.HIGH.value,
        context_id=ctx1.id
    )
    task1 = task_dao.create(task1)

    task2 = Task(
        title="Task 2",
        description="Second task",
        state=TaskState.ACTIVE,
        base_priority=Priority.MEDIUM.value,
        context_id=ctx2.id
    )
    task2 = task_dao.create(task2)

    # Add dependencies
    conn.execute(
        "INSERT INTO dependencies (blocked_task_id, blocking_task_id, created_at) VALUES (?, ?, ?)",
        (task2.id, task1.id, datetime.now().isoformat())
    )

    # Add task-tag association
    conn.execute(
        "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
        (task1.id, tag1.id)
    )

    # Add settings
    settings_dao = SettingsDAO(conn)
    settings_dao.set('test_setting', 'test_value', 'string', 'Test setting')

    conn.commit()

    return {
        'contexts': [ctx1, ctx2],
        'tags': [tag1, tag2],
        'tasks': [task1, task2]
    }


def test_get_reset_summary(reset_service, populated_database):
    """Test that reset summary returns correct counts."""
    summary = reset_service.get_reset_summary()

    assert summary['tasks'] == 2
    assert summary['contexts'] == 2
    assert summary['project_tags'] == 2
    assert summary['dependencies'] == 1
    assert summary['comparisons'] == 0  # None created in fixture
    assert summary['history'] == 0
    assert summary['notifications'] == 0
    # Settings includes default settings loaded by schema initialization
    assert summary['settings'] >= 1


def test_reset_all_data_complete(db_connection, reset_service, populated_database):
    """Test complete nuclear reset deletes all data."""
    result = reset_service.reset_all_data(
        include_contexts=True,
        include_tags=True,
        reset_settings=True
    )

    assert result['success'] is True

    # Verify all data deleted
    conn = db_connection.get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tasks")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM contexts")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM project_tags")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM dependencies")
    assert cursor.fetchone()[0] == 0

    cursor.execute("SELECT COUNT(*) FROM settings")
    assert cursor.fetchone()[0] == 0


def test_reset_preserves_contexts(db_connection, reset_service, populated_database):
    """Test that reset can preserve contexts."""
    result = reset_service.reset_all_data(
        include_contexts=False,
        include_tags=True,
        reset_settings=False
    )

    assert result['success'] is True

    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Tasks should be deleted
    cursor.execute("SELECT COUNT(*) FROM tasks")
    assert cursor.fetchone()[0] == 0

    # Contexts should be preserved
    cursor.execute("SELECT COUNT(*) FROM contexts")
    assert cursor.fetchone()[0] == 2

    # Tags should be deleted
    cursor.execute("SELECT COUNT(*) FROM project_tags")
    assert cursor.fetchone()[0] == 0


def test_reset_preserves_tags(db_connection, reset_service, populated_database):
    """Test that reset can preserve project tags."""
    result = reset_service.reset_all_data(
        include_contexts=True,
        include_tags=False,
        reset_settings=False
    )

    assert result['success'] is True

    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Tasks should be deleted
    cursor.execute("SELECT COUNT(*) FROM tasks")
    assert cursor.fetchone()[0] == 0

    # Contexts should be deleted
    cursor.execute("SELECT COUNT(*) FROM contexts")
    assert cursor.fetchone()[0] == 0

    # Tags should be preserved
    cursor.execute("SELECT COUNT(*) FROM project_tags")
    assert cursor.fetchone()[0] == 2


def test_reset_preserves_settings(db_connection, reset_service, populated_database):
    """Test that reset can preserve settings."""
    result = reset_service.reset_all_data(
        include_contexts=True,
        include_tags=True,
        reset_settings=False
    )

    assert result['success'] is True

    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Tasks should be deleted
    cursor.execute("SELECT COUNT(*) FROM tasks")
    assert cursor.fetchone()[0] == 0

    # Settings should be preserved (includes default settings)
    cursor.execute("SELECT COUNT(*) FROM settings")
    assert cursor.fetchone()[0] >= 1


def test_reset_deleted_counts(reset_service, populated_database):
    """Test that reset returns correct deleted counts."""
    result = reset_service.reset_all_data(
        include_contexts=True,
        include_tags=True,
        reset_settings=False
    )

    assert result['success'] is True

    deleted = result['deleted']
    assert deleted['tasks'] == 2
    assert deleted['contexts'] == 2
    assert deleted['project_tags'] == 2
    assert deleted['dependencies'] == 1
    assert deleted['task_tags'] == 1  # One task-tag association
    assert deleted['settings'] == 0  # Not reset


def test_reset_task_data_only(db_connection, reset_service, populated_database):
    """Test reset_task_data_only helper method."""
    result = reset_service.reset_task_data_only()

    assert result['success'] is True

    conn = db_connection.get_connection()
    cursor = conn.cursor()

    # Tasks deleted
    cursor.execute("SELECT COUNT(*) FROM tasks")
    assert cursor.fetchone()[0] == 0

    # Organizational structures preserved
    cursor.execute("SELECT COUNT(*) FROM contexts")
    assert cursor.fetchone()[0] == 2

    cursor.execute("SELECT COUNT(*) FROM project_tags")
    assert cursor.fetchone()[0] == 2

    # Settings preserved (includes default settings)
    cursor.execute("SELECT COUNT(*) FROM settings")
    assert cursor.fetchone()[0] >= 1


def test_get_total_items_to_delete(reset_service, populated_database):
    """Test calculation of total items to delete."""
    # Full reset
    total = reset_service.get_total_items_to_delete(
        include_contexts=True,
        include_tags=True,
        reset_settings=True
    )
    assert total > 0

    # Partial reset (preserve contexts and tags)
    partial_total = reset_service.get_total_items_to_delete(
        include_contexts=False,
        include_tags=False,
        reset_settings=False
    )
    assert partial_total < total


def test_reset_deletes_in_correct_order(db_connection, reset_service, populated_database):
    """Test that reset deletes in correct dependency order."""
    # This should not raise foreign key constraint errors
    result = reset_service.reset_all_data(
        include_contexts=True,
        include_tags=True,
        reset_settings=True
    )

    assert result['success'] is True
    # If no error, deletion order was correct


def test_reset_empty_database(reset_service):
    """Test resetting an already empty database."""
    result = reset_service.reset_all_data()

    assert result['success'] is True

    deleted = result['deleted']
    assert all(count == 0 for count in deleted.values())


def test_reset_with_notifications(db_connection, reset_service, populated_database):
    """Test that reset deletes notifications."""
    conn = db_connection.get_connection()

    # Add a notification (using schema column names: type, title, message, is_read, created_at)
    conn.execute(
        """INSERT INTO notifications (type, title, message, is_read, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        ('info', 'Test', 'Message', 0, datetime.now().isoformat())
    )
    conn.commit()

    result = reset_service.reset_all_data()

    assert result['success'] is True
    assert result['deleted']['notifications'] == 1


def test_reset_with_postpone_history(db_connection, reset_service, populated_database):
    """Test that reset deletes postpone history."""
    conn = db_connection.get_connection()
    tasks = populated_database['tasks']

    # Add postpone history
    conn.execute(
        """INSERT INTO postpone_history (task_id, postponed_at, reason_type, reason_notes)
           VALUES (?, ?, ?, ?)""",
        (tasks[0].id, datetime.now().isoformat(), 'other', 'Testing')
    )
    conn.commit()

    result = reset_service.reset_all_data()

    assert result['success'] is True
    assert result['deleted']['history'] == 1


def test_reset_transaction_safety(db_connection, reset_service, populated_database):
    """Test that reset uses transactions properly."""
    # The reset should complete successfully or rollback entirely
    result = reset_service.reset_all_data()

    # Either success=True with all data deleted, or success=False with data intact
    assert result['success'] is True

    if result['success']:
        conn = db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks")
        assert cursor.fetchone()[0] == 0
