"""
Focus Mode Widget - Core single-task display for OneTaskAtATime.

Displays one task at a time with action buttons for completing, deferring,
delegating, or moving tasks to different states.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QMessageBox, QGroupBox, QShortcut, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QKeySequence, QCursor
from typing import Optional, Set
from ..models.task import Task
from ..models.enums import TaskState
from ..database.connection import DatabaseConnection
from .message_box import MessageBox


class FocusModeWidget(QWidget):
    """
    Widget that displays a single task with action buttons.

    This is the core UI component of OneTaskAtATime - the focused,
    distraction-free task display.

    Signals:
        task_completed: Emitted when Complete button clicked
        task_deferred: Emitted when Defer button clicked
        task_delegated: Emitted when Delegate button clicked
        task_someday: Emitted when Someday button clicked
        task_trashed: Emitted when Trash button clicked
        task_refreshed: Emitted when user requests to refresh the displayed task
    """

    # Signals for task actions
    task_completed = pyqtSignal(int)  # task_id
    task_deferred = pyqtSignal(int)   # task_id
    task_delegated = pyqtSignal(int)  # task_id
    task_someday = pyqtSignal(int)    # task_id
    task_trashed = pyqtSignal(int)    # task_id
    task_refreshed = pyqtSignal()
    task_created = pyqtSignal(int)    # task_id - Emitted when new task is created
    filters_changed = pyqtSignal()    # Emitted when filters change

    def __init__(self, db_connection: DatabaseConnection, parent=None, test_mode: bool = False):
        """Initialize the Focus Mode widget.

        Args:
            db_connection: Database connection for loading contexts and tags
            parent: Parent widget
            test_mode: If True, skip confirmation dialogs for automated testing
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.test_mode = test_mode
        self._current_task: Optional[Task] = None
        self.active_context_filter: Optional[int] = None  # Single context ID or None
        self.active_tag_filters: Set[int] = set()  # Set of tag IDs
        self.contexts = {}  # Map of context_id -> context_name
        self.project_tags = {}  # Map of tag_id -> tag_name

        self._load_contexts()
        self._load_project_tags()
        self._load_filter_state()
        self._init_ui()
        self._setup_shortcuts()  # Phase 8: Keyboard shortcuts

    def _load_contexts(self):
        """Load contexts from database for filter options."""
        try:
            from ..database.context_dao import ContextDAO
            context_dao = ContextDAO(self.db_connection.get_connection())
            all_contexts = context_dao.get_all()
            self.contexts = {ctx.id: ctx.name for ctx in all_contexts}
        except Exception as e:
            print(f"Error loading contexts: {e}")
            self.contexts = {}

    def _load_project_tags(self):
        """Load project tags from database for filter options."""
        try:
            from ..database.project_tag_dao import ProjectTagDAO
            tag_dao = ProjectTagDAO(self.db_connection.get_connection())
            all_tags = tag_dao.get_all()
            self.project_tags = {tag.id: tag.name for tag in all_tags}
        except Exception as e:
            print(f"Error loading project tags: {e}")
            self.project_tags = {}

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 20, 40, 40)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Set WhatsThis help for the entire Focus Mode widget
        self.setWhatsThis(
            "Focus Mode displays ONE task at a time - your highest-priority task. "
            "This eliminates decision fatigue and helps you concentrate on what truly matters. "
            "Use the action buttons to complete, defer, delegate, or otherwise handle the current task. "
            "Press Shift+F1 and click on any element for specific help."
        )

        # Filter section
        self._create_filter_section(layout)

        # New Task button - centered after filters
        new_task_layout = QHBoxLayout()
        new_task_layout.addStretch()

        new_task_button_style = """
            QPushButton {
                background-color: #5b2c6f;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #4a2359;
            }
            QPushButton:pressed {
                background-color: #3d1d4a;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """

        self.new_task_btn = QPushButton("+ New Task (Ctrl+N)")
        self.new_task_btn.setStyleSheet(new_task_button_style)
        self.new_task_btn.clicked.connect(self._on_new_task)
        self.new_task_btn.setWhatsThis(
            "Create a new task. This opens the task form where you can enter all task details including "
            "title, description, priority, due date, and other attributes."
        )
        new_task_layout.addWidget(self.new_task_btn)

        new_task_layout.addStretch()
        layout.addLayout(new_task_layout)

        # Subtitle between filters and task card
        subtitle_label = QLabel("Your highest priority task right now")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setObjectName("subtitleLabel")
        layout.addWidget(subtitle_label)

        # Task card (fixed position at top)
        self._create_task_card(layout)

        # Add stretch to push buttons to bottom
        layout.addStretch()

        # Action buttons
        self._create_action_buttons(layout)

        # Show empty state initially
        self._show_empty_state()

    def _create_filter_section(self, layout: QVBoxLayout):
        """Create the filter controls section."""
        filters_group = QGroupBox("Filters")
        filters_layout = QVBoxLayout()
        filters_layout.setSpacing(8)
        filters_layout.setContentsMargins(10, 10, 10, 10)

        # Context filter (single selection)
        context_filter_layout = QHBoxLayout()
        context_filter_layout.setSpacing(5)

        context_label = QLabel("Context:")
        context_label.setStyleSheet("font-weight: bold;")
        context_label.setMinimumWidth(100)
        context_filter_layout.addWidget(context_label)

        self.context_filter_label = QLabel("All Contexts")
        self.context_filter_label.setStyleSheet("padding: 4px; border-radius: 4px;")
        self.context_filter_label.setMinimumWidth(150)
        context_filter_layout.addWidget(self.context_filter_label)

        context_select_btn = QPushButton("Select...")
        context_select_btn.clicked.connect(self._on_select_context_filter)
        context_select_btn.setWhatsThis(
            "Choose a specific context to filter tasks. Only tasks matching the selected context "
            "(e.g., @computer, @phone) will be shown in Focus Mode."
        )
        context_filter_layout.addWidget(context_select_btn)

        clear_context_btn = QPushButton("Clear")
        clear_context_btn.clicked.connect(self._on_clear_context_filter)
        clear_context_btn.setWhatsThis(
            "Remove the context filter to show tasks from all contexts."
        )
        context_filter_layout.addWidget(clear_context_btn)

        context_filter_layout.addStretch()
        filters_layout.addLayout(context_filter_layout)

        # Project Tags filter (multiple selection with OR)
        tags_filter_layout = QHBoxLayout()
        tags_filter_layout.setSpacing(5)

        tags_label = QLabel("Project Tags:")
        tags_label.setStyleSheet("font-weight: bold;")
        tags_label.setMinimumWidth(100)
        tags_filter_layout.addWidget(tags_label)

        self.tags_filter_label = QLabel("All Project Tags")
        self.tags_filter_label.setStyleSheet("padding: 4px; border-radius: 4px;")
        self.tags_filter_label.setMinimumWidth(150)
        tags_filter_layout.addWidget(self.tags_filter_label)

        tags_select_btn = QPushButton("Select...")
        tags_select_btn.clicked.connect(self._on_select_tag_filters)
        tags_select_btn.setWhatsThis(
            "Choose one or more project tags to filter tasks. Only tasks with at least one of the "
            "selected tags will be shown in Focus Mode (OR logic)."
        )
        tags_filter_layout.addWidget(tags_select_btn)

        clear_tags_btn = QPushButton("Clear")
        clear_tags_btn.clicked.connect(self._on_clear_tag_filters)
        clear_tags_btn.setWhatsThis(
            "Remove all project tag filters to show tasks with any tags."
        )
        tags_filter_layout.addWidget(clear_tags_btn)

        tags_filter_layout.addStretch()
        filters_layout.addLayout(tags_filter_layout)

        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)

        # Update filter labels with loaded state
        self._update_filter_labels()

    def _create_task_card(self, layout: QVBoxLayout):
        """Create the task card display area."""
        # Card frame
        self.card_frame = QFrame()
        self.card_frame.setFrameShape(QFrame.StyledPanel)
        self.card_frame.setFrameShadow(QFrame.Raised)
        # Remove hardcoded styling - let theme handle it
        self.card_frame.setObjectName("focusTaskCard")

        card_layout = QVBoxLayout()
        self.card_frame.setLayout(card_layout)

        # Task title
        self.task_title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.task_title_label.setFont(title_font)
        self.task_title_label.setWordWrap(True)
        card_layout.addWidget(self.task_title_label)

        # Task metadata (priority, due date)
        self.task_metadata_label = QLabel()
        metadata_font = QFont()
        metadata_font.setPointSize(10)
        self.task_metadata_label.setFont(metadata_font)
        self.task_metadata_label.setObjectName("taskMetadata")
        self.task_metadata_label.setStyleSheet("margin-top: 5px;")
        card_layout.addWidget(self.task_metadata_label)

        # Task description
        self.task_description = QTextEdit()
        self.task_description.setReadOnly(True)
        self.task_description.setMaximumHeight(150)
        # Remove hardcoded styling - let theme handle it
        card_layout.addWidget(self.task_description)

        layout.addWidget(self.card_frame)

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create the action button section."""
        # Primary action (Complete)
        primary_layout = QHBoxLayout()
        primary_layout.addStretch()

        self.complete_button = QPushButton("✓ Complete")
        self.complete_button.setMinimumSize(180, 50)
        self.complete_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        self.complete_button.clicked.connect(self._on_complete_clicked)
        self.complete_button.setWhatsThis(
            "Mark the current task as completed. The task will move to the Completed state, "
            "and the next highest-priority task will automatically be displayed."
        )
        primary_layout.addWidget(self.complete_button)

        primary_layout.addStretch()
        layout.addLayout(primary_layout)

        # Secondary actions (horizontal row)
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(10)

        button_style = """
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 11pt;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """

        self.defer_button = QPushButton("Defer")
        self.defer_button.setStyleSheet(button_style)
        self.defer_button.clicked.connect(self._on_defer_clicked)
        self.defer_button.setWhatsThis(
            "Postpone this task with a future start date. The task becomes deferred and will "
            "resurface when the start date arrives. You'll be prompted for the reason and date."
        )
        secondary_layout.addWidget(self.defer_button)

        self.delegate_button = QPushButton("Delegate")
        self.delegate_button.setStyleSheet(button_style)
        self.delegate_button.clicked.connect(self._on_delegate_clicked)
        self.delegate_button.setWhatsThis(
            "Assign this task to someone else. You'll set a follow-up date and be reminded "
            "to check on progress. The task moves to the Delegated state."
        )
        secondary_layout.addWidget(self.delegate_button)

        self.someday_button = QPushButton("Someday")
        self.someday_button.setStyleSheet(button_style)
        self.someday_button.clicked.connect(self._on_someday_clicked)
        self.someday_button.setWhatsThis(
            "Move this task to Someday/Maybe for things you're not ready to commit to. "
            "These tasks are periodically resurfaced for review."
        )
        secondary_layout.addWidget(self.someday_button)

        self.trash_button = QPushButton("Trash")
        self.trash_button.setStyleSheet(button_style.replace("#6c757d", "#ff8c00"))  # Yellow-orange
        self.trash_button.clicked.connect(self._on_trash_clicked)
        self.trash_button.setWhatsThis(
            "Move this task to Trash for tasks that are no longer relevant or necessary. "
            "Trashed tasks can be permanently deleted later."
        )
        secondary_layout.addWidget(self.trash_button)

        layout.addLayout(secondary_layout)

        # Refresh button (small, centered)
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()

        self.refresh_button = QPushButton("↻ Refresh Task List")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #007bff;
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #007bff;
                color: white;
            }
        """)
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        self.refresh_button.setWhatsThis(
            "Reload the task list to update with the latest highest-priority task. "
            "Use this after creating new tasks or when you think priorities may have changed."
        )
        refresh_layout.addWidget(self.refresh_button)

        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

    def set_task(self, task: Optional[Task]):
        """
        Display a task in Focus Mode.

        Args:
            task: The task to display, or None to show empty state
        """
        self._current_task = task

        if task is None:
            self._show_empty_state()
        else:
            self._show_task(task)

    def _show_task(self, task: Task):
        """Display task information in the UI."""
        # Show card
        self.card_frame.show()

        # Set title
        self.task_title_label.setText(task.title)

        # Set metadata
        metadata_parts = []

        # Priority
        priority_text = task.get_priority_enum().name.capitalize()
        metadata_parts.append(f"Priority: {priority_text}")

        # Effective priority (if adjusted)
        if task.priority_adjustment > 0:
            eff_pri = task.get_effective_priority()
            metadata_parts.append(f"(Effective: {eff_pri:.2f})")

        # Due date
        if task.due_date:
            metadata_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')}")

        self.task_metadata_label.setText(" | ".join(metadata_parts))

        # Set description
        if task.description:
            self.task_description.setText(task.description)
            self.task_description.show()
        else:
            self.task_description.hide()

        # Enable buttons
        self._enable_buttons(True)

    def _show_empty_state(self):
        """Show message when no tasks are available."""
        self.task_title_label.setText("No tasks available")
        self.task_metadata_label.setText("You're all caught up! 🎉")
        self.task_description.setText("Add a new task to get started.")
        self.task_description.show()

        # Disable action buttons
        self._enable_buttons(False)

    def _enable_buttons(self, enabled: bool):
        """Enable or disable all action buttons."""
        self.complete_button.setEnabled(enabled)
        self.defer_button.setEnabled(enabled)
        self.delegate_button.setEnabled(enabled)
        self.someday_button.setEnabled(enabled)
        self.trash_button.setEnabled(enabled)

    # Button click handlers
    def _on_complete_clicked(self):
        """Handle Complete button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_completed.emit(self._current_task.id)

    def _on_defer_clicked(self):
        """Handle Defer button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_deferred.emit(self._current_task.id)

    def _on_delegate_clicked(self):
        """Handle Delegate button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_delegated.emit(self._current_task.id)

    def _on_someday_clicked(self):
        """Handle Someday button click."""
        if self._current_task and self._current_task.id is not None:
            # Skip confirmation dialog in test mode
            if self.test_mode:
                self.task_someday.emit(self._current_task.id)
            else:
                reply = MessageBox.question(
                    self,
                    self.db_connection.get_connection(),
                    "Move to Someday/Maybe?",
                    f"Move '{self._current_task.title}' to Someday/Maybe?\n\n"
                    "This task will be removed from active focus and resurfaced periodically.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.task_someday.emit(self._current_task.id)

    def _on_trash_clicked(self):
        """Handle Trash button click."""
        if self._current_task and self._current_task.id is not None:
            # Skip confirmation dialog in test mode
            if self.test_mode:
                self.task_trashed.emit(self._current_task.id)
            else:
                reply = MessageBox.question(
                    self,
                    self.db_connection.get_connection(),
                    "Move to Trash?",
                    f"Move '{self._current_task.title}' to trash?\n\n"
                    "This task will be marked as unnecessary.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.task_trashed.emit(self._current_task.id)

    def _on_refresh_clicked(self):
        """Handle Refresh button click."""
        self.task_refreshed.emit()

    def _on_new_task(self):
        """Handle new task button click."""
        from .task_form_dialog import TaskFormDialog
        from ..services.task_service import TaskService
        from ..services.task_history_service import TaskHistoryService
        from ..database.task_history_dao import TaskHistoryDAO

        dialog = TaskFormDialog(parent=self)
        if dialog.exec_():
            task = dialog.get_updated_task()
            if task:
                task_service = TaskService(self.db_connection)
                created_task = task_service.create_task(task)

                # Record task creation in history
                task_history_dao = TaskHistoryDAO(self.db_connection.get_connection())
                task_history_service = TaskHistoryService(task_history_dao)
                task_history_service.record_task_created(created_task)

                # Emit signal that a task was created
                self.task_created.emit(created_task.id)

    def get_current_task(self) -> Optional[Task]:
        """
        Get the currently displayed task.

        Returns:
            The current task, or None if no task is displayed
        """
        return self._current_task

    def get_active_context_filter(self) -> Optional[int]:
        """Get the active context filter ID, or None if no filter."""
        return self.active_context_filter

    def get_active_tag_filters(self) -> Set[int]:
        """Get the set of active project tag filter IDs."""
        return self.active_tag_filters.copy()

    def _on_select_context_filter(self):
        """Open dialog to select a single context filter."""
        from .context_single_select_dialog import ContextSingleSelectDialog

        dialog = ContextSingleSelectDialog(
            selected_context_id=self.active_context_filter,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            self.active_context_filter = dialog.get_selected_context_id()
            self._update_filter_labels()
            self._save_filter_state()
            self.filters_changed.emit()

    def _on_clear_context_filter(self):
        """Clear the context filter."""
        self.active_context_filter = None
        self._update_filter_labels()
        self._save_filter_state()
        self.filters_changed.emit()

    def _on_select_tag_filters(self):
        """Open dialog to select multiple project tag filters."""
        from .project_tag_filter_dialog import ProjectTagFilterDialog

        dialog = ProjectTagFilterDialog(
            active_filter_ids=self.active_tag_filters,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            self.active_tag_filters = dialog.get_active_filter_ids()
            self._update_filter_labels()
            self._save_filter_state()
            self.filters_changed.emit()

    def _on_clear_tag_filters(self):
        """Clear all project tag filters."""
        self.active_tag_filters.clear()
        self._update_filter_labels()
        self._save_filter_state()
        self.filters_changed.emit()

    def _update_filter_labels(self):
        """Update the filter labels to show active filters."""
        # Update context filter label
        if self.active_context_filter is None:
            self.context_filter_label.setText("All Contexts")
        elif self.active_context_filter == "NONE":
            self.context_filter_label.setText("(No Context)")
        elif self.active_context_filter in self.contexts:
            self.context_filter_label.setText(self.contexts[self.active_context_filter])
        else:
            self.context_filter_label.setText("Unknown Context")

        # Update tag filter label
        if not self.active_tag_filters:
            self.tags_filter_label.setText("All Project Tags")
        else:
            filter_names = [
                self.project_tags.get(tag_id, f"Tag#{tag_id}")
                for tag_id in self.active_tag_filters
                if tag_id in self.project_tags
            ]
            self.tags_filter_label.setText(", ".join(filter_names) if filter_names else "All Project Tags")

    def _load_filter_state(self):
        """Load saved filter state from settings."""
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())

            # Load context filter
            context_filter = settings_dao.get('focus_mode.context_filter', None)
            if context_filter == "NONE":
                self.active_context_filter = "NONE"
            elif context_filter is not None:
                self.active_context_filter = context_filter

            # Load tag filters
            tag_filters = settings_dao.get('focus_mode.tag_filters', [])
            self.active_tag_filters = set(tag_filters)

        except Exception as e:
            print(f"Error loading filter state: {e}")

    def _save_filter_state(self):
        """Save current filter state to settings."""
        try:
            from ..database.settings_dao import SettingsDAO
            settings_dao = SettingsDAO(self.db_connection.get_connection())

            # Save context filter
            context_value = self.active_context_filter if self.active_context_filter is not None else None
            if context_value == "NONE":
                settings_dao.set('focus_mode.context_filter', "NONE", 'string', 'Focus Mode context filter')
            elif context_value is not None:
                settings_dao.set('focus_mode.context_filter', context_value, 'integer', 'Focus Mode context filter')
            else:
                settings_dao.delete('focus_mode.context_filter')

            # Save tag filters
            tag_list = list(self.active_tag_filters)
            if tag_list:
                settings_dao.set('focus_mode.tag_filters', tag_list, 'json', 'Focus Mode tag filters')
            else:
                settings_dao.delete('focus_mode.tag_filters')

        except Exception as e:
            print(f"Error saving filter state: {e}")

    def _setup_shortcuts(self):
        """Configure keyboard shortcuts for Focus Mode actions (Phase 8)."""
        # Complete: Alt+C
        complete_shortcut = QShortcut(QKeySequence("Alt+C"), self)
        complete_shortcut.activated.connect(self._on_complete_clicked)

        # Defer: Alt+D
        defer_shortcut = QShortcut(QKeySequence("Alt+D"), self)
        defer_shortcut.activated.connect(self._on_defer_clicked)

        # Delegate: Alt+G (G for "deLeGate")
        delegate_shortcut = QShortcut(QKeySequence("Alt+G"), self)
        delegate_shortcut.activated.connect(self._on_delegate_clicked)

        # Someday: Alt+S
        someday_shortcut = QShortcut(QKeySequence("Alt+S"), self)
        someday_shortcut.activated.connect(self._on_someday_clicked)

        # Trash: Alt+X
        trash_shortcut = QShortcut(QKeySequence("Alt+X"), self)
        trash_shortcut.activated.connect(self._on_trash_clicked)

        # Update button text to include keyboard shortcuts
        self.complete_button.setText("✓ Complete (Alt+C)")
        self.defer_button.setText("Defer (Alt+D)")
        self.delegate_button.setText("Delegate (Alt+G)")
        self.someday_button.setText("Someday (Alt+S)")
        self.trash_button.setText("Trash (Alt+X)")

        # Update tooltips with more detailed descriptions
        self.complete_button.setToolTip("Mark task as complete")
        self.defer_button.setToolTip("Defer task to later date")
        self.delegate_button.setToolTip("Delegate task to someone else")
        self.someday_button.setToolTip("Move to Someday/Maybe list")
        self.trash_button.setToolTip("Move to trash")
