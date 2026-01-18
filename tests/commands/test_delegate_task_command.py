"""
Unit tests for DelegateTaskCommand.

Tests task delegation with undo functionality.
"""

import pytest
import sqlite3
from datetime import date, timedelta

from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.schema import DatabaseSchema
from src.commands.delegate_task_command import DelegateTaskCommand


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection)


@pytest.fixture
def sample_active_task(task_dao):
    """Create a sample active task."""
    task = Task(
        title="Active Task",
        description="Test description",
        base_priority=2,
        state=TaskState.ACTIVE
    )
    return task_dao.create(task)


@pytest.fixture
def sample_delegated_task(task_dao):
    """Create a sample already-delegated task."""
    task = Task(
        title="Delegated Task",
        description="Test description",
        base_priority=2,
        state=TaskState.DELEGATED,
        delegated_to="Alice",
        follow_up_date=date.today() + timedelta(days=3)
    )
    return task_dao.create(task)


class TestDelegateTaskCommandExecute:
    """Test execute functionality."""

    def test_execute_delegates_active_task(self, task_dao, sample_active_task):
        """Test that execute changes task state to DELEGATED."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.state == TaskState.DELEGATED
        assert updated_task.delegated_to == "Bob"
        assert updated_task.follow_up_date == follow_up

    def test_execute_stores_original_state(self, task_dao, sample_active_task):
        """Test that execute stores original state for undo."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )

        command.execute()

        assert command.original_state == TaskState.ACTIVE
        assert command.original_delegated_to is None
        assert command.original_follow_up_date is None

    def test_execute_with_invalid_task_id(self, task_dao):
        """Test execute with non-existent task."""
        command = DelegateTaskCommand(task_dao, 99999, "Bob", date.today())

        result = command.execute()

        assert result is False

    def test_execute_can_re_delegate(self, task_dao, sample_delegated_task):
        """Test that already-delegated task can be re-delegated."""
        original_delegatee = sample_delegated_task.delegated_to
        original_follow_up = sample_delegated_task.follow_up_date

        new_follow_up = date.today() + timedelta(days=14)
        command = DelegateTaskCommand(
            task_dao, sample_delegated_task.id, "Charlie", new_follow_up
        )

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_delegated_task.id)
        assert updated_task.delegated_to == "Charlie"
        assert updated_task.follow_up_date == new_follow_up
        # Original should be stored
        assert command.original_delegated_to == original_delegatee
        assert command.original_follow_up_date == original_follow_up


class TestDelegateTaskCommandUndo:
    """Test undo functionality."""

    def test_undo_restores_active_state(self, task_dao, sample_active_task):
        """Test that undo restores task to active state."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )

        command.execute()
        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(sample_active_task.id)
        assert restored_task.state == TaskState.ACTIVE
        assert restored_task.delegated_to is None
        assert restored_task.follow_up_date is None

    def test_undo_restores_previous_delegation(self, task_dao, sample_delegated_task):
        """Test that undo restores previous delegation."""
        original_delegatee = sample_delegated_task.delegated_to
        original_follow_up = sample_delegated_task.follow_up_date

        new_follow_up = date.today() + timedelta(days=14)
        command = DelegateTaskCommand(
            task_dao, sample_delegated_task.id, "Charlie", new_follow_up
        )

        command.execute()
        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(sample_delegated_task.id)
        assert restored_task.state == TaskState.DELEGATED
        assert restored_task.delegated_to == original_delegatee
        assert restored_task.follow_up_date == original_follow_up

    def test_undo_with_deleted_task(self, task_dao, sample_active_task):
        """Test undo when task was deleted."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )
        command.execute()

        # Delete the task
        task_dao.delete(sample_active_task.id)

        result = command.undo()

        assert result is False


class TestDelegateTaskCommandDescription:
    """Test description generation."""

    def test_get_description_includes_title(self, task_dao, sample_active_task):
        """Test that description includes task title."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )
        command.execute()

        description = command.get_description()

        assert "Active Task" in description
        assert "Delegate" in description

    def test_get_description_includes_delegatee(self, task_dao, sample_active_task):
        """Test that description includes delegatee name."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )
        command.execute()

        description = command.get_description()

        assert "Bob" in description

    def test_get_description_before_execute(self, task_dao, sample_active_task):
        """Test description before execute shows task ID."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", follow_up
        )

        description = command.get_description()

        assert f"ID: {sample_active_task.id}" in description


class TestDelegateTaskCommandEdgeCases:
    """Test edge cases."""

    def test_delegate_with_empty_name(self, task_dao, sample_active_task):
        """Test delegating with empty delegatee name."""
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "", follow_up
        )

        result = command.execute()

        # Should still work, empty string is valid
        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.delegated_to == ""

    def test_delegate_with_past_follow_up(self, task_dao, sample_active_task):
        """Test delegating with past follow-up date."""
        past_date = date.today() - timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", past_date
        )

        result = command.execute()

        # Should still work, past dates are allowed
        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.follow_up_date == past_date

    def test_delegate_with_today_follow_up(self, task_dao, sample_active_task):
        """Test delegating with today as follow-up date."""
        today = date.today()
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, "Bob", today
        )

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.follow_up_date == today

    def test_delegate_to_long_name(self, task_dao, sample_active_task):
        """Test delegating to person with long name."""
        long_name = "A" * 200
        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(
            task_dao, sample_active_task.id, long_name, follow_up
        )

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.delegated_to == long_name

    def test_delegate_preserves_other_fields(self, task_dao):
        """Test that delegation preserves other task fields."""
        task = Task(
            title="Task with many fields",
            description="Detailed description",
            base_priority=3,
            state=TaskState.ACTIVE,
            due_date=date.today() + timedelta(days=5),
            elo_rating=1600.0
        )
        task = task_dao.create(task)

        follow_up = date.today() + timedelta(days=7)
        command = DelegateTaskCommand(task_dao, task.id, "Bob", follow_up)

        command.execute()

        updated_task = task_dao.get_by_id(task.id)
        assert updated_task.title == "Task with many fields"
        assert updated_task.description == "Detailed description"
        assert updated_task.base_priority == 3
        assert updated_task.due_date == date.today() + timedelta(days=5)
        assert updated_task.elo_rating == 1600.0
