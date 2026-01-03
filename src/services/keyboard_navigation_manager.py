"""
Keyboard Navigation Manager for OneTaskAtATime.

Manages keyboard navigation, tab order, and focus handling.
"""

from typing import List, Optional
from PyQt5.QtWidgets import QWidget, QDialog, QListWidget, QTableWidget
from PyQt5.QtCore import Qt, QEvent


class KeyboardNavigationManager:
    """
    Manager for keyboard navigation and focus handling.

    Provides methods to configure tab order, handle arrow key navigation,
    and ensure all functionality is accessible via keyboard.
    """

    def configure_dialog(self, dialog: QDialog):
        """
        Set tab order and focus handling for a dialog.

        Args:
            dialog: Dialog to configure
        """
        # Get all focusable widgets
        focusable_widgets = self._get_focusable_widgets(dialog)

        if not focusable_widgets:
            return

        # Set explicit tab order
        for i in range(len(focusable_widgets) - 1):
            dialog.setTabOrder(focusable_widgets[i], focusable_widgets[i + 1])

        # Set initial focus to first widget
        if focusable_widgets:
            focusable_widgets[0].setFocus()

    def add_focus_indicators(self, widget: QWidget):
        """
        Add visible focus outline for keyboard users.

        Args:
            widget: Widget to add focus indicators to
        """
        # Focus indicators are primarily handled via QSS/stylesheets
        # This method ensures widgets have proper focus policy
        widget.setFocusPolicy(Qt.StrongFocus)

        # Enable focus rectangles
        widget.setAttribute(Qt.WA_MacShowFocusRect, True)

    def enable_list_navigation(self, list_widget: QListWidget):
        """
        Enable full keyboard navigation for list widgets.

        Supports:
        - Arrow keys for navigation
        - Home/End for first/last item
        - Page Up/Down for paging
        - Enter/Space for selection

        Args:
            list_widget: List widget to enhance
        """
        # Install event filter for custom key handling
        list_widget.installEventFilter(ListNavigationFilter(list_widget))

    def enable_table_navigation(self, table_widget: QTableWidget):
        """
        Enable full keyboard navigation for table widgets.

        Args:
            table_widget: Table widget to enhance
        """
        # Install event filter for custom key handling
        table_widget.installEventFilter(TableNavigationFilter(table_widget))

    def _get_focusable_widgets(self, parent: QWidget) -> List[QWidget]:
        """
        Get all focusable widgets in tab order.

        Args:
            parent: Parent widget to search

        Returns:
            List of focusable widgets in logical order
        """
        from PyQt5.QtWidgets import (
            QPushButton, QLineEdit, QTextEdit, QComboBox,
            QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
            QSlider, QListWidget, QTableWidget, QTreeWidget
        )

        focusable_types = (
            QPushButton, QLineEdit, QTextEdit, QComboBox,
            QCheckBox, QRadioButton, QSpinBox, QDoubleSpinBox,
            QSlider, QListWidget, QTableWidget, QTreeWidget
        )

        widgets = []

        def collect_widgets(widget: QWidget):
            """Recursively collect focusable widgets."""
            for child in widget.children():
                if not isinstance(child, QWidget):
                    continue

                # Check if widget is visible and enabled
                if not child.isVisible() or not child.isEnabled():
                    continue

                # Check if widget accepts focus
                if isinstance(child, focusable_types):
                    focus_policy = child.focusPolicy()
                    if focus_policy != Qt.NoFocus:
                        widgets.append(child)

                # Recurse to children
                collect_widgets(child)

        collect_widgets(parent)

        # Sort by vertical then horizontal position (top to bottom, left to right)
        widgets.sort(key=lambda w: (w.y(), w.x()))

        return widgets


class ListNavigationFilter(QEvent):
    """Event filter for enhanced list navigation."""

    def __init__(self, list_widget: QListWidget):
        """Initialize the filter."""
        super().__init__(QEvent.None_)
        self.list_widget = list_widget

    def eventFilter(self, obj, event):
        """
        Filter keyboard events for list navigation.

        Args:
            obj: Object receiving event
            event: Event to filter

        Returns:
            True if event was handled, False otherwise
        """
        if event.type() != QEvent.KeyPress:
            return False

        key = event.key()

        # Home - go to first item
        if key == Qt.Key_Home:
            self.list_widget.setCurrentRow(0)
            return True

        # End - go to last item
        elif key == Qt.Key_End:
            self.list_widget.setCurrentRow(self.list_widget.count() - 1)
            return True

        # Page Up - go up one page
        elif key == Qt.Key_PageUp:
            current = self.list_widget.currentRow()
            visible_items = self._get_visible_item_count()
            new_row = max(0, current - visible_items)
            self.list_widget.setCurrentRow(new_row)
            return True

        # Page Down - go down one page
        elif key == Qt.Key_PageDown:
            current = self.list_widget.currentRow()
            visible_items = self._get_visible_item_count()
            new_row = min(self.list_widget.count() - 1, current + visible_items)
            self.list_widget.setCurrentRow(new_row)
            return True

        return False

    def _get_visible_item_count(self) -> int:
        """Get number of items visible in viewport."""
        if self.list_widget.count() == 0:
            return 0

        # Estimate based on first item height
        item_height = self.list_widget.sizeHintForRow(0)
        if item_height == 0:
            return 10  # Default estimate

        viewport_height = self.list_widget.viewport().height()
        return max(1, viewport_height // item_height)


class TableNavigationFilter(QEvent):
    """Event filter for enhanced table navigation."""

    def __init__(self, table_widget: QTableWidget):
        """Initialize the filter."""
        super().__init__(QEvent.None_)
        self.table_widget = table_widget

    def eventFilter(self, obj, event):
        """
        Filter keyboard events for table navigation.

        Args:
            obj: Object receiving event
            event: Event to filter

        Returns:
            True if event was handled, False otherwise
        """
        if event.type() != QEvent.KeyPress:
            return False

        key = event.key()

        # Home - go to first column
        if key == Qt.Key_Home and event.modifiers() == Qt.NoModifier:
            self.table_widget.setCurrentCell(self.table_widget.currentRow(), 0)
            return True

        # Ctrl+Home - go to first cell
        elif key == Qt.Key_Home and event.modifiers() == Qt.ControlModifier:
            self.table_widget.setCurrentCell(0, 0)
            return True

        # End - go to last column
        elif key == Qt.Key_End and event.modifiers() == Qt.NoModifier:
            self.table_widget.setCurrentCell(
                self.table_widget.currentRow(),
                self.table_widget.columnCount() - 1
            )
            return True

        # Ctrl+End - go to last cell
        elif key == Qt.Key_End and event.modifiers() == Qt.ControlModifier:
            self.table_widget.setCurrentCell(
                self.table_widget.rowCount() - 1,
                self.table_widget.columnCount() - 1
            )
            return True

        return False
