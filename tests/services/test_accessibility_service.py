"""
Unit tests for AccessibilityService.

Tests WCAG compliance and accessibility features.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.services.accessibility_service import AccessibilityService


@pytest.fixture
def accessibility_service():
    """Create AccessibilityService instance."""
    return AccessibilityService()


def test_calculate_contrast_ratio_black_white(accessibility_service):
    """Test contrast ratio calculation for black on white."""
    # Black on white should be maximum ratio (21:1)
    ratio = accessibility_service._calculate_contrast_ratio(
        (0, 0, 0),      # Black
        (255, 255, 255) # White
    )

    assert ratio == pytest.approx(21.0, abs=0.1)


def test_calculate_contrast_ratio_same_color(accessibility_service):
    """Test contrast ratio for same color (should be 1:1)."""
    ratio = accessibility_service._calculate_contrast_ratio(
        (128, 128, 128),
        (128, 128, 128)
    )

    assert ratio == pytest.approx(1.0, abs=0.01)


def test_calculate_contrast_ratio_wcag_aa_pass(accessibility_service):
    """Test contrast ratio that passes WCAG AA (4.5:1)."""
    # Dark gray on white should pass
    ratio = accessibility_service._calculate_contrast_ratio(
        (26, 26, 26),   # Very dark gray
        (255, 255, 255) # White
    )

    assert ratio >= 4.5


def test_relative_luminance_black(accessibility_service):
    """Test relative luminance of black is 0."""
    luminance = accessibility_service._relative_luminance((0, 0, 0))
    assert luminance == pytest.approx(0.0, abs=0.001)


def test_relative_luminance_white(accessibility_service):
    """Test relative luminance of white is 1."""
    luminance = accessibility_service._relative_luminance((255, 255, 255))
    assert luminance == pytest.approx(1.0, abs=0.001)


def test_humanize_object_name_snake_case(accessibility_service):
    """Test humanizing snake_case object names."""
    result = accessibility_service._humanize_object_name("task_title_input")
    assert result == "Task title input"


def test_humanize_object_name_camel_case(accessibility_service):
    """Test humanizing camelCase object names."""
    result = accessibility_service._humanize_object_name("taskTitleInput")
    assert result == "Task title input"


def test_announce_to_screen_reader_without_status_bar(accessibility_service):
    """Test announcement when no status bar is set."""
    # Should not raise error
    accessibility_service.announce_to_screen_reader("Test message")


def test_announce_to_screen_reader_with_status_bar(accessibility_service):
    """Test announcement with status bar."""
    mock_status_bar = Mock()
    accessibility_service.set_live_region(mock_status_bar)

    accessibility_service.announce_to_screen_reader("Test message", "polite")

    mock_status_bar.showMessage.assert_called_once_with("Test message", 3000)


def test_announce_assertive_priority(accessibility_service):
    """Test assertive priority announcements stay longer."""
    mock_status_bar = Mock()
    accessibility_service.set_live_region(mock_status_bar)

    accessibility_service.announce_to_screen_reader("Urgent!", "assertive")

    mock_status_bar.showMessage.assert_called_once_with("Urgent!", 5000)


def test_contrast_issue_detection():
    """Test ContrastIssue dataclass creation."""
    from src.services.accessibility_service import ContrastIssue

    issue = ContrastIssue(
        widget_name="test_widget",
        foreground="#000000",
        background="#888888",
        contrast_ratio=3.2,
        required_ratio=4.5
    )

    assert issue.widget_name == "test_widget"
    assert issue.contrast_ratio == 3.2
    assert issue.required_ratio == 4.5
