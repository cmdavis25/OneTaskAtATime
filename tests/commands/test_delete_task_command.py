"""Tests for DeleteTaskCommand."""

import pytest
import sqlite3
from datetime import date

from src.commands.delete_task_command import DeleteTaskCommand
from src.database.task_dao import TaskDAO
from src.database.schema import DatabaseSchema
from src.models.task import Task
from src.models.enums import TaskState, Priority


@pytest.fixture
def db_connection():
    """Create a fresh in-memory database for each test."""
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_dao(db_connection):
    """Create TaskDAO instance."""
    return TaskDAO(db_connection)


def test_execute_deletes_task(task_dao):
    """Test that execute() deletes a task."""
    # Create a task
    task = Task(
        title="Test Task",
        description="Test Description",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.ACTIVE,
        due_date=date(2025, 12, 31)
    )
    created_task = task_dao.create(task)
    task_id = created_task.id

    # Execute delete command
    command = DeleteTaskCommand(task_dao, task_id)
    assert command.execute() is True

    # Verify task is deleted
    deleted_task = task_dao.get_by_id(task_id)
    assert deleted_task is None


def test_undo_restores_deleted_task(task_dao):
    """Test that undo() restores a deleted task with the same ID."""
    # Create a task
    task = Task(
        title="Test Task to Delete",
        description="Test Description",
        base_priority=Priority.HIGH.value,
        state=TaskState.ACTIVE,
        due_date=date(2025, 6, 15)
    )
    created_task = task_dao.create(task)
    original_id = created_task.id

    # Delete the task
    command = DeleteTaskCommand(task_dao, original_id)
    assert command.execute() is True

    # Verify it's deleted
    assert task_dao.get_by_id(original_id) is None

    # Undo the deletion
    assert command.undo() is True

    # Verify task is restored with the same ID
    restored_task = task_dao.get_by_id(original_id)
    assert restored_task is not None
    assert restored_task.id == original_id
    assert restored_task.title == "Test Task to Delete"
    assert restored_task.description == "Test Description"
    assert restored_task.base_priority == Priority.HIGH.value
    assert restored_task.state == TaskState.ACTIVE
    assert restored_task.due_date == date(2025, 6, 15)


def test_get_description_includes_title(task_dao):
    """Test that get_description() includes the task title."""
    task = Task(
        title="Task to Remove",
        base_priority=Priority.LOW.value,
        state=TaskState.ACTIVE
    )
    created_task = task_dao.create(task)

    command = DeleteTaskCommand(task_dao, created_task.id)
    command.execute()

    description = command.get_description()
    assert "Task to Remove" in description
    assert "Delete" in description


def test_execute_with_invalid_task_id(task_dao):
    """Test that execute() returns False for invalid task ID."""
    command = DeleteTaskCommand(task_dao, 99999)
    assert command.execute() is False


def test_undo_without_execute(task_dao):
    """Test that undo() fails if execute() wasn't called first."""
    task = Task(
        title="Test Task",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.ACTIVE
    )
    created_task = task_dao.create(task)

    command = DeleteTaskCommand(task_dao, created_task.id)
    # Call undo without execute
    assert command.undo() is False


def test_multiple_undo_redo_cycles(task_dao):
    """Test that delete/restore works through multiple cycles."""
    task = Task(
        title="Cycle Test Task",
        base_priority=Priority.MEDIUM.value,
        state=TaskState.ACTIVE
    )
    created_task = task_dao.create(task)
    task_id = created_task.id

    command = DeleteTaskCommand(task_dao, task_id)

    # First delete
    assert command.execute() is True
    assert task_dao.get_by_id(task_id) is None

    # First restore
    assert command.undo() is True
    assert task_dao.get_by_id(task_id) is not None

    # Create new command for second delete
    command2 = DeleteTaskCommand(task_dao, task_id)
    assert command2.execute() is True
    assert task_dao.get_by_id(task_id) is None

    # Second restore
    assert command2.undo() is True
    restored = task_dao.get_by_id(task_id)
    assert restored is not None
    assert restored.title == "Cycle Test Task"
