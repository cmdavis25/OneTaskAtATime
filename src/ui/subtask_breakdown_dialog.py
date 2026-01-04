"""
Subtask Breakdown Dialog for OneTaskAtATime application.

Allows users to break down a complex task into multiple subtasks.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QCheckBox
)
from PyQt5.QtCore import Qt
from typing import List, Dict, Any
from ..models.task import Task
from .geometry_mixin import GeometryMixin


class SubtaskBreakdownDialog(QDialog, GeometryMixin):
    """
    Dialog for breaking down a task into subtasks.

    Captures subtask titles and whether to delete the original task.
    """

    def __init__(self, task: Task, parent=None):
        """
        Initialize the subtask breakdown dialog.

        Args:
            task: Task to break down
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=600, default_height=500)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Break Down Task")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title
        title_label = QLabel(f"Break Down Task: {self.task.title}")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # Instructions
        instruction_label = QLabel("Enter subtasks (one per line):")
        instruction_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(instruction_label)

        # Subtask input (multi-line text area)
        self.subtask_edit = QTextEdit()
        self.subtask_edit.setPlaceholderText(
            "Example:\n"
            "Research authentication libraries\n"
            "Set up OAuth configuration\n"
            "Implement login endpoint\n"
            "Add session management\n"
            "Write integration tests"
        )
        layout.addWidget(self.subtask_edit)

        # Delete original checkbox
        self.delete_original_checkbox = QCheckBox("Delete original task after breakdown")
        self.delete_original_checkbox.setToolTip(
            "If checked, the original task will be moved to trash. "
            "Otherwise, it will remain active alongside the subtasks."
        )
        layout.addWidget(self.delete_original_checkbox)

        # Info note
        note_label = QLabel(
            "Note: New tasks will inherit priority, due date, and tags from the original task."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        create_button = QPushButton("Create Subtasks")
        create_button.setDefault(True)
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        create_button.clicked.connect(self._on_create_clicked)
        button_layout.addWidget(create_button)

        layout.addLayout(button_layout)

    def _on_create_clicked(self):
        """Validate input and accept dialog."""
        # Get subtask titles
        text = self.subtask_edit.toPlainText().strip()
        if not text:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter at least one subtask."
            )
            return

        # Parse lines
        lines = [line.strip() for line in text.split('\n')]
        non_empty_lines = [line for line in lines if line]

        if len(non_empty_lines) == 0:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter at least one non-empty subtask."
            )
            return

        # Confirm deletion if checkbox is checked
        if self.delete_original_checkbox.isChecked():
            from PyQt5.QtWidgets import QMessageBox
            reply = QMessageBox.question(
                self,
                "Confirm Deletion",
                f"Are you sure you want to move '{self.task.title}' to trash?\n\n"
                f"The {len(non_empty_lines)} subtask(s) will remain active.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        self.accept()

    def get_result(self) -> Dict[str, Any]:
        """
        Get the dialog result.

        Returns:
            Dictionary with:
                - subtask_titles: List[str] - Non-empty lines only
                - delete_original: bool
        """
        text = self.subtask_edit.toPlainText().strip()
        lines = [line.strip() for line in text.split('\n')]
        subtask_titles = [line for line in lines if line]

        return {
            'subtask_titles': subtask_titles,
            'delete_original': self.delete_original_checkbox.isChecked()
        }
