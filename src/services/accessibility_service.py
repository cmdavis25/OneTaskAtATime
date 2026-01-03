"""
Accessibility Service for OneTaskAtATime.

Provides centralized accessibility management and WCAG 2.1 AA compliance.
"""

from typing import List, Optional
from dataclasses import dataclass
from PyQt5.QtWidgets import QWidget, QMainWindow, QLabel, QStatusBar
from PyQt5.QtCore import QObject, pyqtSignal, QTimer


@dataclass
class ContrastIssue:
    """Represents a color contrast issue found during accessibility check."""
    widget_name: str
    foreground: str
    background: str
    contrast_ratio: float
    required_ratio: float


class AccessibilityService(QObject):
    """
    Service for managing accessibility features and WCAG compliance.

    Provides methods to:
    - Apply accessible labels and descriptions to widgets
    - Configure keyboard navigation
    - Announce messages to screen readers
    - Verify color contrast ratios
    """

    # Signal for screen reader announcements
    announcement_made = pyqtSignal(str, str)  # message, priority

    def __init__(self):
        """Initialize the Accessibility Service."""
        super().__init__()
        self._live_region_label: Optional[QLabel] = None
        self._status_bar: Optional[QStatusBar] = None

    def set_live_region(self, status_bar: QStatusBar):
        """
        Set the status bar to use for screen reader announcements.

        Args:
            status_bar: QStatusBar widget to use for ARIA-like live regions
        """
        self._status_bar = status_bar

    def apply_accessible_labels(self, widget: QWidget):
        """
        Apply accessible names and descriptions to widget tree.

        Recursively walks the widget tree and ensures all interactive
        widgets have proper accessible names for screen readers.

        Args:
            widget: Root widget to start from
        """
        # Set accessible name if not already set
        if not widget.accessibleName():
            # Try to infer from object name or text
            if widget.objectName():
                widget.setAccessibleName(self._humanize_object_name(widget.objectName()))
            elif hasattr(widget, 'text') and callable(widget.text):
                text = widget.text()
                if text:
                    widget.setAccessibleName(text)

        # Recursively process children
        for child in widget.findChildren(QWidget):
            self.apply_accessible_labels(child)

    def configure_keyboard_navigation(self, window: QMainWindow):
        """
        Configure keyboard navigation for the main window.

        Sets up proper tab order and focus handling for keyboard-only users.

        Args:
            window: Main window to configure
        """
        # Set focus policy for main window
        window.setFocusPolicy(0x1)  # Qt.StrongFocus

        # Ensure all interactive widgets are keyboard-accessible
        self._ensure_keyboard_accessible(window)

    def add_keyboard_hints(self, widget: QWidget):
        """
        Add keyboard shortcut hints to widget tooltips.

        Args:
            widget: Widget to add hints to
        """
        # Get existing tooltip
        tooltip = widget.toolTip()

        # Check for shortcuts
        if hasattr(widget, 'shortcut') and widget.shortcut():
            shortcut_text = widget.shortcut().toString()
            if tooltip:
                widget.setToolTip(f"{tooltip} ({shortcut_text})")
            else:
                widget.setToolTip(f"Keyboard shortcut: {shortcut_text}")

    def announce_to_screen_reader(self, message: str, priority: str = "polite"):
        """
        Announce a message to screen readers using ARIA-like live regions.

        Args:
            message: Message to announce
            priority: Priority level - "polite" or "assertive"
        """
        if self._status_bar:
            # Show message in status bar (screen readers will detect this)
            if priority == "assertive":
                # Assertive messages stay longer
                self._status_bar.showMessage(message, 5000)
            else:
                # Polite messages are brief
                self._status_bar.showMessage(message, 3000)

        # Emit signal for other components
        self.announcement_made.emit(message, priority)

    def verify_contrast_ratios(self, widget: QWidget) -> List[ContrastIssue]:
        """
        Check all color combinations for WCAG AA compliance (4.5:1 ratio).

        Args:
            widget: Root widget to check

        Returns:
            List of contrast issues found
        """
        issues = []

        # Walk widget tree and check contrast
        for child in widget.findChildren(QWidget):
            issue = self._check_widget_contrast(child)
            if issue:
                issues.append(issue)

        return issues

    def _check_widget_contrast(self, widget: QWidget) -> Optional[ContrastIssue]:
        """
        Check contrast ratio for a single widget.

        Args:
            widget: Widget to check

        Returns:
            ContrastIssue if ratio is insufficient, None otherwise
        """
        # Get widget colors
        palette = widget.palette()
        fg_color = palette.color(palette.WindowText)
        bg_color = palette.color(palette.Window)

        # Calculate contrast ratio
        ratio = self._calculate_contrast_ratio(
            (fg_color.red(), fg_color.green(), fg_color.blue()),
            (bg_color.red(), bg_color.green(), bg_color.blue())
        )

        # WCAG AA requires 4.5:1 for normal text
        required_ratio = 4.5

        if ratio < required_ratio:
            return ContrastIssue(
                widget_name=widget.objectName() or str(widget),
                foreground=fg_color.name(),
                background=bg_color.name(),
                contrast_ratio=ratio,
                required_ratio=required_ratio
            )

        return None

    def _calculate_contrast_ratio(self, rgb1: tuple, rgb2: tuple) -> float:
        """
        Calculate WCAG contrast ratio between two RGB colors.

        Args:
            rgb1: First color as (r, g, b) tuple (0-255)
            rgb2: Second color as (r, g, b) tuple (0-255)

        Returns:
            Contrast ratio as float
        """
        # Convert to relative luminance
        l1 = self._relative_luminance(rgb1)
        l2 = self._relative_luminance(rgb2)

        # Calculate contrast ratio
        lighter = max(l1, l2)
        darker = min(l1, l2)

        return (lighter + 0.05) / (darker + 0.05)

    def _relative_luminance(self, rgb: tuple) -> float:
        """
        Calculate relative luminance of RGB color.

        Args:
            rgb: Color as (r, g, b) tuple (0-255)

        Returns:
            Relative luminance (0-1)
        """
        # Convert to 0-1 range
        r, g, b = [x / 255.0 for x in rgb]

        # Apply gamma correction
        def gamma_correct(channel):
            if channel <= 0.03928:
                return channel / 12.92
            else:
                return ((channel + 0.055) / 1.055) ** 2.4

        r = gamma_correct(r)
        g = gamma_correct(g)
        b = gamma_correct(b)

        # Calculate luminance using WCAG formula
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _humanize_object_name(self, object_name: str) -> str:
        """
        Convert camelCase or snake_case object name to human-readable text.

        Args:
            object_name: Object name to humanize

        Returns:
            Human-readable text
        """
        # Replace underscores with spaces
        name = object_name.replace('_', ' ')

        # Add spaces before capital letters (camelCase)
        import re
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)

        # Capitalize first letter
        return name.capitalize()

    def _ensure_keyboard_accessible(self, widget: QWidget):
        """
        Ensure widget and children are keyboard accessible.

        Args:
            widget: Widget to check
        """
        # Set focus policy for interactive widgets
        from PyQt5.QtWidgets import (
            QPushButton, QLineEdit, QTextEdit, QComboBox,
            QCheckBox, QRadioButton, QSpinBox, QSlider
        )

        if isinstance(widget, (QPushButton, QLineEdit, QTextEdit, QComboBox,
                              QCheckBox, QRadioButton, QSpinBox, QSlider)):
            widget.setFocusPolicy(0x1)  # Qt.StrongFocus

        # Recurse to children
        for child in widget.findChildren(QWidget):
            self._ensure_keyboard_accessible(child)
