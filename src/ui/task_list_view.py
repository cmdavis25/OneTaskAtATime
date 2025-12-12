"""
Task List View - Comprehensive task management interface

Provides a sortable, filterable table view of all tasks with CRUD operations.
Phase 4: Full task management interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QLabel,
    QMessageBox, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from typing import List, Optional
from datetime import date
from ..models import Task, TaskState
from ..database.connection import DatabaseConnection
from ..services.task_service import TaskService


class TaskListView(QWidget):
    """
    Task list view with sorting, filtering, and CRUD operations.

    Features:
    - Sortable columns (title, priority, due date, state)
    - Filter by state, context, project tag
    - Search by text
    - Edit, delete, and bulk operations
    - Context menu for quick actions

    Signals:
        task_created: Emitted when a new task is created
        task_updated: Emitted when a task is updated
        task_deleted: Emitted when a task is deleted
    """

    task_created = pyqtSignal(int)  # task_id
    task_updated = pyqtSignal(int)  # task_id
    task_deleted = pyqtSignal(int)  # task_id

    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the task list view.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.task_service = TaskService(db_connection)
        self.tasks: List[Task] = []
        self._init_ui()
        self.refresh_tasks()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("All Tasks")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # New Task button
        new_task_btn = QPushButton("+ New Task")
        new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        new_task_btn.clicked.connect(self._on_new_task)
        header_layout.addWidget(new_task_btn)

        layout.addLayout(header_layout)

        # Filter and search bar
        filter_layout = QHBoxLayout()

        # Search box
        search_label = QLabel("Search:")
        filter_layout.addWidget(search_label)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tasks...")
        self.search_box.textChanged.connect(self._on_filter_changed)
        self.search_box.setMaximumWidth(300)
        filter_layout.addWidget(self.search_box)

        filter_layout.addSpacing(20)

        # State filter
        state_label = QLabel("State:")
        filter_layout.addWidget(state_label)

        self.state_filter = QComboBox()
        self.state_filter.addItem("All States", None)
        self.state_filter.addItem("Active", TaskState.ACTIVE.value)
        self.state_filter.addItem("Deferred", TaskState.DEFERRED.value)
        self.state_filter.addItem("Delegated", TaskState.DELEGATED.value)
        self.state_filter.addItem("Someday/Maybe", TaskState.SOMEDAY.value)
        self.state_filter.addItem("Completed", TaskState.COMPLETED.value)
        self.state_filter.addItem("Trash", TaskState.TRASH.value)
        self.state_filter.currentIndexChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.state_filter)

        filter_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_tasks)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(7)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "Title", "Priority", "Effective Priority", "Due Date", "State", "Context"
        ])

        # Configure table appearance
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(True)

        # Set column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Effective Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Due Date
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # State
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Context

        # Enable context menu
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self._show_context_menu)

        # Double-click to edit
        self.task_table.doubleClicked.connect(self._on_edit_task)

        layout.addWidget(self.task_table)

        # Action buttons
        button_layout = QHBoxLayout()

        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._on_edit_task)
        button_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        delete_btn.clicked.connect(self._on_delete_task)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()

        # Task count label
        self.count_label = QLabel()
        button_layout.addWidget(self.count_label)

        layout.addLayout(button_layout)

    def refresh_tasks(self):
        """Refresh the task list from the database."""
        # Get all tasks
        self.tasks = self.task_service.get_all_tasks()
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters and update the table."""
        # Get filter values
        search_text = self.search_box.text().lower()
        state_filter = self.state_filter.currentData()

        # Filter tasks
        filtered_tasks = self.tasks

        if state_filter:
            filtered_tasks = [t for t in filtered_tasks if t.state.value == state_filter]

        if search_text:
            filtered_tasks = [
                t for t in filtered_tasks
                if search_text in t.title.lower() or
                   (t.description and search_text in t.description.lower())
            ]

        # Update table
        self._populate_table(filtered_tasks)

        # Update count
        self.count_label.setText(f"Showing {len(filtered_tasks)} of {len(self.tasks)} tasks")

    def _populate_table(self, tasks: List[Task]):
        """
        Populate the table with tasks.

        Args:
            tasks: List of tasks to display
        """
        # Disable sorting while populating
        self.task_table.setSortingEnabled(False)

        self.task_table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            # ID
            id_item = QTableWidgetItem(str(task.id))
            id_item.setData(Qt.UserRole, task.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 0, id_item)

            # Title
            title_item = QTableWidgetItem(task.title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 1, title_item)

            # Base Priority
            priority_names = {1: "Low", 2: "Medium", 3: "High"}
            priority_item = QTableWidgetItem(priority_names.get(task.base_priority, "Unknown"))
            priority_item.setData(Qt.UserRole, task.base_priority)
            priority_item.setFlags(priority_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 2, priority_item)

            # Effective Priority
            eff_priority = task.get_effective_priority()
            eff_priority_item = QTableWidgetItem(f"{eff_priority:.2f}")
            eff_priority_item.setData(Qt.UserRole, eff_priority)
            eff_priority_item.setFlags(eff_priority_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 3, eff_priority_item)

            # Due Date
            due_date_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else ""
            due_date_item = QTableWidgetItem(due_date_str)
            due_date_item.setData(Qt.UserRole, task.due_date if task.due_date else date.max)
            due_date_item.setFlags(due_date_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 4, due_date_item)

            # State
            state_item = QTableWidgetItem(task.state.value.title())
            state_item.setFlags(state_item.flags() & ~Qt.ItemIsEditable)

            # Color-code by state
            if task.state == TaskState.COMPLETED:
                state_item.setBackground(QBrush(QColor("#d4edda")))
            elif task.state == TaskState.TRASH:
                state_item.setBackground(QBrush(QColor("#f8d7da")))
            elif task.state == TaskState.ACTIVE:
                state_item.setBackground(QBrush(QColor("#d1ecf1")))

            self.task_table.setItem(row, 5, state_item)

            # Context (placeholder - will be implemented later)
            context_item = QTableWidgetItem("")
            context_item.setFlags(context_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 6, context_item)

        # Re-enable sorting
        self.task_table.setSortingEnabled(True)

    def _on_filter_changed(self):
        """Handle filter changes."""
        self._apply_filters()

    def _on_new_task(self):
        """Handle new task button click."""
        from .task_form_dialog import TaskFormDialog

        dialog = TaskFormDialog(parent=self)
        if dialog.exec_():
            task = dialog.get_updated_task()
            if task:
                created_task = self.task_service.create_task(task)
                self.refresh_tasks()
                self.task_created.emit(created_task.id)

    def _on_edit_task(self):
        """Handle edit task action."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a task to edit.")
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task = self.task_service.get_task_by_id(task_id)

        if not task:
            QMessageBox.warning(self, "Error", "Task not found.")
            return

        from .task_form_dialog import TaskFormDialog

        dialog = TaskFormDialog(task=task, parent=self)
        if dialog.exec_():
            updated_task = dialog.get_updated_task()
            if updated_task:
                self.task_service.update_task(updated_task)
                self.refresh_tasks()
                self.task_updated.emit(task_id)

    def _on_delete_task(self):
        """Handle delete task action."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a task to delete.")
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task_title = self.task_table.item(current_row, 1).text()

        reply = QMessageBox.question(
            self,
            "Delete Task",
            f"Are you sure you want to delete task '{task_title}'?\n\n"
            "This action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.task_service.delete_task(task_id)
            self.refresh_tasks()
            self.task_deleted.emit(task_id)

    def _show_context_menu(self, position):
        """
        Show context menu for right-click on task.

        Args:
            position: Position where right-click occurred
        """
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        menu = QMenu(self)

        edit_action = menu.addAction("Edit Task")
        edit_action.triggered.connect(self._on_edit_task)

        menu.addSeparator()

        delete_action = menu.addAction("Delete Task")
        delete_action.triggered.connect(self._on_delete_task)

        menu.exec_(self.task_table.viewport().mapToGlobal(position))
