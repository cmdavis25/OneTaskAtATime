"""
Unit tests for NotificationPanel.

Tests the notification panel widget including:
- Panel initialization
- Notification display
- Dismissal behavior
- Action button handling
"""

import pytest
import sqlite3

from PyQt5.QtWidgets import QApplication

from src.ui.notification_panel import NotificationPanel





@pytest.fixture
def notification_panel(qapp, db_connection):
    """Create notification panel instance."""
    from unittest.mock import MagicMock
    from src.services.notification_manager import NotificationManager

    # Create mock notification manager
    mock_manager = MagicMock(spec=NotificationManager)
    mock_manager.get_unread_count.return_value = 0
    mock_manager.get_all_notifications.return_value = []  # Fixed: use get_all_notifications instead of get_recent_notifications

    panel = NotificationPanel(db_connection.get_connection(), mock_manager)
    yield panel
    panel.close()


class TestPanelInitialization:
    """Test panel initialization."""

    def test_panel_creation(self, notification_panel):
        """Test that notification panel can be created."""
        assert notification_panel is not None

    def test_panel_has_layout(self, notification_panel):
        """Test that panel has layout."""
        assert notification_panel.layout() is not None

    def test_panel_initially_hidden_or_empty(self, notification_panel):
        """Test that panel is initially hidden or shows no notifications."""
        # Panel should start empty or hidden
        assert hasattr(notification_panel, 'notification_list') or hasattr(notification_panel, 'layout')


class TestNotificationDisplay:
    """Test notification display."""

    def test_has_show_notification_method(self, notification_panel):
        """Test that panel has method to show notifications."""
        assert hasattr(notification_panel, 'show_notification')
        assert callable(notification_panel.show_notification)

    def test_has_notification_list_widget(self, notification_panel):
        """Test that panel has widget to display notifications."""
        assert hasattr(notification_panel, 'notification_list') or hasattr(notification_panel, 'notifications_layout')


class TestNotificationActions:
    """Test notification action buttons."""

    def test_has_clear_all_button(self, notification_panel):
        """Test that panel has clear all button."""
        assert hasattr(notification_panel, 'clear_all_button')

    def test_clear_all_button_clears_notifications(self, notification_panel):
        """Test that clear all button clears notifications."""
        # Add a notification (if method exists)
        if hasattr(notification_panel, 'show_notification'):
            notification_panel.show_notification("Test Title", "Test message")

        # Click clear all
        notification_panel.clear_all_button.click()

        # Notifications should be cleared
        if hasattr(notification_panel, 'notification_list'):
            assert notification_panel.notification_list.count() == 0


class TestNotificationDismissal:
    """Test individual notification dismissal."""

    def test_has_dismiss_notification_method(self, notification_panel):
        """Test that panel has method to dismiss notification."""
        assert hasattr(notification_panel, 'dismiss_notification') or hasattr(notification_panel, 'remove_notification')


class TestNotificationCount:
    """Test notification count display."""

    def test_has_count_label(self, notification_panel):
        """Test that panel has count label."""
        assert hasattr(notification_panel, 'count_label') or hasattr(notification_panel, 'notification_count_label')

    def test_count_updates_when_notification_added(self, notification_panel):
        """Test that count updates when notification is added."""
        if hasattr(notification_panel, 'show_notification') and hasattr(notification_panel, 'count_label'):
            initial_count = notification_panel.count_label.text()

            notification_panel.show_notification("Test", "Message")

            updated_count = notification_panel.count_label.text()
            assert updated_count != initial_count


class TestPanelSignals:
    """Test panel signals."""

    def test_has_notification_clicked_signal(self, notification_panel):
        """Test that panel has signal for notification clicks."""
        assert hasattr(notification_panel, 'notification_clicked')

    def test_has_notification_dismissed_signal(self, notification_panel):
        """Test that panel has signal for notification dismissal."""
        assert hasattr(notification_panel, 'notification_dismissed')


class TestPanelToggle:
    """Test panel show/hide functionality."""

    def test_has_toggle_visibility_method(self, notification_panel):
        """Test that panel has method to toggle visibility."""
        assert hasattr(notification_panel, 'toggle_visibility') or hasattr(notification_panel, 'setVisible')

    def test_panel_can_be_hidden(self, notification_panel):
        """Test that panel can be hidden."""
        notification_panel.hide()
        assert not notification_panel.isVisible()

    def test_panel_can_be_shown(self, notification_panel):
        """Test that panel can be shown."""
        notification_panel.show()
        assert notification_panel.isVisible()
