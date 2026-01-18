"""
Review Delegated Tasks Dialog

Allows users to review delegated tasks that have reached their follow-up date.
Provides actions to activate, complete, extend, or re-delegate tasks.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView, QInputDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Set
from datetime import date, timedelta

from ..models.task import Task, TaskState
from ..services.task_service import TaskService
from ..algorithms.priority import calculate_importance_for_tasks
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ReviewDelegatedDialog(QDialog, GeometryMixin):
    """
    Dialog for reviewing delegated tasks needing follow-up.

    Displays delegated tasks whose follow_up_date has arrived,
    sorted by how overdue they are. Allows users to take actions
    on selected tasks.
    """

    def __init__(self, db_connection: sqlite3.Connection, tasks: List[Task] = None, parent=None):
        """
        Initialize the review dialog.

        Args:
            db_connection: Database connection instance
            tasks: Optional list of tasks to review (if None, will fetch from DB)
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.task_service = TaskService(db_connection)
        self.reviewable_tasks: List[Task] = tasks or []
        self.selected_task_ids: Set[int] = set()

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=1000, default_height=600)

        self._init_ui()
        if not tasks:
            self._load_tasks()
        else:
            self._populate_table()

    def refresh(self):
        """Refresh the task list (alias for load_tasks)."""
        self._load_tasks()

    def load_tasks(self):
        """Load tasks (alias for _load_tasks)."""
        self._load_tasks()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Review Delegated Tasks")
        self.setMinimumSize(1000, 600)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog displays delegated tasks that have reached their follow-up date. "
            "Review the tasks and choose actions: Activate (bring back to your list), Complete, "
            "Extend follow-up, or Re-delegate. Click the ? button for help."
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Delegated Tasks Need Follow-up")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Message
        message_label = QLabel(
            "The following delegated tasks have reached their follow-up date.\n"
            "Review them and take appropriate action."
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
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels([
            "Select", "Title", "Delegated To", "Follow-up Date",
            "Days Overdue", "Priority", "Importance"
        ])
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setWhatsThis(
            "List of delegated tasks that have reached their follow-up date. Select tasks using the checkboxes, then choose an action below. Tasks are sorted by how overdue they are."
        )

        # Configure column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Delegated To
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Follow-up Date
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Days Overdue
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Importance

        # Connect checkbox clicks
        self.task_table.cellChanged.connect(self._on_cell_changed)

        layout.addWidget(self.task_table)

        # Info label
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        # Action buttons
        button_layout = QHBoxLayout()

        self.activate_btn = QPushButton("Activate Selected")
        self.activate_btn.setToolTip("Move selected tasks back to Active state")
        self.activate_btn.clicked.connect(self._activate_selected)
        self.activate_btn.setWhatsThis(
            "Move selected delegated tasks back to Active state. Use this when you need to work on the task yourself or follow up directly."
        )
        button_layout.addWidget(self.activate_btn)

        # Create alias for test compatibility
        self.activate_button = self.activate_btn

        self.complete_btn = QPushButton("Mark Complete")
        self.complete_btn.setToolTip("Mark selected tasks as completed")
        self.complete_btn.clicked.connect(self._complete_selected)
        self.complete_btn.setWhatsThis(
            "Mark selected delegated tasks as completed. Use this when the delegated task has been finished successfully."
        )
        button_layout.addWidget(self.complete_btn)

        self.extend_btn = QPushButton("Extend Follow-up")
        self.extend_btn.setToolTip("Reschedule follow-up date for selected tasks")
        self.extend_btn.clicked.connect(self._extend_followup)
        self.extend_btn.setWhatsThis(
            "Reschedule the follow-up date for selected tasks. Use this when more time is needed before checking on the delegated work."
        )
        button_layout.addWidget(self.extend_btn)

        button_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        # Create alias for test compatibility
        self.close_button = self.close_btn

        layout.addLayout(button_layout)

    def _load_tasks(self):
        """Load delegated tasks from database."""
        from ..database.task_dao import TaskDAO

        task_dao = TaskDAO(self.db_connection)
        current_date = date.today()

        # Get delegated tasks needing follow-up
        self.reviewable_tasks = task_dao.get_delegated_tasks_for_followup(current_date, days_before=0)

        # Calculate importance for sorting
        if self.reviewable_tasks:
            calculate_importance_for_tasks(self.reviewable_tasks, current_date)

            # Sort by follow-up date (earliest/most overdue first)
            self.reviewable_tasks.sort(
                key=lambda t: (
                    t.follow_up_date if t.follow_up_date else date(9999, 12, 31),
                    -t.importance
                )
            )

        self._populate_table()

    def _populate_table(self):
        """Populate the task table with reviewable tasks."""
        self.task_table.setRowCount(len(self.reviewable_tasks))
        self.task_table.blockSignals(True)  # Prevent cellChanged during population

        current_date = date.today()

        for row, task in enumerate(self.reviewable_tasks):
            # Column 0: Select checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.task_table.setItem(row, 0, checkbox_item)

            # Column 1: Title
            title_item = QTableWidgetItem(task.title)
            self.task_table.setItem(row, 1, title_item)

            # Column 2: Delegated To
            delegated_to = task.delegated_to or "N/A"
            delegated_item = QTableWidgetItem(delegated_to)
            self.task_table.setItem(row, 2, delegated_item)

            # Column 3: Follow-up Date
            followup_str = task.follow_up_date.isoformat() if task.follow_up_date else "N/A"
            followup_item = QTableWidgetItem(followup_str)
            self.task_table.setItem(row, 3, followup_item)

            # Column 4: Days Overdue
            if task.follow_up_date:
                days_overdue = (current_date - task.follow_up_date).days
                overdue_item = QTableWidgetItem(str(days_overdue))
                if days_overdue > 0:
                    overdue_item.setForeground(Qt.red)
                self.task_table.setItem(row, 4, overdue_item)
            else:
                self.task_table.setItem(row, 4, QTableWidgetItem("N/A"))

            # Column 5: Priority
            priority_labels = {1: "Low", 2: "Medium", 3: "High"}
            priority_str = priority_labels.get(task.base_priority, "Medium")
            priority_item = QTableWidgetItem(priority_str)
            self.task_table.setItem(row, 5, priority_item)

            # Column 6: Importance
            importance_str = f"{task.importance:.2f}" if hasattr(task, 'importance') else "N/A"
            importance_item = QTableWidgetItem(importance_str)
            self.task_table.setItem(row, 6, importance_item)

        self.task_table.blockSignals(False)
        self._update_info_label()

    def _on_cell_changed(self, row: int, column: int):
        """Handle checkbox state changes."""
        if column == 0:  # Select column
            task = self.reviewable_tasks[row]
            checkbox_item = self.task_table.item(row, 0)

            if checkbox_item.checkState() == Qt.Checked:
                self.selected_task_ids.add(task.id)
            else:
                self.selected_task_ids.discard(task.id)

            self._update_info_label()

    def _update_info_label(self):
        """Update the info label with task counts."""
        total = len(self.reviewable_tasks)
        selected = len(self.selected_task_ids)

        if total == 0:
            self.info_label.setText("No delegated tasks need follow-up")
        else:
            self.info_label.setText(
                f"Showing {total} task(s) needing follow-up. {selected} selected."
            )

    def _activate_selected(self):
        """Activate selected tasks (move to ACTIVE state)."""
        if not self.selected_task_ids:
            MessageBox.information(
                self,
                self.db_connection,
                "No Selection",
                "Please select tasks to activate."
            )
            return

        reply = MessageBox.question(
            self,
            self.db_connection,
            "Confirm Activation",
            f"Activate {len(self.selected_task_ids)} selected task(s)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for task in self.reviewable_tasks:
                if task.id in self.selected_task_ids:
                    task.state = TaskState.ACTIVE
                    task.delegated_to = None
                    task.follow_up_date = None
                    self.task_service.update_task(task)

            MessageBox.information(
                self,
                self.db_connection,
                "Tasks Activated",
                f"Successfully activated {len(self.selected_task_ids)} task(s)."
            )

            self.accept()

    def _complete_selected(self):
        """Mark selected tasks as completed."""
        if not self.selected_task_ids:
            MessageBox.information(
                self,
                self.db_connection,
                "No Selection",
                "Please select tasks to complete."
            )
            return

        reply = MessageBox.question(
            self,
            self.db_connection,
            "Confirm Completion",
            f"Mark {len(self.selected_task_ids)} selected task(s) as complete?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for task in self.reviewable_tasks:
                if task.id in self.selected_task_ids:
                    self.task_service.complete_task(task.id)

            MessageBox.information(
                self,
                self.db_connection,
                "Tasks Completed",
                f"Successfully completed {len(self.selected_task_ids)} task(s)."
            )

            self.accept()

    def _extend_followup(self):
        """Extend follow-up date for selected tasks."""
        if not self.selected_task_ids:
            MessageBox.information(
                self,
                self.db_connection,
                "No Selection",
                "Please select tasks to extend."
            )
            return

        # Ask for number of days to extend
        days, ok = QInputDialog.getInt(
            self,
            "Extend Follow-up",
            "Extend follow-up by how many days?",
            value=7,
            min=1,
            max=365
        )

        if ok:
            for task in self.reviewable_tasks:
                if task.id in self.selected_task_ids:
                    if task.follow_up_date:
                        task.follow_up_date = task.follow_up_date + timedelta(days=days)
                    else:
                        task.follow_up_date = date.today() + timedelta(days=days)

                    self.task_service.update_task(task)

            MessageBox.information(
                self,
                self.db_connection,
                "Follow-up Extended",
                f"Extended follow-up for {len(self.selected_task_ids)} task(s) by {days} days."
            )

            self.accept()
