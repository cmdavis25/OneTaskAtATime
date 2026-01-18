"""
Review Deferred/Postponed Tasks Dialog - Prompts users to review non-active tasks.

Shown when Focus Mode has no available tasks. Allows users to review and
activate deferred or postponed tasks that might be ready to work on.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Set
from datetime import date
from ..models.task import Task
from ..models.enums import TaskState
from ..database.connection import DatabaseConnection
from ..services.task_service import TaskService
from ..algorithms.priority import calculate_importance_for_tasks
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ReviewDeferredDialog(QDialog, GeometryMixin):
    """
    Dialog for reviewing deferred and postponed tasks.

    Displays tasks that are not currently active but could be activated,
    sorted by importance (Priority × Urgency). Allows users to activate
    selected tasks to make them actionable in Focus Mode.
    """

    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the review dialog.

        Args:
            db_connection: Database connection instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.task_service = TaskService(db_connection)
        self.reviewable_tasks: List[Task] = []
        self.selected_task_ids: Set[int] = set()

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=900, default_height=600)

        self._init_ui()
        self._load_tasks()

    def refresh(self):
        """Refresh the task list (alias for load_tasks)."""
        self._load_tasks()

    def load_tasks(self):
        """Load tasks (alias for _load_tasks)."""
        self._load_tasks()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Review Deferred/Postponed Tasks")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("No Active Tasks Available")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Message
        message_label = QLabel(
            "You have deferred or postponed tasks that may be ready to work on.\n"
            "Review the tasks below and activate any that you'd like to make actionable."
        )
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(message_label)

        # Task table (also create task_list alias for tests)
        self.task_table = QTableWidget()

        # Create a wrapper class that provides both QTableWidget and QListWidget-like interface
        class TaskListWrapper:
            def __init__(self, table):
                self._table = table

            def count(self):
                """QListWidget-compatible method."""
                return self._table.rowCount()

            def rowCount(self):
                """QTableWidget method."""
                return self._table.rowCount()

            def setCurrentRow(self, row):
                """QListWidget-compatible method."""
                self._table.setCurrentCell(row, 0)

            def __getattr__(self, name):
                """Forward all other attributes to the table."""
                return getattr(self._table, name)

        self.task_list = TaskListWrapper(self.task_table)  # Alias with wrapper for test compatibility
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels([
            "Select", "Title", "State", "Priority", "Due Date", "Start Date"
        ])
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)

        # Configure column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # State
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Due Date
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Start Date

        layout.addWidget(self.task_table)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.activate_button = QPushButton("Activate Selected Tasks")
        self.activate_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.activate_button.clicked.connect(self._on_activate_clicked)
        button_layout.addWidget(self.activate_button)

        self.close_button = QPushButton("Close")
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 11pt;
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.close_button.clicked.connect(self.reject)
        button_layout.addWidget(self.close_button)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def _load_tasks(self):
        """Load deferred and postponed tasks, sorted by importance."""
        # Get tasks in DEFERRED state
        deferred_tasks = self.task_service.get_tasks_by_state(TaskState.DEFERRED)

        # Combine all reviewable tasks
        self.reviewable_tasks = deferred_tasks

        # Calculate importance scores for all tasks
        if self.reviewable_tasks:
            importance_scores = calculate_importance_for_tasks(self.reviewable_tasks)

            # Sort by importance (Priority × Urgency) - highest first
            self.reviewable_tasks.sort(
                key=lambda t: importance_scores.get(t.id, 0.0),
                reverse=True
            )

        # Populate table
        self._populate_table()

        # Update info label
        if not self.reviewable_tasks:
            self.info_label.setText("No deferred or postponed tasks found.")
        else:
            self.info_label.setText(
                f"Showing {len(self.reviewable_tasks)} task(s) sorted by importance (Priority × Urgency)."
            )

    def _populate_table(self):
        """Populate the table with tasks."""
        self.task_table.setRowCount(len(self.reviewable_tasks))

        for row, task in enumerate(self.reviewable_tasks):
            # Checkbox for selection
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.task_table.setItem(row, 0, checkbox_item)

            # Title
            title_item = QTableWidgetItem(task.title)
            self.task_table.setItem(row, 1, title_item)

            # State
            state_item = QTableWidgetItem(task.state.value.capitalize())
            state_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 2, state_item)

            # Priority (show effective priority)
            priority_value = task.get_effective_priority()
            priority_text = f"{priority_value:.2f}"
            priority_item = QTableWidgetItem(priority_text)
            priority_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 3, priority_item)

            # Due Date
            due_date_text = task.due_date.strftime('%Y-%m-%d') if task.due_date else ""
            due_date_item = QTableWidgetItem(due_date_text)
            due_date_item.setTextAlignment(Qt.AlignCenter)
            self.task_table.setItem(row, 4, due_date_item)

            # Start Date
            start_date_text = task.start_date.strftime('%Y-%m-%d') if task.start_date else ""
            start_date_item = QTableWidgetItem(start_date_text)
            start_date_item.setTextAlignment(Qt.AlignCenter)
            # Highlight if start date hasn't arrived yet
            if task.start_date and task.start_date > date.today():
                start_date_item.setBackground(Qt.yellow)
                start_date_item.setToolTip("Start date has not arrived yet")
            self.task_table.setItem(row, 5, start_date_item)

    def _on_activate_clicked(self):
        """Handle activate button click."""
        # Collect selected tasks
        selected_tasks = []
        for row in range(self.task_table.rowCount()):
            checkbox_item = self.task_table.item(row, 0)
            if checkbox_item.checkState() == Qt.Checked:
                task = self.reviewable_tasks[row]
                selected_tasks.append(task)

        if not selected_tasks:
            MessageBox.information(
                self,
                self.db_connection.get_connection(),
                "No Selection",
                "Please select at least one task to activate.",
                QMessageBox.Ok
            )
            return

        # Confirm activation
        task_titles = "\n".join([f"• {task.title}" for task in selected_tasks[:5]])
        if len(selected_tasks) > 5:
            task_titles += f"\n... and {len(selected_tasks) - 5} more"

        # Check if any selected tasks have future start dates
        future_dated = [t for t in selected_tasks if t.start_date and t.start_date > date.today()]
        warning_text = ""
        if future_dated:
            warning_text = (
                f"\n\nNote: {len(future_dated)} task(s) have start dates in the future. "
                "Activating them will make them available immediately."
            )

        reply = MessageBox.question(
            self,
            self.db_connection.get_connection(),
            "Activate Tasks",
            f"Activate {len(selected_tasks)} task(s)?{warning_text}\n\n{task_titles}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            # Activate each selected task
            activated_count = 0
            for task in selected_tasks:
                if task.id is not None:
                    result = self.task_service.activate_task(task.id)
                    if result:
                        activated_count += 1

            # Show success message
            MessageBox.information(
                self,
                self.db_connection.get_connection(),
                "Tasks Activated",
                f"Successfully activated {activated_count} task(s).\n\n"
                "They are now available in Focus Mode.",
                QMessageBox.Ok
            )

            # Close dialog
            self.accept()

    def get_activated_count(self) -> int:
        """
        Get the number of tasks that were activated.

        Returns:
            Count of activated tasks
        """
        return len(self.selected_task_ids)
