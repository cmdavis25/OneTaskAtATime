"""
Main Window - Primary application window for OneTaskAtATime

Provides the main application container with menu bar and navigation.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QMenuBar, QMenu, QAction, QStatusBar, QMessageBox, QStackedWidget, QDialog,
    QApplication, QPushButton, QSizePolicy, QWhatsThis
)
from PyQt5.QtCore import Qt, QTimer, QObject, QEvent
from PyQt5.QtGui import QFont, QCursor
from .focus_mode import FocusModeWidget
from .task_form_dialog import TaskFormDialog
from .task_form_enhanced import EnhancedTaskFormDialog
from .task_list_view import TaskListView
from .context_management_dialog import ContextManagementDialog
from .project_tag_management_dialog import ProjectTagManagementDialog
from .postpone_dialog import DeferDialog, DelegateDialog
from .comparison_dialog import ComparisonDialog, MultipleComparisonDialog
from .notification_panel import NotificationPanel
from .message_box import MessageBox
from .settings_dialog import SettingsDialog
from .review_delegated_dialog import ReviewDelegatedDialog
from .review_someday_dialog import ReviewSomedayDialog
from .activated_tasks_dialog import ActivatedTasksDialog
from .export_dialog import ExportDialog
from .import_dialog import ImportDialog
from .reset_confirmation_dialog import ResetConfirmationDialog
from ..services.task_service import TaskService
from ..services.comparison_service import ComparisonService
from ..services.postpone_workflow_service import PostponeWorkflowService
from ..services.notification_manager import NotificationManager
from ..services.toast_notification_service import ToastNotificationService
from ..services.resurfacing_scheduler import ResurfacingScheduler
from ..services.theme_service import ThemeService
from ..services.task_history_service import TaskHistoryService
from ..services.error_service import ErrorService
from ..services.accessibility_service import AccessibilityService
from ..services.undo_manager import UndoManager
from ..database.task_history_dao import TaskHistoryDAO
from ..database.task_dao import TaskDAO
from ..database.dependency_dao import DependencyDAO
from ..services.first_run_detector import FirstRunDetector
from ..database.connection import DatabaseConnection
from ..database.settings_dao import SettingsDAO
from ..models.enums import TaskState
from ..models.notification import Notification
from ..commands import (
    DeferTaskCommand,
    DeferWithSubtasksCommand,
    DeferWithDependenciesCommand
)


class WhatsThisEventFilter(QObject):
    """
    Event filter to highlight widgets when hovering in WhatsThis mode.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._highlighted_widget = None
        self._original_stylesheet = None
        self._in_style_update = False  # Prevent recursion

    def eventFilter(self, obj, event):
        """Filter events to detect WhatsThis mode and highlight on hover."""
        # Prevent recursion when we're updating styles
        if self._in_style_update:
            return False

        try:
            if QWhatsThis.inWhatsThisMode():
                if event.type() == QEvent.Enter:
                    # Widget entered - highlight it IF it's interactive
                    if hasattr(obj, 'whatsThis') and obj.whatsThis():
                        if self._should_highlight_widget(obj):
                            self._highlight_widget(obj)
                elif event.type() == QEvent.Leave:
                    # Widget left - remove highlight
                    self._unhighlight_widget(obj)
            else:
                # Not in WhatsThis mode - ensure no highlighting
                if self._highlighted_widget == obj:
                    self._unhighlight_widget(obj)
        except Exception:
            # Silently ignore any errors to prevent crashes
            pass

        # Continue normal event processing
        return False

    def _should_highlight_widget(self, widget):
        """
        Determine if widget should be highlighted (interactive widgets only).

        Returns True for interactive widgets, False for containers/layouts.
        """
        from PyQt5.QtWidgets import (
            QDialog, QMainWindow, QWidget, QGroupBox, QFrame, QScrollArea,
            QLineEdit, QTextEdit, QComboBox, QCheckBox, QRadioButton,
            QPushButton, QListWidget, QTableWidget, QDateEdit, QSpinBox,
            QTimeEdit, QDoubleSpinBox, QSlider, QScrollBar, QTabWidget,
            QStackedWidget, QSplitter, QLabel
        )

        # Don't highlight containers - check by exact type name
        widget_type_name = type(widget).__name__
        container_types = (
            'QDialog', 'QMainWindow', 'QWidget', 'QGroupBox', 'QFrame',
            'QScrollArea', 'QTabWidget', 'QStackedWidget', 'QSplitter',
            'QVBoxLayout', 'QHBoxLayout', 'QFormLayout', 'QGridLayout'
        )

        if widget_type_name in container_types:
            return False

        # Only highlight interactive widget types
        interactive_types = (
            QLineEdit, QTextEdit, QComboBox, QCheckBox, QRadioButton,
            QPushButton, QListWidget, QTableWidget, QDateEdit, QSpinBox,
            QTimeEdit, QDoubleSpinBox, QSlider, QScrollBar
        )

        return isinstance(widget, interactive_types)

    def _highlight_widget(self, widget):
        """Add highlight border to widget."""
        if self._highlighted_widget == widget:
            return  # Already highlighted

        # Prevent recursion
        if self._in_style_update:
            return

        try:
            self._in_style_update = True

            # Remove previous highlight
            if self._highlighted_widget is not None and self._highlighted_widget != widget:
                self._restore_style(self._highlighted_widget)

            # Save original stylesheet
            self._original_stylesheet = widget.styleSheet()
            self._highlighted_widget = widget

            # Add highlight using property-based styling to avoid recursion
            widget.setProperty("whatsthis_highlighted", True)

            # Simple border-only highlight
            current_style = self._original_stylesheet if self._original_stylesheet else ""
            new_style = current_style + " border: 2px solid #007bff !important;"

            widget.setStyleSheet(new_style)
        except Exception:
            pass
        finally:
            self._in_style_update = False

    def _unhighlight_widget(self, widget):
        """Remove highlight border from widget."""
        if widget != self._highlighted_widget:
            return

        # Prevent recursion
        if self._in_style_update:
            return

        try:
            self._in_style_update = True
            self._restore_style(widget)
        except Exception:
            pass
        finally:
            self._in_style_update = False

    def _restore_style(self, widget):
        """Restore original style to widget."""
        try:
            # Clear property
            widget.setProperty("whatsthis_highlighted", False)

            # Restore original stylesheet
            if self._original_stylesheet is not None:
                widget.setStyleSheet(self._original_stylesheet)
            else:
                widget.setStyleSheet("")

            if widget == self._highlighted_widget:
                self._highlighted_widget = None
                self._original_stylesheet = None
        except Exception:
            pass


class MainWindow(QMainWindow):
    """
    Main application window.

    Phase 4: Full task management interface with multiple views.
    """

    def __init__(self, app=None):
        """Initialize the main window.

        Args:
            app: QApplication instance for theme management
        """
        super().__init__()
        self.app = app
        self.setWindowTitle("OneTaskAtATime")

        # Initialize database and services
        self.db_connection = DatabaseConnection()
        self.settings_dao = SettingsDAO(self.db_connection.get_connection())
        self.task_service = TaskService(self.db_connection)
        self.comparison_service = ComparisonService(self.db_connection)
        self.postpone_workflow_service = PostponeWorkflowService(self.db_connection.get_connection())

        # Initialize Phase 6 services (notification system and scheduler)
        self.notification_manager = NotificationManager(self.db_connection.get_connection())
        self.toast_service = ToastNotificationService(self.db_connection.get_connection())
        self.notification_manager.set_toast_service(self.toast_service)

        # Initialize resurfacing scheduler
        self.resurfacing_scheduler = ResurfacingScheduler(
            self.db_connection.get_connection(),
            self.notification_manager
        )

        # Initialize Phase 7 services (theme system)
        if self.app:
            self.theme_service = ThemeService(self.db_connection.get_connection(), self.app)
            # Apply saved theme
            current_theme = self.settings_dao.get_str('theme', default='light')
            self.theme_service.apply_theme(current_theme)

        # Initialize Phase 8 services
        task_history_dao = TaskHistoryDAO(self.db_connection.get_connection())
        self.task_history_service = TaskHistoryService(task_history_dao)
        self.error_service = ErrorService()
        self.accessibility_service = AccessibilityService()
        self.undo_manager = UndoManager(max_stack_size=50)
        self.first_run_detector = FirstRunDetector(self.db_connection.get_connection())

        # Initialize DAOs needed for undo/redo commands
        self.task_dao = TaskDAO(self.db_connection.get_connection())
        self.dependency_dao = DependencyDAO(self.db_connection.get_connection())

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Restore saved window geometry and state
        self._restore_window_geometry()

        # Connect scheduler signals
        self._connect_scheduler_signals()

        # Start background scheduler
        self.resurfacing_scheduler.start()

        # Connect undo/redo signals to update menu state
        self.undo_manager.can_undo_changed.connect(self._update_undo_action)
        self.undo_manager.can_redo_changed.connect(self._update_redo_action)

        # Apply accessibility features
        self.accessibility_service.configure_keyboard_navigation(self)
        self.accessibility_service.apply_accessible_labels(self)

        # Install WhatsThis hover highlighting event filter
        self.whatsthis_filter = WhatsThisEventFilter(self)
        if self.app:
            self.app.installEventFilter(self.whatsthis_filter)

        # Show welcome wizard on first run (Phase 8)
        from PyQt5.QtCore import QTimer
        if self.first_run_detector.is_first_run():
            QTimer.singleShot(500, self._show_welcome_wizard)

        # Load initial task
        self._refresh_focus_task()

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget with stacked layout for multiple views
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        central_widget.setLayout(layout)

        # Unified header row with title, switcher, and notifications
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setAlignment(Qt.AlignVCenter)  # Ensure vertical centering

        # Mode title on the left (matching notification button height)
        self.mode_title_label = QLabel("Focus Mode")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.mode_title_label.setFont(title_font)
        self.mode_title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.mode_title_label.setStyleSheet("padding: 8px 0px;")
        header_layout.addWidget(self.mode_title_label)

        # View switcher button in the center (expanding)
        self.view_switcher_btn = QPushButton("→ Switch to Task List (Ctrl+2) →")
        self.view_switcher_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00CED1, stop:0.5 #4B0082, stop:1 #00CED1);
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00B8B8, stop:0.5 #3A006A, stop:1 #00B8B8);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #009999, stop:0.5 #2A0052, stop:1 #009999);
            }
        """)
        self.view_switcher_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.view_switcher_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.view_switcher_btn.clicked.connect(self._toggle_view)
        header_layout.addWidget(self.view_switcher_btn, 1)  # Stretch factor 1

        # Notification panel on the right (Phase 6)
        self.notification_panel = NotificationPanel(
            self.db_connection.get_connection(),
            self.notification_manager
        )
        self.notification_panel.action_requested.connect(self._on_notification_action)
        header_layout.addWidget(self.notification_panel)

        layout.addLayout(header_layout)

        # Stacked widget for switching views
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Focus Mode widget
        self.focus_mode = FocusModeWidget(self.db_connection)
        self.stacked_widget.addWidget(self.focus_mode)

        # Task List View
        self.task_list_view = TaskListView(self.db_connection, self.undo_manager)
        self.stacked_widget.addWidget(self.task_list_view)

        # Connect Focus Mode signals
        self.focus_mode.task_completed.connect(self._on_task_completed)
        self.focus_mode.task_deferred.connect(self._on_task_deferred)
        self.focus_mode.task_delegated.connect(self._on_task_delegated)
        self.focus_mode.task_someday.connect(self._on_task_someday)
        self.focus_mode.task_trashed.connect(self._on_task_trashed)
        self.focus_mode.task_refreshed.connect(self._refresh_focus_task)
        self.focus_mode.filters_changed.connect(self._refresh_focus_task)

        # Connect Task List View signals
        self.task_list_view.task_created.connect(self._on_task_list_changed)
        self.task_list_view.task_updated.connect(self._on_task_list_changed)
        self.task_list_view.task_deleted.connect(self._on_task_list_changed)
        self.task_list_view.task_count_changed.connect(self._on_task_count_changed)

        # Start with Focus Mode
        self.stacked_widget.setCurrentWidget(self.focus_mode)

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        new_task_action = QAction("&New Task", self)
        new_task_action.setShortcut("Ctrl+N")
        new_task_action.setStatusTip("Create a new task")
        new_task_action.triggered.connect(self._on_new_task)
        file_menu.addAction(new_task_action)

        file_menu.addSeparator()

        # Import/Export submenu (Phase 7)
        export_action = QAction("E&xport Data...", self)
        export_action.setShortcut("Ctrl+Shift+E")
        export_action.setStatusTip("Export data to JSON or create database backup")
        export_action.triggered.connect(self._export_data)
        file_menu.addAction(export_action)

        import_action = QAction("&Import Data...", self)
        import_action.setShortcut("Ctrl+Shift+I")
        import_action.setStatusTip("Import data from JSON backup")
        import_action.triggered.connect(self._import_data)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit Menu (Phase 8)
        edit_menu = menubar.addMenu("&Edit")

        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setStatusTip("Undo last action")
        self.undo_action.triggered.connect(self._undo_last_action)
        self.undo_action.setEnabled(False)
        edit_menu.addAction(self.undo_action)

        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setStatusTip("Redo last undone action")
        self.redo_action.triggered.connect(self._redo_last_action)
        self.redo_action.setEnabled(False)
        edit_menu.addAction(self.redo_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        focus_mode_action = QAction("&Focus Mode", self)
        focus_mode_action.setShortcut("Ctrl+1")
        focus_mode_action.setStatusTip("Switch to Focus Mode")
        focus_mode_action.triggered.connect(self._show_focus_mode)
        view_menu.addAction(focus_mode_action)

        task_list_action = QAction("&Task List", self)
        task_list_action.setShortcut("Ctrl+2")
        task_list_action.setStatusTip("Switch to Task List view")
        task_list_action.triggered.connect(self._show_task_list)
        view_menu.addAction(task_list_action)

        view_menu.addSeparator()

        search_action = QAction("&Search Tasks...", self)
        search_action.setShortcut("Ctrl+F")
        search_action.setStatusTip("Focus search box in Task List")
        search_action.triggered.connect(self._focus_search_box)
        view_menu.addAction(search_action)

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Refresh current view")
        refresh_action.triggered.connect(self._refresh_current_view)
        view_menu.addAction(refresh_action)

        # Manage Menu (New in Phase 4)
        manage_menu = menubar.addMenu("&Manage")

        contexts_action = QAction("&Contexts...", self)
        contexts_action.setStatusTip("Manage contexts")
        contexts_action.triggered.connect(self._manage_contexts)
        manage_menu.addAction(contexts_action)

        tags_action = QAction("Project &Tags...", self)
        tags_action.setStatusTip("Manage project tags")
        tags_action.triggered.connect(self._manage_project_tags)
        manage_menu.addAction(tags_action)

        # Tools Menu
        tools_menu = menubar.addMenu("&Tools")

        # Settings action (Phase 6)
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.setStatusTip("Configure application settings")
        settings_action.triggered.connect(self._show_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        analytics_action = QAction("📊 Postpone &Analytics...", self)
        analytics_action.setShortcut("Ctrl+Shift+A")
        analytics_action.setStatusTip("View postpone analytics dashboard")
        analytics_action.triggered.connect(self._show_analytics)
        tools_menu.addAction(analytics_action)

        tools_menu.addSeparator()

        reset_adjustments_action = QAction("Reset &Priority Adjustments", self)
        reset_adjustments_action.setStatusTip("Reset all comparison-based priority adjustments")
        reset_adjustments_action.triggered.connect(self._reset_all_priority_adjustments)
        tools_menu.addAction(reset_adjustments_action)

        tools_menu.addSeparator()

        delete_trash_action = QAction("Delete All &Trash Tasks", self)
        delete_trash_action.setStatusTip("Permanently delete all tasks in Trash state")
        delete_trash_action.triggered.connect(self._delete_trash_tasks)
        tools_menu.addAction(delete_trash_action)

        tools_menu.addSeparator()

        # Phase 7: Replace "Delete All Tasks" with comprehensive "Reset All Data"
        reset_all_action = QAction("Reset All &Data...", self)
        reset_all_action.setStatusTip("Reset all data (nuclear option with multi-step confirmation)")
        reset_all_action.triggered.connect(self._reset_all_data)
        tools_menu.addAction(reset_all_action)

        # Help Menu (Phase 8 enhancements)
        help_menu = menubar.addMenu("&Help")

        help_contents_action = QAction("&Help Contents", self)
        help_contents_action.setShortcut("F1")
        help_contents_action.setStatusTip("Show help documentation")
        help_contents_action.triggered.connect(self._show_help)
        help_menu.addAction(help_contents_action)

        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("Ctrl+?")
        shortcuts_action.setStatusTip("Show keyboard shortcuts reference")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

        help_menu.addSeparator()

        whatsthis_action = QAction("What's &This?", self)
        whatsthis_action.setShortcut("Shift+F1")
        whatsthis_action.setStatusTip("Enter What's This help mode")
        whatsthis_action.triggered.connect(QWhatsThis.enterWhatsThisMode)
        help_menu.addAction(whatsthis_action)

        help_menu.addSeparator()

        about_action = QAction("&About", self)
        about_action.setStatusTip("About OneTaskAtATime")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Create permanent label for task count (right side)
        self.task_count_label = QLabel("")
        self.task_count_label.setStyleSheet("padding: 0 10px;")
        status_bar.addPermanentWidget(self.task_count_label)

        self._update_status_bar()

    def _update_status_bar(self):
        """Update status bar with task counts."""
        counts = self.task_service.get_task_count_by_state()
        active = counts.get('active', 0)
        completed = counts.get('completed', 0)
        self.statusBar().showMessage(
            f"Active: {active} | Completed: {completed}"
        )

    def _refresh_focus_task(self):
        """Refresh the task displayed in Focus Mode."""
        # Get filters from Focus Mode widget
        context_filter = self.focus_mode.get_active_context_filter()
        tag_filters = self.focus_mode.get_active_tag_filters()

        # First check if there are new tasks needing initial ranking
        if self._check_and_handle_new_tasks():
            # New tasks were ranked, refresh again to show the top task
            self._refresh_focus_task()
            return

        # Check if there are tied tasks
        tied_tasks = self.task_service.get_tied_tasks(
            context_filter=context_filter,
            tag_filters=tag_filters
        )

        if len(tied_tasks) >= 2:
            # Show comparison dialog
            self._handle_tied_tasks(tied_tasks)
        else:
            # No tie, get the top task
            task = self.task_service.get_focus_task(
                context_filter=context_filter,
                tag_filters=tag_filters
            )

            # If no task is available, prompt user to review deferred/postponed tasks
            if task is None:
                if self._prompt_review_deferred_tasks():
                    # User activated some tasks, refresh to show them
                    self._refresh_focus_task()
                    return

            self.focus_mode.set_task(task)
            self._update_status_bar()

    def _on_new_task(self):
        """Handle New Task action."""
        dialog = TaskFormDialog(parent=self)
        if dialog.exec_():
            task = dialog.get_updated_task()
            if task:
                created_task = self.task_service.create_task(task)

                # Save dependencies if any were selected
                if dialog.dependencies:
                    from ..models.dependency import Dependency
                    for blocking_task_id in dialog.dependencies:
                        dependency = Dependency(
                            blocked_task_id=created_task.id,
                            blocking_task_id=blocking_task_id
                        )
                        self.dependency_dao.create(dependency)

                # Record task creation in history
                self.task_history_service.record_task_created(created_task)
                self._refresh_focus_task()
                self.statusBar().showMessage("Task created successfully", 3000)

    def _on_task_completed(self, task_id: int):
        """Handle task completion."""
        task = self.task_service.get_task_by_id(task_id)
        if task:
            self.task_service.complete_task(task_id)
            # Record completion in history
            completed_task = self.task_service.get_task_by_id(task_id)
            if completed_task:
                self.task_history_service.record_state_change(
                    completed_task, task.state, TaskState.COMPLETED
                )
            self.statusBar().showMessage("Task completed! 🎉", 3000)
            self._refresh_focus_task()

    def _on_task_deferred(self, task_id: int):
        """Handle task deferral with reflection check and associated workflows."""
        current_task = self.focus_mode.get_current_task()
        if not current_task:
            return

        # Use reflection-aware dialog (checks for patterns first)
        from .postpone_dialog import PostponeDialog
        result = PostponeDialog.show_with_reflection_check(
            current_task,
            self.db_connection,
            action_type="defer",
            parent=self
        )

        if result:
            # Check if user chose a disposition action (from reflection dialog)
            if result.get('action_type') == 'disposition':
                disposition = result.get('disposition')
                if disposition == TaskState.SOMEDAY:
                    self.task_service.move_to_someday(task_id)
                    self.statusBar().showMessage("Task moved to Someday/Maybe", 3000)
                elif disposition == TaskState.TRASH:
                    self.task_service.move_to_trash(task_id)
                    self.statusBar().showMessage("Task moved to trash", 3000)
                self._refresh_focus_task()
                return

            # Track dependencies before workflows to detect what was added
            dependencies_before = set(
                dep.blocking_task_id
                for dep in self.dependency_dao.get_dependencies_for_task(task_id)
            )

            # Choose the appropriate command based on workflow results
            command = None

            # Check for subtask workflow
            if subtask_result := result.get('subtask_result'):
                command = DeferWithSubtasksCommand(
                    self.task_dao,
                    task_id,
                    result['start_date'],
                    subtask_result['subtask_titles'],
                    subtask_result['delete_original'],
                    result.get('reason')
                )

            # Check for blocker/dependency workflow (unified)
            elif result.get('dependency_added'):
                # Get the dependency task IDs that were just added
                dependencies_after = set(
                    dep.blocking_task_id
                    for dep in self.dependency_dao.get_dependencies_for_task(task_id)
                )
                newly_added_deps = list(dependencies_after - dependencies_before)

                if newly_added_deps:
                    # Get created blocking task IDs from result
                    created_blocking_task_ids = result.get('created_blocking_task_ids', [])

                    command = DeferWithDependenciesCommand(
                        self.task_dao,
                        self.dependency_dao,
                        task_id,
                        result['start_date'],
                        newly_added_deps,
                        result.get('reason'),
                        created_blocking_task_ids
                    )
                else:
                    # Fallback to basic defer if no dependencies found
                    command = DeferTaskCommand(
                        self.task_dao,
                        task_id,
                        result['start_date'],
                        result.get('reason')
                    )

            # Default: simple defer
            else:
                command = DeferTaskCommand(
                    self.task_dao,
                    task_id,
                    result['start_date'],
                    result.get('reason')
                )

            if self.undo_manager.execute_command(command):
                # Handle notes separately (not part of the command)
                if result.get('notes'):
                    current_task.notes = result.get('notes')
                    self.task_dao.update(current_task)

                self.statusBar().showMessage("Task deferred", 3000)
                self._refresh_focus_task()

    def _on_task_delegated(self, task_id: int):
        """Handle task delegation."""
        current_task = self.focus_mode.get_current_task()
        if not current_task:
            return

        dialog = DelegateDialog(current_task.title, current_task, self.db_connection, self)
        if dialog.exec_():
            result = dialog.get_result()
            if result and result.get('delegated_to'):
                self.task_service.delegate_task(
                    task_id,
                    result['delegated_to'],
                    result['follow_up_date'],
                    result.get('notes')
                )
                self.statusBar().showMessage("Task delegated", 3000)
                self._refresh_focus_task()

    def _on_task_someday(self, task_id: int):
        """Handle moving task to Someday/Maybe."""
        self.task_service.move_to_someday(task_id)
        self.statusBar().showMessage("Task moved to Someday/Maybe", 3000)
        self._refresh_focus_task()

    def _on_task_trashed(self, task_id: int):
        """Handle moving task to trash."""
        self.task_service.move_to_trash(task_id)
        self.statusBar().showMessage("Task moved to trash", 3000)
        self._refresh_focus_task()

    def _handle_postpone_workflows(self, postpone_result: dict, task_id: int, notes: str):
        """
        Process workflow results from postpone dialog.

        Args:
            postpone_result: Dictionary from PostponeDialog.get_result()
            task_id: ID of the postponed task
            notes: User notes about postponement
        """
        # Handle blocker workflow
        if blocker_result := postpone_result.get('blocker_result'):
            result = self.postpone_workflow_service.handle_blocker_workflow(
                task_id,
                notes,
                blocker_task_id=blocker_result.get('blocker_task_id'),
                new_blocker_title=blocker_result.get('new_blocker_title')
            )
            if result['success']:
                MessageBox.information(self, self.db_connection.get_connection(), "Blocker Created", result['message'])
            else:
                MessageBox.warning(self, self.db_connection.get_connection(), "Blocker Failed", result['message'])

        # Handle subtask workflow
        if subtask_result := postpone_result.get('subtask_result'):
            result = self.postpone_workflow_service.handle_subtask_breakdown(
                task_id,
                notes,
                subtask_result['subtask_titles'],
                subtask_result['delete_original']
            )
            if result['success']:
                MessageBox.information(self, self.db_connection.get_connection(), "Tasks Created", result['message'])
            else:
                MessageBox.warning(self, self.db_connection.get_connection(), "Breakdown Failed", result['message'])

        # Note: Dependency workflow doesn't need handling here because
        # DependencySelectionDialog saves dependencies directly

    def _prompt_review_deferred_tasks(self) -> bool:
        """
        Prompt user to review deferred/postponed tasks when no active tasks are available.

        Returns:
            True if user activated tasks, False otherwise
        """
        # Check if there are any deferred or postponed tasks
        deferred_tasks = self.task_service.get_tasks_by_state(TaskState.DEFERRED)

        if not deferred_tasks:
            # No reviewable tasks, nothing to do
            return False

        # Show review dialog
        from .review_deferred_dialog import ReviewDeferredDialog

        dialog = ReviewDeferredDialog(self.db_connection, parent=self)
        if dialog.exec_():
            # User activated some tasks
            self.statusBar().showMessage("Tasks activated successfully", 3000)
            return True

        return False

    def _check_and_handle_new_tasks(self) -> bool:
        """
        Check for new tasks (comparison_count = 0) and prompt for initial ranking.

        Returns:
            True if new tasks were found and user completed ranking, False otherwise
        """
        from ..algorithms.initial_ranking import (
            check_for_new_tasks,
            get_ranking_candidates,
            assign_elo_ratings_from_ranking
        )
        from .sequential_ranking_dialog import SequentialRankingDialog

        # Get all tasks to check for new ones
        all_tasks = self.task_service.get_all_tasks()

        # Check if there are new tasks in any priority band
        has_new, priority_band, new_tasks = check_for_new_tasks(all_tasks)

        if not has_new:
            return False

        # Get ranking candidates (new tasks + top/bottom existing tasks)
        candidates = get_ranking_candidates(all_tasks, new_tasks, priority_band)

        # Separate new from existing for dialog display
        existing_tasks = [t for t in candidates if t.comparison_count > 0]
        top_existing = max(existing_tasks, key=lambda t: t.elo_rating) if existing_tasks else None
        bottom_existing = min(existing_tasks, key=lambda t: t.elo_rating) if existing_tasks else None

        # Show sequential ranking dialog
        dialog = SequentialRankingDialog(
            new_tasks=new_tasks,
            top_existing=top_existing,
            bottom_existing=bottom_existing,
            priority_band=priority_band,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            # User completed ranking
            ranked_tasks = dialog.get_ranked_tasks()

            # Calculate Elo ratings based on ranking
            top_elo = top_existing.elo_rating if top_existing else None
            bottom_elo = bottom_existing.elo_rating if bottom_existing else None

            task_elo_assignments = assign_elo_ratings_from_ranking(
                ranked_tasks,
                top_elo,
                bottom_elo,
                priority_band
            )

            # Update each task's Elo rating in the database
            for task, new_elo in task_elo_assignments:
                task.elo_rating = new_elo
                # Mark as having been in at least one comparison
                # (even though this is interpolation, not actual comparison)
                task.comparison_count = 1
                self.task_service.update_task(task)

            self.statusBar().showMessage(
                f"Ranked {len(ranked_tasks)} new task{'s' if len(ranked_tasks) != 1 else ''} "
                f"in {['Low', 'Medium', 'High'][priority_band - 1]} priority band",
                3000
            )
            return True

        # User skipped ranking
        return False

    def _handle_tied_tasks(self, tied_tasks):
        """
        Handle tied tasks by showing comparison dialog.

        Args:
            tied_tasks: List of tasks tied for top priority
        """
        if len(tied_tasks) == 2:
            # Simple pairwise comparison
            dialog = ComparisonDialog(tied_tasks[0], tied_tasks[1], self.db_connection, self)
            if dialog.exec_():
                result = dialog.get_comparison_result()
                if result:
                    winner, loser = result
                    self.comparison_service.record_comparison(winner, loser)
                    self.statusBar().showMessage(
                        f"Comparison recorded: '{winner.title}' prioritized", 3000
                    )
                    # Refresh to show winner
                    self._refresh_focus_task()
        else:
            # Multiple tasks tied
            dialog = MultipleComparisonDialog(tied_tasks, self.db_connection, self)
            if dialog.exec_():
                results = dialog.get_comparison_results()
                if results:
                    self.comparison_service.record_multiple_comparisons(results)
                    self.statusBar().showMessage(
                        f"{len(results)} comparisons recorded", 3000
                    )
                    # Refresh to show winner
                    self._refresh_focus_task()

    def _reset_all_priority_adjustments(self):
        """Reset all priority adjustments for all tasks."""
        reply = MessageBox.warning(
            self,
            self.db_connection.get_connection(),
            "Reset Priority Adjustments",
            "This will reset all comparison-based priority adjustments to zero "
            "and delete all comparison history.\n\n"
            "Tasks that were deprioritized through comparisons will return to "
            "their base priority, which may create new ties requiring re-comparison.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            count = self.comparison_service.reset_all_priority_adjustments()
            self.statusBar().showMessage(
                f"Reset {count} task priority adjustments", 5000
            )
            self._refresh_focus_task()

    def _delete_all_tasks(self):
        """Delete all tasks from the database with confirmation."""
        reply = MessageBox.warning(
            self,
            self.db_connection.get_connection(),
            "Delete All Tasks",
            "This will permanently delete ALL tasks from the database.\n\n"
            "This action cannot be undone!\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            count = self.task_service.delete_all_tasks()
            self.statusBar().showMessage(
                f"Deleted {count} tasks", 5000
            )
            self._refresh_focus_task()
            # Refresh task list view if visible
            if self.stacked_widget.currentWidget() == self.task_list_view:
                self.task_list_view.refresh_tasks()

    def _delete_trash_tasks(self):
        """Delete all tasks in Trash state with confirmation."""
        # Count trash tasks first
        trash_tasks = self.task_service.get_tasks_by_state(TaskState.TRASH)
        trash_count = len(trash_tasks)

        if trash_count == 0:
            MessageBox.information(
                self,
                self.db_connection.get_connection(),
                "No Trash Tasks",
                "There are no tasks in the Trash to delete."
            )
            return

        reply = MessageBox.warning(
            self,
            self.db_connection.get_connection(),
            "Delete All Trash Tasks",
            f"This will permanently delete {trash_count} task(s) from the Trash.\n\n"
            "This action cannot be undone!\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            count = self.task_service.delete_trash_tasks()
            self.statusBar().showMessage(
                f"Deleted {count} trash task(s)", 5000
            )
            self._refresh_focus_task()
            # Refresh task list view if visible
            if self.stacked_widget.currentWidget() == self.task_list_view:
                self.task_list_view.refresh_tasks()

    def _toggle_view(self):
        """Toggle between Focus Mode and Task List view."""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget == self.focus_mode:
            self._show_task_list()
        else:
            self._show_focus_mode()

    def _show_focus_mode(self):
        """Switch to Focus Mode view."""
        self.stacked_widget.setCurrentWidget(self.focus_mode)
        self.mode_title_label.setText("Focus Mode")
        self.view_switcher_btn.setText("→ Switch to Task List (Ctrl+2) →")
        self._refresh_focus_task()
        # Clear task count label when switching to Focus Mode
        self.task_count_label.setText("")
        self.statusBar().showMessage("Switched to Focus Mode", 2000)

    def _show_task_list(self):
        """Switch to Task List view."""
        self.stacked_widget.setCurrentWidget(self.task_list_view)
        self.mode_title_label.setText("Task List")
        self.view_switcher_btn.setText("← Switch to Focus Mode (Ctrl+1) ←")
        self.task_list_view.refresh_tasks()
        # Task count will be updated automatically via the task_count_changed signal

    def _focus_search_box(self):
        """
        Focus the search box in Task List.

        If currently in Focus Mode, automatically switches to Task List first.
        """
        # Switch to Task List if not already there
        current_widget = self.stacked_widget.currentWidget()
        if current_widget != self.task_list_view:
            self._show_task_list()

        # Focus the search box
        self.task_list_view.focus_search_box()
        self.statusBar().showMessage("Search box focused", 2000)

    def _refresh_current_view(self):
        """Refresh the currently visible view."""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget == self.focus_mode:
            self._refresh_focus_task()
        elif current_widget == self.task_list_view:
            self.task_list_view.refresh_tasks()

    def _on_task_list_changed(self, task_id: int):
        """
        Handle changes from task list view.

        Args:
            task_id: ID of task that was changed
        """
        self._update_status_bar()
        # Refresh focus mode in case the change affects it
        if self.stacked_widget.currentWidget() == self.focus_mode:
            self._refresh_focus_task()

    def _on_task_count_changed(self, count_message: str):
        """
        Update status bar with task count from Task List view.

        Args:
            count_message: Formatted message showing filtered/total count
        """
        self.task_count_label.setText(count_message)

    def _manage_contexts(self):
        """Open context management dialog."""
        dialog = ContextManagementDialog(self.db_connection, self)
        dialog.exec_()

    def _manage_project_tags(self):
        """Open project tag management dialog."""
        dialog = ProjectTagManagementDialog(self.db_connection, self)
        dialog.exec_()

    def _show_analytics(self):
        """Open postpone analytics dashboard."""
        from .analytics_view import AnalyticsView
        dialog = AnalyticsView(self.db_connection, self)
        dialog.exec_()

    def _show_settings(self):
        """Show settings dialog (Phase 6)."""
        dialog = SettingsDialog(self.db_connection.get_connection(), self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.rerun_wizard_requested.connect(self._on_wizard_rerun_requested)
        dialog.exec_()

    def _on_settings_saved(self):
        """Handle settings saved signal."""
        # Reload scheduler settings
        self.resurfacing_scheduler.reload_settings()

        # Reapply theme if changed (Phase 7)
        if hasattr(self, 'theme_service'):
            current_theme = self.settings_dao.get_str('theme', default='light')
            self.theme_service.apply_theme(current_theme)

        self.statusBar().showMessage("Settings saved and scheduler updated", 3000)

    def _on_wizard_rerun_requested(self):
        """Handle request to re-run welcome wizard."""
        # Use QTimer to delay showing wizard until settings dialog is fully closed
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self._show_welcome_wizard)

    def _connect_scheduler_signals(self):
        """Connect scheduler signals to UI handlers (Phase 6)."""
        self.resurfacing_scheduler.deferred_tasks_activated.connect(
            self._on_deferred_tasks_activated
        )
        self.resurfacing_scheduler.delegated_followup_needed.connect(
            self._on_delegated_followup_needed
        )
        self.resurfacing_scheduler.someday_review_triggered.connect(
            self._on_someday_review_triggered
        )

    def _on_deferred_tasks_activated(self, tasks):
        """Handle deferred tasks auto-activation (Phase 6)."""
        if tasks:
            self._refresh_focus_task()
            self.statusBar().showMessage(
                f"{len(tasks)} deferred task(s) activated", 5000
            )

    def _on_delegated_followup_needed(self, tasks):
        """Show delegated follow-up dialog (Phase 6)."""
        dialog = ReviewDelegatedDialog(self.db_connection.get_connection(), tasks, self)
        dialog.exec_()
        self._refresh_focus_task()

    def _on_someday_review_triggered(self):
        """Show someday review dialog (Phase 6)."""
        dialog = ReviewSomedayDialog(self.db_connection.get_connection(), self)
        dialog.exec_()
        self._refresh_focus_task()

    def _on_notification_action(self, notification: Notification):
        """Handle notification action button click (Phase 6)."""
        action_type = notification.action_type

        if action_type == 'open_focus':
            # Show dialog with activated tasks
            task_ids = notification.action_data.get('task_ids', []) if notification.action_data else []

            if task_ids:
                dialog = ActivatedTasksDialog(task_ids, self.db_connection.get_connection(), self)
                dialog.exec_()
            else:
                # Fallback: just switch to focus mode
                self._show_focus_mode()
                self.statusBar().showMessage("Viewing activated tasks in Focus Mode", 3000)

        elif action_type == 'open_review_delegated':
            # Get task IDs from action data
            task_ids = notification.action_data.get('task_ids', []) if notification.action_data else []

            # Fetch tasks and show dialog
            from ..database.task_dao import TaskDAO
            task_dao = TaskDAO(self.db_connection.get_connection())
            tasks = [task_dao.get_by_id(task_id) for task_id in task_ids]
            tasks = [t for t in tasks if t is not None]

            if tasks:
                dialog = ReviewDelegatedDialog(self.db_connection.get_connection(), tasks, self)
                dialog.exec_()
                self._refresh_focus_task()

        elif action_type == 'open_review_someday':
            # Show someday review dialog
            self._on_someday_review_triggered()

        elif action_type == 'open_postpone_analytics':
            # Show analytics dashboard
            self._show_analytics()

    def _show_about(self):
        """Show about dialog."""
        MessageBox.information(
            self,
            self.db_connection.get_connection(),
            "About OneTaskAtATime",
            "OneTaskAtATime v1.0.0\n\n"
            "A focused to-do list application designed to help users\n"
            "concentrate on executing one task at a time using\n"
            "GTD-inspired principles.\n\n"
            "Phase 8: Polish & UX Complete"
        )

    def _show_help(self):
        """Show help dialog (Phase 8)."""
        from .help_dialog import HelpDialog
        dialog = HelpDialog(self)
        dialog.exec_()

    def _show_shortcuts(self):
        """Show keyboard shortcuts reference (Phase 8)."""
        from .shortcuts_dialog import ShortcutsDialog
        dialog = ShortcutsDialog(self)
        dialog.exec_()

    def _show_welcome_wizard(self):
        """Show welcome wizard on first run (Phase 8)."""
        from .welcome_wizard import WelcomeWizard
        from PyQt5.QtWidgets import QWizard

        wizard = WelcomeWizard(self.db_connection.get_connection(), self)
        if wizard.exec_() == QWizard.Accepted:
            self.first_run_detector.mark_onboarding_complete()
            self._refresh_focus_task()

    def _undo_last_action(self):
        """Undo last action (Phase 8)."""
        desc = self.undo_manager.get_undo_description()
        if self.undo_manager.undo():
            self.statusBar().showMessage(f"Undone: {desc}", 3000)

            # Only refresh focus task if Focus Mode is active
            if self.stacked_widget.currentWidget() == self.focus_mode:
                self._refresh_focus_task()

            # Refresh task list view if it exists
            if hasattr(self, 'task_list_view'):
                self.task_list_view.refresh_tasks()
        else:
            self.statusBar().showMessage("Nothing to undo", 2000)

    def _redo_last_action(self):
        """Redo last undone action (Phase 8)."""
        desc = self.undo_manager.get_redo_description()
        if self.undo_manager.redo():
            self.statusBar().showMessage(f"Redone: {desc}", 3000)

            # Only refresh focus task if Focus Mode is active
            if self.stacked_widget.currentWidget() == self.focus_mode:
                self._refresh_focus_task()

            # Refresh task list view if it exists
            if hasattr(self, 'task_list_view'):
                self.task_list_view.refresh_tasks()
        else:
            self.statusBar().showMessage("Nothing to redo", 2000)

    def _update_undo_action(self, can_undo: bool):
        """Update undo action enabled state (Phase 8)."""
        if hasattr(self, 'undo_action'):
            self.undo_action.setEnabled(can_undo)
            if can_undo:
                desc = self.undo_manager.get_undo_description()
                self.undo_action.setText(f"&Undo {desc}")
            else:
                self.undo_action.setText("&Undo")

    def _update_redo_action(self, can_redo: bool):
        """Update redo action enabled state (Phase 8)."""
        if hasattr(self, 'redo_action'):
            self.redo_action.setEnabled(can_redo)
            if can_redo:
                desc = self.undo_manager.get_redo_description()
                self.redo_action.setText(f"&Redo {desc}")
            else:
                self.redo_action.setText("&Redo")

    def _export_data(self):
        """Show export data dialog (Phase 7)."""
        dialog = ExportDialog(self.db_connection.get_connection(), self)
        dialog.exec_()

    def _import_data(self):
        """Show import data dialog (Phase 7)."""
        dialog = ImportDialog(self.db_connection.get_connection(), self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh all views after successful import
            self._refresh_focus_task()
            if hasattr(self, 'task_list_view'):
                self.task_list_view.refresh_tasks()
            self.statusBar().showMessage("Data imported successfully", 5000)

    def _reset_all_data(self):
        """Show reset all data confirmation dialog (Phase 7)."""
        dialog = ResetConfirmationDialog(self.db_connection.get_connection(), self)
        if dialog.exec_() == QDialog.Accepted:
            # Refresh all views after successful reset
            self._refresh_focus_task()
            if hasattr(self, 'task_list_view'):
                self.task_list_view.refresh_tasks()
            self.statusBar().showMessage("All data has been reset", 5000)

    def _restore_window_geometry(self):
        """Restore saved window position, size, and maximized state."""
        # Set minimum size to prevent button text clipping in Task List
        # Minimum width accounts for 7 buttons + spacing + margins
        self.setMinimumSize(1125, 600)

        try:
            saved_geometry = self.settings_dao.get('window_geometry_main')

            if not saved_geometry:
                # First run - use defaults
                self.setGeometry(100, 100, 1000, 700)
                return

            # Validate screen still exists
            app = QApplication.instance()
            screens = app.screens()
            screen_number = saved_geometry.get('screen_number', 0)

            if screen_number >= len(screens):
                # Screen no longer exists, use primary screen
                screen_number = 0

            target_screen = screens[screen_number]
            screen_geometry = target_screen.availableGeometry()

            # Get saved geometry values
            x = saved_geometry.get('x', 100)
            y = saved_geometry.get('y', 100)
            width = saved_geometry.get('width', 1000)
            height = saved_geometry.get('height', 700)

            # Ensure at least 100px of the window is visible on screen
            if (x + width < screen_geometry.x() + 100 or
                x > screen_geometry.x() + screen_geometry.width() - 100 or
                y > screen_geometry.y() + screen_geometry.height() - 100):
                # Window would be off-screen, center on target screen
                x = screen_geometry.x() + (screen_geometry.width() - width) // 2
                y = screen_geometry.y() + (screen_geometry.height() - height) // 2

            # Apply geometry
            self.setGeometry(x, y, width, height)

            # Move to correct screen if needed (only if windowHandle is available)
            window_handle = self.windowHandle()
            if window_handle:
                window_handle.setScreen(target_screen)

            # Apply maximized state
            if saved_geometry.get('is_maximized', False):
                self.showMaximized()

        except Exception as e:
            # On error, fall back to defaults
            print(f"Warning: Failed to restore window geometry: {e}")
            self.setGeometry(100, 100, 1000, 700)

    def _save_window_geometry(self):
        """Save current window geometry to settings."""
        try:
            # Don't save while maximized - save the restored geometry
            if self.isMaximized():
                # Use normalGeometry() to get pre-maximized size
                geometry = self.normalGeometry()
            else:
                geometry = self.geometry()

            # Determine which screen the window is on
            window_center = self.geometry().center()
            app = QApplication.instance()
            screens = app.screens()
            screen_number = 0

            for i, screen in enumerate(screens):
                if screen.geometry().contains(window_center):
                    screen_number = i
                    break

            geometry_data = {
                'x': geometry.x(),
                'y': geometry.y(),
                'width': geometry.width(),
                'height': geometry.height(),
                'is_maximized': self.isMaximized(),
                'screen_number': screen_number
            }

            self.settings_dao.set(
                'window_geometry_main',
                geometry_data,
                'json',
                'Main window geometry and state'
            )

        except Exception as e:
            # Silently fail - don't crash on save errors
            print(f"Warning: Failed to save window geometry: {e}")

    def resizeEvent(self, event):
        """Handle window resize - save geometry with debouncing."""
        super().resizeEvent(event)

        # Use QTimer to debounce saves
        if not hasattr(self, '_geometry_save_timer'):
            self._geometry_save_timer = QTimer()
            self._geometry_save_timer.setSingleShot(True)
            self._geometry_save_timer.timeout.connect(self._save_window_geometry)

        self._geometry_save_timer.start(500)  # Save after 500ms of no changes

    def moveEvent(self, event):
        """Handle window move - save geometry with debouncing."""
        super().moveEvent(event)

        # Reuse same timer as resizeEvent
        if not hasattr(self, '_geometry_save_timer'):
            self._geometry_save_timer = QTimer()
            self._geometry_save_timer.setSingleShot(True)
            self._geometry_save_timer.timeout.connect(self._save_window_geometry)

        self._geometry_save_timer.start(500)

    def closeEvent(self, event):
        """Handle application close event."""
        # Save window geometry before closing
        self._save_window_geometry()

        # Shutdown scheduler gracefully (Phase 6)
        self.resurfacing_scheduler.shutdown(wait=True, timeout=5)

        # Close database connection
        self.db_connection.close()

        event.accept()
