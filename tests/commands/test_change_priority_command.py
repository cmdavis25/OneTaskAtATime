"""
Unit tests for ChangePriorityCommand.

Tests priority changes with Elo reset and undo.
"""

import pytest
import sqlite3

from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.database.schema import DatabaseSchema
from src.commands.change_priority_command import ChangePriorityCommand


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
    """Create a sample task with modified Elo."""
    task = Task(
        title="Test Task",
        description="Test description",
        base_priority=2,
        elo_rating=1600.0,  # Non-default Elo
        comparison_count=5,
        state=TaskState.ACTIVE
    )
    return task_dao.create(task)


def test_execute_changes_priority(task_dao, sample_task):
    """Test that execute changes task priority."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=3)

    assert command.execute()

    updated_task = task_dao.get_by_id(sample_task.id)
    assert updated_task.base_priority == 3


def test_execute_resets_elo_rating(task_dao, sample_task):
    """Test that execute resets Elo to default."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=3)

    command.execute()

    updated_task = task_dao.get_by_id(sample_task.id)
    assert updated_task.elo_rating == 1500.0  # Default
    assert updated_task.comparison_count == 0


def test_undo_restores_original_priority(task_dao, sample_task):
    """Test that undo restores original priority."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=3)

    command.execute()
    assert command.undo()

    restored_task = task_dao.get_by_id(sample_task.id)
    assert restored_task.base_priority == 2  # Original


def test_undo_restores_original_elo(task_dao, sample_task):
    """Test that undo restores original Elo rating."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=3)

    command.execute()
    command.undo()

    restored_task = task_dao.get_by_id(sample_task.id)
    assert restored_task.elo_rating == 1600.0  # Original
    assert restored_task.comparison_count == 5


def test_get_description_shows_priority_change(task_dao, sample_task):
    """Test that description shows priority transition."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=3)
    command.execute()

    description = command.get_description()

    assert "Test Task" in description
    assert "MEDIUM" in description or "Medium" in description
    assert "HIGH" in description or "High" in description


def test_execute_with_same_priority(task_dao, sample_task):
    """Test changing to same priority still resets Elo."""
    command = ChangePriorityCommand(task_dao, sample_task.id, new_priority=2)

    command.execute()

    updated_task = task_dao.get_by_id(sample_task.id)
    assert updated_task.base_priority == 2
    assert updated_task.elo_rating == 1500.0  # Still resets
