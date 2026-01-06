"""
Dependency Selection Dialog - Manage task dependencies

Phase 4: Allows users to select blocking tasks for a given task.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from typing import List, Optional, Set
from ..models.task import Task
from ..models.dependency import Dependency
from ..database.connection import DatabaseConnection
from ..database.task_dao import TaskDAO
from ..database.dependency_dao import DependencyDAO
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class DependencySelectionDialog(QDialog, GeometryMixin):
    """
    Dialog for selecting task dependencies.

    Features:
    - View available tasks that could block current task
    - Add dependencies (with circular dependency detection)
    - Remove existing dependencies
    - Search/filter available tasks
    - Visual indication of already-selected dependencies

    Args:
        task: The task to manage dependencies for
        db_connection: Database connection
        parent: Parent widget
    """

    dependencies_changed = pyqtSignal()

    def __init__(self, task: Task, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the dependency selection dialog.

        Args:
            task: Task to manage dependencies for
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.db_connection = db_connection
        self.task_dao = TaskDAO(db_connection.get_connection())
        self.dependency_dao = DependencyDAO(db_connection.get_connection())

        self.all_tasks: List[Task] = []
        self.current_dependencies: Set[int] = set()  # Set of blocking task IDs
        self.created_blocking_task_ids: List[int] = []  # Track tasks created during this session

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=400)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(f"Manage Dependencies - {self.task.title}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel(f"Manage Dependencies for: {self.task.title}")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Select tasks that must be completed before this task can be started.\n"
            "This task will not appear in Focus Mode until all blocking tasks are complete."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: Available tasks
        available_layout = QVBoxLayout()

        available_label = QLabel("Available Tasks:")
        available_label.setStyleSheet("font-weight: bold;")
        available_layout.addWidget(available_label)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tasks...")
        self.search_box.textChanged.connect(self._filter_available_tasks)
        available_layout.addWidget(self.search_box)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SingleSelection)
        available_layout.addWidget(self.available_list)

        # Button layout for Add and New Task
        button_layout = QHBoxLayout()

        new_task_btn = QPushButton("+ New Task")
        new_task_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        new_task_btn.clicked.connect(self._on_new_task)
        button_layout.addWidget(new_task_btn)

        add_btn = QPushButton("Add Dependency →")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_btn.clicked.connect(self._on_add_dependency)
        button_layout.addWidget(add_btn)

        available_layout.addLayout(button_layout)

        content_layout.addLayout(available_layout, 1)

        # Right side: Current dependencies
        dependencies_layout = QVBoxLayout()

        dependencies_label = QLabel("Current Dependencies (Blocking Tasks):")
        dependencies_label.setStyleSheet("font-weight: bold;")
        dependencies_layout.addWidget(dependencies_label)

        self.dependencies_list = QListWidget()
        self.dependencies_list.setSelectionMode(QListWidget.SingleSelection)
        dependencies_layout.addWidget(self.dependencies_list)

        remove_btn = QPushButton("← Remove Dependency")
        remove_btn.setStyleSheet("""
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
        remove_btn.clicked.connect(self._on_remove_dependency)
        dependencies_layout.addWidget(remove_btn)

        content_layout.addLayout(dependencies_layout, 1)

        layout.addLayout(content_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Dependencies")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        save_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(save_btn)

        layout.addLayout(bottom_layout)

    def _load_data(self):
        """Load tasks and existing dependencies."""
        from ..models.enums import TaskState

        # Load all tasks except the current task, and exclude completed/trash tasks
        self.all_tasks = [
            t for t in self.task_dao.get_all()
            if t.id != self.task.id
            and t.id is not None
            and t.state not in (TaskState.COMPLETED, TaskState.TRASH)
        ]

        # Load existing dependencies
        if self.task.id:
            dependencies = self.dependency_dao.get_dependencies_for_task(self.task.id)
            self.current_dependencies = {dep.blocking_task_id for dep in dependencies}

        self._refresh_lists()

    def _refresh_lists(self):
        """Refresh both lists."""
        self._refresh_available_tasks()
        self._refresh_dependencies_list()

    def _refresh_available_tasks(self):
        """Refresh the available tasks list."""
        self.available_list.clear()

        search_text = self.search_box.text().lower()

        for task in self.all_tasks:
            # Skip if already a dependency
            if task.id in self.current_dependencies:
                continue

            # Filter by search text
            if search_text and search_text not in task.title.lower():
                continue

            item = QListWidgetItem(f"[{task.state.value}] {task.title}")
            item.setData(Qt.UserRole, task.id)

            # Color-code by state
            if task.state.value == "completed":
                item.setForeground(Qt.gray)

            self.available_list.addItem(item)

    def _refresh_dependencies_list(self):
        """Refresh the current dependencies list."""
        self.dependencies_list.clear()

        for task in self.all_tasks:
            if task.id in self.current_dependencies:
                item = QListWidgetItem(f"[{task.state.value}] {task.title}")
                item.setData(Qt.UserRole, task.id)

                # Color-code by state
                if task.state.value == "completed":
                    item.setForeground(Qt.gray)
                    item.setText(f"✓ {item.text()}")

                self.dependencies_list.addItem(item)

    def _filter_available_tasks(self):
        """Filter available tasks based on search text."""
        self._refresh_available_tasks()

    def _on_new_task(self):
        """Handle creating a new task from the dependency dialog."""
        from .task_form_enhanced import EnhancedTaskFormDialog

        # Create the dialog for a NEW task (task=None)
        dialog = EnhancedTaskFormDialog(
            task=None,
            db_connection=self.db_connection,
            parent=self
        )

        # Pre-fill default values from the blocked task
        # Priority
        for i in range(dialog.priority_combo.count()):
            if dialog.priority_combo.itemData(i) == self.task.base_priority:
                dialog.priority_combo.setCurrentIndex(i)
                break

        # Due date
        if self.task.due_date:
            dialog.due_date_edit.setText(self.task.due_date.strftime("%Y-%m-%d"))
            dialog.has_due_date_check.setChecked(True)
            dialog.due_date_edit.setEnabled(True)
            dialog.due_date_calendar_btn.setEnabled(True)

        # Context
        if self.task.context_id:
            for i in range(dialog.context_combo.count()):
                if dialog.context_combo.itemData(i) == self.task.context_id:
                    dialog.context_combo.setCurrentIndex(i)
                    break

        # Project tags - use the tag_checkboxes dictionary
        if self.task.project_tags:
            for tag_id in self.task.project_tags:
                if tag_id in dialog.tag_checkboxes:
                    dialog.tag_checkboxes[tag_id].setChecked(True)

        if dialog.exec_():
            new_task = dialog.get_updated_task()
            if new_task:
                # Save the task to the database
                try:
                    created_task = self.task_dao.create(new_task)

                    # Track this as a created blocking task
                    if created_task.id:
                        self.created_blocking_task_ids.append(created_task.id)

                    # Reload the task list to include the new task
                    self._load_data()

                    MessageBox.information(
                        self,
                        self.db_connection.get_connection(),
                        "Success",
                        f"Task '{created_task.title}' created successfully."
                    )
                except Exception as e:
                    MessageBox.critical(
                        self,
                        self.db_connection.get_connection(),
                        "Error",
                        f"Failed to create task: {str(e)}"
                    )

    def _on_add_dependency(self):
        """Handle add dependency button click."""
        current_item = self.available_list.currentItem()
        if not current_item:
            MessageBox.warning(
                self,
                self.db_connection.get_connection(),
                "No Selection",
                "Please select a task to add as a dependency."
            )
            return

        blocking_task_id = current_item.data(Qt.UserRole)

        # Create dependency object
        dependency = Dependency(
            blocked_task_id=self.task.id,
            blocking_task_id=blocking_task_id
        )

        try:
            # Try to create the dependency (will check for circular dependencies)
            self.dependency_dao.create(dependency)

            # Add to current dependencies
            self.current_dependencies.add(blocking_task_id)

            # Refresh lists
            self._refresh_lists()

            self.dependencies_changed.emit()

            # Find task title for confirmation
            task_title = next(
                (t.title for t in self.all_tasks if t.id == blocking_task_id),
                "Unknown"
            )

            MessageBox.information(
                self,
                self.db_connection.get_connection(),
                "Success",
                f"Added dependency: '{self.task.title}' is now blocked by '{task_title}'."
            )

        except ValueError as e:
            MessageBox.warning(
                self,
                self.db_connection.get_connection(),
                "Cannot Add Dependency",
                str(e)
            )
        except Exception as e:
            MessageBox.critical(
                self,
                self.db_connection.get_connection(),
                "Error",
                f"Failed to add dependency: {str(e)}"
            )

    def _on_remove_dependency(self):
        """Handle remove dependency button click."""
        current_item = self.dependencies_list.currentItem()
        if not current_item:
            MessageBox.warning(
                self,
                self.db_connection.get_connection(),
                "No Selection",
                "Please select a dependency to remove."
            )
            return

        blocking_task_id = current_item.data(Qt.UserRole)

        reply = MessageBox.question(
            self,
            self.db_connection.get_connection(),
            "Remove Dependency",
            f"Are you sure you want to remove this dependency?\n\n"
            f"'{self.task.title}' will no longer be blocked by this task.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Delete the dependency
                self.dependency_dao.delete_by_tasks(self.task.id, blocking_task_id)

                # Remove from current dependencies
                self.current_dependencies.discard(blocking_task_id)

                # Refresh lists
                self._refresh_lists()

                self.dependencies_changed.emit()

                MessageBox.information(
                    self,
                    self.db_connection.get_connection(),
                    "Success",
                    "Dependency removed successfully."
                )

            except Exception as e:
                MessageBox.critical(
                    self,
                    self.db_connection.get_connection(),
                    "Error",
                    f"Failed to remove dependency: {str(e)}"
                )

    def get_created_blocking_task_ids(self) -> List[int]:
        """
        Get the list of blocking task IDs that were created during this dialog session.

        Returns:
            List of task IDs created as blocking tasks
        """
        return self.created_blocking_task_ids
