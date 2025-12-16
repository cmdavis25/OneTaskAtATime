"""
Task List View - Comprehensive task management interface

Provides a sortable, filterable table view of all tasks with CRUD operations.
Phase 4: Full task management interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QLabel,
    QMessageBox, QMenu, QCheckBox, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from typing import List, Optional
from datetime import date
from ..models import Task, TaskState
from ..database.connection import DatabaseConnection
from ..services.task_service import TaskService
from ..database.context_dao import ContextDAO
from ..database.project_tag_dao import ProjectTagDAO
from ..algorithms.priority import calculate_urgency_for_tasks, calculate_importance


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
        self.contexts = {}  # Map of context_id -> context_name
        self.project_tags = {}  # Map of tag_id -> tag_name
        self._load_contexts()
        self._load_project_tags()
        self._init_ui()
        self.refresh_tasks()

    def _load_contexts(self):
        """Load contexts from database for display."""
        try:
            context_dao = ContextDAO(self.db_connection.get_connection())
            all_contexts = context_dao.get_all()
            self.contexts = {ctx.id: ctx.name for ctx in all_contexts}
        except Exception as e:
            print(f"Error loading contexts: {e}")
            self.contexts = {}

    def _load_project_tags(self):
        """Load project tags from database for display."""
        try:
            tag_dao = ProjectTagDAO(self.db_connection.get_connection())
            all_tags = tag_dao.get_all()
            self.project_tags = {tag.id: tag.name for tag in all_tags}
        except Exception as e:
            print(f"Error loading project tags: {e}")
            self.project_tags = {}

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

        filter_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_tasks)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # State and Context filters
        filters_group = QGroupBox("Filters")
        filters_layout = QGridLayout()
        filters_layout.setSpacing(5)

        # State filter checkboxes
        state_filter_label = QLabel("State:")
        state_filter_label.setStyleSheet("font-weight: bold;")
        filters_layout.addWidget(state_filter_label, 0, 0)

        self.state_checkboxes = {}
        states = [
            ("Active", TaskState.ACTIVE),
            ("Deferred", TaskState.DEFERRED),
            ("Delegated", TaskState.DELEGATED),
            ("Someday/Maybe", TaskState.SOMEDAY),
            ("Completed", TaskState.COMPLETED),
            ("Trash", TaskState.TRASH)
        ]

        for idx, (label, state) in enumerate(states):
            checkbox = QCheckBox(label)
            checkbox.setChecked(True)  # All states shown by default
            checkbox.stateChanged.connect(self._on_filter_changed)
            self.state_checkboxes[state] = checkbox
            # Arrange in 2 rows
            row = (idx // 3) + 1
            col = idx % 3
            filters_layout.addWidget(checkbox, row, col)

        # Context filter
        context_filter_label = QLabel("Context:")
        context_filter_label.setStyleSheet("font-weight: bold;")
        filters_layout.addWidget(context_filter_label, 3, 0)

        self.context_filter_combo = QComboBox()
        self.context_filter_combo.addItem("All Contexts", None)
        self.context_filter_combo.addItem("No Context", "NONE")
        for ctx_id, ctx_name in self.contexts.items():
            self.context_filter_combo.addItem(ctx_name, ctx_id)
        self.context_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filters_layout.addWidget(self.context_filter_combo, 3, 1, 1, 2)

        # Project Tags filter
        tags_filter_label = QLabel("Project Tags:")
        tags_filter_label.setStyleSheet("font-weight: bold;")
        filters_layout.addWidget(tags_filter_label, 4, 0)

        # Create scrollable area for project tag checkboxes
        tags_widget = QWidget()
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(5)
        tags_layout.setContentsMargins(0, 0, 0, 0)

        self.tag_checkboxes = {}
        for tag_id, tag_name in sorted(self.project_tags.items(), key=lambda x: x[1]):
            checkbox = QCheckBox(tag_name)
            checkbox.setChecked(True)  # All tags shown by default
            checkbox.stateChanged.connect(self._on_filter_changed)
            self.tag_checkboxes[tag_id] = checkbox
            tags_layout.addWidget(checkbox)

        tags_layout.addStretch()
        tags_widget.setLayout(tags_layout)
        filters_layout.addWidget(tags_widget, 4, 1, 1, 2)

        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)

        # Sort controls
        sort_layout = QHBoxLayout()
        sort_layout.addWidget(QLabel("Sort by:"))

        self.primary_sort_combo = QComboBox()
        self.primary_sort_combo.addItem("Importance (desc)", ("importance", False))
        self.primary_sort_combo.addItem("Importance (asc)", ("importance", True))
        self.primary_sort_combo.addItem("Effective Priority (desc)", ("eff_priority", False))
        self.primary_sort_combo.addItem("Effective Priority (asc)", ("eff_priority", True))
        self.primary_sort_combo.addItem("Due Date (earliest)", ("due_date", True))
        self.primary_sort_combo.addItem("Due Date (latest)", ("due_date", False))
        self.primary_sort_combo.addItem("State", ("state", True))
        self.primary_sort_combo.addItem("Title", ("title", True))
        self.primary_sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.primary_sort_combo)

        sort_layout.addWidget(QLabel("Then by:"))

        self.secondary_sort_combo = QComboBox()
        self.secondary_sort_combo.addItem("(None)", None)
        self.secondary_sort_combo.addItem("Importance (desc)", ("importance", False))
        self.secondary_sort_combo.addItem("Importance (asc)", ("importance", True))
        self.secondary_sort_combo.addItem("Effective Priority (desc)", ("eff_priority", False))
        self.secondary_sort_combo.addItem("Effective Priority (asc)", ("eff_priority", True))
        self.secondary_sort_combo.addItem("Due Date (earliest)", ("due_date", True))
        self.secondary_sort_combo.addItem("Due Date (latest)", ("due_date", False))
        self.secondary_sort_combo.addItem("State", ("state", True))
        self.secondary_sort_combo.addItem("Title", ("title", True))
        self.secondary_sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self.secondary_sort_combo)

        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(10)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "Title", "Priority", "Effective Priority", "Importance", "Due Date", "Start Date", "State", "Context", "Project Tags"
        ])

        # Configure table appearance
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(False)  # Use custom multi-column sorting

        # Set column widths
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Priority
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Effective Priority
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Importance
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Due Date
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Start Date
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # State
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Context
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Project Tags

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
        # Reload contexts and tags in case they changed
        self._load_contexts()
        self._load_project_tags()
        self._update_context_filter()
        self._apply_filters()

    def _update_context_filter(self):
        """Update the context filter combo with current contexts."""
        current_selection = self.context_filter_combo.currentData()
        self.context_filter_combo.clear()
        self.context_filter_combo.addItem("All Contexts", None)
        self.context_filter_combo.addItem("No Context", "NONE")
        for ctx_id, ctx_name in self.contexts.items():
            self.context_filter_combo.addItem(ctx_name, ctx_id)
        # Try to restore previous selection
        if current_selection is not None:
            for i in range(self.context_filter_combo.count()):
                if self.context_filter_combo.itemData(i) == current_selection:
                    self.context_filter_combo.setCurrentIndex(i)
                    break

    def _apply_filters(self):
        """Apply current filters and update the table."""
        # Get filter values
        search_text = self.search_box.text().lower()

        # Get selected states from checkboxes
        selected_states = [
            state for state, checkbox in self.state_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Get selected context
        context_filter = self.context_filter_combo.currentData()

        # Get selected project tags from checkboxes
        selected_tags = [
            tag_id for tag_id, checkbox in self.tag_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Filter tasks
        filtered_tasks = self.tasks

        # Filter by selected states
        if selected_states:
            filtered_tasks = [t for t in filtered_tasks if t.state in selected_states]

        # Filter by context
        if context_filter == "NONE":
            # Show only tasks with no context
            filtered_tasks = [t for t in filtered_tasks if t.context_id is None]
        elif context_filter is not None:
            # Show only tasks with the selected context
            filtered_tasks = [t for t in filtered_tasks if t.context_id == context_filter]

        # Filter by project tags (show tasks that have at least one selected tag, or no tags if no tags selected)
        if selected_tags:
            filtered_tasks = [
                t for t in filtered_tasks
                if not t.project_tags or any(tag_id in selected_tags for tag_id in t.project_tags)
            ]

        # Filter by search text
        if search_text:
            filtered_tasks = [
                t for t in filtered_tasks
                if search_text in t.title.lower() or
                   (t.description and search_text in t.description.lower())
            ]

        # Apply sorting
        filtered_tasks = self._apply_sorting(filtered_tasks)

        # Update table
        self._populate_table(filtered_tasks)

        # Update count
        self.count_label.setText(f"Showing {len(filtered_tasks)} of {len(self.tasks)} tasks")

    def _apply_sorting(self, tasks: List[Task]) -> List[Task]:
        """
        Apply multi-column sorting to tasks.

        Args:
            tasks: List of tasks to sort

        Returns:
            Sorted list of tasks
        """
        if not tasks:
            return tasks

        # Calculate urgency and importance for all tasks
        urgency_scores = calculate_urgency_for_tasks(tasks)

        # Create a list of (task, sort_keys) tuples
        task_data = []
        for task in tasks:
            urgency = urgency_scores.get(task.id, 1.0) if task.id else 1.0
            importance = calculate_importance(task, urgency)

            # Create sort keys dictionary
            sort_keys = {
                'importance': importance,
                'eff_priority': task.get_effective_priority(),
                'due_date': task.due_date if task.due_date else date.max,
                'start_date': task.start_date if task.start_date else date.max,
                'state': task.state.value,
                'title': task.title.lower()
            }
            task_data.append((task, sort_keys))

        # Get primary and secondary sort criteria
        primary_sort = self.primary_sort_combo.currentData()
        secondary_sort = self.secondary_sort_combo.currentData()

        # Define sort key function
        def sort_key(item):
            task, keys = item
            primary_field, primary_asc = primary_sort

            # Primary sort key
            primary_value = keys[primary_field]
            if not primary_asc:
                # For descending, negate numeric values or reverse strings
                if isinstance(primary_value, (int, float)):
                    primary_value = -primary_value
                elif isinstance(primary_value, str):
                    # For strings, we'll handle in reverse parameter
                    pass

            # Secondary sort key (if specified)
            if secondary_sort:
                secondary_field, secondary_asc = secondary_sort
                secondary_value = keys[secondary_field]
                if not secondary_asc:
                    if isinstance(secondary_value, (int, float)):
                        secondary_value = -secondary_value

                return (primary_value, secondary_value)
            else:
                return (primary_value,)

        # Sort the task data
        sorted_data = sorted(task_data, key=sort_key)

        # Extract just the tasks
        return [task for task, _ in sorted_data]

    def _populate_table(self, tasks: List[Task]):
        """
        Populate the table with tasks.

        Args:
            tasks: List of tasks to display
        """
        self.task_table.setRowCount(len(tasks))

        # Calculate urgency for all tasks (requires normalization across tasks)
        urgency_scores = calculate_urgency_for_tasks(tasks) if tasks else {}

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

            # Importance (Effective Priority × Urgency)
            urgency = urgency_scores.get(task.id, 1.0) if task.id else 1.0
            importance = calculate_importance(task, urgency)
            importance_item = QTableWidgetItem(f"{importance:.2f}")
            importance_item.setData(Qt.UserRole, importance)
            importance_item.setFlags(importance_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 4, importance_item)

            # Due Date
            due_date_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else ""
            due_date_item = QTableWidgetItem(due_date_str)
            due_date_item.setData(Qt.UserRole, task.due_date if task.due_date else date.max)
            due_date_item.setFlags(due_date_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 5, due_date_item)

            # Start Date
            start_date_str = task.start_date.strftime("%Y-%m-%d") if task.start_date else ""
            start_date_item = QTableWidgetItem(start_date_str)
            start_date_item.setData(Qt.UserRole, task.start_date if task.start_date else date.max)
            start_date_item.setFlags(start_date_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 6, start_date_item)

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

            self.task_table.setItem(row, 7, state_item)

            # Context
            context_name = self.contexts.get(task.context_id, "") if task.context_id else ""
            context_item = QTableWidgetItem(context_name)
            context_item.setFlags(context_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 8, context_item)

            # Project Tags
            tag_names = [self.project_tags.get(tag_id, f"Tag#{tag_id}") for tag_id in task.project_tags]
            tags_str = ", ".join(tag_names) if tag_names else ""
            tags_item = QTableWidgetItem(tags_str)
            tags_item.setFlags(tags_item.flags() & ~Qt.ItemIsEditable)
            self.task_table.setItem(row, 9, tags_item)

    def _on_filter_changed(self):
        """Handle filter changes."""
        self._apply_filters()

    def _on_sort_changed(self):
        """Handle sort order changes."""
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
