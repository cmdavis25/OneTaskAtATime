"""
Unit tests for ResurfacingService.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.database.schema import DatabaseSchema
from src.database.task_dao import TaskDAO
from src.database.settings_dao import SettingsDAO
from src.services.resurfacing_service import ResurfacingService
from src.models import Task
from src.models.enums import TaskState
from src.models.notification import NotificationType


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
    # Run Phase 6 migration to create notifications table and settings
    DatabaseSchema.migrate_to_notification_system(conn)
    yield conn
    conn.close()


@pytest.fixture
def task_dao(db_connection):
    """Create a TaskDAO instance for testing."""
    return TaskDAO(db_connection)


@pytest.fixture
def settings_dao(db_connection):
    """Create a SettingsDAO instance for testing."""
    return SettingsDAO(db_connection)


@pytest.fixture
def resurfacing_service(db_connection):
    """Create a ResurfacingService instance for testing."""
    return ResurfacingService(db_connection)


@pytest.fixture
def mock_notification_manager():
    """Create a mock notification manager."""
    mock = Mock()
    mock.create_notification = Mock()
    mock.get_unread_notifications = Mock(return_value=[])
    return mock


class TestActivateReadyDeferredTasks:
    """Tests for activate_ready_deferred_tasks method."""

    def test_activates_task_with_past_start_date(self, resurfacing_service, task_dao):
        """Test that a deferred task with past start date is activated."""
        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Deferred Task",
            state=TaskState.DEFERRED,
            start_date=yesterday
        )
        created_task = task_dao.create(task)

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        assert len(activated_tasks) == 1
        assert activated_tasks[0].id == created_task.id

        # Verify task was updated
        updated_task = task_dao.get_by_id(created_task.id)
        assert updated_task.state == TaskState.ACTIVE
        assert updated_task.start_date is None
        assert updated_task.resurface_count == 1

    def test_activates_task_with_today_start_date(self, resurfacing_service, task_dao):
        """Test that a deferred task with today's start date is activated."""
        today = date.today()
        task = Task(
            title="Due Today",
            state=TaskState.DEFERRED,
            start_date=today
        )
        created_task = task_dao.create(task)

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        assert len(activated_tasks) == 1
        updated_task = task_dao.get_by_id(created_task.id)
        assert updated_task.state == TaskState.ACTIVE

    def test_does_not_activate_future_task(self, resurfacing_service, task_dao):
        """Test that a deferred task with future start date is not activated."""
        tomorrow = date.today() + timedelta(days=1)
        task = Task(
            title="Future Task",
            state=TaskState.DEFERRED,
            start_date=tomorrow
        )
        task_dao.create(task)

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        assert len(activated_tasks) == 0

    def test_returns_empty_list_when_no_tasks(self, resurfacing_service):
        """Test returns empty list when no deferred tasks exist."""
        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()
        assert activated_tasks == []

    def test_activates_multiple_tasks(self, resurfacing_service, task_dao):
        """Test activating multiple deferred tasks."""
        yesterday = date.today() - timedelta(days=1)

        for i in range(3):
            task = Task(
                title=f"Deferred Task {i}",
                state=TaskState.DEFERRED,
                start_date=yesterday
            )
            task_dao.create(task)

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        assert len(activated_tasks) == 3

    def test_updates_resurface_count(self, resurfacing_service, task_dao):
        """Test that resurface_count is properly updated."""
        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Test Task",
            state=TaskState.DEFERRED,
            start_date=yesterday,
            resurface_count=5
        )
        created_task = task_dao.create(task)

        resurfacing_service.activate_ready_deferred_tasks()

        updated_task = task_dao.get_by_id(created_task.id)
        assert updated_task.resurface_count == 6

    def test_creates_notification_when_manager_available(self, db_connection, task_dao, mock_notification_manager, settings_dao):
        """Test that notification is created when notification manager is available."""
        # Enable notifications
        settings_dao.set('notify_deferred_activation', True, 'boolean')

        service = ResurfacingService(db_connection, mock_notification_manager)

        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Deferred Task",
            state=TaskState.DEFERRED,
            start_date=yesterday
        )
        task_dao.create(task)

        service.activate_ready_deferred_tasks()

        mock_notification_manager.create_notification.assert_called_once()
        call_kwargs = mock_notification_manager.create_notification.call_args[1]
        assert call_kwargs['type'] == NotificationType.INFO
        assert "1 deferred task(s)" in call_kwargs['message']


class TestCheckDelegatedFollowups:
    """Tests for check_delegated_followups method."""

    def test_finds_task_needing_followup(self, resurfacing_service, task_dao):
        """Test finding a delegated task needing follow-up."""
        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Delegated Task",
            state=TaskState.DELEGATED,
            delegated_to="Alice",
            follow_up_date=yesterday
        )
        task_dao.create(task)

        followup_tasks = resurfacing_service.check_delegated_followups()

        assert len(followup_tasks) == 1
        assert followup_tasks[0].delegated_to == "Alice"

    def test_finds_task_with_today_followup(self, resurfacing_service, task_dao):
        """Test finding a task with today as follow-up date."""
        today = date.today()
        task = Task(
            title="Follow Up Today",
            state=TaskState.DELEGATED,
            delegated_to="Bob",
            follow_up_date=today
        )
        task_dao.create(task)

        followup_tasks = resurfacing_service.check_delegated_followups()

        assert len(followup_tasks) == 1

    def test_does_not_find_future_followup(self, resurfacing_service, task_dao):
        """Test that future follow-up tasks are not returned."""
        future = date.today() + timedelta(days=7)
        task = Task(
            title="Future Follow-up",
            state=TaskState.DELEGATED,
            delegated_to="Carol",
            follow_up_date=future
        )
        task_dao.create(task)

        followup_tasks = resurfacing_service.check_delegated_followups()

        assert len(followup_tasks) == 0

    def test_returns_empty_when_no_delegated_tasks(self, resurfacing_service):
        """Test returns empty list when no delegated tasks exist."""
        followup_tasks = resurfacing_service.check_delegated_followups()
        assert followup_tasks == []

    def test_updates_resurface_tracking(self, resurfacing_service, task_dao):
        """Test that resurface tracking is updated."""
        yesterday = date.today() - timedelta(days=1)
        task = Task(
            title="Delegated Task",
            state=TaskState.DELEGATED,
            delegated_to="Dan",
            follow_up_date=yesterday,
            resurface_count=2
        )
        created_task = task_dao.create(task)

        resurfacing_service.check_delegated_followups()

        updated_task = task_dao.get_by_id(created_task.id)
        assert updated_task.resurface_count == 3
        assert updated_task.last_resurfaced_at is not None


class TestShouldTriggerSomedayReview:
    """Tests for should_trigger_someday_review method."""

    def test_returns_true_when_never_reviewed(self, resurfacing_service):
        """Test returns True when no previous review exists."""
        result = resurfacing_service.should_trigger_someday_review()
        assert result is True

    def test_returns_true_when_interval_elapsed(self, resurfacing_service, settings_dao):
        """Test returns True when review interval has elapsed."""
        # Set last review to 10 days ago
        ten_days_ago = datetime.now() - timedelta(days=10)
        settings_dao.set('last_someday_review_at', ten_days_ago.isoformat(), 'string')
        settings_dao.set('someday_review_days', 7, 'integer')

        result = resurfacing_service.should_trigger_someday_review()

        assert result is True

    def test_returns_false_when_interval_not_elapsed(self, resurfacing_service, settings_dao):
        """Test returns False when review interval has not elapsed."""
        # Set last review to 3 days ago
        three_days_ago = datetime.now() - timedelta(days=3)
        settings_dao.set('last_someday_review_at', three_days_ago.isoformat(), 'string')
        settings_dao.set('someday_review_days', 7, 'integer')

        result = resurfacing_service.should_trigger_someday_review()

        assert result is False

    def test_uses_default_interval(self, resurfacing_service, settings_dao):
        """Test uses default 7-day interval when not configured."""
        # Set last review to 6 days ago (less than default 7)
        six_days_ago = datetime.now() - timedelta(days=6)
        settings_dao.set('last_someday_review_at', six_days_ago.isoformat(), 'string')

        result = resurfacing_service.should_trigger_someday_review()

        assert result is False


class TestGetSomedayTasks:
    """Tests for get_someday_tasks method."""

    def test_returns_someday_tasks(self, resurfacing_service, task_dao):
        """Test returning all someday tasks."""
        task_dao.create(Task(title="Someday 1", state=TaskState.SOMEDAY))
        task_dao.create(Task(title="Someday 2", state=TaskState.SOMEDAY))
        task_dao.create(Task(title="Active", state=TaskState.ACTIVE))

        someday_tasks = resurfacing_service.get_someday_tasks()

        assert len(someday_tasks) == 2
        assert all(t.state == TaskState.SOMEDAY for t in someday_tasks)

    def test_returns_empty_when_no_someday_tasks(self, resurfacing_service):
        """Test returns empty list when no someday tasks exist."""
        someday_tasks = resurfacing_service.get_someday_tasks()
        assert someday_tasks == []


class TestUpdateSomedayReviewTimestamp:
    """Tests for update_someday_review_timestamp method."""

    def test_updates_timestamp(self, resurfacing_service, settings_dao):
        """Test that timestamp is updated correctly."""
        before = datetime.now()

        resurfacing_service.update_someday_review_timestamp()

        after = datetime.now()

        saved_timestamp = settings_dao.get_datetime('last_someday_review_at')
        assert saved_timestamp is not None
        assert before <= saved_timestamp <= after


class TestAnalyzePostponementPatterns:
    """Tests for analyze_postponement_patterns method."""

    def test_returns_empty_when_no_postponements(self, resurfacing_service):
        """Test returns empty list when no postponements exist."""
        suggestions = resurfacing_service.analyze_postponement_patterns()
        assert suggestions == []

    def test_uses_intervention_threshold_setting(self, resurfacing_service, settings_dao):
        """Test that intervention threshold setting is used."""
        settings_dao.set('postpone_intervention_threshold', 5, 'integer')

        suggestions = resurfacing_service.analyze_postponement_patterns()

        # Should complete without error
        assert isinstance(suggestions, list)


class TestBlockedTaskHandling:
    """Tests for handling blocked deferred tasks."""

    def test_skips_deferred_task_with_incomplete_blockers(self, resurfacing_service, task_dao, db_connection):
        """Test that deferred tasks with incomplete blockers are not activated."""
        yesterday = date.today() - timedelta(days=1)

        # Create blocking task (incomplete)
        blocker = Task(title="Blocker", state=TaskState.ACTIVE)
        blocker = task_dao.create(blocker)

        # Create blocked task
        blocked = Task(
            title="Blocked Task",
            state=TaskState.DEFERRED,
            start_date=yesterday
        )
        blocked = task_dao.create(blocked)

        # Create dependency
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO dependencies (blocked_task_id, blocking_task_id) VALUES (?, ?)",
            (blocked.id, blocker.id)
        )
        db_connection.commit()

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        # Should not activate blocked task
        assert len(activated_tasks) == 0

        # Verify task is still deferred
        updated_task = task_dao.get_by_id(blocked.id)
        assert updated_task.state == TaskState.DEFERRED

    def test_activates_task_when_blocker_completed(self, resurfacing_service, task_dao, db_connection):
        """Test that deferred tasks are activated when blockers are complete."""
        yesterday = date.today() - timedelta(days=1)

        # Create blocking task (completed)
        blocker = Task(title="Blocker", state=TaskState.COMPLETED)
        blocker = task_dao.create(blocker)

        # Create blocked task
        blocked = Task(
            title="Blocked Task",
            state=TaskState.DEFERRED,
            start_date=yesterday
        )
        blocked = task_dao.create(blocked)

        # Create dependency
        cursor = db_connection.cursor()
        cursor.execute(
            "INSERT INTO dependencies (blocked_task_id, blocking_task_id) VALUES (?, ?)",
            (blocked.id, blocker.id)
        )
        db_connection.commit()

        activated_tasks = resurfacing_service.activate_ready_deferred_tasks()

        # Should activate since blocker is complete
        assert len(activated_tasks) == 1
