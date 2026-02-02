"""
Test for max_occurrences enforcement in recurring tasks.
"""

import pytest
import sqlite3
from datetime import date, timedelta

from src.models.task import Task
from src.models.enums import TaskState
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


def test_recurring_task_respects_max_occurrences(task_dao):
    """Test that recurring task series stops after max_occurrences is reached."""
    # Create a daily recurring task with max 3 occurrences
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task with max occurrences",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        max_occurrences=3,  # Only 3 occurrences allowed
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)
    assert created_task.occurrence_count == 0

    # Complete first occurrence (0 -> 1) - should spawn next
    command1 = CompleteTaskCommand(task_dao, created_task.id)
    assert command1.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1
    assert active_tasks[0].occurrence_count == 1
    assert active_tasks[0].due_date == today + timedelta(days=1)

    # Complete second occurrence (1 -> 2) - should spawn next (last one)
    command2 = CompleteTaskCommand(task_dao, active_tasks[0].id)
    assert command2.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 1
    assert active_tasks[0].occurrence_count == 2
    assert active_tasks[0].due_date == today + timedelta(days=2)

    # Complete third occurrence (2 -> 3) - should NOT spawn next (max reached)
    command3 = CompleteTaskCommand(task_dao, active_tasks[0].id)
    assert command3.execute()

    all_tasks = task_dao.get_all()
    active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
    assert len(active_tasks) == 0  # No more occurrences spawned (reached max of 3)


def test_recurring_task_unlimited_when_max_occurrences_is_none(task_dao):
    """Test that series continues indefinitely when max_occurrences is None."""
    # Create a daily recurring task with no max occurrences
    pattern = RecurrencePattern(
        type=RecurrenceType.DAILY,
        interval=1
    )

    today = date.today()
    recurring_task = Task(
        title="Daily Recurring Task",
        description="Test recurring task without max occurrences",
        base_priority=2,
        state=TaskState.ACTIVE,
        due_date=today,
        is_recurring=True,
        recurrence_pattern=pattern.to_json(),
        max_occurrences=None,  # Unlimited
        share_elo_rating=False
    )
    created_task = task_dao.create(recurring_task)

    # Complete 5 times and verify it keeps spawning
    current_task = created_task
    for i in range(5):
        command = CompleteTaskCommand(task_dao, current_task.id)
        assert command.execute()

        all_tasks = task_dao.get_all()
        active_tasks = [t for t in all_tasks if t.state == TaskState.ACTIVE]
        assert len(active_tasks) == 1
        assert active_tasks[0].occurrence_count == i + 1
        current_task = active_tasks[0]
