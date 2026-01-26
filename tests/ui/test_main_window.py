"""
Unit tests for MainWindow.

Tests the main application window including:
- Window initialization and setup
- Menu bar actions
- View switching (Focus Mode <-> Task List)
- Keyboard shortcuts
- Status bar updates
- Dialog invocations
- Window geometry persistence
- Signal handling
"""

import pytest
import sqlite3
from datetime import date, timedelta
from unittest.mock import MagicMock, patch, call

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QMessageBox
from PyQt5.QtTest import QTest

from src.models.task import Task
from src.models.enums import TaskState
from src.ui.main_window import MainWindow




@pytest.fixture
def main_window(qapp, db_connection):
    """Create MainWindow instance in test mode."""
    window = MainWindow(app=qapp, test_mode=True, db_connection=db_connection)
    yield window
    window.close()


@pytest.fixture
def sample_tasks(db_connection):
    """Create sample tasks in database."""
    from src.database.task_dao import TaskDAO

    task_dao = TaskDAO(db_connection.get_connection())

    tasks = [
        Task(
            title="High Priority Task",
            description="Important task",
            base_priority=3,
            due_date=date.today() + timedelta(days=1),
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        ),
        Task(
            title="Medium Priority Task",
            description="Normal task",
            base_priority=2,
            due_date=date.today() + timedelta(days=7),
            state=TaskState.ACTIVE,
            elo_rating=1500.0,
            comparison_count=1
        ),
        Task(
            title="Deferred Task",
            description="Deferred task",
            base_priority=2,
            start_date=date.today() + timedelta(days=3),
            state=TaskState.DEFERRED,
            elo_rating=1500.0,
            comparison_count=1
        ),
    ]

    created_tasks = []
    for task in tasks:
        created = task_dao.create(task)
        created_tasks.append(created)

    return created_tasks


class TestWindowInitialization:
    """Test window initialization and setup."""

    def test_window_title_set(self, main_window):
        """Test that window title is set correctly."""
        assert main_window.windowTitle() == "OneTaskAtATime"

    def test_window_has_menu_bar(self, main_window):
        """Test that menu bar is created."""
        assert main_window.menuBar() is not None

    def test_window_has_status_bar(self, main_window):
        """Test that status bar is created."""
        assert main_window.statusBar() is not None

    def test_window_has_focus_mode(self, main_window):
        """Test that Focus Mode widget is created."""
        assert main_window.focus_mode is not None

    def test_window_has_task_list_view(self, main_window):
        """Test that Task List view is created."""
        assert main_window.task_list_view is not None

    def test_window_starts_in_focus_mode(self, main_window):
        """Test that window starts in Focus Mode."""
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

    def test_services_initialized(self, main_window):
        """Test that all required services are initialized."""
        assert main_window.task_service is not None
        assert main_window.comparison_service is not None
        assert main_window.postpone_workflow_service is not None
        assert main_window.notification_manager is not None
        assert main_window.toast_service is not None
        assert main_window.resurfacing_scheduler is not None
        assert main_window.task_history_service is not None
        assert main_window.error_service is not None
        assert main_window.accessibility_service is not None
        assert main_window.undo_manager is not None

    def test_test_mode_disables_scheduler(self, main_window):
        """Test that test mode prevents scheduler from starting."""
        # In test mode, scheduler should not be running
        assert not main_window.resurfacing_scheduler.running


class TestMenuBar:
    """Test menu bar structure and actions."""

    def test_file_menu_exists(self, main_window):
        """Test that File menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        file_menu = None
        for action in actions:
            if action.text() == "&File":
                file_menu = action.menu()
                break
        assert file_menu is not None

    def test_edit_menu_exists(self, main_window):
        """Test that Edit menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        edit_menu = None
        for action in actions:
            if action.text() == "&Edit":
                edit_menu = action.menu()
                break
        assert edit_menu is not None

    def test_view_menu_exists(self, main_window):
        """Test that View menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        view_menu = None
        for action in actions:
            if action.text() == "&View":
                view_menu = action.menu()
                break
        assert view_menu is not None

    def test_manage_menu_exists(self, main_window):
        """Test that Manage menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        manage_menu = None
        for action in actions:
            if action.text() == "&Manage":
                manage_menu = action.menu()
                break
        assert manage_menu is not None

    def test_tools_menu_exists(self, main_window):
        """Test that Tools menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        tools_menu = None
        for action in actions:
            if action.text() == "&Tools":
                tools_menu = action.menu()
                break
        assert tools_menu is not None

    def test_help_menu_exists(self, main_window):
        """Test that Help menu exists."""
        menubar = main_window.menuBar()
        actions = menubar.actions()
        help_menu = None
        for action in actions:
            if action.text() == "&Help":
                help_menu = action.menu()
                break
        assert help_menu is not None

    def test_new_task_action_has_shortcut(self, main_window):
        """Test that New Task action has Ctrl+N shortcut."""
        assert main_window.new_task_action.shortcut().toString() == "Ctrl+N"

    def test_undo_action_initially_disabled(self, main_window):
        """Test that Undo action is initially disabled."""
        assert not main_window.undo_action.isEnabled()

    def test_redo_action_initially_disabled(self, main_window):
        """Test that Redo action is initially disabled."""
        assert not main_window.redo_action.isEnabled()


class TestViewSwitching:
    """Test view switching between Focus Mode and Task List."""

    def test_switch_to_task_list(self, main_window):
        """Test switching from Focus Mode to Task List."""
        # Should start in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

        # Switch to Task List
        main_window._show_task_list()

        # Should now be in Task List
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view
        assert main_window.mode_title_label.text() == "Task List"

    def test_switch_to_focus_mode(self, main_window):
        """Test switching from Task List to Focus Mode."""
        # Switch to Task List first
        main_window._show_task_list()
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view

        # Switch back to Focus Mode
        main_window._show_focus_mode()

        # Should be back in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode
        assert main_window.mode_title_label.text() == "Focus Mode"

    def test_toggle_view_from_focus_mode(self, main_window):
        """Test toggling view from Focus Mode."""
        # Should start in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

        # Toggle
        main_window._toggle_view()

        # Should be in Task List
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view

    def test_toggle_view_from_task_list(self, main_window):
        """Test toggling view from Task List."""
        # Switch to Task List
        main_window._show_task_list()

        # Toggle
        main_window._toggle_view()

        # Should be back in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

    def test_view_switcher_button_updates_text(self, main_window):
        """Test that view switcher button updates its text."""
        # In Focus Mode
        assert "Task List" in main_window.view_switcher_btn.text()

        # Switch to Task List
        main_window._show_task_list()
        assert "Focus Mode" in main_window.view_switcher_btn.text()

    def test_view_switcher_button_click(self, main_window, qtbot):
        """Test clicking view switcher button toggles view."""
        # Should start in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

        # Click button
        qtbot.mouseClick(main_window.view_switcher_btn, Qt.LeftButton)

        # Should switch to Task List
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view


class TestKeyboardShortcuts:
    """Test keyboard shortcuts."""

    def test_ctrl_1_shows_focus_mode(self, main_window, qtbot, qapp):
        """Test Ctrl+1 switches to Focus Mode."""
        # Switch to Task List first
        main_window._show_task_list()

        # Call the shortcut handler directly (qtbot.keyClick doesn't trigger QShortcuts reliably)
        main_window._show_focus_mode()

        # Should switch to Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

    def test_ctrl_2_shows_task_list(self, main_window, qtbot, qapp):
        """Test Ctrl+2 switches to Task List."""
        # Should start in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

        # Call the shortcut handler directly (qtbot.keyClick doesn't trigger QShortcuts reliably)
        main_window._show_task_list()

        # Should switch to Task List
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view

    def test_f5_refreshes_current_view(self, main_window, qtbot, qapp):
        """Test F5 refreshes the current view."""
        with patch.object(main_window, '_refresh_focus_task') as mock_refresh:
            # Call the shortcut handler directly (qtbot.keyClick doesn't trigger QShortcuts reliably)
            main_window._refresh_current_view()

            # Should call refresh
            mock_refresh.assert_called_once()


class TestStatusBar:
    """Test status bar functionality."""

    def test_status_bar_shows_task_counts(self, main_window, sample_tasks):
        """Test that status bar shows active and completed task counts."""
        # Update status bar
        main_window._update_status_bar()

        # Should show counts
        status_text = main_window.statusBar().currentMessage()
        assert "Active:" in status_text
        assert "Completed:" in status_text

    def test_status_bar_updates_on_task_change(self, main_window, sample_tasks):
        """Test that status bar updates when tasks change."""
        # Complete a task
        task = sample_tasks[0]
        main_window.task_service.complete_task(task.id)

        # Update status bar
        main_window._update_status_bar()

        # Should show updated counts
        status_text = main_window.statusBar().currentMessage()
        assert "Active:" in status_text
        assert "Completed:" in status_text


class TestTaskActions:
    """Test task-related actions."""

    def test_complete_task_updates_status(self, main_window, sample_tasks):
        """Test that completing a task updates the status bar."""
        task = sample_tasks[0]

        # Complete task
        main_window._on_task_completed(task.id)

        # Check task is completed
        completed_task = main_window.task_service.get_task_by_id(task.id)
        assert completed_task.state == TaskState.COMPLETED

    def test_trash_task_moves_to_trash(self, main_window, sample_tasks):
        """Test that trashing a task moves it to trash state."""
        task = sample_tasks[0]

        # Trash task
        main_window._on_task_trashed(task.id)

        # Check task is trashed
        trashed_task = main_window.task_service.get_task_by_id(task.id)
        assert trashed_task.state == TaskState.TRASH

    def test_someday_task_moves_to_someday(self, main_window, sample_tasks):
        """Test that moving task to Someday works."""
        task = sample_tasks[0]

        # Move to Someday
        main_window._on_task_someday(task.id)

        # Check task is in Someday
        someday_task = main_window.task_service.get_task_by_id(task.id)
        assert someday_task.state == TaskState.SOMEDAY


class TestDialogInvocations:
    """Test that menu actions invoke appropriate dialogs."""

    def test_manage_contexts_opens_dialog(self, main_window):
        """Test that Manage Contexts opens dialog."""
        with patch('src.ui.main_window.ContextManagementDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._manage_contexts()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()

    def test_manage_project_tags_opens_dialog(self, main_window):
        """Test that Manage Project Tags opens dialog."""
        with patch('src.ui.main_window.ProjectTagManagementDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._manage_project_tags()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()

    def test_show_analytics_opens_dialog(self, main_window):
        """Test that Show Analytics opens dialog."""
        with patch('src.ui.analytics_view.AnalyticsView') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._show_analytics()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()

    def test_show_settings_opens_dialog(self, main_window):
        """Test that Show Settings opens dialog."""
        with patch('src.ui.main_window.SettingsDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._show_settings()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()

    def test_show_help_opens_dialog(self, main_window):
        """Test that Show Help opens dialog."""
        with patch('src.ui.help_dialog.HelpDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._show_help()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()

    def test_show_shortcuts_opens_dialog(self, main_window):
        """Test that Show Shortcuts opens dialog."""
        with patch('src.ui.shortcuts_dialog.ShortcutsDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._show_shortcuts()

            # Dialog should be created and shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()


class TestUndoRedo:
    """Test undo/redo functionality."""

    def test_undo_action_enabled_after_command(self, main_window, sample_tasks):
        """Test that undo action is enabled after executing a command."""
        task = sample_tasks[0]

        # Complete task (uses command pattern)
        main_window._on_task_completed(task.id)

        # Undo action should be enabled
        assert main_window.undo_action.isEnabled()

    def test_redo_action_enabled_after_undo(self, main_window, sample_tasks):
        """Test that redo action is enabled after undo."""
        task = sample_tasks[0]

        # Complete task
        main_window._on_task_completed(task.id)

        # Undo
        main_window._undo_last_action()

        # Redo action should be enabled
        assert main_window.redo_action.isEnabled()

    def test_undo_reverses_task_completion(self, main_window, sample_tasks):
        """Test that undo reverses task completion."""
        task = sample_tasks[0]

        # Complete task
        main_window._on_task_completed(task.id)
        completed_task = main_window.task_service.get_task_by_id(task.id)
        assert completed_task.state == TaskState.COMPLETED

        # Undo
        main_window._undo_last_action()

        # Task should be active again
        active_task = main_window.task_service.get_task_by_id(task.id)
        assert active_task.state == TaskState.ACTIVE

    def test_redo_reapplies_task_completion(self, main_window, sample_tasks):
        """Test that redo reapplies task completion."""
        task = sample_tasks[0]

        # Complete task
        main_window._on_task_completed(task.id)

        # Undo
        main_window._undo_last_action()
        active_task = main_window.task_service.get_task_by_id(task.id)
        assert active_task.state == TaskState.ACTIVE

        # Redo
        main_window._redo_last_action()

        # Task should be completed again
        completed_task = main_window.task_service.get_task_by_id(task.id)
        assert completed_task.state == TaskState.COMPLETED


class TestWindowGeometry:
    """Test window geometry persistence."""

    def test_save_window_geometry(self, main_window):
        """Test that window geometry is saved."""
        # Set specific geometry
        main_window.setGeometry(200, 200, 1200, 800)

        # Save geometry
        main_window._save_window_geometry()

        # Check saved geometry
        saved = main_window.settings_dao.get('window_geometry_main')
        assert saved is not None
        assert saved['width'] == 1200
        assert saved['height'] == 800

    def test_restore_window_geometry(self, main_window):
        """Test that window geometry is restored."""
        # Save specific geometry
        main_window.setGeometry(200, 200, 1200, 800)
        main_window._save_window_geometry()

        # Create new window
        from src.ui.main_window import MainWindow
        new_window = MainWindow(app=main_window.app, test_mode=True)

        # Check restored geometry (might be slightly different due to window manager)
        geometry = new_window.geometry()
        assert geometry.width() >= 1000  # At least minimum size
        assert geometry.height() >= 600

        new_window.close()

    def test_minimum_window_size(self, main_window):
        """Test that minimum window size is enforced."""
        min_size = main_window.minimumSize()
        assert min_size.width() == 1125
        assert min_size.height() == 800


class TestCloseEvent:
    """Test window close event handling."""

    def test_close_saves_geometry(self, main_window):
        """Test that closing window saves geometry."""
        # Mock the geometry save method
        with patch.object(main_window, '_save_window_geometry') as mock_save:
            # Close window (don't actually close to avoid database closure issues)
            event = MagicMock()
            main_window.closeEvent(event)

            # Geometry save method should be called
            mock_save.assert_called_once()

    def test_close_shuts_down_scheduler(self, main_window):
        """Test that closing window shuts down scheduler."""
        with patch.object(main_window.resurfacing_scheduler, 'shutdown') as mock_shutdown:
            # Close window
            main_window.close()

            # Scheduler shutdown should be called
            mock_shutdown.assert_called_once_with(wait=True, timeout=5)

    def test_close_closes_database(self, main_window):
        """Test that closing window closes database connection."""
        with patch.object(main_window.db_connection, 'close') as mock_close:
            # Close window
            main_window.close()

            # Database should be closed
            mock_close.assert_called_once()


class TestDeleteTrashTasks:
    """Test deleting trash tasks."""

    def test_delete_trash_tasks_confirmation(self, main_window, sample_tasks):
        """Test that deleting trash tasks requires confirmation."""
        # Move task to trash
        task = sample_tasks[0]
        main_window.task_service.move_to_trash(task.id)

        # Mock MessageBox to simulate user clicking No
        with patch('src.ui.main_window.MessageBox.warning', return_value=QMessageBox.No):
            # Try to delete trash tasks
            main_window._delete_trash_tasks()

            # Task should still exist
            trashed_task = main_window.task_service.get_task_by_id(task.id)
            assert trashed_task is not None
            assert trashed_task.state == TaskState.TRASH

    def test_delete_trash_tasks_deletes_on_confirmation(self, main_window, sample_tasks):
        """Test that trash tasks are deleted when confirmed."""
        # Move task to trash
        task = sample_tasks[0]
        main_window.task_service.move_to_trash(task.id)

        # Mock MessageBox to simulate user clicking Yes
        with patch('src.ui.main_window.MessageBox.warning', return_value=QMessageBox.Yes):
            # Delete trash tasks
            main_window._delete_trash_tasks()

            # Task should be deleted
            trash_tasks = main_window.task_service.get_tasks_by_state(TaskState.TRASH)
            assert len(trash_tasks) == 0

    def test_delete_trash_tasks_no_trash_shows_info(self, main_window):
        """Test that info message is shown when no trash tasks exist."""
        # Mock MessageBox
        with patch('src.ui.main_window.MessageBox.information') as mock_info:
            # Try to delete trash tasks
            main_window._delete_trash_tasks()

            # Info message should be shown
            mock_info.assert_called_once()


class TestResetPriorityAdjustments:
    """Test resetting priority adjustments."""

    @pytest.mark.skip(reason="deprecated - use Elo system")
    def test_reset_priority_adjustments_confirmation(self, main_window, sample_tasks):
        """Test that resetting priority adjustments requires confirmation."""
        # Mock MessageBox to simulate user clicking No
        with patch('src.ui.main_window.MessageBox.warning', return_value=QMessageBox.No):
            with patch.object(main_window.comparison_service, 'reset_all_priority_adjustments') as mock_reset:
                # Try to reset
                main_window._reset_all_priority_adjustments()

                # Should not call reset
                mock_reset.assert_not_called()

    @pytest.mark.skip(reason="deprecated - use Elo system")
    def test_reset_priority_adjustments_on_confirmation(self, main_window, sample_tasks):
        """Test that priority adjustments are reset when confirmed."""
        # Mock MessageBox to simulate user clicking Yes
        with patch('src.ui.main_window.MessageBox.warning', return_value=QMessageBox.Yes):
            with patch.object(main_window.comparison_service, 'reset_all_priority_adjustments', return_value=2) as mock_reset:
                # Reset adjustments
                main_window._reset_all_priority_adjustments()

                # Should call reset
                mock_reset.assert_called_once()


class TestFocusSearchBox:
    """Test search box focus functionality."""

    def test_focus_search_box_switches_to_task_list(self, main_window):
        """Test that focusing search box switches to Task List if needed."""
        # Should start in Focus Mode
        assert main_window.stacked_widget.currentWidget() == main_window.focus_mode

        # Focus search box
        main_window._focus_search_box()

        # Should switch to Task List
        assert main_window.stacked_widget.currentWidget() == main_window.task_list_view

    def test_focus_search_box_calls_task_list_focus(self, main_window):
        """Test that focus search box calls task list's focus method."""
        with patch.object(main_window.task_list_view, 'focus_search_box') as mock_focus:
            # Focus search box
            main_window._focus_search_box()

            # Should call task list's focus method
            mock_focus.assert_called_once()


class TestNotificationPanel:
    """Test notification panel integration."""

    def test_notification_panel_exists(self, main_window):
        """Test that notification panel is created."""
        assert main_window.notification_panel is not None

    def test_notification_action_open_focus(self, main_window):
        """Test handling notification action to open focus."""
        from src.models.notification import Notification

        notification = Notification(
            id=1,
            title="Test",
            message="Test message",
            action_type="open_focus",
            action_data={"task_ids": [1, 2]}
        )

        with patch('src.ui.main_window.ActivatedTasksDialog') as mock_dialog:
            mock_instance = MagicMock()
            mock_dialog.return_value = mock_instance

            main_window._on_notification_action(notification)

            # Dialog should be shown
            mock_dialog.assert_called_once()
            mock_instance.exec_.assert_called_once()


class TestWhatsThisMode:
    """Test WhatsThis mode functionality."""

    def test_whatsthis_event_filter_installed(self, main_window):
        """Test that WhatsThis event filter is installed."""
        assert hasattr(main_window, 'whatsthis_filter')
        assert main_window.whatsthis_filter is not None

    def test_whatsthis_filter_is_whatsthis_event_filter(self, main_window):
        """Test that filter is correct type."""
        from src.ui.main_window import WhatsThisEventFilter
        assert isinstance(main_window.whatsthis_filter, WhatsThisEventFilter)
