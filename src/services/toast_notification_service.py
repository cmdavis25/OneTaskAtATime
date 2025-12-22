"""
Toast Notification Service for OneTaskAtATime application.

Provides Windows toast notifications using winotify library.
Gracefully degrades on non-Windows platforms.
"""

import platform
import logging
import threading
from typing import Optional

from ..models.notification import NotificationType


# Configure logging
logger = logging.getLogger(__name__)


class ToastNotificationService:
    """
    Service for showing Windows toast notifications.

    This service:
    - Detects if running on Windows
    - Uses win10toast library for toast notifications
    - Runs in background thread to avoid blocking UI
    - Gracefully handles errors and platform limitations
    """

    def __init__(self, db_connection=None):
        """
        Initialize the toast notification service.

        Args:
            db_connection: Optional database connection (for future use)
        """
        self.db_connection = db_connection
        self.is_windows = platform.system() == 'Windows'
        self.notification_class = None

        # Initialize winotify if on Windows
        if self.is_windows:
            try:
                from winotify import Notification
                self.notification_class = Notification
                logger.info("Toast notification service initialized (Windows)")
            except ImportError:
                logger.warning("winotify library not available - toast notifications disabled")
                self.is_windows = False
            except Exception as e:
                logger.error(f"Error initializing toast notifier: {e}", exc_info=True)
                self.is_windows = False
        else:
            logger.info(f"Toast notifications not available on {platform.system()}")

    def show_toast(
        self,
        title: str,
        message: str,
        type: NotificationType = NotificationType.INFO,
        duration: int = 5
    ) -> bool:
        """
        Show a Windows toast notification.

        Args:
            title: Notification title
            message: Notification message
            type: Notification type (affects icon)
            duration: Duration in seconds (default 5) - converted to 'short' (<5s) or 'long' (>=5s)

        Returns:
            True if toast was shown, False otherwise
        """
        if not self.is_windows or not self.notification_class:
            logger.debug("Toast notifications not available")
            return False

        try:
            # Convert numeric duration to winotify format
            # winotify only accepts 'short' or 'long'
            toast_duration = 'short' if duration < 5 else 'long'

            # Create and show toast notification
            toast = self.notification_class(
                app_id="OneTaskAtATime",
                title=title,
                msg=message,
                duration=toast_duration
            )

            # Get icon based on notification type
            icon_path = self._get_icon_path(type)
            if icon_path:
                toast.set_icon(icon_path)

            # Show toast in background thread to avoid blocking
            thread = threading.Thread(
                target=toast.show,
                daemon=True
            )
            thread.start()

            logger.debug(f"Toast notification queued: {title}")
            return True

        except Exception as e:
            logger.error(f"Error showing toast notification: {e}", exc_info=True)
            return False

    def _get_icon_path(self, type: NotificationType) -> Optional[str]:
        """
        Get icon path for notification type.

        Args:
            type: Notification type

        Returns:
            Path to icon file, or None for default icon
        """
        # For now, return None to use default system icon
        # In the future, we could bundle custom icons for different types
        return None

    def is_available(self) -> bool:
        """
        Check if toast notifications are available.

        Returns:
            True if toast notifications can be shown, False otherwise
        """
        return self.is_windows and self.notification_class is not None
