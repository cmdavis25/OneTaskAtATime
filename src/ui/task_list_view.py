"""
Task List View - Comprehensive task management interface

Provides a sortable, filterable table view of all tasks with CRUD operations.
Phase 4: Full task management interface.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QLineEdit, QComboBox, QLabel,
    QMessageBox, QMenu, QCheckBox, QGroupBox, QGridLayout, QShortcut
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QKeySequence
from typing import List, Optional
from datetime import date
from ..models import Task, TaskState
from ..models.recurrence_pattern import RecurrencePattern
from ..database.connection import DatabaseConnection
from ..services.task_service import TaskService
from ..services.task_history_service import TaskHistoryService
from ..database.context_dao import ContextDAO
from ..database.project_tag_dao import ProjectTagDAO
from ..database.dependency_dao import DependencyDAO
from ..database.task_history_dao import TaskHistoryDAO
from ..algorithms.priority import calculate_urgency_for_tasks, calculate_importance
from .task_history_dialog import TaskHistoryDialog


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

        # Initialize task history service
        task_history_dao = TaskHistoryDAO(db_connection.get_connection())
        self.task_history_service = TaskHistoryService(task_history_dao)

        self.tasks: List[Task] = []
        self.contexts = {}  # Map of context_id -> context_name
        self.project_tags = {}  # Map of tag_id -> tag_name
        self.active_context_filters = set()  # Set of active context filter IDs (can include 'NONE')
        self.active_tag_filters = set()  # Set of active project tag filter IDs
        self.hide_tasks_with_dependencies = False  # Filter flag for hiding tasks with dependencies

        # Column configuration
        self.all_columns = {
            "ID": "ID",
            "Recurring": "Recurring",
            "Title": "Title",
            "Dependencies": "Dependencies",
            "Importance": "Importance",
            "Priority": "Priority",
            "Effective Priority": "Effective Priority",
            "Start Date": "Start Date",
            "Due Date": "Due Date",
            "State": "State",
            "Context": "Context",
            "Project Tags": "Project Tags",
            "Delegated To": "Delegated To",
            "Follow-Up Date": "Follow-Up Date"
        }
        self.visible_columns = list(self.all_columns.keys())  # All visible by default
        self.column_indices = {col: idx for idx, col in enumerate(self.visible_columns)}  # Initialize mapping

        self._load_contexts()
        self._load_project_tags()
        self._load_filter_state()
        self._init_ui()
        self._setup_shortcuts()  # Phase 8: Keyboard shortcuts
        self.refresh_tasks()

    def _style_combobox(self, combobox: QComboBox):
        """Apply consistent styling to a QComboBox to show clear dropdown arrow."""
        combobox.setStyleSheet("""
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

    def _format_recurrence_pattern(self, pattern_json: Optional[str]) -> str:
        """
        Convert JSON pattern to human-readable string for tooltip.

        Args:
            pattern_json: JSON string representation of recurrence pattern

        Returns:
            Human-readable description of the pattern
        """
        if not pattern_json:
            return ""

        try:
            pattern = RecurrencePattern.from_json(pattern_json)
            return pattern.to_human_readable()
        except (ValueError, KeyError) as e:
            print(f"Error formatting recurrence pattern: {e}")
            return "Invalid pattern"

    def _init_ui(self):
        """Initialize the user interface."""
        self.setFocusPolicy(Qt.NoFocus)  # Parent should not steal focus from children

        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.setLayout(layout)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("All Tasks")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Manage Columns button
        manage_cols_btn = QPushButton("Manage Columns")
        manage_cols_btn.clicked.connect(self._on_manage_columns)
        header_layout.addWidget(manage_cols_btn)

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
        self.search_box.setMaximumWidth(300)
        self.search_box.setFocusPolicy(Qt.StrongFocus)

        # Fix: Override mousePressEvent to explicitly set focus
        # This works around an issue where QLineEdit doesn't properly gain focus
        self.search_box.mousePressEvent = lambda event: self._search_box_mouse_click(event)

        # Override keyPressEvent to handle up/down arrows for table navigation
        self.search_box.keyPressEvent = lambda event: self._search_box_key_press(event)

        # Restore saved search text (before connecting signal to avoid triggering filter before UI is ready)
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())
            saved_search = settings_dao.get('task_list.search_text', '')
            if saved_search:
                self.search_box.setText(saved_search)
        except Exception:
            pass

        # Connect signal AFTER setting initial text to avoid premature filter calls
        self.search_box.textChanged.connect(self._on_filter_changed)

        filter_layout.addWidget(self.search_box)

        filter_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_tasks)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # State and Context filters
        filters_group = QGroupBox("Filters")
        filters_main_layout = QVBoxLayout()
        filters_main_layout.setSpacing(8)
        filters_main_layout.setContentsMargins(10, 10, 10, 10)

        # State filter checkboxes
        state_filter_layout = QVBoxLayout()
        state_filter_layout.setSpacing(5)

        state_filter_label = QLabel("State:")
        state_filter_label.setStyleSheet("font-weight: bold;")
        state_filter_layout.addWidget(state_filter_label)

        state_checkboxes_layout = QHBoxLayout()
        state_checkboxes_layout.setSpacing(10)

        self.state_checkboxes = {}
        states = [
            ("Active", TaskState.ACTIVE),
            ("Deferred", TaskState.DEFERRED),
            ("Delegated", TaskState.DELEGATED),
            ("Someday/Maybe", TaskState.SOMEDAY),
            ("Completed", TaskState.COMPLETED),
            ("Trash", TaskState.TRASH)
        ]

        # Load saved state filters
        saved_state_filters = None
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())
            saved_state_filters = settings_dao.get('task_list.state_filters', None)
        except Exception:
            pass

        for label, state in states:
            checkbox = QCheckBox(label)
            # Check if we have saved state, otherwise default to all checked
            if saved_state_filters is not None:
                checkbox.setChecked(state.value in saved_state_filters)
            else:
                checkbox.setChecked(True)  # All states shown by default
            checkbox.stateChanged.connect(self._on_filter_changed)
            self.state_checkboxes[state] = checkbox
            state_checkboxes_layout.addWidget(checkbox)

        state_checkboxes_layout.addStretch()
        state_filter_layout.addLayout(state_checkboxes_layout)
        filters_main_layout.addLayout(state_filter_layout)

        # Context filter
        context_filter_container = QVBoxLayout()
        context_filter_container.setSpacing(5)

        context_filter_label = QLabel("Context:")
        context_filter_label.setStyleSheet("font-weight: bold;")
        context_filter_container.addWidget(context_filter_label)

        context_filter_layout = QHBoxLayout()
        context_filter_layout.setSpacing(5)

        self.context_filter_label = QLabel("All Contexts")
        self.context_filter_label.setStyleSheet("padding: 4px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;")
        self.context_filter_label.setMinimumWidth(150)
        context_filter_layout.addWidget(self.context_filter_label)

        context_filter_btn = QPushButton("Manage Filters...")
        context_filter_btn.clicked.connect(self._on_manage_context_filters)
        context_filter_layout.addWidget(context_filter_btn)

        clear_context_btn = QPushButton("Clear Context Filters")
        clear_context_btn.clicked.connect(self._on_clear_context_filters)
        context_filter_layout.addWidget(clear_context_btn)

        context_filter_layout.addStretch()
        context_filter_container.addLayout(context_filter_layout)
        filters_main_layout.addLayout(context_filter_container)

        # Project Tags filter
        tags_filter_container = QVBoxLayout()
        tags_filter_container.setSpacing(5)

        tags_filter_label = QLabel("Project Tags:")
        tags_filter_label.setStyleSheet("font-weight: bold;")
        tags_filter_container.addWidget(tags_filter_label)

        tags_filter_layout = QHBoxLayout()
        tags_filter_layout.setSpacing(5)

        self.tags_filter_label = QLabel("All Project Tags")
        self.tags_filter_label.setStyleSheet("padding: 4px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;")
        self.tags_filter_label.setMinimumWidth(150)
        tags_filter_layout.addWidget(self.tags_filter_label)

        tags_filter_btn = QPushButton("Manage Filters...")
        tags_filter_btn.clicked.connect(self._on_manage_tag_filters)
        tags_filter_layout.addWidget(tags_filter_btn)

        clear_tags_btn = QPushButton("Clear Project Tag Filters")
        clear_tags_btn.clicked.connect(self._on_clear_tag_filters)
        tags_filter_layout.addWidget(clear_tags_btn)

        tags_filter_layout.addStretch()
        tags_filter_container.addLayout(tags_filter_layout)
        filters_main_layout.addLayout(tags_filter_container)

        # Dependencies filter
        dependencies_filter_container = QVBoxLayout()
        dependencies_filter_container.setSpacing(5)

        dependencies_filter_label = QLabel("Dependencies:")
        dependencies_filter_label.setStyleSheet("font-weight: bold;")
        dependencies_filter_container.addWidget(dependencies_filter_label)

        dependencies_filter_layout = QHBoxLayout()
        dependencies_filter_layout.setSpacing(5)

        self.hide_dependencies_checkbox = QCheckBox("Hide tasks with dependencies")
        self.hide_dependencies_checkbox.setToolTip("When checked, tasks that are blocked by other tasks will be hidden")

        # Load saved dependency filter state
        saved_hide_dependencies = False
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())
            saved_hide_dependencies = settings_dao.get('task_list.hide_dependencies', False)
        except Exception:
            pass

        self.hide_dependencies_checkbox.setChecked(saved_hide_dependencies)
        self.hide_tasks_with_dependencies = saved_hide_dependencies
        self.hide_dependencies_checkbox.stateChanged.connect(self._on_dependencies_filter_changed)
        dependencies_filter_layout.addWidget(self.hide_dependencies_checkbox)

        dependencies_filter_layout.addStretch()
        dependencies_filter_container.addLayout(dependencies_filter_layout)
        filters_main_layout.addLayout(dependencies_filter_container)

        filters_group.setLayout(filters_main_layout)
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
        self._style_combobox(self.primary_sort_combo)
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
        self._style_combobox(self.secondary_sort_combo)
        sort_layout.addWidget(self.secondary_sort_combo)

        sort_layout.addStretch()
        layout.addLayout(sort_layout)

        # Task table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(14)
        self.task_table.setHorizontalHeaderLabels([
            "ID", "Recurring", "Title", "Dependencies", "Importance", "Priority", "Effective Priority", "Start Date", "Due Date", "State", "Context", "Project Tags", "Delegated To", "Follow-Up Date"
        ])

        # Configure table appearance
        self.task_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.task_table.setSelectionMode(QTableWidget.SingleSelection)
        self.task_table.setAlternatingRowColors(True)
        self.task_table.setSortingEnabled(False)  # Use custom multi-column sorting

        # Set column widths - use Interactive to allow user resizing
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)  # Allow manual resizing for all columns

        # Set initial column widths
        header.resizeSection(0, 50)   # ID
        header.resizeSection(1, 50)   # Recurring
        header.resizeSection(2, 300)  # Title
        header.resizeSection(3, 100)  # Dependencies
        header.resizeSection(4, 100)  # Importance
        header.resizeSection(5, 80)   # Priority
        header.resizeSection(6, 120)  # Effective Priority
        header.resizeSection(7, 100)  # Start Date
        header.resizeSection(8, 100)  # Due Date
        header.resizeSection(9, 100)  # State
        header.resizeSection(10, 100) # Context
        header.resizeSection(11, 120) # Project Tags
        header.resizeSection(12, 120) # Delegated To
        header.resizeSection(13, 120) # Follow-Up Date

        # Make the last visible column stretch to fill remaining space
        header.setStretchLastSection(True)

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

    def _setup_shortcuts(self):
        """Configure keyboard shortcuts for Task List View (Phase 8)."""
        # Enter key - Edit selected task (only when table has focus, not when editing search box)
        edit_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self.task_table)
        edit_shortcut.activated.connect(self._on_edit_task)

        # Alternative: Enter on numpad
        edit_shortcut_numpad = QShortcut(QKeySequence(Qt.Key_Enter), self.task_table)
        edit_shortcut_numpad.activated.connect(self._on_edit_task)

        # Ctrl+H - View task history
        history_shortcut = QShortcut(QKeySequence("Ctrl+H"), self)
        history_shortcut.activated.connect(self._on_view_task_history)

    def focus_search_box(self):
        """
        Set focus to the search box.

        Called by Ctrl+F shortcut from main window.
        """
        self.search_box.setFocus(Qt.ShortcutFocusReason)
        self.search_box.selectAll()  # Select all text for easy replacement

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
        """Update the context filter label with current filters."""
        self._update_filter_labels()

    def _update_filter_labels(self):
        """Update the filter labels to show active filters."""
        # Update context filter label
        if not self.active_context_filters:
            self.context_filter_label.setText("All Contexts")
        else:
            filter_names = []
            if "NONE" in self.active_context_filters:
                filter_names.append("(No Context)")
            for ctx_id in self.active_context_filters:
                if ctx_id != "NONE" and ctx_id in self.contexts:
                    filter_names.append(self.contexts[ctx_id])
            self.context_filter_label.setText(", ".join(filter_names) if filter_names else "All Contexts")

        # Update tag filter label
        if not self.active_tag_filters:
            self.tags_filter_label.setText("All Project Tags")
        else:
            filter_names = []
            for tag_id in self.active_tag_filters:
                if tag_id in self.project_tags:
                    filter_names.append(self.project_tags[tag_id])
            self.tags_filter_label.setText(", ".join(filter_names) if filter_names else "All Project Tags")

    def _load_filter_state(self):
        """Load saved filter state from settings."""
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())

            # Load context filters
            context_filters = settings_dao.get('task_list.context_filters', [])
            self.active_context_filters = set(context_filters)

            # Load tag filters
            tag_filters = settings_dao.get('task_list.tag_filters', [])
            self.active_tag_filters = set(tag_filters)

            # Load search text
            search_text = settings_dao.get('task_list.search_text', '')
            # Will be applied when UI is initialized

            # Load state filters
            state_filters = settings_dao.get('task_list.state_filters', None)
            # Will be applied when UI is initialized

        except Exception as e:
            print(f"Error loading filter state: {e}")

    def _save_filter_state(self):
        """Save current filter state to settings."""
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())

            # Save context filters
            context_list = []
            for ctx_id in self.active_context_filters:
                if ctx_id == "NONE":
                    context_list.append("NONE")
                else:
                    context_list.append(ctx_id)

            if context_list:
                settings_dao.set('task_list.context_filters', context_list, 'json', 'Task List context filters')
            else:
                settings_dao.delete('task_list.context_filters')

            # Save tag filters
            tag_list = list(self.active_tag_filters)
            if tag_list:
                settings_dao.set('task_list.tag_filters', tag_list, 'json', 'Task List tag filters')
            else:
                settings_dao.delete('task_list.tag_filters')

            # Save search text
            search_text = self.search_box.text()
            if search_text:
                settings_dao.set('task_list.search_text', search_text, 'string', 'Task List search text')
            else:
                settings_dao.delete('task_list.search_text')

            # Save state filters (which checkboxes are checked)
            state_filters = [state.value for state, checkbox in self.state_checkboxes.items() if checkbox.isChecked()]
            settings_dao.set('task_list.state_filters', state_filters, 'json', 'Task List state filters')

            # Save dependency filter
            settings_dao.set('task_list.hide_dependencies', self.hide_tasks_with_dependencies, 'boolean', 'Hide tasks with dependencies')

        except Exception as e:
            print(f"Error saving filter state: {e}")

    def _task_has_dependencies(self, task: Task) -> bool:
        """
        Check if a task has any dependencies (is blocked by other tasks).

        Args:
            task: Task to check

        Returns:
            True if task has dependencies, False otherwise
        """
        if not task.id:
            return False

        try:
            dependency_dao = DependencyDAO(self.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(task.id)
            return len(dependencies) > 0
        except Exception as e:
            print(f"Error checking dependencies for task {task.id}: {e}")
            return False

    def _apply_filters(self):
        """Apply current filters and update the table."""
        # Get filter values
        search_text = self.search_box.text().lower()

        # Get selected states from checkboxes
        selected_states = [
            state for state, checkbox in self.state_checkboxes.items()
            if checkbox.isChecked()
        ]

        # Filter tasks
        filtered_tasks = self.tasks

        # Filter by selected states
        if selected_states:
            filtered_tasks = [t for t in filtered_tasks if t.state in selected_states]

        # Filter by context (if any filters are active)
        if self.active_context_filters:
            filtered_tasks = [
                t for t in filtered_tasks
                if (t.context_id is None and "NONE" in self.active_context_filters) or
                   (t.context_id in self.active_context_filters)
            ]

        # Filter by project tags (if any filters are active)
        if self.active_tag_filters:
            filtered_tasks = [
                t for t in filtered_tasks
                if t.project_tags and any(tag_id in self.active_tag_filters for tag_id in t.project_tags)
            ]

        # Filter by dependencies
        if self.hide_tasks_with_dependencies:
            filtered_tasks = [
                t for t in filtered_tasks
                if not self._task_has_dependencies(t)
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
            # Calculate shared values
            urgency = urgency_scores.get(task.id, 1.0) if task.id else 1.0
            importance = calculate_importance(task, urgency)
            priority_names = {1: "Low", 2: "Medium", 3: "High"}

            # Prepare all column data
            recurring_symbol = "🔁" if task.is_recurring else ""
            recurring_tooltip = self._format_recurrence_pattern(task.recurrence_pattern) if task.is_recurring else ""

            column_data = {
                "ID": (str(task.id), task.id, None),
                "Recurring": (recurring_symbol, None, recurring_tooltip),
                "Title": (task.title, None, None),
                "Dependencies": (self._get_dependencies_str(task), None, None),
                "Importance": (f"{importance:.2f}", importance, None),
                "Priority": (priority_names.get(task.base_priority, "Unknown"), task.base_priority, None),
                "Effective Priority": (f"{task.get_effective_priority():.2f}", task.get_effective_priority(), None),
                "Start Date": (task.start_date.strftime("%Y-%m-%d") if task.start_date else "", task.start_date if task.start_date else date.max, None),
                "Due Date": (task.due_date.strftime("%Y-%m-%d") if task.due_date else "", task.due_date if task.due_date else date.max, None),
                "State": (task.state.value.title(), None, None),
                "Context": (self.contexts.get(task.context_id, "") if task.context_id else "", None, None),
                "Project Tags": (", ".join([self.project_tags.get(tag_id, f"Tag#{tag_id}") for tag_id in task.project_tags]), None, None),
                "Delegated To": (task.delegated_to if task.delegated_to else "", None, None),
                "Follow-Up Date": (task.follow_up_date.strftime("%Y-%m-%d") if task.follow_up_date else "", task.follow_up_date if task.follow_up_date else date.max, None)
            }

            # Populate only visible columns
            for col_name in self.visible_columns:
                if col_name not in column_data:
                    continue

                col_idx = self.column_indices[col_name]
                text, user_data, tooltip = column_data[col_name]

                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                if user_data is not None:
                    item.setData(Qt.UserRole, user_data)

                # Set tooltip if provided
                if tooltip:
                    item.setToolTip(tooltip)

                # Special formatting for Title column
                if col_name == "Title":
                    # Add tooltip showing full title
                    item.setToolTip(task.title)

                # Special formatting for Recurring column
                if col_name == "Recurring":
                    # Center-align the recurring symbol
                    item.setTextAlignment(Qt.AlignCenter)

                # Special formatting for State column
                if col_name == "State":
                    if task.state == TaskState.COMPLETED:
                        item.setBackground(QBrush(QColor("#d4edda")))
                    elif task.state == TaskState.TRASH:
                        item.setBackground(QBrush(QColor("#f8d7da")))
                    elif task.state == TaskState.ACTIVE:
                        item.setBackground(QBrush(QColor("#d1ecf1")))

                # Special formatting for Dependencies column
                if col_name == "Dependencies":
                    if text.startswith("⛔"):
                        # Red foreground for blocked tasks
                        item.setForeground(QBrush(QColor("#dc3545")))
                    else:
                        # Gray for tasks without dependencies
                        item.setForeground(QBrush(QColor("#6c757d")))
                    # Add tooltip showing blocking task titles
                    tooltip = self._get_dependency_tooltip(task)
                    item.setToolTip(tooltip)

                self.task_table.setItem(row, col_idx, item)

    def _get_dependencies_str(self, task: Task) -> str:
        """
        Get dependencies as a formatted string with visual indicator.

        Returns:
            String showing blocking task count with indicator (e.g., "⛔ 2" or "—")
        """
        if not task.id:
            return "—"

        try:
            dependency_dao = DependencyDAO(self.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(task.id)
            blocking_count = len(dependencies)

            if blocking_count > 0:
                return f"⛔ {blocking_count}"
            else:
                return "—"
        except Exception as e:
            print(f"Error loading dependencies for task {task.id}: {e}")
            return "—"

    def _get_dependency_tooltip(self, task: Task) -> str:
        """
        Get tooltip text showing titles of blocking tasks.

        Args:
            task: Task to get dependency info for

        Returns:
            Tooltip string with blocking task titles
        """
        if not task.id:
            return ""

        try:
            from ..database.task_dao import TaskDAO
            dependency_dao = DependencyDAO(self.db_connection.get_connection())
            task_dao = TaskDAO(self.db_connection.get_connection())
            dependencies = dependency_dao.get_dependencies_for_task(task.id)

            if not dependencies:
                return "No dependencies"

            blocking_tasks = []
            for dep in dependencies:
                blocking_task = task_dao.get_by_id(dep.blocking_task_id)
                if blocking_task:
                    blocking_tasks.append(blocking_task.title)

            if blocking_tasks:
                return "Blocked by:\n" + "\n".join(f"• {title}" for title in blocking_tasks)
            else:
                return "Dependencies found but tasks not loaded"

        except Exception as e:
            return f"Error loading dependencies: {e}"

    def _on_filter_changed(self):
        """Handle filter changes."""
        self._save_filter_state()
        self._apply_filters()

    def _on_dependencies_filter_changed(self):
        """Handle dependencies filter checkbox change."""
        self.hide_tasks_with_dependencies = self.hide_dependencies_checkbox.isChecked()
        self._save_filter_state()
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
                # Record task creation in history
                self.task_history_service.record_task_created(created_task)
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
                # Store old task for history comparison
                old_task = self.task_service.get_task_by_id(task_id)
                self.task_service.update_task(updated_task)
                # Record task edit in history
                if old_task:
                    self.task_history_service.record_task_edited(updated_task, old_task)
                self.refresh_tasks()
                self.task_updated.emit(task_id)

    def _on_view_dependency_graph(self):
        """Handle view dependency graph action."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a task to view dependencies.")
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task = self.task_service.get_task_by_id(task_id)

        if not task:
            QMessageBox.warning(self, "Error", "Task not found.")
            return

        from .dependency_graph_view import DependencyGraphView

        graph_view = DependencyGraphView(task, self.db_connection, self)
        graph_view.exec_()

    def _on_view_task_history(self):
        """Handle view task history action."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a task to view its history.")
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task = self.task_service.get_task_by_id(task_id)

        if not task:
            QMessageBox.warning(self, "Error", "Task not found.")
            return

        history_dialog = TaskHistoryDialog(task, self.task_history_service, self)
        history_dialog.exec_()

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

    def _on_change_state_active(self):
        """Handle change task state to Active."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        self.task_service.activate_task(task_id)
        self.refresh_tasks()
        self.task_updated.emit(task_id)

    def _on_change_state_deferred(self):
        """Handle change task state to Deferred."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task = self.task_service.get_task_by_id(task_id)

        if not task:
            QMessageBox.warning(self, "Error", "Task not found.")
            return

        from .postpone_dialog import DeferDialog

        dialog = DeferDialog(task.title, task, self.db_connection, self)
        if dialog.exec_():
            result = dialog.get_result()
            if result:
                self.task_service.defer_task(
                    task_id,
                    result['start_date'],
                    result.get('reason'),
                    result.get('notes')
                )
                self.refresh_tasks()
                self.task_updated.emit(task_id)

    def _on_change_state_delegated(self):
        """Handle change task state to Delegated."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        task = self.task_service.get_task_by_id(task_id)

        if not task:
            QMessageBox.warning(self, "Error", "Task not found.")
            return

        from .postpone_dialog import DelegateDialog

        dialog = DelegateDialog(task.title, task, self.db_connection, self)
        if dialog.exec_():
            result = dialog.get_result()
            if result:
                self.task_service.delegate_task(
                    task_id,
                    result['delegated_to'],
                    result['follow_up_date'],
                    result.get('notes')
                )
                self.refresh_tasks()
                self.task_updated.emit(task_id)

    def _on_change_state_someday(self):
        """Handle change task state to Someday/Maybe."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        self.task_service.move_to_someday(task_id)
        self.refresh_tasks()
        self.task_updated.emit(task_id)

    def _on_change_state_completed(self):
        """Handle change task state to Completed."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        self.task_service.complete_task(task_id)
        self.refresh_tasks()
        self.task_updated.emit(task_id)

    def _on_change_state_trash(self):
        """Handle change task state to Trash."""
        current_row = self.task_table.currentRow()
        if current_row < 0:
            return

        task_id = self.task_table.item(current_row, 0).data(Qt.UserRole)
        self.task_service.move_to_trash(task_id)
        self.refresh_tasks()
        self.task_updated.emit(task_id)

    def _on_manage_context_filters(self):
        """Open the context filter management dialog."""
        from .context_filter_dialog import ContextFilterDialog

        dialog = ContextFilterDialog(
            active_filter_ids=self.active_context_filters,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            # Update active filters
            self.active_context_filters = dialog.get_active_filter_ids()
            # Update label and apply filters
            self._update_filter_labels()
            self._save_filter_state()
            self._apply_filters()

    def _on_manage_tag_filters(self):
        """Open the project tag filter management dialog."""
        from .project_tag_filter_dialog import ProjectTagFilterDialog

        dialog = ProjectTagFilterDialog(
            active_filter_ids=self.active_tag_filters,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            # Update active filters
            self.active_tag_filters = dialog.get_active_filter_ids()
            # Update label and apply filters
            self._update_filter_labels()
            self._save_filter_state()
            self._apply_filters()

    def _on_clear_context_filters(self):
        """Clear all active context filters."""
        self.active_context_filters.clear()
        self._update_filter_labels()
        self._save_filter_state()
        self._apply_filters()

    def _on_clear_tag_filters(self):
        """Clear all active project tag filters."""
        self.active_tag_filters.clear()
        self._update_filter_labels()
        self._save_filter_state()
        self._apply_filters()

    def _on_manage_columns(self):
        """Open the column manager dialog."""
        from .column_manager_dialog import ColumnManagerDialog

        dialog = ColumnManagerDialog(
            visible_columns=self.visible_columns,
            all_columns=self.all_columns,
            parent=self
        )

        if dialog.exec_():
            # Update visible columns with new configuration
            self.visible_columns = dialog.get_visible_columns()
            self._update_column_visibility()

    def _update_column_visibility(self):
        """Update table columns based on visible_columns configuration."""
        # Update column count and headers
        self.task_table.setColumnCount(len(self.visible_columns))
        self.task_table.setHorizontalHeaderLabels([
            self.all_columns[col] for col in self.visible_columns
        ])

        # Update column indices mapping
        self.column_indices = {col: idx for idx, col in enumerate(self.visible_columns)}

        # Configure column resize modes - allow user resizing
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)

        # Set initial widths for each visible column
        default_widths = {
            "ID": 50,
            "Title": 300,
            "Dependencies": 100,
            "Importance": 100,
            "Priority": 80,
            "Effective Priority": 120,
            "Start Date": 100,
            "Due Date": 100,
            "State": 100,
            "Context": 100,
            "Project Tags": 120,
            "Delegated To": 120,
            "Follow-Up Date": 120
        }
        for idx, col in enumerate(self.visible_columns):
            width = default_widths.get(col, 100)
            header.resizeSection(idx, width)

        # Make the last visible column stretch to fill remaining space
        header.setStretchLastSection(True)

        # Refresh the table data
        self._apply_filters()

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

        # Add dependency graph option
        graph_action = menu.addAction("📊 View Dependency Graph")
        graph_action.triggered.connect(self._on_view_dependency_graph)

        # Add task history option
        history_action = menu.addAction("📜 View History")
        history_action.setShortcut("Ctrl+H")
        history_action.triggered.connect(self._on_view_task_history)

        menu.addSeparator()

        # Add Change State submenu
        state_menu = menu.addMenu("Change State")

        active_action = state_menu.addAction("Active")
        active_action.triggered.connect(self._on_change_state_active)

        deferred_action = state_menu.addAction("Deferred...")
        deferred_action.triggered.connect(self._on_change_state_deferred)

        delegated_action = state_menu.addAction("Delegated...")
        delegated_action.triggered.connect(self._on_change_state_delegated)

        someday_action = state_menu.addAction("Someday/Maybe")
        someday_action.triggered.connect(self._on_change_state_someday)

        state_menu.addSeparator()

        completed_action = state_menu.addAction("Completed")
        completed_action.triggered.connect(self._on_change_state_completed)

        trash_action = state_menu.addAction("Trash")
        trash_action.triggered.connect(self._on_change_state_trash)

        menu.addSeparator()

        delete_action = menu.addAction("Delete Task")
        delete_action.triggered.connect(self._on_delete_task)

        menu.exec_(self.task_table.viewport().mapToGlobal(position))

    def _search_box_mouse_click(self, event):
        """
        Handle mouse click on search box.

        Explicitly sets focus when clicked to work around focus issue.
        """
        # Set focus explicitly
        self.search_box.setFocus(Qt.MouseFocusReason)
        # Call original handler for cursor positioning, selection, etc.
        QLineEdit.mousePressEvent(self.search_box, event)

    def _search_box_key_press(self, event):
        """
        Handle key press in search box.

        Intercepts up/down arrow keys to navigate the task table even when
        the search box has focus. All other keys are handled normally.
        """
        key = event.key()

        # Check if it's an up or down arrow key
        if key == Qt.Key_Up or key == Qt.Key_Down:
            # Forward the event to the task table
            self.task_table.keyPressEvent(event)
        else:
            # Normal search box behavior for all other keys
            QLineEdit.keyPressEvent(self.search_box, event)
