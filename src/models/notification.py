"""
Notification model for OneTaskAtATime application.

Represents in-app notifications and Windows toast notifications.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import json


class NotificationType(Enum):
    """Types of notifications."""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'


@dataclass
class Notification:
    """
    Represents a notification in the system.

    Notifications can be displayed as:
    - Windows toast notifications (optional, Windows only)
    - In-app notification panel entries (always available)

    Attributes:
        id: Database ID (None for new notifications)
        type: Type of notification (INFO, WARNING, ERROR)
        title: Short title/heading
        message: Detailed message content
        created_at: When notification was created
        is_read: Whether user has marked as read
        action_type: Optional action identifier (e.g., 'open_focus', 'open_review_delegated')
        action_data: Optional JSON data for the action (stored as dict, serialized in DB)
        dismissed_at: When notification was dismissed (None if not dismissed)
    """

    id: Optional[int] = None
    type: NotificationType = NotificationType.INFO
    title: str = ""
    message: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    action_type: Optional[str] = None
    action_data: Optional[dict] = None
    dismissed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """
        Convert notification to dictionary for serialization.

        Returns:
            Dictionary representation of notification
        """
        return {
            'id': self.id,
            'type': self.type.value,
            'title': self.title,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_read': self.is_read,
            'action_type': self.action_type,
            'action_data': json.dumps(self.action_data) if self.action_data else None,
            'dismissed_at': self.dismissed_at.isoformat() if self.dismissed_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Notification':
        """
        Create notification from dictionary.

        Args:
            data: Dictionary with notification fields

        Returns:
            Notification instance
        """
        # Parse type enum
        notification_type = NotificationType(data.get('type', 'info'))

        # Parse datetimes
        created_at = None
        if data.get('created_at'):
            if isinstance(data['created_at'], str):
                created_at = datetime.fromisoformat(data['created_at'])
            else:
                created_at = data['created_at']

        dismissed_at = None
        if data.get('dismissed_at'):
            if isinstance(data['dismissed_at'], str):
                dismissed_at = datetime.fromisoformat(data['dismissed_at'])
            else:
                dismissed_at = data['dismissed_at']

        # Parse action data JSON
        action_data = data.get('action_data')
        if isinstance(action_data, str):
            try:
                action_data = json.loads(action_data)
            except (json.JSONDecodeError, TypeError):
                action_data = None

        return cls(
            id=data.get('id'),
            type=notification_type,
            title=data.get('title', ''),
            message=data.get('message', ''),
            created_at=created_at or datetime.now(),
            is_read=bool(data.get('is_read', False)),
            action_type=data.get('action_type'),
            action_data=action_data,
            dismissed_at=dismissed_at
        )

    def get_icon(self) -> str:
        """
        Get icon character for notification type.

        Returns:
            Unicode character representing notification type
        """
        if self.type == NotificationType.INFO:
            return "ℹ️"
        elif self.type == NotificationType.WARNING:
            return "⚠️"
        elif self.type == NotificationType.ERROR:
            return "❌"
        return "ℹ️"

    def get_time_ago(self) -> str:
        """
        Get human-readable time since notification was created.

        Returns:
            String like "5 minutes ago", "2 hours ago", "3 days ago"
        """
        if not self.created_at:
            return "Unknown"

        delta = datetime.now() - self.created_at
        seconds = delta.total_seconds()

        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
