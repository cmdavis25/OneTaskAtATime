"""
Main Window - Primary application window for OneTaskAtATime

Provides the main application container with menu bar and navigation.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QMenu, QAction, QStatusBar, QMessageBox, QStackedWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .focus_mode import FocusModeWidget
from .task_form_dialog import TaskFormDialog
from .task_form_enhanced import EnhancedTaskFormDialog
from .task_list_view import TaskListView
from .context_management_dialog import ContextManagementDialog
from .project_tag_management_dialog import ProjectTagManagementDialog
from .postpone_dialog import DeferDialog, DelegateDialog
from .comparison_dialog import ComparisonDialog, MultipleComparisonDialog
from ..services.task_service import TaskService
from ..services.comparison_service import ComparisonService
from ..services.postpone_workflow_service import PostponeWorkflowService
from ..database.connection import DatabaseConnection
from ..models.enums import TaskState


class MainWindow(QMainWindow):
    """
    Main application window.

    Phase 4: Full task management interface with multiple views.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("OneTaskAtATime")
        self.setGeometry(100, 100, 1000, 700)

        # Initialize database and services
        self.db_connection = DatabaseConnection()
        self.task_service = TaskService(self.db_connection)
        self.comparison_service = ComparisonService(self.db_connection)
        self.postpone_workflow_service = PostponeWorkflowService(self.db_connection.get_connection())

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Load initial task
        self._refresh_focus_task()

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget with stacked layout for multiple views
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Stacked widget for switching views
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Focus Mode widget
        self.focus_mode = FocusModeWidget()
        self.stacked_widget.addWidget(self.focus_mode)

        # Task List View
        self.task_list_view = TaskListView(self.db_connection)
        self.stacked_widget.addWidget(self.task_list_view)

        # Connect Focus Mode signals
        self.focus_mode.task_completed.connect(self._on_task_completed)
        self.focus_mode.task_deferred.connect(self._on_task_deferred)
        self.focus_mode.task_delegated.connect(self._on_task_delegated)
        self.focus_mode.task_someday.connect(self._on_task_someday)
        self.focus_mode.task_trashed.connect(self._on_task_trashed)
        self.focus_mode.task_refreshed.connect(self._refresh_focus_task)

        # Connect Task List View signals
        self.task_list_view.task_created.connect(self._on_task_list_changed)
        self.task_list_view.task_updated.connect(self._on_task_list_changed)
        self.task_list_view.task_deleted.connect(self._on_task_list_changed)

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

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menubar.addMenu("&View")

        focus_mode_action = QAction("&Focus Mode", self)
        focus_mode_action.setShortcut("Ctrl+F")
        focus_mode_action.setStatusTip("Switch to Focus Mode")
        focus_mode_action.triggered.connect(self._show_focus_mode)
        view_menu.addAction(focus_mode_action)

        task_list_action = QAction("&Task List", self)
        task_list_action.setShortcut("Ctrl+L")
        task_list_action.setStatusTip("Switch to Task List view")
        task_list_action.triggered.connect(self._show_task_list)
        view_menu.addAction(task_list_action)

        view_menu.addSeparator()

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

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("About OneTaskAtATime")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
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
        # First check if there are tied tasks
        tied_tasks = self.task_service.get_tied_tasks()

        if len(tied_tasks) >= 2:
            # Show comparison dialog
            self._handle_tied_tasks(tied_tasks)
        else:
            # No tie, get the top task
            task = self.task_service.get_focus_task()
            self.focus_mode.set_task(task)
            self._update_status_bar()

    def _on_new_task(self):
        """Handle New Task action."""
        dialog = TaskFormDialog(parent=self)
        if dialog.exec_():
            task = dialog.get_updated_task()
            if task:
                self.task_service.create_task(task)
                self._refresh_focus_task()
                self.statusBar().showMessage("Task created successfully", 3000)

    def _on_task_completed(self, task_id: int):
        """Handle task completion."""
        self.task_service.complete_task(task_id)
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

            # Normal defer flow
            self.task_service.defer_task(
                task_id,
                result['start_date'],
                result.get('reason'),
                result.get('notes')
            )

            # Handle workflow results
            self._handle_postpone_workflows(result, task_id, result.get('notes', ''))

            self.statusBar().showMessage("Task deferred", 3000)
            self._refresh_focus_task()

    def _on_task_delegated(self, task_id: int):
        """Handle task delegation."""
        current_task = self.focus_mode.get_current_task()
        if not current_task:
            return

        dialog = DelegateDialog(current_task.title, parent=self)
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
                QMessageBox.information(self, "Blocker Created", result['message'])
            else:
                QMessageBox.warning(self, "Blocker Failed", result['message'])

        # Handle subtask workflow
        if subtask_result := postpone_result.get('subtask_result'):
            result = self.postpone_workflow_service.handle_subtask_breakdown(
                task_id,
                notes,
                subtask_result['subtask_titles'],
                subtask_result['delete_original']
            )
            if result['success']:
                QMessageBox.information(self, "Tasks Created", result['message'])
            else:
                QMessageBox.warning(self, "Breakdown Failed", result['message'])

        # Note: Dependency workflow doesn't need handling here because
        # DependencySelectionDialog saves dependencies directly

    def _handle_tied_tasks(self, tied_tasks):
        """
        Handle tied tasks by showing comparison dialog.

        Args:
            tied_tasks: List of tasks tied for top priority
        """
        if len(tied_tasks) == 2:
            # Simple pairwise comparison
            dialog = ComparisonDialog(tied_tasks[0], tied_tasks[1], self)
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
            dialog = MultipleComparisonDialog(tied_tasks, self)
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
        reply = QMessageBox.warning(
            self,
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

    def _show_focus_mode(self):
        """Switch to Focus Mode view."""
        self.stacked_widget.setCurrentWidget(self.focus_mode)
        self._refresh_focus_task()
        self.statusBar().showMessage("Switched to Focus Mode", 2000)

    def _show_task_list(self):
        """Switch to Task List view."""
        self.stacked_widget.setCurrentWidget(self.task_list_view)
        self.task_list_view.refresh_tasks()
        self.statusBar().showMessage("Switched to Task List", 2000)

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

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OneTaskAtATime",
            "OneTaskAtATime v1.0.0\n\n"
            "A focused to-do list application designed to help users\n"
            "concentrate on executing one task at a time using\n"
            "GTD-inspired principles.\n\n"
            "Phase 4: Task Management Interface Complete"
        )

    def closeEvent(self, event):
        """Handle application close event."""
        # Close database connection
        self.db_connection.close()
        event.accept()
