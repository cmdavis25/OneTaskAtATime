"""
Unit tests for PostponeHistoryDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from src.database.schema import DatabaseSchema
from src.database.postpone_history_dao import PostponeHistoryDAO
from src.database.task_dao import TaskDAO
from src.models.postpone_record import PostponeRecord
from src.models.enums import PostponeReasonType, ActionTaken
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
def postpone_history_dao(db_connection):
    """Create a PostponeHistoryDAO instance for testing."""
    return PostponeHistoryDAO(db_connection)


@pytest.fixture
def task_dao(db_connection):
    """Create a TaskDAO instance for testing."""
    return TaskDAO(db_connection)


@pytest.fixture
def sample_task(task_dao):
    """Create a sample task for testing."""
    task = Task(title="Test Task")
    return task_dao.create(task)


class TestPostponeHistoryDAO:
    """Tests for PostponeHistoryDAO class."""

    def test_create_basic_record(self, postpone_history_dao, sample_task):
        """Test creating a basic postpone record."""
        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.NOT_READY
        )

        created = postpone_history_dao.create(record)

        assert created.id is not None
        assert created.task_id == sample_task.id
        assert created.reason_type == PostponeReasonType.NOT_READY
        assert created.postponed_at is not None

    def test_create_record_with_all_fields(self, postpone_history_dao, sample_task):
        """Test creating a record with all fields populated."""
        now = datetime.now()
        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.BLOCKER,
            reason_notes="Waiting for API to be available",
            action_taken=ActionTaken.CREATED_BLOCKER,
            postponed_at=now
        )

        created = postpone_history_dao.create(record)

        assert created.id is not None
        assert created.reason_notes == "Waiting for API to be available"
        assert created.action_taken == ActionTaken.CREATED_BLOCKER

    def test_create_record_with_existing_id_raises_error(self, postpone_history_dao, sample_task):
        """Test that creating a record with an ID raises an error."""
        record = PostponeRecord(
            id=1,
            task_id=sample_task.id,
            reason_type=PostponeReasonType.OTHER
        )

        with pytest.raises(ValueError, match="Cannot create postpone record that already has an id"):
            postpone_history_dao.create(record)

    def test_create_auto_sets_postponed_at(self, postpone_history_dao, sample_task):
        """Test that postponed_at is auto-set if not provided."""
        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.NOT_READY,
            postponed_at=None
        )

        created = postpone_history_dao.create(record)

        assert created.postponed_at is not None
        # Should be recent
        assert (datetime.now() - created.postponed_at).total_seconds() < 5

    def test_get_by_id(self, postpone_history_dao, sample_task):
        """Test retrieving a record by ID."""
        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.MULTIPLE_SUBTASKS
        )
        created = postpone_history_dao.create(record)

        retrieved = postpone_history_dao.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.reason_type == PostponeReasonType.MULTIPLE_SUBTASKS

    def test_get_by_id_not_found(self, postpone_history_dao):
        """Test retrieving a non-existent record."""
        record = postpone_history_dao.get_by_id(9999)
        assert record is None

    def test_get_by_task_id(self, postpone_history_dao, sample_task):
        """Test retrieving records for a task."""
        # Create multiple records
        for reason in [PostponeReasonType.NOT_READY, PostponeReasonType.BLOCKER]:
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=reason
            )
            postpone_history_dao.create(record)

        records = postpone_history_dao.get_by_task_id(sample_task.id)

        assert len(records) == 2
        # Should be ordered by postponed_at DESC
        assert records[0].postponed_at >= records[1].postponed_at

    def test_get_by_task_id_with_limit(self, postpone_history_dao, sample_task):
        """Test retrieving records with a limit."""
        for i in range(10):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.OTHER
            )
            postpone_history_dao.create(record)

        records = postpone_history_dao.get_by_task_id(sample_task.id, limit=5)

        assert len(records) == 5

    def test_get_by_task_id_empty(self, postpone_history_dao, sample_task):
        """Test retrieving records for a task with no history."""
        records = postpone_history_dao.get_by_task_id(sample_task.id)
        assert records == []

    def test_get_by_reason_type(self, postpone_history_dao, task_dao):
        """Test retrieving records by reason type."""
        # Create tasks and records
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        postpone_history_dao.create(PostponeRecord(
            task_id=task1.id,
            reason_type=PostponeReasonType.BLOCKER
        ))
        postpone_history_dao.create(PostponeRecord(
            task_id=task2.id,
            reason_type=PostponeReasonType.BLOCKER
        ))
        postpone_history_dao.create(PostponeRecord(
            task_id=task1.id,
            reason_type=PostponeReasonType.NOT_READY
        ))

        blocker_records = postpone_history_dao.get_by_reason_type(PostponeReasonType.BLOCKER)

        assert len(blocker_records) == 2
        assert all(r.reason_type == PostponeReasonType.BLOCKER for r in blocker_records)

    def test_get_by_reason_type_with_limit(self, postpone_history_dao, sample_task):
        """Test get_by_reason_type with a limit."""
        for i in range(10):
            postpone_history_dao.create(PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.OTHER
            ))

        records = postpone_history_dao.get_by_reason_type(PostponeReasonType.OTHER, limit=3)

        assert len(records) == 3

    def test_get_recent(self, postpone_history_dao, sample_task, db_connection):
        """Test retrieving recent records."""
        # Create a recent record
        postpone_history_dao.create(PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.NOT_READY
        ))

        # Create an old record (manually, to set old date)
        cursor = db_connection.cursor()
        old_date = (datetime.now() - timedelta(days=14)).isoformat()
        cursor.execute(
            """
            INSERT INTO postpone_history (task_id, reason_type, action_taken, postponed_at)
            VALUES (?, ?, ?, ?)
            """,
            (sample_task.id, "other", "none", old_date)
        )
        db_connection.commit()

        # Get recent records (within 7 days)
        recent = postpone_history_dao.get_recent(days=7)

        assert len(recent) == 1
        assert recent[0].reason_type == PostponeReasonType.NOT_READY

    def test_get_recent_with_custom_days(self, postpone_history_dao, sample_task, db_connection):
        """Test get_recent with custom days window."""
        # Create records at different dates
        cursor = db_connection.cursor()

        # 5 days ago
        five_days_ago = (datetime.now() - timedelta(days=5)).isoformat()
        cursor.execute(
            """
            INSERT INTO postpone_history (task_id, reason_type, action_taken, postponed_at)
            VALUES (?, ?, ?, ?)
            """,
            (sample_task.id, "not_ready", "none", five_days_ago)
        )

        # 15 days ago
        fifteen_days_ago = (datetime.now() - timedelta(days=15)).isoformat()
        cursor.execute(
            """
            INSERT INTO postpone_history (task_id, reason_type, action_taken, postponed_at)
            VALUES (?, ?, ?, ?)
            """,
            (sample_task.id, "blocker", "none", fifteen_days_ago)
        )
        db_connection.commit()

        # Get records within 10 days
        recent_10 = postpone_history_dao.get_recent(days=10)
        assert len(recent_10) == 1

        # Get records within 30 days
        recent_30 = postpone_history_dao.get_recent(days=30)
        assert len(recent_30) == 2

    def test_delete_by_task_id(self, postpone_history_dao, sample_task):
        """Test deleting all records for a task."""
        # Create records
        postpone_history_dao.create(PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.NOT_READY
        ))
        postpone_history_dao.create(PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.BLOCKER
        ))

        count = postpone_history_dao.delete_by_task_id(sample_task.id)

        assert count == 2

        # Verify deleted
        records = postpone_history_dao.get_by_task_id(sample_task.id)
        assert records == []

    def test_delete_by_task_id_no_records(self, postpone_history_dao, sample_task):
        """Test deleting when no records exist."""
        count = postpone_history_dao.delete_by_task_id(sample_task.id)
        assert count == 0

    def test_get_all(self, postpone_history_dao, task_dao):
        """Test retrieving all records."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        postpone_history_dao.create(PostponeRecord(
            task_id=task1.id,
            reason_type=PostponeReasonType.NOT_READY
        ))
        postpone_history_dao.create(PostponeRecord(
            task_id=task2.id,
            reason_type=PostponeReasonType.BLOCKER
        ))

        all_records = postpone_history_dao.get_all()

        assert len(all_records) == 2

    def test_get_all_empty(self, postpone_history_dao):
        """Test get_all when no records exist."""
        records = postpone_history_dao.get_all()
        assert records == []

    def test_all_reason_types(self, postpone_history_dao, sample_task):
        """Test all postpone reason types."""
        for reason_type in PostponeReasonType:
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=reason_type
            )
            created = postpone_history_dao.create(record)

            retrieved = postpone_history_dao.get_by_id(created.id)

            assert retrieved.reason_type == reason_type

    def test_all_action_taken_types(self, postpone_history_dao, sample_task):
        """Test all action taken types."""
        for action in ActionTaken:
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.OTHER,
                action_taken=action
            )
            created = postpone_history_dao.create(record)

            retrieved = postpone_history_dao.get_by_id(created.id)

            assert retrieved.action_taken == action

    def test_record_with_long_notes(self, postpone_history_dao, sample_task):
        """Test record with long reason notes."""
        long_notes = "A" * 1000  # 1000 character note

        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.OTHER,
            reason_notes=long_notes
        )
        created = postpone_history_dao.create(record)

        retrieved = postpone_history_dao.get_by_id(created.id)

        assert retrieved.reason_notes == long_notes
