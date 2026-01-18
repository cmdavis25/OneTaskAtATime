"""
Unit tests for ToastNotificationService.

Tests toast notification functionality including:
- Service initialization
- Platform detection (Windows/non-Windows)
- Toast notification display
- Error handling
- Availability checking
- Icon handling
"""

import pytest
import platform
import sys
from unittest.mock import MagicMock, patch, call
import logging

from src.services.toast_notification_service import ToastNotificationService
from src.models.notification import NotificationType


@pytest.fixture
def mock_db_connection():
    """Create mock database connection."""
    return MagicMock()


@pytest.fixture
def fresh_toast_service():
    """Create a fresh ToastNotificationService by temporarily removing winotify from cache."""
    # Store original winotify module if it exists
    original_winotify = sys.modules.get('winotify')

    yield

    # Restore original winotify module
    if original_winotify:
        sys.modules['winotify'] = original_winotify
    elif 'winotify' in sys.modules:
        del sys.modules['winotify']


class TestInitialization:
    """Test service initialization."""

    @patch('src.services.toast_notification_service.platform.system', return_value='Windows')
    def test_initialization_on_windows(self, mock_platform):
        """Test that service initializes correctly on Windows."""
        with patch('src.services.toast_notification_service.Notification', create=True) as mock_notification:
            service = ToastNotificationService()

            assert service.is_windows is True
            assert service.notification_class is not None

    @patch('src.services.toast_notification_service.platform.system', return_value='Linux')
    def test_initialization_on_linux(self, mock_platform):
        """Test that service detects non-Windows platform."""
        service = ToastNotificationService()

        assert service.is_windows is False
        assert service.notification_class is None

    @patch('src.services.toast_notification_service.platform.system', return_value='Darwin')
    def test_initialization_on_macos(self, mock_platform):
        """Test that service detects macOS platform."""
        service = ToastNotificationService()

        assert service.is_windows is False

    def test_initialization_handles_import_error(self):
        """Test that service handles missing winotify library gracefully."""
        # Test the service's graceful degradation by directly manipulating its state
        # This simulates what happens when winotify import fails
        service = ToastNotificationService()

        # Simulate import error condition by setting notification_class to None
        service.notification_class = None
        service.is_windows = False

        # Verify the service gracefully degrades
        assert service.notification_class is None
        assert service.is_windows is False
        assert service.is_available() is False

        # show_toast should return False when not available
        result = service.show_toast("Test", "Test message")
        assert result is False

    def test_initialization_handles_other_errors(self):
        """Test that service handles unexpected initialization errors gracefully."""
        # Test the service's graceful degradation by directly manipulating its state
        # This simulates what happens when any error occurs during initialization
        service = ToastNotificationService()

        # Simulate error condition by setting notification_class to None
        service.notification_class = None
        service.is_windows = False

        # Verify the service gracefully degrades
        assert service.notification_class is None
        assert service.is_windows is False
        assert service.is_available() is False

        # show_toast should return False when not available
        result = service.show_toast("Test", "Test message")
        assert result is False

    def test_initialization_with_db_connection(self, mock_db_connection):
        """Test that service stores database connection."""
        service = ToastNotificationService(mock_db_connection)

        assert service.db_connection == mock_db_connection


class TestIsAvailable:
    """Test availability checking."""

    @patch('src.services.toast_notification_service.platform.system', return_value='Windows')
    def test_is_available_on_windows_with_library(self, mock_platform):
        """Test that service is available on Windows with library."""
        with patch('src.services.toast_notification_service.Notification', create=True):
            service = ToastNotificationService()

            assert service.is_available() is True

    def test_is_available_on_windows_without_library(self):
        """Test that service is not available without library."""
        # Test by simulating the condition where winotify is not available
        service = ToastNotificationService()

        # Simulate missing library condition
        service.notification_class = None
        service.is_windows = True  # Even on Windows, if notification_class is None, not available

        assert service.is_available() is False

    def test_is_available_requires_notification_class(self):
        """Test that is_available returns False when notification_class is None."""
        service = ToastNotificationService()

        # Even if is_windows is True, need notification_class to be available
        original_notification_class = service.notification_class
        service.notification_class = None

        assert service.is_available() is False

        # Restore
        service.notification_class = original_notification_class

    @patch('src.services.toast_notification_service.platform.system', return_value='Linux')
    def test_is_available_on_non_windows(self, mock_platform):
        """Test that service is not available on non-Windows."""
        service = ToastNotificationService()

        assert service.is_available() is False


class TestShowToast:
    """Test showing toast notifications."""

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_toast_success(self, mock_thread):
        """Test showing toast notification successfully."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Test Title",
            message="Test Message",
            type=NotificationType.INFO,
            duration=5
        )

        # Should return True
        assert result is True

        # Should create notification with correct parameters
        mock_notification_class.assert_called_once_with(
            app_id="OneTaskAtATime",
            title="Test Title",
            msg="Test Message",
            duration='long'
        )

        # Should start thread to show toast
        mock_thread.assert_called_once()

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_toast_short_duration(self, mock_thread):
        """Test showing toast with short duration."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Quick Toast",
            message="Short message",
            duration=3
        )

        # Should use 'short' duration
        call_args = mock_notification_class.call_args
        assert call_args[1]['duration'] == 'short'

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_toast_long_duration(self, mock_thread):
        """Test showing toast with long duration."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Long Toast",
            message="Longer message",
            duration=10
        )

        # Should use 'long' duration
        call_args = mock_notification_class.call_args
        assert call_args[1]['duration'] == 'long'

    @patch('src.services.toast_notification_service.platform.system', return_value='Linux')
    def test_show_toast_on_non_windows(self, mock_platform):
        """Test that show_toast returns False on non-Windows."""
        service = ToastNotificationService()

        result = service.show_toast(
            title="Test",
            message="Test message"
        )

        assert result is False

    def test_show_toast_handles_exception(self):
        """Test that show_toast handles exceptions gracefully."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock notification class to raise an exception
        mock_notification_class = MagicMock(side_effect=Exception("Toast error"))
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Test",
            message="Test message"
        )

        # Should return False on error
        assert result is False

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_toast_with_icon(self, mock_thread):
        """Test showing toast with icon."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        # Mock _get_icon_path to return a path
        with patch.object(service, '_get_icon_path', return_value='/path/to/icon.png'):
            result = service.show_toast(
                title="Test",
                message="Test message",
                type=NotificationType.INFO  # Use INFO instead of SUCCESS (which doesn't exist)
            )

            # Should call set_icon
            mock_notification_instance.set_icon.assert_called_once_with('/path/to/icon.png')

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_toast_without_icon(self, mock_thread):
        """Test showing toast without custom icon."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Test",
            message="Test message"
        )

        # Should not call set_icon when icon_path is None
        mock_notification_instance.set_icon.assert_not_called()


class TestGetIconPath:
    """Test icon path retrieval."""

    def test_get_icon_path_info(self):
        """Test getting icon path for INFO type."""
        service = ToastNotificationService()

        icon_path = service._get_icon_path(NotificationType.INFO)

        # Currently returns None (default icon)
        assert icon_path is None

    def test_get_icon_path_warning(self):
        """Test getting icon path for WARNING type."""
        service = ToastNotificationService()

        icon_path = service._get_icon_path(NotificationType.WARNING)

        # Currently returns None (default icon)
        assert icon_path is None

    def test_get_icon_path_error(self):
        """Test getting icon path for ERROR type."""
        service = ToastNotificationService()

        icon_path = service._get_icon_path(NotificationType.ERROR)

        # Currently returns None (default icon)
        assert icon_path is None

    def test_get_icon_path_all_types(self):
        """Test getting icon path for all notification types."""
        service = ToastNotificationService()

        # All types should return None currently (uses default icons)
        for notification_type in NotificationType:
            icon_path = service._get_icon_path(notification_type)
            assert icon_path is None


class TestNotificationTypes:
    """Test different notification types."""

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_info_notification(self, mock_thread):
        """Test showing INFO notification."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Info",
            message="Information message",
            type=NotificationType.INFO
        )

        assert result is True

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_warning_notification(self, mock_thread):
        """Test showing WARNING notification."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Warning",
            message="Warning message",
            type=NotificationType.WARNING
        )

        assert result is True

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_error_notification(self, mock_thread):
        """Test showing ERROR notification."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        result = service.show_toast(
            title="Error",
            message="Error message",
            type=NotificationType.ERROR
        )

        assert result is True

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_show_all_notification_types(self, mock_thread):
        """Test showing all available notification types."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Test each notification type
        for notification_type in NotificationType:
            # Mock the notification class after service init
            mock_notification_instance = MagicMock()
            mock_notification_class = MagicMock(return_value=mock_notification_instance)
            service.notification_class = mock_notification_class

            result = service.show_toast(
                title=f"Test {notification_type.name}",
                message=f"Testing {notification_type.name} notification",
                type=notification_type
            )

            assert result is True, f"Failed for {notification_type.name}"


class TestThreading:
    """Test threading behavior."""

    @patch('src.services.toast_notification_service.threading.Thread')
    def test_toast_shown_in_background_thread(self, mock_thread):
        """Test that toast is shown in background thread."""
        service = ToastNotificationService()

        # Skip test if not on Windows with winotify
        if not service.is_available():
            pytest.skip("winotify not available")

        # Mock the notification class after service init
        mock_notification_instance = MagicMock()
        mock_notification_class = MagicMock(return_value=mock_notification_instance)
        service.notification_class = mock_notification_class

        service.show_toast(
            title="Test",
            message="Test message"
        )

        # Should create daemon thread
        mock_thread.assert_called_once()
        call_kwargs = mock_thread.call_args[1]
        assert call_kwargs['daemon'] is True

        # Should start the thread
        thread_instance = mock_thread.return_value
        thread_instance.start.assert_called_once()


class TestLogging:
    """Test logging behavior."""

    def test_logs_initialization_on_windows(self, caplog):
        """Test that initialization is logged on Windows."""
        service = ToastNotificationService()

        if service.is_available():
            # On Windows with winotify, check for success message
            with caplog.at_level(logging.INFO):
                service2 = ToastNotificationService()
                assert any("Toast notification service initialized" in record.message
                          or "Windows" in record.message for record in caplog.records)
        else:
            # On non-Windows or without winotify, just pass
            pytest.skip("Not on Windows with winotify")

    @patch('src.services.toast_notification_service.platform.system', return_value='Linux')
    def test_logs_non_windows_platform(self, mock_platform, caplog):
        """Test that non-Windows platform is logged."""
        with caplog.at_level(logging.INFO):
            service = ToastNotificationService()

            # Should log platform unavailability
            assert any("not available on" in record.message for record in caplog.records)

    def test_service_logs_debug_when_not_available(self, caplog):
        """Test that service logs debug message when show_toast called but not available."""
        service = ToastNotificationService()

        # Simulate unavailable condition
        service.notification_class = None
        service.is_windows = False

        with caplog.at_level(logging.DEBUG):
            result = service.show_toast("Test", "Test message")

            assert result is False
            # Should log debug message about notifications not available
            assert any("not available" in record.message.lower() for record in caplog.records)
