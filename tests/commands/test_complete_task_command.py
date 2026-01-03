"""
Unit tests for CompleteTaskCommand.

Tests task completion with undo functionality.
"""

import pytest
import sqlite3
from datetime import datetime

from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.database.task_dao import TaskDAO
from src.database.schema import DatabaseSchema
from src.commands.complete_task_command import CompleteTaskCommand


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
def sample_task(task_dao):
    """Create a sample active task."""
    task = Task(
        title="Test Task",
        description="Test description",
        base_priority=2,
        state=TaskState.ACTIVE
    )
    return task_dao.create(task)


def test_execute_completes_task(task_dao, sample_task):
    """Test that execute marks task as completed."""
    command = CompleteTaskCommand(task_dao, sample_task.id)

    assert command.execute()

    # Verify task is completed
    updated_task = task_dao.get_by_id(sample_task.id)
    assert updated_task.state == TaskState.COMPLETED
    assert updated_task.completed_at is not None


def test_undo_restores_active_state(task_dao, sample_task):
    """Test that undo restores task to active state."""
    command = CompleteTaskCommand(task_dao, sample_task.id)

    # Execute then undo
    command.execute()
    assert command.undo()

    # Verify task is back to active
    restored_task = task_dao.get_by_id(sample_task.id)
    assert restored_task.state == TaskState.ACTIVE
    assert restored_task.completed_at is None


def test_get_description_includes_title(task_dao, sample_task):
    """Test that description includes task title."""
    command = CompleteTaskCommand(task_dao, sample_task.id)
    command.execute()

    description = command.get_description()

    assert "Test Task" in description
    assert "Complete" in description


def test_execute_with_invalid_task_id(task_dao):
    """Test execute with non-existent task."""
    command = CompleteTaskCommand(task_dao, 99999)

    assert not command.execute()


def test_undo_with_invalid_task_id(task_dao, sample_task):
    """Test undo with task that was deleted."""
    command = CompleteTaskCommand(task_dao, sample_task.id)
    command.execute()

    # Delete the task
    task_dao.delete(sample_task.id)

    # Undo should fail gracefully
    assert not command.undo()


def test_preserves_completed_at_on_undo(task_dao, sample_task):
    """Test that undo restores null completed_at."""
    command = CompleteTaskCommand(task_dao, sample_task.id)

    # Task starts with no completed_at
    assert sample_task.completed_at is None

    # Execute completion
    command.execute()
    completed_task = task_dao.get_by_id(sample_task.id)
    assert completed_task.completed_at is not None

    # Undo should restore to None
    command.undo()
    restored_task = task_dao.get_by_id(sample_task.id)
    assert restored_task.completed_at is None
