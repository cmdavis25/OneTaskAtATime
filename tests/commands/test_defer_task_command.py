"""
Unit tests for DeferTaskCommand.

Tests task deferral with undo functionality.
"""

import pytest
import sqlite3
from datetime import date, timedelta

from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.schema import DatabaseSchema
from src.commands.defer_task_command import DeferTaskCommand


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
def sample_deferred_task(task_dao):
    """Create a sample already-deferred task."""
    task = Task(
        title="Deferred Task",
        description="Test description",
        base_priority=2,
        state=TaskState.DEFERRED,
        start_date=date.today() + timedelta(days=3)
    )
    return task_dao.create(task)


class TestDeferTaskCommandExecute:
    """Test execute functionality."""

    def test_execute_defers_active_task(self, task_dao, sample_active_task):
        """Test that execute changes task state to DEFERRED."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.state == TaskState.DEFERRED
        assert updated_task.start_date == start_date

    def test_execute_stores_original_state(self, task_dao, sample_active_task):
        """Test that execute stores original state for undo."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)

        command.execute()

        assert command.original_state == TaskState.ACTIVE
        assert command.original_start_date is None

    def test_execute_with_invalid_task_id(self, task_dao):
        """Test execute with non-existent task."""
        command = DeferTaskCommand(task_dao, 99999, date.today())

        result = command.execute()

        assert result is False

    def test_execute_can_re_defer_already_deferred(self, task_dao, sample_deferred_task):
        """Test that already-deferred task can be deferred again with new date."""
        original_start = sample_deferred_task.start_date
        new_start_date = date.today() + timedelta(days=14)
        command = DeferTaskCommand(task_dao, sample_deferred_task.id, new_start_date)

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_deferred_task.id)
        assert updated_task.start_date == new_start_date
        # Original should be stored
        assert command.original_start_date == original_start


class TestDeferTaskCommandUndo:
    """Test undo functionality."""

    def test_undo_restores_active_state(self, task_dao, sample_active_task):
        """Test that undo restores task to active state."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)

        command.execute()
        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(sample_active_task.id)
        assert restored_task.state == TaskState.ACTIVE
        assert restored_task.start_date is None

    def test_undo_restores_previous_deferred_state(self, task_dao, sample_deferred_task):
        """Test that undo restores previous deferred state."""
        original_start = sample_deferred_task.start_date
        new_start_date = date.today() + timedelta(days=14)
        command = DeferTaskCommand(task_dao, sample_deferred_task.id, new_start_date)

        command.execute()
        result = command.undo()

        assert result is True
        restored_task = task_dao.get_by_id(sample_deferred_task.id)
        assert restored_task.state == TaskState.DEFERRED
        assert restored_task.start_date == original_start

    def test_undo_with_deleted_task(self, task_dao, sample_active_task):
        """Test undo when task was deleted."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)
        command.execute()

        # Delete the task
        task_dao.delete(sample_active_task.id)

        result = command.undo()

        assert result is False


class TestDeferTaskCommandDescription:
    """Test description generation."""

    def test_get_description_includes_title(self, task_dao, sample_active_task):
        """Test that description includes task title."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)
        command.execute()

        description = command.get_description()

        assert "Active Task" in description
        assert "Defer" in description

    def test_get_description_includes_date(self, task_dao, sample_active_task):
        """Test that description includes start date."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)
        command.execute()

        description = command.get_description()

        assert str(start_date) in description

    def test_get_description_before_execute(self, task_dao, sample_active_task):
        """Test description before execute shows task ID."""
        start_date = date.today() + timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date)

        description = command.get_description()

        assert f"ID: {sample_active_task.id}" in description


class TestDeferTaskCommandEdgeCases:
    """Test edge cases."""

    def test_defer_to_past_date(self, task_dao, sample_active_task):
        """Test deferring to a past date (should still work)."""
        past_date = date.today() - timedelta(days=7)
        command = DeferTaskCommand(task_dao, sample_active_task.id, past_date)

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.start_date == past_date

    def test_defer_to_today(self, task_dao, sample_active_task):
        """Test deferring to today."""
        today = date.today()
        command = DeferTaskCommand(task_dao, sample_active_task.id, today)

        result = command.execute()

        assert result is True
        updated_task = task_dao.get_by_id(sample_active_task.id)
        assert updated_task.start_date == today

    def test_defer_with_reason(self, task_dao, sample_active_task):
        """Test deferring with a reason."""
        start_date = date.today() + timedelta(days=7)
        reason = "Waiting for dependencies"
        command = DeferTaskCommand(task_dao, sample_active_task.id, start_date, reason=reason)

        result = command.execute()

        assert result is True
        assert command.reason == reason
