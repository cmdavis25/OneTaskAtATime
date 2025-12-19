"""
Activated Tasks Dialog - Shows tasks that were automatically activated.

Displays a list of tasks that were activated from deferred state,
allowing users to see what became actionable.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List

from ..models.task import Task


class ActivatedTasksDialog(QDialog):
    """
    Dialog showing recently activated tasks.

    Displays tasks that were automatically activated from deferred state,
    showing their title, priority, and due date.
    """

    def __init__(self, task_ids: List[int], db_connection, parent=None):
        """
        Initialize activated tasks dialog.

        Args:
            task_ids: List of task IDs that were activated
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.task_ids = task_ids
        self.db_connection = db_connection
        self.tasks: List[Task] = []

        self._init_ui()
        self._load_tasks()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Tasks Ready to Work")
        self.setMinimumSize(700, 400)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Tasks Activated")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Message
        message_label = QLabel(
            "The following tasks were automatically activated because their start date arrived:"
        )
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignCenter)
        message_label.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(message_label)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(4)
        self.task_table.setHorizontalHeaderLabels([
            "Title", "Priority", "Due Date", "Importance"
        ])
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)

        # Configure column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Due Date
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Importance

        layout.addWidget(self.task_table)

        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _load_tasks(self):
        """Load and display the activated tasks."""
        from ..database.task_dao import TaskDAO
        from ..algorithms.priority import calculate_importance_for_tasks
        from datetime import date

        task_dao = TaskDAO(self.db_connection)

        # Load tasks
        for task_id in self.task_ids:
            task = task_dao.get_by_id(task_id)
            if task:
                self.tasks.append(task)

        # Calculate importance for sorting
        if self.tasks:
            importance_scores = calculate_importance_for_tasks(self.tasks, date.today())

            # Set importance on each task object
            for task in self.tasks:
                task.importance = importance_scores.get(task.id, 0.0)

            # Sort by importance (descending)
            self.tasks.sort(key=lambda t: -t.importance)

        self._populate_table()

    def _populate_table(self):
        """Populate the task table."""
        self.task_table.setRowCount(len(self.tasks))

        priority_labels = {1: "Low", 2: "Medium", 3: "High"}

        for row, task in enumerate(self.tasks):
            # Column 0: Title
            title_item = QTableWidgetItem(task.title)
            title_item.setToolTip(task.description or "")
            self.task_table.setItem(row, 0, title_item)

            # Column 1: Priority
            priority_str = priority_labels.get(task.base_priority, "Medium")
            priority_item = QTableWidgetItem(priority_str)
            self.task_table.setItem(row, 1, priority_item)

            # Column 2: Due Date
            due_date_str = task.due_date.isoformat() if task.due_date else "No due date"
            due_date_item = QTableWidgetItem(due_date_str)
            self.task_table.setItem(row, 2, due_date_item)

            # Column 3: Importance
            importance_str = f"{task.importance:.2f}" if hasattr(task, 'importance') else "N/A"
            importance_item = QTableWidgetItem(importance_str)
            self.task_table.setItem(row, 3, importance_item)

        # Update info label
        self.info_label.setText(
            f"Showing {len(self.tasks)} activated task{'s' if len(self.tasks) != 1 else ''}. "
            f"These are now available in Focus Mode."
        )
