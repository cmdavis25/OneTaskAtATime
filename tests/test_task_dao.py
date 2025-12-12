"""
Unit tests for TaskDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import date, datetime, timedelta
from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.models import Task, TaskState


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
def task_dao(db_connection):
    """Create a TaskDAO instance for testing."""
    return TaskDAO(db_connection)


class TestTaskDAO:
    """Tests for TaskDAO class."""

    def test_create_basic_task(self, task_dao):
        """Test creating a basic task."""
        task = Task(title="Test Task")
        created_task = task_dao.create(task)

        assert created_task.id is not None
        assert created_task.title == "Test Task"
        assert created_task.state == TaskState.ACTIVE
        assert created_task.base_priority == 2  # Default medium
        assert created_task.priority_adjustment == 0.0
        assert created_task.created_at is not None
        assert created_task.updated_at is not None

    def test_create_task_with_all_fields(self, task_dao):
        """Test creating a task with all fields populated."""
        tomorrow = date.today() + timedelta(days=1)
        task = Task(
            title="Complete Task",
            description="Detailed description",
            base_priority=3,
            due_date=tomorrow,
            state=TaskState.ACTIVE
        )
        created_task = task_dao.create(task)

        assert created_task.id is not None
        assert created_task.title == "Complete Task"
        assert created_task.description == "Detailed description"
        assert created_task.base_priority == 3
        assert created_task.due_date == tomorrow

    def test_create_task_with_existing_id_raises_error(self, task_dao):
        """Test that creating a task with an ID raises an error."""
        task = Task(title="Test", id=1)

        with pytest.raises(ValueError, match="Cannot create task that already has an id"):
            task_dao.create(task)

    def test_get_by_id(self, task_dao):
        """Test retrieving a task by ID."""
        task = Task(title="Test Task")
        created_task = task_dao.create(task)

        retrieved_task = task_dao.get_by_id(created_task.id)

        assert retrieved_task is not None
        assert retrieved_task.id == created_task.id
        assert retrieved_task.title == created_task.title

    def test_get_by_id_not_found(self, task_dao):
        """Test retrieving a non-existent task."""
        task = task_dao.get_by_id(9999)
        assert task is None

    def test_get_all_tasks(self, task_dao):
        """Test retrieving all tasks."""
        task_dao.create(Task(title="Task 1"))
        task_dao.create(Task(title="Task 2"))
        task_dao.create(Task(title="Task 3"))

        tasks = task_dao.get_all()

        assert len(tasks) == 3
        assert all(isinstance(t, Task) for t in tasks)

    def test_get_all_tasks_by_state(self, task_dao):
        """Test retrieving tasks filtered by state."""
        task_dao.create(Task(title="Active 1", state=TaskState.ACTIVE))
        task_dao.create(Task(title="Active 2", state=TaskState.ACTIVE))
        task_dao.create(Task(title="Completed", state=TaskState.COMPLETED))

        active_tasks = task_dao.get_all(TaskState.ACTIVE)
        completed_tasks = task_dao.get_all(TaskState.COMPLETED)

        assert len(active_tasks) == 2
        assert len(completed_tasks) == 1
        assert all(t.state == TaskState.ACTIVE for t in active_tasks)

    def test_update_task(self, task_dao):
        """Test updating a task."""
        task = task_dao.create(Task(title="Original Title"))

        task.title = "Updated Title"
        task.description = "New description"
        task.base_priority = 3

        updated_task = task_dao.update(task)

        assert updated_task.title == "Updated Title"
        assert updated_task.description == "New description"
        assert updated_task.base_priority == 3

        # Verify in database
        retrieved = task_dao.get_by_id(task.id)
        assert retrieved.title == "Updated Title"

    def test_update_task_without_id_raises_error(self, task_dao):
        """Test that updating a task without an ID raises an error."""
        task = Task(title="Test")

        with pytest.raises(ValueError, match="Cannot update task without an id"):
            task_dao.update(task)

    def test_delete_task(self, task_dao):
        """Test deleting a task."""
        task = task_dao.create(Task(title="To Delete"))

        result = task_dao.delete(task.id)
        assert result is True

        # Verify deleted
        retrieved = task_dao.get_by_id(task.id)
        assert retrieved is None

    def test_delete_nonexistent_task(self, task_dao):
        """Test deleting a non-existent task."""
        result = task_dao.delete(9999)
        assert result is False

    def test_get_active_tasks(self, task_dao):
        """Test getting active tasks."""
        task_dao.create(Task(title="Active 1", state=TaskState.ACTIVE))
        task_dao.create(Task(title="Deferred", state=TaskState.DEFERRED))
        task_dao.create(Task(title="Active 2", state=TaskState.ACTIVE))

        active_tasks = task_dao.get_active_tasks()

        assert len(active_tasks) == 2
        assert all(t.state == TaskState.ACTIVE for t in active_tasks)

    def test_get_deferred_tasks_ready_to_activate(self, task_dao):
        """Test getting deferred tasks that are ready to activate."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Create deferred tasks with different start dates
        task1 = Task(title="Ready 1", state=TaskState.DEFERRED, start_date=yesterday)
        task2 = Task(title="Ready 2", state=TaskState.DEFERRED, start_date=today)
        task3 = Task(title="Not Ready", state=TaskState.DEFERRED, start_date=tomorrow)

        task_dao.create(task1)
        task_dao.create(task2)
        task_dao.create(task3)

        ready_tasks = task_dao.get_deferred_tasks_ready_to_activate(today)

        assert len(ready_tasks) == 2
        assert all(t.start_date <= today for t in ready_tasks)

    def test_get_delegated_tasks_for_followup(self, task_dao):
        """Test getting delegated tasks that need follow-up."""
        today = date.today()
        two_days_later = today + timedelta(days=2)
        five_days_later = today + timedelta(days=5)

        # Create delegated tasks
        task1 = Task(
            title="Follow up soon",
            state=TaskState.DELEGATED,
            delegated_to="Alice",
            follow_up_date=two_days_later
        )
        task2 = Task(
            title="Follow up later",
            state=TaskState.DELEGATED,
            delegated_to="Bob",
            follow_up_date=five_days_later
        )

        task_dao.create(task1)
        task_dao.create(task2)

        # Get tasks needing follow-up within 3 days
        followup_tasks = task_dao.get_delegated_tasks_for_followup(today, days_before=3)

        # Should only get task1 (2 days < 3 days)
        assert len(followup_tasks) == 1
        assert followup_tasks[0].title == "Follow up soon"

    def test_task_model_methods(self, task_dao):
        """Test Task model helper methods."""
        task = Task(title="Test Task", base_priority=3)
        created_task = task_dao.create(task)

        # Test effective priority
        assert created_task.get_effective_priority() == 3.0

        created_task.priority_adjustment = 0.5
        assert created_task.get_effective_priority() == 2.5

        # Test state methods
        assert created_task.is_active() is True
        assert created_task.is_completed() is False

        # Test mark_completed
        created_task.mark_completed()
        assert created_task.state == TaskState.COMPLETED
        assert created_task.completed_at is not None

        # Test defer
        tomorrow = date.today() + timedelta(days=1)
        created_task.defer_until(tomorrow)
        assert created_task.state == TaskState.DEFERRED
        assert created_task.start_date == tomorrow

    def test_task_with_project_tags(self, task_dao, db_connection):
        """Test creating and updating tasks with project tags."""
        # Create a project tag first
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO project_tags (name) VALUES (?)", ("Work",))
        tag_id = cursor.lastrowid
        db_connection.commit()

        # Create task with project tag
        task = Task(title="Work Task", project_tags=[tag_id])
        created_task = task_dao.create(task)

        # Retrieve and verify
        retrieved = task_dao.get_by_id(created_task.id)
        assert tag_id in retrieved.project_tags

    def test_task_with_blocking_tasks(self, task_dao, db_connection):
        """Test tasks with dependencies (blocking tasks)."""
        # Create two tasks
        task1 = task_dao.create(Task(title="Blocking Task"))
        task2 = task_dao.create(Task(title="Blocked Task"))

        # Create dependency
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO dependencies (blocked_task_id, blocking_task_id) VALUES (?, ?)",
            (task2.id, task1.id)
        )
        db_connection.commit()

        # Retrieve blocked task
        retrieved = task_dao.get_by_id(task2.id)
        assert task1.id in retrieved.blocking_task_ids
        assert retrieved.is_blocked() is True

    def test_resurface_tracking(self, task_dao):
        """Test task resurfacing tracking."""
        task = task_dao.create(Task(title="Test Task"))

        assert task.resurface_count == 0
        assert task.last_resurfaced_at is None

        # Record resurface
        task.record_resurface()
        assert task.resurface_count == 1
        assert task.last_resurfaced_at is not None

        # Update in database
        task_dao.update(task)

        # Verify
        retrieved = task_dao.get_by_id(task.id)
        assert retrieved.resurface_count == 1
        assert retrieved.last_resurfaced_at is not None
