"""
Unit tests for TaskHistoryService.

Tests comprehensive audit logging and event recording.
"""

import pytest
import sqlite3
from datetime import datetime, date

from src.models.task import Task
from src.models.enums import TaskState, TaskEventType, Priority
from src.models.task_history_event import TaskHistoryEvent
from src.database.task_history_dao import TaskHistoryDAO
from src.services.task_history_service import TaskHistoryService
from src.database.schema import DatabaseSchema


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def history_dao(db_connection):
    """Create TaskHistoryDAO instance."""
    return TaskHistoryDAO(db_connection)


@pytest.fixture
def history_service(history_dao):
    """Create TaskHistoryService instance."""
    return TaskHistoryService(history_dao)


@pytest.fixture
def sample_task():
    """Create a sample task for testing."""
    return Task(
        id=1,
        title="Test Task",
        description="Test description",
        base_priority=2,
        state=TaskState.ACTIVE,
        created_at=datetime.now()
    )


def test_record_task_created(history_service, sample_task):
    """Test recording task creation event."""
    event = history_service.record_task_created(sample_task)

    assert event.id is not None
    assert event.task_id == sample_task.id
    assert event.event_type == TaskEventType.CREATED
    assert event.changed_by == "user"


def test_record_task_edited(history_service, sample_task):
    """Test recording task edit event."""
    old_task = Task(
        id=1,
        title="Old Title",
        description="Old description",
        base_priority=1,
        state=TaskState.ACTIVE
    )

    new_task = Task(
        id=1,
        title="New Title",
        description="New description",
        base_priority=2,
        state=TaskState.ACTIVE
    )

    event = history_service.record_task_edited(new_task, old_task)

    assert event is not None
    assert event.event_type == TaskEventType.EDITED
    assert event.task_id == 1


def test_record_state_change(history_service, sample_task):
    """Test recording state change event."""
    event = history_service.record_state_change(
        sample_task,
        TaskState.ACTIVE,
        TaskState.COMPLETED
    )

    assert event.event_type == TaskEventType.COMPLETED
    assert event.old_value == "active"
    assert event.new_value == "completed"


def test_record_priority_change(history_service, sample_task):
    """Test recording priority change event."""
    event = history_service.record_priority_change(
        sample_task,
        old_priority=2,
        new_priority=3
    )

    assert event.event_type == TaskEventType.PRIORITY_CHANGED
    assert event.old_value == "2"
    assert event.new_value == "3"


def test_get_timeline(history_service, history_dao, sample_task):
    """Test retrieving task timeline."""
    # Record multiple events
    history_service.record_task_created(sample_task)
    history_service.record_priority_change(sample_task, 2, 3)
    history_service.record_state_change(sample_task, TaskState.ACTIVE, TaskState.COMPLETED)

    timeline = history_service.get_timeline(sample_task.id)

    assert len(timeline) == 3
    assert all(e.task_id == sample_task.id for e in timeline)


def test_formatted_summary(history_service, sample_task):
    """Test event formatting."""
    event = history_service.record_task_created(sample_task)
    summary = history_service.get_formatted_summary(event)

    assert "created" in summary.lower()
    assert isinstance(summary, str)
    assert len(summary) > 0
