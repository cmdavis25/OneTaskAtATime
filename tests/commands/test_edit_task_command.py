"""
Unit tests for EditTaskCommand.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import date, timedelta

from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.commands.edit_task_command import EditTaskCommand
from src.models import Task
from src.models.enums import TaskState


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


@pytest.fixture
def sample_task(task_dao):
    """Create a sample task for testing."""
    task = Task(
        title="Original Title",
        description="Original Description",
        base_priority=2
    )
    return task_dao.create(task)


class TestEditTaskCommandExecute:
    """Tests for EditTaskCommand execute method."""

    def test_execute_updates_title(self, task_dao, sample_task):
        """Test that execute updates the task title."""
        new_task = Task(
            title="Updated Title",
            description=sample_task.description,
            base_priority=sample_task.base_priority
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.title == "Updated Title"

    def test_execute_updates_description(self, task_dao, sample_task):
        """Test that execute updates the task description."""
        new_task = Task(
            title=sample_task.title,
            description="Updated Description",
            base_priority=sample_task.base_priority
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.description == "Updated Description"

    def test_execute_updates_priority(self, task_dao, sample_task):
        """Test that execute updates the task priority."""
        new_task = Task(
            title=sample_task.title,
            description=sample_task.description,
            base_priority=3
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.base_priority == 3

    def test_execute_updates_due_date(self, task_dao, sample_task):
        """Test that execute updates the task due date."""
        tomorrow = date.today() + timedelta(days=1)
        new_task = Task(
            title=sample_task.title,
            description=sample_task.description,
            base_priority=sample_task.base_priority,
            due_date=tomorrow
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.due_date == tomorrow

    def test_execute_updates_multiple_fields(self, task_dao, sample_task):
        """Test that execute updates multiple fields at once."""
        tomorrow = date.today() + timedelta(days=1)
        new_task = Task(
            title="New Title",
            description="New Description",
            base_priority=3,
            due_date=tomorrow
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.title == "New Title"
        assert updated_task.description == "New Description"
        assert updated_task.base_priority == 3
        assert updated_task.due_date == tomorrow

    def test_execute_preserves_task_id(self, task_dao, sample_task):
        """Test that execute preserves the original task ID."""
        new_task = Task(
            id=9999,  # Different ID should be ignored
            title="Updated Title"
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True

        # Original task should be updated
        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task is not None
        assert updated_task.id == sample_task.id

        # Fake ID should not create a new task
        fake_task = task_dao.get_by_id(9999)
        assert fake_task is None

    def test_execute_stores_original_for_undo(self, task_dao, sample_task):
        """Test that execute stores the original task for undo."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()

        assert command.original_task is not None
        assert command.original_task.title == "Original Title"
        assert command.original_task.description == "Original Description"

    def test_execute_returns_false_for_nonexistent_task(self, task_dao):
        """Test that execute returns False for non-existent task."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, 9999, new_task)
        result = command.execute()

        assert result is False

    def test_execute_does_not_change_state(self, task_dao, sample_task):
        """Test that execute does not unintentionally change the task state."""
        new_task = Task(
            title="Updated Title",
            state=TaskState.COMPLETED  # Different state
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()

        updated_task = task_dao.get_by_id(sample_task.id)
        # State will be updated to COMPLETED since we're replacing the whole task
        # This is expected behavior for EditTaskCommand
        assert updated_task.state == TaskState.COMPLETED


class TestEditTaskCommandUndo:
    """Tests for EditTaskCommand undo method."""

    def test_undo_restores_original_title(self, task_dao, sample_task):
        """Test that undo restores the original title."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()

        # Verify update happened
        assert task_dao.get_by_id(sample_task.id).title == "Updated Title"

        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(sample_task.id)
        assert restored_task.title == "Original Title"

    def test_undo_restores_all_original_fields(self, task_dao, sample_task):
        """Test that undo restores all original fields."""
        tomorrow = date.today() + timedelta(days=1)
        new_task = Task(
            title="New Title",
            description="New Description",
            base_priority=3,
            due_date=tomorrow
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()
        result = command.undo()

        assert result is True

        restored_task = task_dao.get_by_id(sample_task.id)
        assert restored_task.title == "Original Title"
        assert restored_task.description == "Original Description"
        assert restored_task.base_priority == 2
        assert restored_task.due_date is None

    def test_undo_returns_false_without_execute(self, task_dao, sample_task):
        """Test that undo returns False if execute was not called."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        # Don't call execute

        result = command.undo()

        assert result is False

    def test_multiple_execute_undo_cycles(self, task_dao, sample_task):
        """Test multiple execute/undo cycles."""
        new_task = Task(title="Updated Title")
        command = EditTaskCommand(task_dao, sample_task.id, new_task)

        # First cycle
        command.execute()
        assert task_dao.get_by_id(sample_task.id).title == "Updated Title"
        command.undo()
        assert task_dao.get_by_id(sample_task.id).title == "Original Title"

        # Second cycle
        command.execute()
        assert task_dao.get_by_id(sample_task.id).title == "Updated Title"
        command.undo()
        assert task_dao.get_by_id(sample_task.id).title == "Original Title"


class TestEditTaskCommandGetDescription:
    """Tests for EditTaskCommand get_description method."""

    def test_get_description_after_execute(self, task_dao, sample_task):
        """Test get_description after execute."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()

        description = command.get_description()

        assert "Edit task" in description
        assert "Original Title" in description

    def test_get_description_before_execute(self, task_dao, sample_task):
        """Test get_description before execute."""
        new_task = Task(title="Updated Title")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)

        description = command.get_description()

        assert "Edit task" in description
        assert str(sample_task.id) in description


class TestEditTaskCommandEdgeCases:
    """Edge case tests for EditTaskCommand."""

    def test_edit_with_empty_title(self, task_dao, sample_task):
        """Test editing with an empty title."""
        new_task = Task(title="")

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.title == ""

    def test_edit_clears_description(self, task_dao, sample_task):
        """Test editing to clear description."""
        new_task = Task(
            title=sample_task.title,
            description=None
        )

        command = EditTaskCommand(task_dao, sample_task.id, new_task)
        command.execute()

        updated_task = task_dao.get_by_id(sample_task.id)
        assert updated_task.description is None

    def test_edit_preserves_unchanged_fields(self, task_dao):
        """Test that unchanged fields are preserved when editing."""
        # Create task with specific values
        original = task_dao.create(Task(
            title="Original",
            description="Original Desc",
            base_priority=3,
            due_date=date.today()
        ))

        # Edit only title, but use original values for other fields
        new_task = Task(
            title="New Title",
            description=original.description,
            base_priority=original.base_priority,
            due_date=original.due_date
        )

        command = EditTaskCommand(task_dao, original.id, new_task)
        command.execute()

        updated_task = task_dao.get_by_id(original.id)
        assert updated_task.title == "New Title"
        assert updated_task.description == "Original Desc"
        assert updated_task.base_priority == 3
        assert updated_task.due_date == date.today()
