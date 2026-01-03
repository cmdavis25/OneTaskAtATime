"""
Keyboard Shortcuts Dialog for OneTaskAtATime.

Displays a comprehensive cheatsheet of all keyboard shortcuts.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QTableWidget, QTableWidgetItem, QPushButton,
    QHeaderView, QLabel
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class ShortcutsDialog(QDialog):
    """
    Dialog displaying all keyboard shortcuts in categorized tabs.

    Shows shortcuts for:
    - General navigation
    - Focus Mode actions
    - Task List operations
    - Dialogs and editing
    """

    # Define all shortcuts by category
    SHORTCUTS = {
        "General": [
            ("New Task", "Ctrl+N"),
            ("Export Data", "Ctrl+Shift+E"),
            ("Import Data", "Ctrl+Shift+I"),
            ("Settings", "Ctrl+,"),
            ("Help", "F1"),
            ("Keyboard Shortcuts", "Ctrl+?"),
            ("Exit", "Ctrl+Q"),
            ("Undo", "Ctrl+Z"),
            ("Redo", "Ctrl+Y"),
        ],
        "Navigation": [
            ("Focus Mode", "Ctrl+1"),
            ("Task List", "Ctrl+2"),
            ("Refresh", "F5"),
        ],
        "Focus Mode": [
            ("Complete Task", "Alt+C"),
            ("Defer Task", "Alt+D"),
            ("Delegate Task", "Alt+G"),
            ("Move to Someday/Maybe", "Alt+S"),
            ("Move to Trash", "Alt+X"),
        ],
        "Task List": [
            ("Edit Selected Task", "Enter"),
        ],
        "Dialogs": [
            ("Confirm/OK", "Enter"),
            ("Cancel/Close", "Esc"),
            ("Next Field", "Tab"),
            ("Previous Field", "Shift+Tab"),
        ],
    }

    def __init__(self, parent=None):
        """
        Initialize the Shortcuts Dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(650, 500)
        self.setModal(False)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("<h2>Keyboard Shortcuts</h2>")
        layout.addWidget(header_label)

        # Tab widget for categories
        self.tab_widget = QTabWidget()

        for category, shortcuts in self.SHORTCUTS.items():
            tab = self._create_shortcut_tab(shortcuts)
            self.tab_widget.addTab(tab, category)

        layout.addWidget(self.tab_widget)

        # Footer with buttons
        button_layout = QHBoxLayout()

        # Print button (placeholder for future)
        print_button = QPushButton("Print")
        print_button.setEnabled(False)  # TODO: Implement print functionality
        button_layout.addWidget(print_button)

        button_layout.addStretch()

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_shortcut_tab(self, shortcuts: list) -> QWidget:
        """
        Create a tab widget displaying shortcuts in a table.

        Args:
            shortcuts: List of (action, shortcut) tuples

        Returns:
            QWidget containing the shortcuts table
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Create table
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        table.setRowCount(len(shortcuts))

        # Disable editing
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        # Set selection behavior
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)

        # Populate table
        for row, (action, shortcut) in enumerate(shortcuts):
            # Action column
            action_item = QTableWidgetItem(action)
            table.setItem(row, 0, action_item)

            # Shortcut column
            shortcut_item = QTableWidgetItem(shortcut)
            shortcut_font = QFont()
            shortcut_font.setBold(True)
            shortcut_item.setFont(shortcut_font)
            shortcut_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1, shortcut_item)

        # Adjust column widths
        table.setColumnWidth(0, 400)
        table.setColumnWidth(1, 200)
        table.horizontalHeader().setStretchLastSection(True)

        # Adjust row heights
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(30)

        # Alternating row colors
        table.setAlternatingRowColors(True)

        layout.addWidget(table)

        return widget
