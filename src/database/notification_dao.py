"""
Notification Data Access Object for OneTaskAtATime application.

Handles all database CRUD operations for notifications.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
import json

from ..models.notification import Notification, NotificationType


class NotificationDAO:
    """Data Access Object for Notification operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize NotificationDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def create(self, notification: Notification) -> Notification:
        """
        Insert a new notification into the database.

        Args:
            notification: Notification object to insert (id should be None)

        Returns:
            Notification object with id populated

        Raises:
            ValueError: If notification already has an id
        """
        if notification.id is not None:
            raise ValueError("Cannot create notification that already has an id")

        cursor = self.db.cursor()

        # Serialize action_data to JSON string
        action_data_str = None
        if notification.action_data:
            action_data_str = json.dumps(notification.action_data)

        cursor.execute(
            """
            INSERT INTO notifications (
                type, title, message, created_at, is_read,
                action_type, action_data, dismissed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                notification.type.value,
                notification.title,
                notification.message,
                notification.created_at.isoformat(),
                1 if notification.is_read else 0,
                notification.action_type,
                action_data_str,
                notification.dismissed_at.isoformat() if notification.dismissed_at else None
            )
        )

        notification.id = cursor.lastrowid
        self.db.commit()

        return notification

    def get_by_id(self, notification_id: int) -> Optional[Notification]:
        """
        Retrieve a notification by its ID.

        Args:
            notification_id: ID of notification to retrieve

        Returns:
            Notification object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, type, title, message, created_at, is_read,
                   action_type, action_data, dismissed_at
            FROM notifications
            WHERE id = ?
            """,
            (notification_id,)
        )

        row = cursor.fetchone()
        if row:
            return self._row_to_notification(row)
        return None

    def get_all(self, include_dismissed: bool = False) -> List[Notification]:
        """
        Get all notifications.

        Args:
            include_dismissed: Whether to include dismissed notifications

        Returns:
            List of Notification objects, ordered by created_at DESC
        """
        cursor = self.db.cursor()

        if include_dismissed:
            query = """
                SELECT id, type, title, message, created_at, is_read,
                       action_type, action_data, dismissed_at
                FROM notifications
                ORDER BY created_at DESC
            """
            cursor.execute(query)
        else:
            query = """
                SELECT id, type, title, message, created_at, is_read,
                       action_type, action_data, dismissed_at
                FROM notifications
                WHERE dismissed_at IS NULL
                ORDER BY created_at DESC
            """
            cursor.execute(query)

        notifications = []
        for row in cursor.fetchall():
            notifications.append(self._row_to_notification(row))

        return notifications

    def get_unread(self) -> List[Notification]:
        """
        Get all unread, non-dismissed notifications.

        Returns:
            List of unread Notification objects, ordered by created_at DESC
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, type, title, message, created_at, is_read,
                   action_type, action_data, dismissed_at
            FROM notifications
            WHERE is_read = 0 AND dismissed_at IS NULL
            ORDER BY created_at DESC
            """
        )

        notifications = []
        for row in cursor.fetchall():
            notifications.append(self._row_to_notification(row))

        return notifications

    def mark_read(self, notification_id: int) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of notification to mark as read

        Returns:
            True if notification was updated, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute(
            "UPDATE notifications SET is_read = 1 WHERE id = ?",
            (notification_id,)
        )
        self.db.commit()

        return cursor.rowcount > 0

    def mark_all_read(self) -> int:
        """
        Mark all notifications as read.

        Returns:
            Number of notifications updated
        """
        cursor = self.db.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
        self.db.commit()

        return cursor.rowcount

    def dismiss(self, notification_id: int) -> bool:
        """
        Dismiss a notification (soft delete).

        Args:
            notification_id: ID of notification to dismiss

        Returns:
            True if notification was updated, False if not found
        """
        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            "UPDATE notifications SET dismissed_at = ? WHERE id = ?",
            (now.isoformat(), notification_id)
        )
        self.db.commit()

        return cursor.rowcount > 0

    def delete(self, notification_id: int) -> bool:
        """
        Permanently delete a notification.

        Args:
            notification_id: ID of notification to delete

        Returns:
            True if notification was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
        self.db.commit()

        return cursor.rowcount > 0

    def delete_old_notifications(self, days: int = 30) -> int:
        """
        Delete notifications older than specified days.

        Args:
            days: Number of days to keep (default 30)

        Returns:
            Number of notifications deleted
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)
        cursor = self.db.cursor()

        cursor.execute(
            "DELETE FROM notifications WHERE created_at < ?",
            (cutoff_date.isoformat(),)
        )
        self.db.commit()

        return cursor.rowcount

    def _row_to_notification(self, row: tuple) -> Notification:
        """
        Convert a database row to a Notification object.

        Args:
            row: Tuple from database query

        Returns:
            Notification object
        """
        (
            notification_id, notification_type, title, message, created_at, is_read,
            action_type, action_data, dismissed_at
        ) = row

        # Parse type enum
        try:
            type_enum = NotificationType(notification_type)
        except ValueError:
            type_enum = NotificationType.INFO

        # Parse datetimes
        created_at_dt = datetime.fromisoformat(created_at) if created_at else datetime.now()
        dismissed_at_dt = datetime.fromisoformat(dismissed_at) if dismissed_at else None

        # Parse action_data JSON
        action_data_dict = None
        if action_data:
            try:
                action_data_dict = json.loads(action_data)
            except (json.JSONDecodeError, TypeError):
                action_data_dict = None

        return Notification(
            id=notification_id,
            type=type_enum,
            title=title,
            message=message,
            created_at=created_at_dt,
            is_read=bool(is_read),
            action_type=action_type,
            action_data=action_data_dict,
            dismissed_at=dismissed_at_dt
        )
