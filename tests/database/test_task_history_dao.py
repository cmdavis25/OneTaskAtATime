"""
Unit tests for TaskHistoryDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, date, timedelta

from src.database.schema import DatabaseSchema
from src.database.task_history_dao import TaskHistoryDAO
from src.database.task_dao import TaskDAO
from src.models.task_history_event import TaskHistoryEvent
from src.models.enums import TaskEventType
from src.models import Task


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
def task_history_dao(db_connection):
    """Create a TaskHistoryDAO instance for testing."""
    return TaskHistoryDAO(db_connection)


@pytest.fixture
def task_dao(db_connection):
    """Create a TaskDAO instance for testing."""
    return TaskDAO(db_connection)


@pytest.fixture
def sample_task(task_dao):
    """Create a sample task for testing."""
    task = Task(title="Test Task")
    return task_dao.create(task)


class TestTaskHistoryDAO:
    """Tests for TaskHistoryDAO class."""

    def test_create_event(self, task_history_dao, sample_task):
        """Test creating a task history event."""
        event = TaskHistoryEvent(
            task_id=sample_task.id,
            event_type=TaskEventType.CREATED,
            old_value=None,
            new_value='{"title": "Test Task"}',
            changed_by="user"
        )

        created_event = task_history_dao.create_event(event)

        assert created_event.id is not None
        assert created_event.task_id == sample_task.id
        assert created_event.event_type == TaskEventType.CREATED
        assert created_event.changed_by == "user"

    def test_create_event_with_all_fields(self, task_history_dao, sample_task):
        """Test creating an event with all fields populated."""
        now = datetime.now()
        event = TaskHistoryEvent(
            task_id=sample_task.id,
            event_type=TaskEventType.EDITED,
            event_timestamp=now,
            old_value='{"title": "Old Title"}',
            new_value='{"title": "New Title"}',
            changed_by="user",
            context_data='{"field": "title"}'
        )

        created_event = task_history_dao.create_event(event)

        assert created_event.id is not None
        assert created_event.old_value == '{"title": "Old Title"}'
        assert created_event.new_value == '{"title": "New Title"}'
        assert created_event.context_data == '{"field": "title"}'

    def test_get_by_id(self, task_history_dao, sample_task):
        """Test retrieving an event by ID."""
        event = TaskHistoryEvent(
            task_id=sample_task.id,
            event_type=TaskEventType.COMPLETED
        )
        created_event = task_history_dao.create_event(event)

        retrieved_event = task_history_dao.get_by_id(created_event.id)

        assert retrieved_event is not None
        assert retrieved_event.id == created_event.id
        assert retrieved_event.event_type == TaskEventType.COMPLETED

    def test_get_by_id_not_found(self, task_history_dao):
        """Test retrieving a non-existent event."""
        event = task_history_dao.get_by_id(9999)
        assert event is None

    def test_get_by_task_id(self, task_history_dao, sample_task):
        """Test retrieving all events for a task."""
        # Create multiple events
        events = [
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.CREATED),
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED),
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.COMPLETED),
        ]
        for event in events:
            task_history_dao.create_event(event)

        retrieved_events = task_history_dao.get_by_task_id(sample_task.id)

        assert len(retrieved_events) == 3
        # Should be ordered by timestamp ASC (chronological)
        assert retrieved_events[0].event_type == TaskEventType.CREATED
        assert retrieved_events[2].event_type == TaskEventType.COMPLETED

    def test_get_by_task_id_with_limit(self, task_history_dao, sample_task):
        """Test retrieving events with a limit."""
        # Create more events than the limit
        for i in range(10):
            event = TaskHistoryEvent(
                task_id=sample_task.id,
                event_type=TaskEventType.EDITED
            )
            task_history_dao.create_event(event)

        retrieved_events = task_history_dao.get_by_task_id(sample_task.id, limit=5)

        assert len(retrieved_events) == 5

    def test_get_by_task_id_empty(self, task_history_dao, sample_task):
        """Test retrieving events for a task with no events."""
        events = task_history_dao.get_by_task_id(sample_task.id)
        assert events == []

    def test_get_recent(self, task_history_dao, task_dao):
        """Test retrieving recent events across all tasks."""
        # Create multiple tasks and events
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        task_history_dao.create_event(
            TaskHistoryEvent(task_id=task1.id, event_type=TaskEventType.CREATED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=task2.id, event_type=TaskEventType.CREATED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=task1.id, event_type=TaskEventType.COMPLETED)
        )

        recent_events = task_history_dao.get_recent(limit=10)

        assert len(recent_events) == 3
        # Should be ordered by timestamp DESC (most recent first)
        assert recent_events[0].event_type == TaskEventType.COMPLETED

    def test_get_recent_with_limit(self, task_history_dao, sample_task):
        """Test get_recent with a limit."""
        for i in range(10):
            task_history_dao.create_event(
                TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
            )

        recent_events = task_history_dao.get_recent(limit=3)

        assert len(recent_events) == 3

    def test_get_by_type(self, task_history_dao, sample_task):
        """Test retrieving events by type."""
        # Create events of different types
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.CREATED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.COMPLETED)
        )

        edit_events = task_history_dao.get_by_type(TaskEventType.EDITED)

        assert len(edit_events) == 2
        assert all(e.event_type == TaskEventType.EDITED for e in edit_events)

    def test_get_date_range(self, task_history_dao, sample_task):
        """Test retrieving events within a date range."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)

        # Create event for today
        event = TaskHistoryEvent(
            task_id=sample_task.id,
            event_type=TaskEventType.CREATED,
            event_timestamp=datetime.now()
        )
        task_history_dao.create_event(event)

        # Get events for today
        events = task_history_dao.get_date_range(today, today)

        assert len(events) >= 1

        # Get events for yesterday only (should be empty)
        events_yesterday = task_history_dao.get_date_range(yesterday, yesterday)

        # May or may not have events depending on timing, but shouldn't error
        assert isinstance(events_yesterday, list)

    def test_delete_by_task_id(self, task_history_dao, sample_task):
        """Test deleting all events for a task."""
        # Create events
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.CREATED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
        )

        result = task_history_dao.delete_by_task_id(sample_task.id)

        assert result is True

        # Verify deleted
        events = task_history_dao.get_by_task_id(sample_task.id)
        assert events == []

    def test_delete_by_task_id_no_events(self, task_history_dao, sample_task):
        """Test deleting events for a task with no events."""
        result = task_history_dao.delete_by_task_id(sample_task.id)
        assert result is False

    def test_get_count_by_task(self, task_history_dao, sample_task):
        """Test getting count of events for a task."""
        # Create events
        for i in range(5):
            task_history_dao.create_event(
                TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
            )

        count = task_history_dao.get_count_by_task(sample_task.id)

        assert count == 5

    def test_get_count_by_task_empty(self, task_history_dao, sample_task):
        """Test getting count for a task with no events."""
        count = task_history_dao.get_count_by_task(sample_task.id)
        assert count == 0

    def test_get_count_by_type(self, task_history_dao, sample_task):
        """Test getting count of a specific event type for a task."""
        # Create events of different types
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.EDITED)
        )
        task_history_dao.create_event(
            TaskHistoryEvent(task_id=sample_task.id, event_type=TaskEventType.COMPLETED)
        )

        edit_count = task_history_dao.get_count_by_type(sample_task.id, TaskEventType.EDITED)
        completed_count = task_history_dao.get_count_by_type(sample_task.id, TaskEventType.COMPLETED)

        assert edit_count == 2
        assert completed_count == 1

    def test_event_type_enum_conversion(self, task_history_dao, sample_task):
        """Test that event type enum is properly converted."""
        event = TaskHistoryEvent(
            task_id=sample_task.id,
            event_type=TaskEventType.PRIORITY_CHANGED
        )
        created_event = task_history_dao.create_event(event)

        retrieved_event = task_history_dao.get_by_id(created_event.id)

        assert retrieved_event.event_type == TaskEventType.PRIORITY_CHANGED
        assert isinstance(retrieved_event.event_type, TaskEventType)

    def test_all_event_types(self, task_history_dao, sample_task):
        """Test creating events with all event types."""
        event_types = [
            TaskEventType.CREATED,
            TaskEventType.EDITED,
            TaskEventType.COMPLETED,
            TaskEventType.DEFERRED,
            TaskEventType.DELEGATED,
            TaskEventType.ACTIVATED,
            TaskEventType.MOVED_TO_SOMEDAY,
            TaskEventType.MOVED_TO_TRASH,
            TaskEventType.PRIORITY_CHANGED,
            TaskEventType.DUE_DATE_CHANGED,
        ]

        for event_type in event_types:
            event = TaskHistoryEvent(
                task_id=sample_task.id,
                event_type=event_type
            )
            created = task_history_dao.create_event(event)
            assert created.id is not None

        count = task_history_dao.get_count_by_task(sample_task.id)
        assert count == len(event_types)
