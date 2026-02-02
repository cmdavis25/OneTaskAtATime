"""
Unit tests for CompleteTaskCommand.

Tests task completion with undo functionality.
"""

import pytest
import sqlite3
from datetime import datetime, date, timedelta

from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.models.recurrence_pattern import RecurrencePattern, RecurrenceType
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


def test_recurring_task_spawns_next_occurrence(task_dao):
    """Test that completing a recurring task spawns the next occurrence."""
    # Create a daily recurring task
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)

    # Complete the task
    command = CompleteTaskCommand(task_dao, created_task.id)
    assert command.execute()

    # Verify original task is completed
    completed_task = task_dao.get_by_id(created_task.id)
    assert completed_task.state == TaskState.COMPLETED

    # Verify next occurrence was spawned
    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1

    next_task = active_tasks[0]
    assert next_task.title == "Daily Recurring Task"
    assert next_task.due_date == today + timedelta(days=1)
    assert next_task.is_recurring is True
    assert next_task.state == TaskState.ACTIVE


def test_recurring_task_undo_deletes_spawned_occurrence(task_dao):
    """Test that undoing completion removes the spawned next occurrence."""
    # Create a daily recurring task
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)

    # Complete the task
    command = CompleteTaskCommand(task_dao, created_task.id)
    command.execute()

    # Verify next occurrence was spawned
    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1

    # Undo the completion
    assert command.undo()

    # Verify spawned task was deleted
    all_tasks_after_undo = task_dao.get_all()
    active_tasks_after_undo = [t for t in all_tasks_after_undo if t.state == TaskState.ACTIVE]
    assert len(active_tasks_after_undo) == 1
    assert active_tasks_after_undo[0].id == created_task.id  # Original task is active again


def test_recurring_task_respects_end_date(task_dao):
    """Test that recurring task series ends when recurrence_end_date is reached."""
    # Create a recurring task that ends today
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task with end date",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        recurrence_end_date=today,  # Series ends today
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)

    # Complete the task
    command = CompleteTaskCommand(task_dao, created_task.id)
    assert command.execute()

    # Verify original task is completed
    completed_task = task_dao.get_by_id(created_task.id)
    assert completed_task.state == TaskState.COMPLETED

    # Verify NO next occurrence was spawned (series ended)
    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 0


def test_recurring_task_stops_after_end_date(task_dao):
    """Test that series stops when next occurrence would exceed end date."""
    # Create a daily recurring task with end date 2 days from now
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    end_date = today + timedelta(days=2)

    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task with future end date",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        recurrence_end_date=end_date,  # Series ends in 2 days
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)

    # Complete first occurrence (today) - should spawn next for tomorrow
    command1 = CompleteTaskCommand(task_dao, created_task.id)
    assert command1.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1
    assert active_tasks[0].due_date == today + timedelta(days=1)

    # Complete second occurrence (tomorrow) - should spawn next for day after tomorrow
    command2 = CompleteTaskCommand(task_dao, active_tasks[0].id)
    assert command2.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1
    assert active_tasks[0].due_date == today + timedelta(days=2)

    # Complete third occurrence (day after tomorrow) - should NOT spawn next (would be beyond end date)
    command3 = CompleteTaskCommand(task_dao, active_tasks[0].id)
    assert command3.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 0  # No more occurrences spawned

