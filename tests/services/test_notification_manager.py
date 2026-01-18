"""
Unit tests for NotificationManager.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from src.database.schema import DatabaseSchema
from src.database.notification_dao import NotificationDAO
from src.database.settings_dao import SettingsDAO
from src.services.notification_manager import NotificationManager
from src.models.notification import Notification, NotificationType


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
    # Run Phase 6 migration to create notifications table
    DatabaseSchema.migrate_to_notification_system(conn)
    yield conn
    conn.close()


@pytest.fixture
def notification_manager(db_connection):
    """Create a NotificationManager instance for testing."""
    # Need to patch Qt parent to avoid Qt initialization issues
    with patch.object(NotificationManager, '__init__', lambda self, db_conn: None):
        manager = NotificationManager.__new__(NotificationManager)
        manager.db_connection = db_connection
        manager.notification_dao = NotificationDAO(db_connection)
        manager.settings_dao = SettingsDAO(db_connection)
        manager.toast_service = None
        # Mock Qt signals
        manager.new_notification = Mock()
        manager.notification_updated = Mock()
        manager.notification_dismissed = Mock()
        return manager


@pytest.fixture
def settings_dao(db_connection):
    """Create a SettingsDAO instance for testing."""
    return SettingsDAO(db_connection)


class TestCreateNotification:
    """Tests for create_notification method."""

    def test_creates_basic_notification(self, notification_manager):
        """Test creating a basic notification."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO,
            title="Test Title",
            message="Test message"
        )

        assert notification.id is not None
        assert notification.title == "Test Title"
        assert notification.message == "Test message"
        assert notification.type == NotificationType.INFO

    def test_creates_notification_with_action(self, notification_manager):
        """Test creating a notification with action data."""
        notification = notification_manager.create_notification(
            type=NotificationType.WARNING,
            title="Warning",
            message="Something happened",
            action_type="open_task",
            action_data={"task_id": 123}
        )

        assert notification.action_type == "open_task"
        assert notification.action_data == {"task_id": 123}

    def test_emits_new_notification_signal(self, notification_manager):
        """Test that new_notification signal is emitted."""
        notification_manager.create_notification(
            type=NotificationType.INFO,
            title="Test",
            message="Message"
        )

        notification_manager.new_notification.emit.assert_called_once()

    def test_all_notification_types(self, notification_manager):
        """Test creating notifications with all types."""
        for notification_type in NotificationType:
            notification = notification_manager.create_notification(
                type=notification_type,
                title=f"Type: {notification_type.value}",
                message="Test"
            )

            assert notification.type == notification_type


class TestGetNotifications:
    """Tests for notification retrieval methods."""

    def test_get_all_notifications(self, notification_manager):
        """Test getting all notifications."""
        notification_manager.create_notification(
            type=NotificationType.INFO, title="First", message="msg"
        )
        notification_manager.create_notification(
            type=NotificationType.INFO, title="Second", message="msg"
        )

        notifications = notification_manager.get_all_notifications()

        assert len(notifications) == 2

    def test_get_all_excludes_dismissed(self, notification_manager):
        """Test that get_all excludes dismissed by default."""
        n1 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Active", message="msg"
        )
        n2 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Dismissed", message="msg"
        )
        notification_manager.dismiss_notification(n2.id)

        notifications = notification_manager.get_all_notifications()

        assert len(notifications) == 1
        assert notifications[0].title == "Active"

    def test_get_all_includes_dismissed_when_requested(self, notification_manager):
        """Test get_all includes dismissed when requested."""
        n1 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Active", message="msg"
        )
        n2 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Dismissed", message="msg"
        )
        notification_manager.dismiss_notification(n2.id)

        notifications = notification_manager.get_all_notifications(include_dismissed=True)

        assert len(notifications) == 2

    def test_get_unread_notifications(self, notification_manager):
        """Test getting unread notifications."""
        n1 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Unread", message="msg"
        )
        n2 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Read", message="msg"
        )
        notification_manager.mark_as_read(n2.id)

        unread = notification_manager.get_unread_notifications()

        assert len(unread) == 1
        assert unread[0].title == "Unread"

    def test_get_unread_count(self, notification_manager):
        """Test getting unread count."""
        notification_manager.create_notification(
            type=NotificationType.INFO, title="First", message="msg"
        )
        notification_manager.create_notification(
            type=NotificationType.INFO, title="Second", message="msg"
        )

        count = notification_manager.get_unread_count()

        assert count == 2


class TestMarkAsRead:
    """Tests for mark_as_read method."""

    def test_marks_notification_as_read(self, notification_manager):
        """Test marking a notification as read."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )

        result = notification_manager.mark_as_read(notification.id)

        assert result is True

        # Verify it's marked as read
        unread = notification_manager.get_unread_notifications()
        assert len(unread) == 0

    def test_emits_updated_signal(self, notification_manager):
        """Test that notification_updated signal is emitted."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )
        notification_manager.notification_updated.reset_mock()

        notification_manager.mark_as_read(notification.id)

        notification_manager.notification_updated.emit.assert_called_once()

    def test_returns_false_for_nonexistent(self, notification_manager):
        """Test returns False for non-existent notification."""
        result = notification_manager.mark_as_read(9999)
        assert result is False


class TestMarkAsUnread:
    """Tests for mark_as_unread method."""

    def test_marks_notification_as_unread(self, notification_manager):
        """Test marking a notification as unread."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )
        notification_manager.mark_as_read(notification.id)

        result = notification_manager.mark_as_unread(notification.id)

        assert result is True

        # Verify it's unread
        unread = notification_manager.get_unread_notifications()
        assert len(unread) == 1

    def test_returns_false_for_nonexistent(self, notification_manager):
        """Test returns False for non-existent notification."""
        result = notification_manager.mark_as_unread(9999)
        assert result is False


class TestMarkAllRead:
    """Tests for mark_all_read method."""

    def test_marks_all_as_read(self, notification_manager):
        """Test marking all notifications as read."""
        notification_manager.create_notification(
            type=NotificationType.INFO, title="First", message="msg"
        )
        notification_manager.create_notification(
            type=NotificationType.INFO, title="Second", message="msg"
        )

        count = notification_manager.mark_all_read()

        assert count == 2

        unread = notification_manager.get_unread_notifications()
        assert len(unread) == 0

    def test_returns_zero_when_all_read(self, notification_manager):
        """Test returns 0 when all are already read."""
        n1 = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )
        notification_manager.mark_as_read(n1.id)

        count = notification_manager.mark_all_read()

        assert count == 0


class TestDismissNotification:
    """Tests for dismiss_notification method."""

    def test_dismisses_notification(self, notification_manager):
        """Test dismissing a notification."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )

        result = notification_manager.dismiss_notification(notification.id)

        assert result is True

        # Verify it's not in the list
        all_notifications = notification_manager.get_all_notifications()
        assert len(all_notifications) == 0

    def test_emits_dismissed_signal(self, notification_manager):
        """Test that notification_dismissed signal is emitted."""
        notification = notification_manager.create_notification(
            type=NotificationType.INFO, title="Test", message="msg"
        )

        notification_manager.dismiss_notification(notification.id)

        notification_manager.notification_dismissed.emit.assert_called_with(notification.id)

    def test_returns_false_for_nonexistent(self, notification_manager):
        """Test returns False for non-existent notification."""
        result = notification_manager.dismiss_notification(9999)
        assert result is False


class TestCleanupOldNotifications:
    """Tests for cleanup_old_notifications method."""

    def test_cleans_up_old_notifications(self, notification_manager, db_connection, settings_dao):
        """Test cleaning up old notifications."""
        settings_dao.set('notification_retention_days', 30, 'integer')

        # Create an old notification directly in DB
        cursor = db_connection.cursor()
        old_date = (datetime.now() - __import__('datetime').timedelta(days=60)).isoformat()
        cursor.execute(
            """
            INSERT INTO notifications (type, title, message, created_at, is_read)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("info", "Old", "Old message", old_date, 0)
        )
        db_connection.commit()

        # Create a recent notification
        notification_manager.create_notification(
            type=NotificationType.INFO, title="Recent", message="msg"
        )

        count = notification_manager.cleanup_old_notifications()

        assert count == 1

        # Verify only recent remains
        all_notifications = notification_manager.get_all_notifications()
        assert len(all_notifications) == 1
        assert all_notifications[0].title == "Recent"


class TestToastNotifications:
    """Tests for toast notification integration."""

    def test_shows_toast_when_enabled(self, notification_manager, settings_dao):
        """Test that toast is shown when enabled."""
        settings_dao.set('enable_toast_notifications', True, 'boolean')

        mock_toast_service = Mock()
        notification_manager.set_toast_service(mock_toast_service)

        notification_manager.create_notification(
            type=NotificationType.INFO,
            title="Toast Test",
            message="Should show toast"
        )

        mock_toast_service.show_toast.assert_called_once()

    def test_does_not_show_toast_when_disabled(self, notification_manager, settings_dao):
        """Test that toast is not shown when disabled."""
        settings_dao.set('enable_toast_notifications', False, 'boolean')

        mock_toast_service = Mock()
        notification_manager.set_toast_service(mock_toast_service)

        notification_manager.create_notification(
            type=NotificationType.INFO,
            title="Toast Test",
            message="Should not show toast"
        )

        mock_toast_service.show_toast.assert_not_called()

    def test_handles_missing_toast_service(self, notification_manager, settings_dao):
        """Test that missing toast service is handled gracefully."""
        settings_dao.set('enable_toast_notifications', True, 'boolean')
        notification_manager.toast_service = None

        # Should not raise
        notification = notification_manager.create_notification(
            type=NotificationType.INFO,
            title="Test",
            message="No toast service"
        )

        assert notification.id is not None


class TestSetToastService:
    """Tests for set_toast_service method."""

    def test_sets_toast_service(self, notification_manager):
        """Test setting the toast service."""
        mock_service = Mock()

        notification_manager.set_toast_service(mock_service)

        assert notification_manager.toast_service == mock_service
