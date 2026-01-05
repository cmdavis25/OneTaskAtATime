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
from PyQt5.QtGui import QFont, QTextDocument, QPageLayout
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from .geometry_mixin import GeometryMixin


class ShortcutsDialog(QDialog, GeometryMixin):
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

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=700, default_height=500)
        else:
            # Set flag to prevent GeometryMixin.showEvent from failing
            self._geometry_restored = True

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

        # Print button
        print_button = QPushButton("Print")
        print_button.clicked.connect(self._print_shortcuts)
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

    def _print_shortcuts(self):
        """Print the keyboard shortcuts reference."""
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageOrientation(QPageLayout.Portrait)

        # Show print dialog
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Print Keyboard Shortcuts")

        if dialog.exec_() == QPrintDialog.Accepted:
            # Create HTML document with all shortcuts
            html = self._generate_shortcuts_html()

            # Create text document and print
            document = QTextDocument()
            document.setHtml(html)
            document.print_(printer)

    def _generate_shortcuts_html(self) -> str:
        """
        Generate HTML representation of all shortcuts for printing.

        Returns:
            HTML string containing formatted shortcuts
        """
        html = """
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1 { color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }
                h2 { color: #666; margin-top: 30px; margin-bottom: 10px; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
                th { background-color: #f0f0f0; padding: 8px; text-align: left; border: 1px solid #ddd; }
                td { padding: 8px; border: 1px solid #ddd; }
                .shortcut { font-weight: bold; text-align: center; }
                tr:nth-child(even) { background-color: #f9f9f9; }
            </style>
        </head>
        <body>
            <h1>OneTaskAtATime - Keyboard Shortcuts</h1>
        """

        for category, shortcuts in self.SHORTCUTS.items():
            html += f"<h2>{category}</h2>"
            html += "<table>"
            html += "<tr><th>Action</th><th>Shortcut</th></tr>"

            for action, shortcut in shortcuts:
                html += f"<tr><td>{action}</td><td class='shortcut'>{shortcut}</td></tr>"

            html += "</table>"

        html += """
        </body>
        </html>
        """

        return html
