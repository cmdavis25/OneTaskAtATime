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
from .notification_panel import NotificationPanel
from .settings_dialog import SettingsDialog
from .review_delegated_dialog import ReviewDelegatedDialog
from .review_someday_dialog import ReviewSomedayDialog
from .activated_tasks_dialog import ActivatedTasksDialog
from ..services.task_service import TaskService
from ..services.comparison_service import ComparisonService
from ..services.postpone_workflow_service import PostponeWorkflowService
from ..services.notification_manager import NotificationManager
from ..services.toast_notification_service import ToastNotificationService
from ..services.resurfacing_scheduler import ResurfacingScheduler
from ..database.connection import DatabaseConnection
from ..models.enums import TaskState
from ..models.notification import Notification


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

        # Initialize Phase 6 services (notification system and scheduler)
        self.notification_manager = NotificationManager(self.db_connection.get_connection())
        self.toast_service = ToastNotificationService(self.db_connection.get_connection())
        self.notification_manager.set_toast_service(self.toast_service)

        # Initialize resurfacing scheduler
        self.resurfacing_scheduler = ResurfacingScheduler(
            self.db_connection.get_connection(),
            self.notification_manager
        )

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Connect scheduler signals
        self._connect_scheduler_signals()

        # Start background scheduler
        self.resurfacing_scheduler.start()

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

        # Notification panel (Phase 6)
        self.notification_panel = NotificationPanel(
            self.db_connection.get_connection(),
            self.notification_manager
        )
        self.notification_panel.action_requested.connect(self._on_notification_action)
        layout.addWidget(self.notification_panel)

        # Stacked widget for switching views
        self.stacked_widget = QStackedWidget()
        layout.addWidget(self.stacked_widget)

        # Focus Mode widget
        self.focus_mode = FocusModeWidget(self.db_connection)
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
        self.focus_mode.filters_changed.connect(self._refresh_focus_task)

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

        delete_all_tasks_action = QAction("Delete &All Tasks...", self)
        delete_all_tasks_action.setStatusTip("Delete all tasks from the database")
        delete_all_tasks_action.triggered.connect(self._delete_all_tasks)
        tools_menu.addAction(delete_all_tasks_action)

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

    def _delete_all_tasks(self):
        """Delete all tasks from the database with confirmation."""
        reply = QMessageBox.warning(
            self,
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

    def _show_settings(self):
        """Show settings dialog (Phase 6)."""
        dialog = SettingsDialog(self.db_connection.get_connection(), self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec_()

    def _on_settings_saved(self):
        """Handle settings saved signal."""
        # Reload scheduler settings
        self.resurfacing_scheduler.reload_settings()
        self.statusBar().showMessage("Settings saved and scheduler updated", 3000)

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
        QMessageBox.about(
            self,
            "About OneTaskAtATime",
            "OneTaskAtATime v1.0.0\n\n"
            "A focused to-do list application designed to help users\n"
            "concentrate on executing one task at a time using\n"
            "GTD-inspired principles.\n\n"
            "Phase 6: Task Resurfacing and Notification System Complete"
        )

    def closeEvent(self, event):
        """Handle application close event."""
        # Shutdown scheduler gracefully (Phase 6)
        self.resurfacing_scheduler.shutdown(wait=True, timeout=5)

        # Close database connection
        self.db_connection.close()

        event.accept()
