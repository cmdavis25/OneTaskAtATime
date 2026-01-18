"""
Review Someday/Maybe Tasks Dialog

Allows users to periodically review tasks in Someday/Maybe state.
Provides actions to activate, keep, or trash tasks.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QAbstractItemView
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from typing import List, Set
from datetime import date, datetime

from ..models.task import Task, TaskState
from ..services.task_service import TaskService
from ..services.resurfacing_service import ResurfacingService
from ..algorithms.priority import calculate_importance_for_tasks
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ReviewSomedayDialog(QDialog, GeometryMixin):
    """
    Dialog for reviewing Someday/Maybe tasks.

    Displays all tasks in SOMEDAY state, sorted by effective priority.
    Allows users to activate tasks they're ready to work on, keep tasks
    for future review, or trash tasks that are no longer relevant.
    """

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """
        Initialize the review dialog.

        Args:
            db_connection: Database connection instance
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.task_service = TaskService(db_connection)
        self.resurfacing_service = ResurfacingService(db_connection)
        self.someday_tasks: List[Task] = []
        self.selected_task_ids: Set[int] = set()

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=1000, default_height=600)

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
        self.setWindowTitle("Review Someday/Maybe Tasks")
        self.setMinimumSize(1000, 600)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog lets you review tasks in the Someday/Maybe state. "
            "These tasks aren't currently actionable but should be reviewed periodically. "
            "Activate tasks you're ready to work on, or trash tasks no longer relevant. Click the ? button for help."
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Someday/Maybe Task Review")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Message
        message_label = QLabel(
            "Review your Someday/Maybe tasks. Activate tasks you're ready to work on,\n"
            "or keep them in Someday for future review. Trash tasks that are no longer relevant."
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
            "Select", "Title", "Priority", "Effective Priority",
            "Tags", "Days Since Created", "Last Resurfaced"
        ])
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setWhatsThis(
            "List of all Someday/Maybe tasks. These tasks aren't currently actionable but should be reviewed periodically. Select tasks using checkboxes, then choose an action below."
        )

        # Configure column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Select
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Effective Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Tags
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Days Since Created
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Last Resurfaced

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
        self.activate_btn.setToolTip("Move selected tasks to Active state")
        self.activate_btn.clicked.connect(self._activate_selected)
        self.activate_btn.setWhatsThis(
            "Move selected Someday/Maybe tasks to Active state. Use this when you're ready to work on these tasks."
        )
        button_layout.addWidget(self.activate_btn)

        # Create alias for test compatibility
        self.activate_button = self.activate_btn

        self.trash_btn = QPushButton("Move to Trash")
        self.trash_btn.setToolTip("Move selected tasks to Trash")
        self.trash_btn.clicked.connect(self._trash_selected)
        self.trash_btn.setWhatsThis(
            "Move selected tasks to Trash. Use this for tasks that are no longer relevant or needed."
        )
        button_layout.addWidget(self.trash_btn)

        # Create alias for test compatibility (trash_button or delete_button)
        self.trash_button = self.trash_btn
        self.delete_button = self.trash_btn

        button_layout.addStretch()

        self.keep_btn = QPushButton("Keep in Someday")
        self.keep_btn.setToolTip("Keep tasks in Someday/Maybe for future review")
        self.keep_btn.clicked.connect(self._keep_in_someday)
        self.keep_btn.setWhatsThis(
            "Keep all tasks in Someday/Maybe state for future review. This resets the review timer so you'll be reminded again later."
        )
        button_layout.addWidget(self.keep_btn)

        # Create alias for test compatibility
        self.close_button = self.keep_btn

        layout.addLayout(button_layout)

    def _load_tasks(self):
        """Load someday tasks from database."""
        # Get all someday tasks
        self.someday_tasks = self.resurfacing_service.get_someday_tasks()

        # Calculate effective priority for sorting
        if self.someday_tasks:
            current_date = date.today()

            # For someday tasks, urgency is not as relevant (no due dates typically)
            # But we'll calculate importance anyway for sorting by effective priority
            calculate_importance_for_tasks(self.someday_tasks, current_date)

            # Sort by effective priority (descending)
            self.someday_tasks.sort(
                key=lambda t: -t.importance if hasattr(t, 'importance') else 0
            )

        self._populate_table()

    def _populate_table(self):
        """Populate the task table with someday tasks."""
        self.task_table.setRowCount(len(self.someday_tasks))
        self.task_table.blockSignals(True)  # Prevent cellChanged during population

        current_date = date.today()

        for row, task in enumerate(self.someday_tasks):
            # Column 0: Select checkbox
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            checkbox_item.setCheckState(Qt.Unchecked)
            self.task_table.setItem(row, 0, checkbox_item)

            # Column 1: Title
            title_item = QTableWidgetItem(task.title)
            self.task_table.setItem(row, 1, title_item)

            # Column 2: Priority
            priority_labels = {1: "Low", 2: "Medium", 3: "High"}
            priority_str = priority_labels.get(task.base_priority, "Medium")
            priority_item = QTableWidgetItem(priority_str)
            self.task_table.setItem(row, 2, priority_item)

            # Column 3: Effective Priority
            effective_priority = task.effective_priority if hasattr(task, 'effective_priority') else task.base_priority
            effective_item = QTableWidgetItem(f"{effective_priority:.2f}")
            self.task_table.setItem(row, 3, effective_item)

            # Column 4: Tags
            tags_str = ", ".join([str(tag_id) for tag_id in task.project_tags]) if task.project_tags else "None"
            tags_item = QTableWidgetItem(tags_str)
            self.task_table.setItem(row, 4, tags_item)

            # Column 5: Days Since Created
            if task.created_at:
                if isinstance(task.created_at, str):
                    created_at = datetime.fromisoformat(task.created_at)
                else:
                    created_at = task.created_at

                days_since_created = (datetime.now() - created_at).days
                days_item = QTableWidgetItem(str(days_since_created))
                self.task_table.setItem(row, 5, days_item)
            else:
                self.task_table.setItem(row, 5, QTableWidgetItem("N/A"))

            # Column 6: Last Resurfaced
            if task.last_resurfaced_at:
                if isinstance(task.last_resurfaced_at, str):
                    last_resurfaced = datetime.fromisoformat(task.last_resurfaced_at)
                else:
                    last_resurfaced = task.last_resurfaced_at

                days_since_resurfaced = (datetime.now() - last_resurfaced).days
                resurfaced_str = f"{days_since_resurfaced} days ago"
            else:
                resurfaced_str = "Never"

            resurfaced_item = QTableWidgetItem(resurfaced_str)
            self.task_table.setItem(row, 6, resurfaced_item)

        self.task_table.blockSignals(False)
        self._update_info_label()

    def _on_cell_changed(self, row: int, column: int):
        """Handle checkbox state changes."""
        if column == 0:  # Select column
            task = self.someday_tasks[row]
            checkbox_item = self.task_table.item(row, 0)

            if checkbox_item.checkState() == Qt.Checked:
                self.selected_task_ids.add(task.id)
            else:
                self.selected_task_ids.discard(task.id)

            self._update_info_label()

    def _update_info_label(self):
        """Update the info label with task counts."""
        total = len(self.someday_tasks)
        selected = len(self.selected_task_ids)

        if total == 0:
            self.info_label.setText("No Someday/Maybe tasks to review")
        else:
            self.info_label.setText(
                f"Showing {total} Someday/Maybe task(s). {selected} selected."
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
            for task in self.someday_tasks:
                if task.id in self.selected_task_ids:
                    task.state = TaskState.ACTIVE
                    self.task_service.update_task(task)

            MessageBox.information(
                self,
                self.db_connection,
                "Tasks Activated",
                f"Successfully activated {len(self.selected_task_ids)} task(s)."
            )

            # Update review timestamp
            self.resurfacing_service.update_someday_review_timestamp()

            self.accept()

    def _trash_selected(self):
        """Move selected tasks to trash."""
        if not self.selected_task_ids:
            MessageBox.information(
                self,
                self.db_connection,
                "No Selection",
                "Please select tasks to trash."
            )
            return

        reply = MessageBox.question(
            self,
            self.db_connection,
            "Confirm Trash",
            f"Move {len(self.selected_task_ids)} selected task(s) to trash?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            for task in self.someday_tasks:
                if task.id in self.selected_task_ids:
                    task.state = TaskState.TRASH
                    self.task_service.update_task(task)

            MessageBox.information(
                self,
                self.db_connection,
                "Tasks Trashed",
                f"Successfully moved {len(self.selected_task_ids)} task(s) to trash."
            )

            # Update review timestamp
            self.resurfacing_service.update_someday_review_timestamp()

            self.accept()

    def _keep_in_someday(self):
        """Keep tasks in Someday/Maybe state (close dialog)."""
        # Update review timestamp to reset the review interval
        self.resurfacing_service.update_someday_review_timestamp()

        self.accept()
