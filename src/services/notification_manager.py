"""
Notification Manager Service for OneTaskAtATime application.

Centralized service for creating, managing, and delivering notifications through
multiple channels (in-app panel and Windows toast notifications).
"""

import sqlite3
import logging
from typing import List, Optional, Dict, Any

from PyQt5.QtCore import QObject, pyqtSignal

from ..models.notification import Notification, NotificationType
from ..database.notification_dao import NotificationDAO
from ..database.settings_dao import SettingsDAO


# Configure logging
logger = logging.getLogger(__name__)


class NotificationManager(QObject):
    """
    Centralized notification manager.

    This service:
    - Creates notifications and stores them in the database
    - Emits Qt signals for UI updates
    - Triggers toast notifications (if enabled)
    - Provides query methods for the UI
    """

    # Qt signals
    new_notification = pyqtSignal(Notification)  # Emitted when new notification is created
    notification_updated = pyqtSignal(Notification)  # Emitted when notification is updated
    notification_dismissed = pyqtSignal(int)  # Emitted when notification is dismissed (ID)

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize the notification manager.

        Args:
            db_connection: Active SQLite database connection
        """
        super().__init__()

        self.db_connection = db_connection
        self.notification_dao = NotificationDAO(db_connection)
        self.settings_dao = SettingsDAO(db_connection)

        # Toast service will be set externally to avoid circular dependency
        self.toast_service = None

    def set_toast_service(self, toast_service):
        """
        Set the toast notification service.

        Args:
            toast_service: ToastNotificationService instance
        """
        self.toast_service = toast_service

    def create_notification(
        self,
        type: NotificationType,
        title: str,
        message: str,
        action_type: Optional[str] = None,
        action_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Create and deliver a new notification.

        This method:
        1. Creates notification in database
        2. Emits Qt signal for UI update
        3. Triggers toast notification (if enabled)

        Args:
            type: Notification type (INFO, WARNING, ERROR)
            title: Short notification title
            message: Detailed message content
            action_type: Optional action identifier
            action_data: Optional action payload dictionary

        Returns:
            Created Notification object
        """
        logger.info(f"Creating notification: {title}")

        # Create notification object
        notification = Notification(
            type=type,
            title=title,
            message=message,
            action_type=action_type,
            action_data=action_data
        )

        try:
            # Save to database
            notification = self.notification_dao.create(notification)

            # Emit signal for UI update
            self.new_notification.emit(notification)

            # Trigger toast notification if enabled
            self._maybe_show_toast(notification)

            logger.info(f"Notification created successfully (ID: {notification.id})")

        except Exception as e:
            logger.error(f"Error creating notification: {e}", exc_info=True)

        return notification

    def get_all_notifications(self, include_dismissed: bool = False) -> List[Notification]:
        """
        Get all notifications.

        Args:
            include_dismissed: Whether to include dismissed notifications

        Returns:
            List of Notification objects
        """
        try:
            return self.notification_dao.get_all(include_dismissed=include_dismissed)
        except Exception as e:
            logger.error(f"Error getting all notifications: {e}", exc_info=True)
            return []

    def get_unread_notifications(self) -> List[Notification]:
        """
        Get all unread, non-dismissed notifications.

        Returns:
            List of unread Notification objects
        """
        try:
            return self.notification_dao.get_unread()
        except Exception as e:
            logger.error(f"Error getting unread notifications: {e}", exc_info=True)
            return []

    def get_unread_count(self) -> int:
        """
        Get count of unread notifications.

        Returns:
            Number of unread notifications
        """
        try:
            unread = self.notification_dao.get_unread()
            return len(unread)
        except Exception as e:
            logger.error(f"Error getting unread count: {e}", exc_info=True)
            return 0

    def mark_as_read(self, notification_id: int) -> bool:
        """
        Mark a notification as read.

        Args:
            notification_id: ID of notification to mark as read

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.notification_dao.mark_read(notification_id)

            if success:
                # Get updated notification and emit signal
                notification = self.notification_dao.get_by_id(notification_id)
                if notification:
                    self.notification_updated.emit(notification)

                logger.debug(f"Marked notification {notification_id} as read")

            return success

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}", exc_info=True)
            return False

    def mark_as_unread(self, notification_id: int) -> bool:
        """
        Mark a notification as unread.

        Args:
            notification_id: ID of notification to mark as unread

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.notification_dao.mark_unread(notification_id)

            if success:
                # Get updated notification and emit signal
                notification = self.notification_dao.get_by_id(notification_id)
                if notification:
                    self.notification_updated.emit(notification)

                logger.debug(f"Marked notification {notification_id} as unread")

            return success

        except Exception as e:
            logger.error(f"Error marking notification as unread: {e}", exc_info=True)
            return False

    def mark_all_read(self) -> int:
        """
        Mark all notifications as read.

        Returns:
            Number of notifications marked as read
        """
        try:
            count = self.notification_dao.mark_all_read()

            logger.info(f"Marked {count} notifications as read")

            # Emit update signal regardless of count (UI should refresh)
            # Using a special signal with ID=0 to indicate "all notifications"
            self.notification_updated.emit(Notification(id=0))

            return count

        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}", exc_info=True)
            return 0

    def dismiss_notification(self, notification_id: int) -> bool:
        """
        Dismiss a notification (soft delete).

        Args:
            notification_id: ID of notification to dismiss

        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.notification_dao.dismiss(notification_id)

            if success:
                self.notification_dismissed.emit(notification_id)
                logger.debug(f"Dismissed notification {notification_id}")

            return success

        except Exception as e:
            logger.error(f"Error dismissing notification: {e}", exc_info=True)
            return False

    def cleanup_old_notifications(self) -> int:
        """
        Delete old notifications based on retention settings.

        Returns:
            Number of notifications deleted
        """
        try:
            retention_days = self.settings_dao.get_int('notification_retention_days', default=30)
            count = self.notification_dao.delete_old_notifications(days=retention_days)

            if count > 0:
                logger.info(f"Cleaned up {count} old notifications (>{retention_days} days)")

            return count

        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}", exc_info=True)
            return 0

    def _maybe_show_toast(self, notification: Notification) -> None:
        """
        Show toast notification if enabled and available.

        Args:
            notification: Notification to show as toast
        """
        try:
            # Check if toast notifications are enabled
            toast_enabled = self.settings_dao.get_bool('enable_toast_notifications', default=True)

            if not toast_enabled:
                logger.debug("Toast notifications disabled in settings")
                return

            # Check if toast service is available
            if self.toast_service is None:
                logger.debug("Toast service not available")
                return

            # Show toast
            self.toast_service.show_toast(
                title=notification.title,
                message=notification.message,
                type=notification.type
            )

        except Exception as e:
            logger.error(f"Error showing toast notification: {e}", exc_info=True)
