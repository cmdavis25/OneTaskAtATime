"""
Task Form Dialog - Create and edit tasks.

Phase 2: Basic task creation with essential fields.
Future phases will add tags, contexts, and dependencies.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QDateEdit, QFormLayout,
    QCheckBox
)
from PyQt5.QtCore import Qt, QDate
from datetime import date
from typing import Optional
from ..models.task import Task
from ..models.enums import Priority, TaskState


class TaskFormDialog(QDialog):
    """
    Dialog for creating or editing tasks.

    Phase 2: Basic fields (title, description, priority, due date)
    Future: Add contexts, tags, dependencies
    """

    def __init__(self, task: Optional[Task] = None, parent=None):
        """
        Initialize the task form.

        Args:
            task: Existing task to edit, or None to create new
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.is_new = (task is None)
        self._init_ui()

        if task is not None:
            self._load_task_data()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("New Task" if self.is_new else "Edit Task")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Create a new task" if self.is_new else "Edit task")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        # Form fields
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # Title (required)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter task title...")
        form_layout.addRow("Title*:", self.title_edit)

        # Description (optional)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Add detailed description (optional)...")
        self.description_edit.setMaximumHeight(100)
        form_layout.addRow("Description:", self.description_edit)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Low", Priority.LOW.value)
        self.priority_combo.addItem("Medium", Priority.MEDIUM.value)
        self.priority_combo.addItem("High", Priority.HIGH.value)
        self.priority_combo.setCurrentIndex(1)  # Default to Medium
        form_layout.addRow("Priority:", self.priority_combo)

        # Due date (optional)
        due_date_layout = QHBoxLayout()

        self.has_due_date_check = QCheckBox("Set due date")
        self.has_due_date_check.stateChanged.connect(self._on_due_date_toggled)
        due_date_layout.addWidget(self.has_due_date_check)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate.currentDate().addDays(7))
        self.due_date_edit.setEnabled(False)
        due_date_layout.addWidget(self.due_date_edit)

        due_date_layout.addStretch()

        form_layout.addRow("Due date:", due_date_layout)

        layout.addLayout(form_layout)

        # Info text
        info_label = QLabel("* Required field")
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save" if self.is_new else "Update")
        save_button.setDefault(True)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _on_due_date_toggled(self, state: int):
        """Enable/disable due date picker based on checkbox."""
        self.due_date_edit.setEnabled(state == Qt.Checked)

    def _load_task_data(self):
        """Load data from existing task into form fields."""
        if self.task is None:
            return

        # Title
        self.title_edit.setText(self.task.title)

        # Description
        if self.task.description:
            self.description_edit.setText(self.task.description)

        # Priority
        priority_index = self.task.base_priority - 1  # Convert 1-3 to 0-2
        self.priority_combo.setCurrentIndex(priority_index)

        # Due date
        if self.task.due_date:
            self.has_due_date_check.setChecked(True)
            self.due_date_edit.setDate(QDate(
                self.task.due_date.year,
                self.task.due_date.month,
                self.task.due_date.day
            ))

    def _on_save_clicked(self):
        """Validate and save the task."""
        # Validate title
        title = self.title_edit.text().strip()
        if not title:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a task title."
            )
            self.title_edit.setFocus()
            return

        # Accept the dialog
        self.accept()

    def get_task_data(self) -> Optional[dict]:
        """
        Get task data from form fields.

        Returns:
            Dictionary with task data, or None if canceled
        """
        if self.result() != QDialog.Accepted:
            return None

        # Get due date (if enabled)
        due_date = None
        if self.has_due_date_check.isChecked():
            due_date = self.due_date_edit.date().toPyDate()

        data = {
            'title': self.title_edit.text().strip(),
            'description': self.description_edit.toPlainText().strip() or None,
            'base_priority': self.priority_combo.currentData(),
            'due_date': due_date,
        }

        return data

    def get_updated_task(self) -> Optional[Task]:
        """
        Get the updated Task object.

        Returns:
            Task object with form data, or None if canceled
        """
        data = self.get_task_data()
        if data is None:
            return None

        if self.is_new:
            # Create new task
            task = Task(
                title=data['title'],
                description=data['description'],
                base_priority=data['base_priority'],
                due_date=data['due_date'],
                state=TaskState.ACTIVE
            )
        else:
            # Update existing task
            task = self.task
            task.title = data['title']
            task.description = data['description']
            task.base_priority = data['base_priority']
            task.due_date = data['due_date']

        return task
