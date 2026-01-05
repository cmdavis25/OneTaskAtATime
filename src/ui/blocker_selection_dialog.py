"""
Blocker Selection Dialog for OneTaskAtATime application.

Allows users to create a new blocker task or select an existing task as a blocker.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QLineEdit, QComboBox, QTextEdit
)
from PyQt5.QtCore import Qt
from typing import Optional, Dict, Any
from ..database.connection import DatabaseConnection
from ..database.task_dao import TaskDAO
from ..models.task import Task
from ..models.enums import TaskState
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class BlockerSelectionDialog(QDialog, GeometryMixin):
    """
    Dialog for creating or selecting a blocker task.

    Provides two modes:
    1. Create a new task to address the blocker
    2. Select an existing task as the blocker
    """

    def __init__(self, task: Task, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the blocker selection dialog.

        Args:
            task: Task that is being blocked
            db_connection: DatabaseConnection wrapper
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.db_connection = db_connection
        self.task_dao = TaskDAO(db_connection.get_connection())

        # Track created blocker task (when using new task mode)
        self.created_blocker_task_id = None
        self.created_blocker_task_title = None

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=400)

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Create Blocker")
        self.setMinimumWidth(550)

        # Apply stylesheet for QComboBox to show clear dropdown arrows
        self.setStyleSheet("""
            QComboBox {
                padding: 5px;
                padding-right: 25px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #495057;
                width: 0;
                height: 0;
                margin-right: 5px;
            }
            QComboBox:hover {
                border-color: #80bdff;
            }
            QComboBox:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title
        title_label = QLabel(f"Create Blocker for: {self.task.title}")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # Question
        question_label = QLabel("What is blocking you?")
        question_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(question_label)

        # Mode selection
        self.mode_group = QButtonGroup(self)

        self.mode_new = QRadioButton("Create new task to address blocker")
        self.mode_existing = QRadioButton("Select existing task as blocker")

        self.mode_group.addButton(self.mode_new, 0)
        self.mode_group.addButton(self.mode_existing, 1)
        self.mode_new.setChecked(True)

        layout.addWidget(self.mode_new)
        layout.addWidget(self.mode_existing)

        # Connect mode change to update UI
        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        # New task mode: no additional inputs needed here (handled by EnhancedTaskFormDialog)
        self.new_task_label = QLabel("You will be prompted to fill in all task details in the next dialog.")
        self.new_task_label.setStyleSheet("font-style: italic; color: #6c757d;")
        layout.addWidget(self.new_task_label)

        # Existing task dropdown
        self.existing_task_label = QLabel("Select existing task:")
        self.existing_task_combo = QComboBox()
        self._populate_existing_tasks()
        layout.addWidget(self.existing_task_label)
        layout.addWidget(self.existing_task_combo)

        # Additional notes
        notes_label = QLabel("Additional notes about this blocker (optional):")
        layout.addWidget(notes_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Add any context about why this task is blocked...")
        layout.addWidget(self.notes_edit)

        # Update UI based on default mode
        self._on_mode_changed()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        create_button = QPushButton("Create Blocker")
        create_button.setDefault(True)
        create_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        create_button.clicked.connect(self._on_create_clicked)
        button_layout.addWidget(create_button)

        layout.addLayout(button_layout)

    def _populate_existing_tasks(self):
        """Populate the combo box with active tasks."""
        self.existing_task_combo.clear()

        # Get all active tasks except the current one
        active_tasks = self.task_dao.get_all(state=TaskState.ACTIVE)

        for task in active_tasks:
            if task.id != self.task.id:  # Don't include the task being blocked
                self.existing_task_combo.addItem(task.title, task.id)

        # Also include deferred tasks (might become actionable)
        deferred_tasks = self.task_dao.get_all(state=TaskState.DEFERRED)
        for task in deferred_tasks:
            if task.id != self.task.id:
                self.existing_task_combo.addItem(f"{task.title} (deferred)", task.id)

    def _on_mode_changed(self):
        """Update UI visibility based on selected mode."""
        is_new_mode = self.mode_new.isChecked()

        # Show/hide appropriate inputs
        self.new_task_label.setVisible(is_new_mode)
        self.existing_task_label.setVisible(not is_new_mode)
        self.existing_task_combo.setVisible(not is_new_mode)

    def _on_create_clicked(self):
        """Validate input and accept dialog."""
        if self.mode_new.isChecked():
            # Launch the full task creation dialog
            from .task_form_enhanced import EnhancedTaskFormDialog

            # Create the dialog for a NEW task (task=None)
            task_dialog = EnhancedTaskFormDialog(
                task=None,
                db_connection=self.db_connection,
                parent=self
            )

            # Pre-fill default values from the blocked task
            # Priority
            for i in range(task_dialog.priority_combo.count()):
                if task_dialog.priority_combo.itemData(i) == self.task.base_priority:
                    task_dialog.priority_combo.setCurrentIndex(i)
                    break

            # Due date
            if self.task.due_date:
                task_dialog.due_date_edit.setText(self.task.due_date.strftime("%Y-%m-%d"))
                task_dialog.has_due_date_check.setChecked(True)
                task_dialog.due_date_edit.setEnabled(True)
                task_dialog.due_date_calendar_btn.setEnabled(True)

            # Context
            if self.task.context_id:
                for i in range(task_dialog.context_combo.count()):
                    if task_dialog.context_combo.itemData(i) == self.task.context_id:
                        task_dialog.context_combo.setCurrentIndex(i)
                        break

            # Project tags - use the tag_checkboxes dictionary
            if self.task.project_tags:
                for tag_id in self.task.project_tags:
                    if tag_id in task_dialog.tag_checkboxes:
                        task_dialog.tag_checkboxes[tag_id].setChecked(True)

            if task_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled the task creation

            # Get the created task from the dialog
            created_task = task_dialog.get_updated_task()
            if not created_task:
                return

            # Save the task to the database
            from ..database.task_dao import TaskDAO
            task_dao = TaskDAO(self.db_connection.get_connection())
            saved_task = task_dao.create(created_task)

            if not saved_task:
                MessageBox.warning(
                    self,
                    self.db_connection.get_connection(),
                    "Task Creation Failed",
                    "Failed to create the blocker task."
                )
                return

            # Store the created task ID for the result
            self.created_blocker_task_id = saved_task.id
            self.created_blocker_task_title = saved_task.title

        else:
            # Validate existing task selection
            if self.existing_task_combo.count() == 0:
                MessageBox.warning(
                    self,
                    self.db_connection.get_connection(),
                    "No Tasks Available",
                    "There are no existing tasks to select as a blocker."
                )
                return

        self.accept()

    def get_result(self) -> Dict[str, Any]:
        """
        Get the dialog result.

        Returns:
            Dictionary with:
                - mode: 'new' or 'existing'
                - blocker_task_id: int (the task ID for both new and existing)
                - notes: str
        """
        result = {
            'notes': self.notes_edit.toPlainText().strip()
        }

        if self.mode_new.isChecked():
            result['mode'] = 'new'
            # Return the created task ID (already saved to DB)
            result['blocker_task_id'] = self.created_blocker_task_id
        else:
            result['mode'] = 'existing'
            result['blocker_task_id'] = self.existing_task_combo.currentData()

        return result
