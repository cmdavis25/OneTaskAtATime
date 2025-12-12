"""
Main Window - Primary application window for OneTaskAtATime

Provides the main application container with menu bar and navigation.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QMenu, QAction, QStatusBar, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from .focus_mode import FocusModeWidget
from .task_form_dialog import TaskFormDialog
from .postpone_dialog import DeferDialog, DelegateDialog
from ..services.task_service import TaskService
from ..database.connection import DatabaseConnection


class MainWindow(QMainWindow):
    """
    Main application window.

    Phase 2: Integrates Focus Mode with full task lifecycle support.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("OneTaskAtATime")
        self.setGeometry(100, 100, 900, 700)

        # Initialize database and services
        self.db_connection = DatabaseConnection()
        self.task_service = TaskService(self.db_connection)

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

        # Load initial task
        self._refresh_focus_task()

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Focus Mode widget
        self.focus_mode = FocusModeWidget()
        layout.addWidget(self.focus_mode)

        # Connect signals
        self.focus_mode.task_completed.connect(self._on_task_completed)
        self.focus_mode.task_deferred.connect(self._on_task_deferred)
        self.focus_mode.task_delegated.connect(self._on_task_delegated)
        self.focus_mode.task_someday.connect(self._on_task_someday)
        self.focus_mode.task_trashed.connect(self._on_task_trashed)
        self.focus_mode.task_refreshed.connect(self._refresh_focus_task)

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

        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.setStatusTip("Refresh current task")
        refresh_action.triggered.connect(self._refresh_focus_task)
        view_menu.addAction(refresh_action)

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
        """Handle task deferral."""
        current_task = self.focus_mode.get_current_task()
        if not current_task:
            return

        dialog = DeferDialog(current_task.title, parent=self)
        if dialog.exec_():
            result = dialog.get_result()
            if result:
                self.task_service.defer_task(
                    task_id,
                    result['start_date'],
                    result.get('reason'),
                    result.get('notes')
                )
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

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About OneTaskAtATime",
            "OneTaskAtATime v1.0.0\n\n"
            "A focused to-do list application designed to help users\n"
            "concentrate on executing one task at a time using\n"
            "GTD-inspired principles.\n\n"
            "Phase 2: MVP Focus Mode Complete"
        )

    def closeEvent(self, event):
        """Handle application close event."""
        # Close database connection
        self.db_connection.close()
        event.accept()
