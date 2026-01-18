"""
Unit tests for NotificationDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta

from src.database.schema import DatabaseSchema
from src.database.notification_dao import NotificationDAO
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
def notification_dao(db_connection):
    """Create a NotificationDAO instance for testing."""
    return NotificationDAO(db_connection)


class TestNotificationDAO:
    """Tests for NotificationDAO class."""

    def test_create_basic_notification(self, notification_dao):
        """Test creating a basic notification."""
        notification = Notification(
            title="Test Notification",
            message="This is a test message"
        )

        created = notification_dao.create(notification)

        assert created.id is not None
        assert created.title == "Test Notification"
        assert created.message == "This is a test message"
        assert created.type == NotificationType.INFO
        assert created.is_read is False

    def test_create_notification_with_all_fields(self, notification_dao):
        """Test creating a notification with all fields populated."""
        notification = Notification(
            type=NotificationType.WARNING,
            title="Warning",
            message="This is a warning",
            action_type="open_task",
            action_data={"task_id": 123}
        )

        created = notification_dao.create(notification)

        assert created.id is not None
        assert created.type == NotificationType.WARNING
        assert created.action_type == "open_task"
        assert created.action_data == {"task_id": 123}

    def test_create_notification_with_existing_id_raises_error(self, notification_dao):
        """Test that creating a notification with an ID raises an error."""
        notification = Notification(id=1, title="Test", message="Test")

        with pytest.raises(ValueError, match="Cannot create notification that already has an id"):
            notification_dao.create(notification)

    def test_get_by_id(self, notification_dao):
        """Test retrieving a notification by ID."""
        notification = Notification(title="Find Me", message="Test")
        created = notification_dao.create(notification)

        retrieved = notification_dao.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == "Find Me"

    def test_get_by_id_not_found(self, notification_dao):
        """Test retrieving a non-existent notification."""
        notification = notification_dao.get_by_id(9999)
        assert notification is None

    def test_get_all(self, notification_dao):
        """Test getting all non-dismissed notifications."""
        notification_dao.create(Notification(title="First", message="msg"))
        notification_dao.create(Notification(title="Second", message="msg"))
        notification_dao.create(Notification(title="Third", message="msg"))

        notifications = notification_dao.get_all()

        assert len(notifications) == 3

    def test_get_all_excludes_dismissed_by_default(self, notification_dao):
        """Test that get_all excludes dismissed notifications by default."""
        n1 = notification_dao.create(Notification(title="Active", message="msg"))
        n2 = notification_dao.create(Notification(title="Dismissed", message="msg"))

        notification_dao.dismiss(n2.id)

        notifications = notification_dao.get_all()

        assert len(notifications) == 1
        assert notifications[0].title == "Active"

    def test_get_all_includes_dismissed_when_requested(self, notification_dao):
        """Test that get_all includes dismissed when requested."""
        n1 = notification_dao.create(Notification(title="Active", message="msg"))
        n2 = notification_dao.create(Notification(title="Dismissed", message="msg"))

        notification_dao.dismiss(n2.id)

        notifications = notification_dao.get_all(include_dismissed=True)

        assert len(notifications) == 2

    def test_get_unread(self, notification_dao):
        """Test getting unread notifications."""
        n1 = notification_dao.create(Notification(title="Unread 1", message="msg"))
        n2 = notification_dao.create(Notification(title="Unread 2", message="msg"))
        n3 = notification_dao.create(Notification(title="Read", message="msg"))

        notification_dao.mark_read(n3.id)

        unread = notification_dao.get_unread()

        assert len(unread) == 2
        assert all(not n.is_read for n in unread)

    def test_get_unread_excludes_dismissed(self, notification_dao):
        """Test that get_unread excludes dismissed notifications."""
        n1 = notification_dao.create(Notification(title="Unread", message="msg"))
        n2 = notification_dao.create(Notification(title="Dismissed", message="msg"))

        notification_dao.dismiss(n2.id)

        unread = notification_dao.get_unread()

        assert len(unread) == 1
        assert unread[0].title == "Unread"

    def test_mark_read(self, notification_dao):
        """Test marking a notification as read."""
        notification = notification_dao.create(Notification(title="Test", message="msg"))
        assert notification.is_read is False

        result = notification_dao.mark_read(notification.id)

        assert result is True

        retrieved = notification_dao.get_by_id(notification.id)
        assert retrieved.is_read is True

    def test_mark_read_not_found(self, notification_dao):
        """Test marking a non-existent notification as read."""
        result = notification_dao.mark_read(9999)
        assert result is False

    def test_mark_unread(self, notification_dao):
        """Test marking a notification as unread."""
        notification = notification_dao.create(Notification(title="Test", message="msg"))
        notification_dao.mark_read(notification.id)

        result = notification_dao.mark_unread(notification.id)

        assert result is True

        retrieved = notification_dao.get_by_id(notification.id)
        assert retrieved.is_read is False

    def test_mark_unread_not_found(self, notification_dao):
        """Test marking a non-existent notification as unread."""
        result = notification_dao.mark_unread(9999)
        assert result is False

    def test_mark_all_read(self, notification_dao):
        """Test marking all notifications as read."""
        notification_dao.create(Notification(title="First", message="msg"))
        notification_dao.create(Notification(title="Second", message="msg"))
        notification_dao.create(Notification(title="Third", message="msg"))

        count = notification_dao.mark_all_read()

        assert count == 3

        unread = notification_dao.get_unread()
        assert len(unread) == 0

    def test_mark_all_read_no_unread(self, notification_dao):
        """Test mark_all_read when all are already read."""
        n1 = notification_dao.create(Notification(title="Test", message="msg"))
        notification_dao.mark_read(n1.id)

        count = notification_dao.mark_all_read()

        assert count == 0

    def test_dismiss(self, notification_dao):
        """Test dismissing a notification."""
        notification = notification_dao.create(Notification(title="Test", message="msg"))
        assert notification.dismissed_at is None

        result = notification_dao.dismiss(notification.id)

        assert result is True

        retrieved = notification_dao.get_by_id(notification.id)
        assert retrieved.dismissed_at is not None

    def test_dismiss_not_found(self, notification_dao):
        """Test dismissing a non-existent notification."""
        result = notification_dao.dismiss(9999)
        assert result is False

    def test_delete(self, notification_dao):
        """Test permanently deleting a notification."""
        notification = notification_dao.create(Notification(title="Test", message="msg"))

        result = notification_dao.delete(notification.id)

        assert result is True

        retrieved = notification_dao.get_by_id(notification.id)
        assert retrieved is None

    def test_delete_not_found(self, notification_dao):
        """Test deleting a non-existent notification."""
        result = notification_dao.delete(9999)
        assert result is False

    def test_delete_old_notifications(self, notification_dao, db_connection):
        """Test deleting old notifications."""
        # Create a notification with old timestamp
        cursor = db_connection.cursor()
        old_date = (datetime.now() - timedelta(days=60)).isoformat()

        cursor.execute(
            """
            INSERT INTO notifications (type, title, message, created_at, is_read)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("info", "Old Notification", "Very old", old_date, 0)
        )
        db_connection.commit()

        # Create a recent notification
        notification_dao.create(Notification(title="Recent", message="msg"))

        # Delete notifications older than 30 days
        count = notification_dao.delete_old_notifications(days=30)

        assert count == 1

        # Verify only recent notification remains
        all_notifications = notification_dao.get_all()
        assert len(all_notifications) == 1
        assert all_notifications[0].title == "Recent"

    def test_delete_old_notifications_none_old(self, notification_dao):
        """Test delete_old_notifications when no old notifications exist."""
        notification_dao.create(Notification(title="Recent", message="msg"))

        count = notification_dao.delete_old_notifications(days=30)

        assert count == 0

    def test_notification_types(self, notification_dao):
        """Test all notification types."""
        for notification_type in NotificationType:
            notification = Notification(
                type=notification_type,
                title=f"Type: {notification_type.value}",
                message="Test"
            )
            created = notification_dao.create(notification)

            retrieved = notification_dao.get_by_id(created.id)

            assert retrieved.type == notification_type

    def test_action_data_json_serialization(self, notification_dao):
        """Test that action_data is properly serialized/deserialized."""
        complex_data = {
            "task_ids": [1, 2, 3],
            "filters": {"priority": "high", "tags": ["work", "urgent"]},
            "count": 42
        }

        notification = Notification(
            title="Complex Action",
            message="Test",
            action_type="complex_action",
            action_data=complex_data
        )
        created = notification_dao.create(notification)

        retrieved = notification_dao.get_by_id(created.id)

        assert retrieved.action_data == complex_data
        assert retrieved.action_data["task_ids"] == [1, 2, 3]
        assert retrieved.action_data["filters"]["priority"] == "high"

    def test_get_all_ordered_by_created_at_desc(self, notification_dao, db_connection):
        """Test that get_all returns notifications ordered by created_at descending."""
        # Create notifications with specific timestamps
        cursor = db_connection.cursor()

        timestamps = [
            (datetime.now() - timedelta(hours=2)).isoformat(),
            (datetime.now() - timedelta(hours=1)).isoformat(),
            datetime.now().isoformat(),
        ]

        for i, ts in enumerate(timestamps):
            cursor.execute(
                """
                INSERT INTO notifications (type, title, message, created_at, is_read)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("info", f"Notification {i}", "msg", ts, 0)
            )
        db_connection.commit()

        notifications = notification_dao.get_all()

        # Most recent should be first
        assert notifications[0].title == "Notification 2"
        assert notifications[2].title == "Notification 0"
