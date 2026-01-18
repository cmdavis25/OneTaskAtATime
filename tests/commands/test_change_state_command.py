"""
Unit tests for ChangeStateCommand.
"""

import pytest
import sqlite3
import tempfile
import os

from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.commands.change_state_command import ChangeStateCommand
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
def active_task(task_dao):
    """Create an active task for testing."""
    task = Task(title="Active Task", state=TaskState.ACTIVE)
    return task_dao.create(task)


class TestChangeStateCommandExecute:
    """Tests for ChangeStateCommand execute method."""

    def test_execute_changes_to_completed(self, task_dao, active_task):
        """Test changing task state to completed."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(active_task.id)
        assert updated_task.state == TaskState.COMPLETED

    def test_execute_changes_to_someday(self, task_dao, active_task):
        """Test changing task state to someday/maybe."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.SOMEDAY)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(active_task.id)
        assert updated_task.state == TaskState.SOMEDAY

    def test_execute_changes_to_trash(self, task_dao, active_task):
        """Test changing task state to trash."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.TRASH)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(active_task.id)
        assert updated_task.state == TaskState.TRASH

    def test_execute_changes_to_active(self, task_dao):
        """Test changing task state to active."""
        # Create a someday task
        task = Task(title="Someday Task", state=TaskState.SOMEDAY)
        created_task = task_dao.create(task)

        command = ChangeStateCommand(task_dao, created_task.id, TaskState.ACTIVE)
        result = command.execute()

        assert result is True

        updated_task = task_dao.get_by_id(created_task.id)
        assert updated_task.state == TaskState.ACTIVE

    def test_execute_stores_original_state(self, task_dao, active_task):
        """Test that execute stores the original state for undo."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command.execute()

        assert command.original_state == TaskState.ACTIVE

    def test_execute_stores_task_title(self, task_dao, active_task):
        """Test that execute stores the task title."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command.execute()

        assert command.task_title == "Active Task"

    def test_execute_returns_false_for_nonexistent_task(self, task_dao):
        """Test that execute returns False for non-existent task."""
        command = ChangeStateCommand(task_dao, 9999, TaskState.COMPLETED)
        result = command.execute()

        assert result is False

    def test_execute_all_state_transitions(self, task_dao):
        """Test all possible state transitions."""
        states = [
            TaskState.ACTIVE,
            TaskState.DEFERRED,
            TaskState.DELEGATED,
            TaskState.SOMEDAY,
            TaskState.COMPLETED,
            TaskState.TRASH
        ]

        for from_state in states:
            for to_state in states:
                if from_state != to_state:
                    task = Task(title=f"Task {from_state.value} to {to_state.value}", state=from_state)
                    created_task = task_dao.create(task)

                    command = ChangeStateCommand(task_dao, created_task.id, to_state)
                    result = command.execute()

                    assert result is True
                    updated_task = task_dao.get_by_id(created_task.id)
                    assert updated_task.state == to_state


class TestChangeStateCommandUndo:
    """Tests for ChangeStateCommand undo method."""

    def test_undo_restores_original_state(self, task_dao, active_task):
        """Test that undo restores the original state."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command.execute()

        # Verify state was changed
        assert task_dao.get_by_id(active_task.id).state == TaskState.COMPLETED

        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(active_task.id)
        assert restored_task.state == TaskState.ACTIVE

    def test_undo_without_execute_has_no_original_state(self, task_dao, active_task):
        """Test that undo without execute has no original state to restore."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        # Don't call execute, so original_state is None

        # The undo will try to set state to None, which may cause an error
        # or succeed but leave the task in an undefined state.
        # This is expected behavior - undo should only be called after execute.
        # We verify the command hasn't stored the original state
        assert command.original_state is None
        assert command.task_title is None

    def test_undo_after_multiple_state_changes(self, task_dao, active_task):
        """Test undo after multiple state changes (only undoes the last one)."""
        # First change: Active -> Someday
        command1 = ChangeStateCommand(task_dao, active_task.id, TaskState.SOMEDAY)
        command1.execute()

        # Second change: Someday -> Completed
        command2 = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command2.execute()

        # Verify current state
        assert task_dao.get_by_id(active_task.id).state == TaskState.COMPLETED

        # Undo second change
        command2.undo()
        assert task_dao.get_by_id(active_task.id).state == TaskState.SOMEDAY

        # Undo first change
        command1.undo()
        assert task_dao.get_by_id(active_task.id).state == TaskState.ACTIVE

    def test_undo_returns_false_for_deleted_task(self, task_dao, active_task):
        """Test that undo returns False if task was deleted."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command.execute()

        # Delete the task
        task_dao.delete(active_task.id)

        result = command.undo()

        assert result is False


class TestChangeStateCommandGetDescription:
    """Tests for ChangeStateCommand get_description method."""

    def test_get_description_for_complete(self, task_dao, active_task):
        """Test get_description for completing a task."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)
        command.execute()

        description = command.get_description()

        assert "Complete" in description
        assert "Active Task" in description

    def test_get_description_for_someday(self, task_dao, active_task):
        """Test get_description for moving to someday/maybe."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.SOMEDAY)
        command.execute()

        description = command.get_description()

        assert "Someday/Maybe" in description
        assert "Active Task" in description

    def test_get_description_for_trash(self, task_dao, active_task):
        """Test get_description for moving to trash."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.TRASH)
        command.execute()

        description = command.get_description()

        assert "Trash" in description
        assert "Active Task" in description

    def test_get_description_for_activate(self, task_dao):
        """Test get_description for activating a task."""
        task = Task(title="Someday Task", state=TaskState.SOMEDAY)
        created_task = task_dao.create(task)

        command = ChangeStateCommand(task_dao, created_task.id, TaskState.ACTIVE)
        command.execute()

        description = command.get_description()

        assert "Activate" in description
        assert "Someday Task" in description

    def test_get_description_before_execute(self, task_dao, active_task):
        """Test get_description before execute."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)

        description = command.get_description()

        # Should still work, but without task title
        assert "Complete" in description
        assert str(active_task.id) in description


class TestChangeStateCommandEdgeCases:
    """Edge case tests for ChangeStateCommand."""

    def test_change_to_same_state(self, task_dao, active_task):
        """Test changing to the same state."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.ACTIVE)
        result = command.execute()

        assert result is True
        # State should remain the same
        task = task_dao.get_by_id(active_task.id)
        assert task.state == TaskState.ACTIVE

    def test_command_with_deferred_state(self, task_dao, active_task):
        """Test changing to deferred state."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.DEFERRED)
        result = command.execute()

        assert result is True
        task = task_dao.get_by_id(active_task.id)
        assert task.state == TaskState.DEFERRED

    def test_command_with_delegated_state(self, task_dao, active_task):
        """Test changing to delegated state."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.DELEGATED)
        result = command.execute()

        assert result is True
        task = task_dao.get_by_id(active_task.id)
        assert task.state == TaskState.DELEGATED

    def test_execute_undo_cycle(self, task_dao, active_task):
        """Test multiple execute/undo cycles."""
        command = ChangeStateCommand(task_dao, active_task.id, TaskState.COMPLETED)

        # Cycle 1
        command.execute()
        assert task_dao.get_by_id(active_task.id).state == TaskState.COMPLETED
        command.undo()
        assert task_dao.get_by_id(active_task.id).state == TaskState.ACTIVE

        # Cycle 2
        command.execute()
        assert task_dao.get_by_id(active_task.id).state == TaskState.COMPLETED
        command.undo()
        assert task_dao.get_by_id(active_task.id).state == TaskState.ACTIVE

    def test_undo_preserves_other_task_fields(self, task_dao):
        """Test that undo preserves other task fields."""
        task = Task(
            title="Test Task",
            description="Test Description",
            base_priority=3,
            state=TaskState.ACTIVE
        )
        created_task = task_dao.create(task)

        command = ChangeStateCommand(task_dao, created_task.id, TaskState.COMPLETED)
        command.execute()
        command.undo()

        restored_task = task_dao.get_by_id(created_task.id)
        assert restored_task.title == "Test Task"
        assert restored_task.description == "Test Description"
        assert restored_task.base_priority == 3
        assert restored_task.state == TaskState.ACTIVE
