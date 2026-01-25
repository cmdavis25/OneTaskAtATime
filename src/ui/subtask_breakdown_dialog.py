"""
Subtask Breakdown Dialog for OneTaskAtATime application.

Allows users to break down a complex task into multiple subtasks.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QCheckBox, QMessageBox, QListWidgetItem
)
from PyQt5.QtCore import Qt
from typing import List, Dict, Any
from ..models.task import Task
from ..models.enums import TaskState
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox
from .task_form_dialog import EnhancedTaskFormDialog


class SubtaskBreakdownDialog(QDialog, GeometryMixin):
    """
    Dialog for breaking down a task into subtasks.

    Uses the full New Task dialog for creating subtasks with complete data entry.
    Allows editing and deletion of created tasks before final confirmation.
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
        self.created_tasks: List[Task] = []  # Store created Task objects

        # Store db_connection from parent for MessageBox usage
        self.db_connection = None
        if parent and hasattr(parent, 'db_connection'):
            self.db_connection = parent.db_connection

        # Initialize geometry persistence (get db_connection from parent if available)
        if self.db_connection:
            self._init_geometry_persistence(self.db_connection, default_width=700, default_height=600)
        else:
            # Set flag to prevent GeometryMixin.showEvent from failing
            self._geometry_restored = True

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Break Down Task")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog helps you break down a complex task into smaller, actionable subtasks. "
            "Create multiple tasks, select one as the Next Action, and the original task will be marked complete. "
            "Click the ? button for help on specific actions."
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title
        title_label = QLabel(f"Break Down Task: {self.task.title}")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # Instructions
        instruction_label = QLabel("Create tasks that break down this larger task into actionable subtasks:")
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(instruction_label)

        # Task list with action buttons
        list_button_layout = QHBoxLayout()

        # Left side: Task list
        self.task_list = QListWidget()
        self.task_list.setMinimumHeight(300)
        self.task_list.itemDoubleClicked.connect(self._on_edit_task)
        self.task_list.setWhatsThis(
            "List of subtasks you're creating. Each subtask becomes an independent task with its own priority."
        )
        list_button_layout.addWidget(self.task_list, stretch=1)

        # Right side: Action buttons
        action_button_layout = QVBoxLayout()

        self.add_button = QPushButton("Add Task")
        self.add_button.setToolTip("Create a new task using the full task creation dialog")
        self.add_button.setWhatsThis(
            "Add a new subtask to the list. You'll be able to set its title and other details."
        )
        self.add_button.clicked.connect(self._on_add_task)
        action_button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Task")
        self.edit_button.setToolTip("Edit the selected task")
        self.edit_button.setWhatsThis(
            "Edit the selected subtask's details including title, priority, and due date."
        )
        self.edit_button.clicked.connect(self._on_edit_task)
        self.edit_button.setEnabled(False)
        action_button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Task")
        self.delete_button.setToolTip("Remove the selected task from the list")
        self.delete_button.setWhatsThis(
            "Remove the selected subtask from the list."
        )
        self.delete_button.clicked.connect(self._on_delete_task)
        self.delete_button.setEnabled(False)
        action_button_layout.addWidget(self.delete_button)

        action_button_layout.addStretch()

        list_button_layout.addLayout(action_button_layout)
        layout.addLayout(list_button_layout)

        # Connect selection change to enable/disable buttons
        self.task_list.itemSelectionChanged.connect(self._on_selection_changed)

        # Delete original checkbox
        self.delete_original_checkbox = QCheckBox("Delete original task after breakdown")
        self.delete_original_checkbox.setToolTip(
            "If checked, the original task will be moved to trash after creating these tasks.\n"
            "If unchecked, the original task will be kept and these new tasks will be added as blocking dependencies."
        )
        self.delete_original_checkbox.setWhatsThis(
            "Check this to delete the original parent task after creating subtasks. Recommended if "
            "subtasks fully replace the parent. If unchecked, subtasks become dependencies of the parent."
        )
        layout.addWidget(self.delete_original_checkbox)

        # Info note
        note_label = QLabel(
            "Note: New tasks will inherit priority, due date, context, and project tags from the original task by default."
        )
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; font-size: 9pt; margin-top: 5px;")
        layout.addWidget(note_label)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        confirm_button = QPushButton("Confirm Breakdown")
        confirm_button.setDefault(True)
        confirm_button.setStyleSheet("""
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
        confirm_button.clicked.connect(self._on_confirm_clicked)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)

    def _on_selection_changed(self):
        """Enable/disable buttons based on selection."""
        has_selection = len(self.task_list.selectedItems()) > 0
        self.edit_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _on_add_task(self):
        """Open the New Task dialog to create a new task."""
        # Create a new task inheriting properties from the original
        new_task = Task(
            title="",
            base_priority=self.task.base_priority,
            due_date=self.task.due_date,
            context_id=self.task.context_id,
            state=TaskState.ACTIVE
        )

        # Copy project tags if any
        if self.task.project_tags:
            new_task.project_tags = self.task.project_tags.copy()

        # Open the task form dialog
        dialog = EnhancedTaskFormDialog(task=new_task, db_connection=self.db_connection, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            created_task = dialog.get_updated_task()
            if created_task:
                # Add to our list
                self.created_tasks.append(created_task)
                # Update the list widget
                self._refresh_task_list()

    def _on_edit_task(self, item=None):
        """Edit the selected task."""
        # If item provided (from double-click), use it
        # Otherwise, use the current selection
        if item is None:
            selected_items = self.task_list.selectedItems()
            if not selected_items:
                return
            item = selected_items[0]

        # Get the index of the item
        current_row = self.task_list.row(item)
        if current_row < 0 or current_row >= len(self.created_tasks):
            return

        # Get the task to edit
        task_to_edit = self.created_tasks[current_row]

        # Open the task form dialog for editing
        dialog = EnhancedTaskFormDialog(task=task_to_edit, db_connection=self.db_connection, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            updated_task = dialog.get_updated_task()
            if updated_task:
                # Update in our list
                self.created_tasks[current_row] = updated_task
                # Refresh the display
                self._refresh_task_list()

    def _on_delete_task(self):
        """Delete the selected task from the list."""
        selected_items = self.task_list.selectedItems()
        if not selected_items:
            return

        # Get the index of the selected item
        current_row = self.task_list.row(selected_items[0])
        if current_row < 0 or current_row >= len(self.created_tasks):
            return

        # Confirm deletion
        task_to_delete = self.created_tasks[current_row]
        reply = MessageBox.question(
            self,
            self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
            "Confirm Deletion",
            f"Remove task '{task_to_delete.title}' from the breakdown list?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Remove from our list
            del self.created_tasks[current_row]
            # Refresh the display
            self._refresh_task_list()

    def _refresh_task_list(self):
        """Refresh the task list widget display."""
        self.task_list.clear()
        for task in self.created_tasks:
            # Create a display string with key task info
            display_text = task.title

            # Add priority indicator
            priority_text = {1: "Low", 2: "Medium", 3: "High"}.get(task.base_priority, "")
            if priority_text:
                display_text = f"[{priority_text}] {display_text}"

            # Add due date if set
            if task.due_date:
                display_text = f"{display_text} (Due: {task.due_date})"

            self.task_list.addItem(display_text)

    def _on_confirm_clicked(self):
        """Validate and accept dialog."""
        # Check that at least one task was created
        if len(self.created_tasks) == 0:
            MessageBox.warning(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
                "No Tasks Created",
                "Please create at least one task for the breakdown."
            )
            return

        # Confirm deletion if checkbox is checked
        if self.delete_original_checkbox.isChecked():
            reply = MessageBox.question(
                self,
                self.db_connection.get_connection() if self.db_connection and hasattr(self.db_connection, 'get_connection') else self.db_connection,
                "Confirm Deletion",
                f"Are you sure you want to move '{self.task.title}' to trash?\n\n"
                f"The {len(self.created_tasks)} task(s) will remain active.",
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
                - created_tasks: List[Task] - Complete Task objects
                - delete_original: bool
        """
        return {
            'created_tasks': self.created_tasks,
            'delete_original': self.delete_original_checkbox.isChecked()
        }
