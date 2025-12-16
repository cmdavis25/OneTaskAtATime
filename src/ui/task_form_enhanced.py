"""
Enhanced Task Form Dialog - Comprehensive task creation and editing

Phase 4: Full-featured task form with contexts, project tags, and all fields.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QFormLayout,
    QCheckBox, QListWidget, QListWidgetItem, QGroupBox, QScrollArea,
    QWidget, QMessageBox, QCalendarWidget
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon
from datetime import date
from typing import Optional, List
from ..models.task import Task
from ..models.context import Context
from ..models.project_tag import ProjectTag
from ..models.enums import Priority, TaskState
from ..database.connection import DatabaseConnection
from ..database.context_dao import ContextDAO
from ..database.project_tag_dao import ProjectTagDAO
from ..database.dependency_dao import DependencyDAO
from ..database.task_dao import TaskDAO


class EnhancedTaskFormDialog(QDialog):
    """
    Comprehensive dialog for creating or editing tasks.

    Features:
    - All task fields (title, description, priority, due date, start date)
    - Context selection
    - Project tag multi-select
    - State management
    - Delegation fields
    - Scrollable form for long content

    Phase 4: Full task management interface
    """

    def __init__(self, task: Optional[Task] = None,
                 db_connection: Optional[DatabaseConnection] = None,
                 parent=None):
        """
        Initialize the enhanced task form.

        Args:
            task: Existing task to edit, or None to create new
            db_connection: Database connection for loading contexts/tags
            parent: Parent widget
        """
        super().__init__(parent)
        self.task = task
        self.is_new = (task is None)
        self.db_connection = db_connection

        # Load reference data
        self.contexts: List[Context] = []
        self.project_tags: List[ProjectTag] = []
        self.dependencies: List[int] = []  # List of blocking task IDs
        if db_connection:
            self._load_reference_data()
            if task and task.id:
                self._load_dependencies()

        self._init_ui()

        if task is not None:
            self._load_task_data()

    def _load_reference_data(self):
        """Load contexts and project tags from database."""
        if not self.db_connection:
            return

        try:
            context_dao = ContextDAO(self.db_connection.get_connection())
            self.contexts = context_dao.get_all()

            tag_dao = ProjectTagDAO(self.db_connection.get_connection())
            self.project_tags = tag_dao.get_all()
        except Exception as e:
            print(f"Error loading reference data: {e}")

    def _load_dependencies(self):
        """Load existing dependencies for this task."""
        if not self.db_connection or not self.task or not self.task.id:
            return

        try:
            dependency_dao = DependencyDAO(self.db_connection.get_connection())
            deps = dependency_dao.get_dependencies_for_task(self.task.id)
            self.dependencies = [dep.blocking_task_id for dep in deps]
        except Exception as e:
            print(f"Error loading dependencies: {e}")

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("New Task" if self.is_new else "Edit Task")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        self.setLayout(main_layout)

        # Header
        header_label = QLabel("Create a new task" if self.is_new else "Edit task")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(header_label)

        # Scrollable form area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame)

        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        form_widget.setLayout(form_layout)

        # === Basic Information ===
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)

        # Title (required)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Enter task title...")
        basic_layout.addRow("Title*:", self.title_edit)

        # Description (optional)
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Add detailed description (optional)...")
        self.description_edit.setMaximumHeight(100)
        basic_layout.addRow("Description:", self.description_edit)

        basic_group.setLayout(basic_layout)
        form_layout.addWidget(basic_group)

        # === Priority & Urgency ===
        priority_group = QGroupBox("Priority & Urgency")
        priority_layout = QFormLayout()
        priority_layout.setSpacing(10)

        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("Low", Priority.LOW.value)
        self.priority_combo.addItem("Medium", Priority.MEDIUM.value)
        self.priority_combo.addItem("High", Priority.HIGH.value)
        self.priority_combo.setCurrentIndex(1)  # Default to Medium
        priority_layout.addRow("Priority:", self.priority_combo)

        # Due date (optional)
        due_date_layout = QHBoxLayout()

        self.has_due_date_check = QCheckBox("Set due date")
        self.has_due_date_check.stateChanged.connect(self._on_due_date_toggled)
        due_date_layout.addWidget(self.has_due_date_check)

        self.due_date_edit = QLineEdit()
        self.due_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.due_date_edit.setMaximumWidth(120)
        self.due_date_edit.setEnabled(False)
        due_date_layout.addWidget(self.due_date_edit)

        self.due_date_calendar_btn = QPushButton("📅")
        self.due_date_calendar_btn.setMaximumWidth(40)
        self.due_date_calendar_btn.setEnabled(False)
        self.due_date_calendar_btn.clicked.connect(lambda: self._show_calendar(self.due_date_edit))
        due_date_layout.addWidget(self.due_date_calendar_btn)

        due_date_layout.addStretch()

        priority_layout.addRow("Due date:", due_date_layout)

        priority_group.setLayout(priority_layout)
        form_layout.addWidget(priority_group)

        # === Organization ===
        org_group = QGroupBox("Organization")
        org_layout = QFormLayout()
        org_layout.setSpacing(10)

        # Context
        self.context_combo = QComboBox()
        self.context_combo.addItem("(No Context)", None)
        for context in self.contexts:
            self.context_combo.addItem(context.name, context.id)
        org_layout.addRow("Context:", self.context_combo)

        # Project Tags
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.MultiSelection)
        self.tags_list.setMaximumHeight(100)
        for tag in self.project_tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.UserRole, tag.id)
            self.tags_list.addItem(item)
        org_layout.addRow("Project Tags:", self.tags_list)

        org_group.setLayout(org_layout)
        form_layout.addWidget(org_group)

        # === State & Scheduling ===
        state_group = QGroupBox("State & Scheduling")
        state_layout = QFormLayout()
        state_layout.setSpacing(10)

        # State (only show for editing existing tasks)
        if not self.is_new:
            self.state_combo = QComboBox()
            self.state_combo.addItem("Active", TaskState.ACTIVE.value)
            self.state_combo.addItem("Deferred", TaskState.DEFERRED.value)
            self.state_combo.addItem("Delegated", TaskState.DELEGATED.value)
            self.state_combo.addItem("Someday/Maybe", TaskState.SOMEDAY.value)
            self.state_combo.addItem("Completed", TaskState.COMPLETED.value)
            self.state_combo.addItem("Trash", TaskState.TRASH.value)
            self.state_combo.currentTextChanged.connect(self._on_state_changed)
            state_layout.addRow("State:", self.state_combo)

        # Start date (for deferred tasks)
        start_date_layout = QHBoxLayout()

        self.has_start_date_check = QCheckBox("Set start date (defer until)")
        self.has_start_date_check.stateChanged.connect(self._on_start_date_toggled)
        start_date_layout.addWidget(self.has_start_date_check)

        self.start_date_edit = QLineEdit()
        self.start_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.start_date_edit.setMaximumWidth(120)
        self.start_date_edit.setEnabled(False)
        start_date_layout.addWidget(self.start_date_edit)

        self.start_date_calendar_btn = QPushButton("📅")
        self.start_date_calendar_btn.setMaximumWidth(40)
        self.start_date_calendar_btn.setEnabled(False)
        self.start_date_calendar_btn.clicked.connect(lambda: self._show_calendar(self.start_date_edit))
        start_date_layout.addWidget(self.start_date_calendar_btn)

        start_date_layout.addStretch()

        state_layout.addRow("Start date:", start_date_layout)

        state_group.setLayout(state_layout)
        form_layout.addWidget(state_group)

        # === Delegation ===
        delegation_group = QGroupBox("Delegation")
        delegation_layout = QFormLayout()
        delegation_layout.setSpacing(10)

        # Delegated to
        self.delegated_to_edit = QLineEdit()
        self.delegated_to_edit.setPlaceholderText("Person or system name...")
        delegation_layout.addRow("Delegated to:", self.delegated_to_edit)

        # Follow-up date
        followup_date_layout = QHBoxLayout()

        self.has_followup_check = QCheckBox("Set follow-up date")
        self.has_followup_check.stateChanged.connect(self._on_followup_toggled)
        followup_date_layout.addWidget(self.has_followup_check)

        self.followup_date_edit = QLineEdit()
        self.followup_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.followup_date_edit.setMaximumWidth(120)
        self.followup_date_edit.setEnabled(False)
        followup_date_layout.addWidget(self.followup_date_edit)

        self.followup_date_calendar_btn = QPushButton("📅")
        self.followup_date_calendar_btn.setMaximumWidth(40)
        self.followup_date_calendar_btn.setEnabled(False)
        self.followup_date_calendar_btn.clicked.connect(lambda: self._show_calendar(self.followup_date_edit))
        followup_date_layout.addWidget(self.followup_date_calendar_btn)

        followup_date_layout.addStretch()

        delegation_layout.addRow("Follow-up date:", followup_date_layout)

        delegation_group.setLayout(delegation_layout)
        form_layout.addWidget(delegation_group)

        # === Dependencies ===
        dependencies_group = QGroupBox("Dependencies")
        dependencies_layout = QVBoxLayout()
        dependencies_layout.setSpacing(10)

        # Info label
        dep_info_label = QLabel("Specify which tasks must be completed before this task can begin:")
        dep_info_label.setWordWrap(True)
        dep_info_label.setStyleSheet("color: #666; font-size: 9pt;")
        dependencies_layout.addWidget(dep_info_label)

        # Dependencies list display
        self.dependencies_label = QLabel("No dependencies")
        self.dependencies_label.setWordWrap(True)
        self.dependencies_label.setStyleSheet("padding: 8px; background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px;")
        dependencies_layout.addWidget(self.dependencies_label)

        # Manage dependencies button
        manage_deps_btn = QPushButton("Manage Dependencies...")
        manage_deps_btn.clicked.connect(self._on_manage_dependencies)
        # Only enable for existing tasks (can't set dependencies on unsaved tasks)
        if self.is_new:
            manage_deps_btn.setEnabled(False)
            manage_deps_btn.setToolTip("Save the task first before adding dependencies")
        dependencies_layout.addWidget(manage_deps_btn)

        dependencies_group.setLayout(dependencies_layout)
        form_layout.addWidget(dependencies_group)

        scroll_area.setWidget(form_widget)
        main_layout.addWidget(scroll_area)

        # Info text
        info_label = QLabel("* Required field")
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        main_layout.addWidget(info_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        save_button = QPushButton("Save" if self.is_new else "Update")
        save_button.setDefault(True)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_button.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_button)

        main_layout.addLayout(button_layout)

    def _on_due_date_toggled(self, state: int):
        """Enable/disable due date field and calendar button based on checkbox."""
        enabled = state == Qt.Checked
        self.due_date_edit.setEnabled(enabled)
        self.due_date_calendar_btn.setEnabled(enabled)

    def _on_start_date_toggled(self, state: int):
        """Enable/disable start date field and calendar button based on checkbox."""
        enabled = state == Qt.Checked
        self.start_date_edit.setEnabled(enabled)
        self.start_date_calendar_btn.setEnabled(enabled)

    def _on_followup_toggled(self, state: int):
        """Enable/disable follow-up date field and calendar button based on checkbox."""
        enabled = state == Qt.Checked
        self.followup_date_edit.setEnabled(enabled)
        self.followup_date_calendar_btn.setEnabled(enabled)

    def _on_state_changed(self, state_text: str):
        """Handle state changes to show relevant fields."""
        # Could auto-enable/disable delegation fields based on state
        pass

    def _show_calendar(self, date_field: QLineEdit):
        """Show calendar widget and populate the date field with selected date."""
        # Create a dialog to hold the calendar
        calendar_dialog = QDialog(self)
        calendar_dialog.setWindowTitle("Select Date")
        layout = QVBoxLayout()

        # Create calendar widget
        calendar = QCalendarWidget()

        # Set calendar to date from field if valid, otherwise today
        current_text = date_field.text().strip()
        if current_text:
            try:
                parts = current_text.split('-')
                if len(parts) == 3:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                    calendar.setSelectedDate(QDate(year, month, day))
            except (ValueError, IndexError):
                # Invalid date format, use today
                calendar.setSelectedDate(QDate.currentDate())
        else:
            calendar.setSelectedDate(QDate.currentDate())

        layout.addWidget(calendar)

        # Add buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(calendar_dialog.reject)
        button_layout.addWidget(cancel_btn)

        select_btn = QPushButton("Select")
        select_btn.setDefault(True)
        select_btn.clicked.connect(calendar_dialog.accept)
        button_layout.addWidget(select_btn)

        layout.addLayout(button_layout)
        calendar_dialog.setLayout(layout)

        # Show dialog and handle result
        if calendar_dialog.exec_() == QDialog.Accepted:
            selected_date = calendar.selectedDate()
            date_field.setText(selected_date.toString("yyyy-MM-dd"))

    def _on_manage_dependencies(self):
        """Open the dependency selection dialog."""
        if not self.task or not self.task.id:
            QMessageBox.warning(
                self,
                "Cannot Manage Dependencies",
                "Please save the task first before adding dependencies."
            )
            return

        from .dependency_selection_dialog import DependencySelectionDialog

        dialog = DependencySelectionDialog(
            task=self.task,
            db_connection=self.db_connection,
            parent=self
        )

        if dialog.exec_():
            # Reload dependencies after changes
            self._load_dependencies()
            self._update_dependencies_display()

    def _update_dependencies_display(self):
        """Update the dependencies label with current dependencies."""
        if not self.dependencies:
            self.dependencies_label.setText("No dependencies")
            return

        # Get task titles for the dependencies
        if not self.db_connection:
            self.dependencies_label.setText(f"{len(self.dependencies)} blocking task(s)")
            return

        try:
            task_dao = TaskDAO(self.db_connection.get_connection())
            task_titles = []
            for task_id in self.dependencies:
                task = task_dao.get_by_id(task_id)
                if task:
                    task_titles.append(f"• {task.title}")

            if task_titles:
                self.dependencies_label.setText("\n".join(task_titles))
            else:
                self.dependencies_label.setText("No dependencies")
        except Exception as e:
            print(f"Error updating dependencies display: {e}")
            self.dependencies_label.setText(f"{len(self.dependencies)} blocking task(s)")

    def _load_task_data(self):
        """Load data from existing task into form fields."""
        if self.task is None:
            return

        # Title
        self.title_edit.setText(self.task.title)

        # Description
        if self.task.description:
            self.description_edit.setText(self.task.description)

        # Priority
        priority_index = self.task.base_priority - 1  # Convert 1-3 to 0-2
        self.priority_combo.setCurrentIndex(priority_index)

        # Due date
        if self.task.due_date:
            self.has_due_date_check.setChecked(True)
            self.due_date_edit.setText(self.task.due_date.strftime("%Y-%m-%d"))

        # Context
        if self.task.context_id:
            for i in range(self.context_combo.count()):
                if self.context_combo.itemData(i) == self.task.context_id:
                    self.context_combo.setCurrentIndex(i)
                    break

        # Project tags
        if self.task.project_tags:
            for i in range(self.tags_list.count()):
                item = self.tags_list.item(i)
                tag_id = item.data(Qt.UserRole)
                if tag_id in self.task.project_tags:
                    item.setSelected(True)

        # State (only for existing tasks)
        if not self.is_new:
            for i in range(self.state_combo.count()):
                if self.state_combo.itemData(i) == self.task.state.value:
                    self.state_combo.setCurrentIndex(i)
                    break

        # Start date
        if self.task.start_date:
            self.has_start_date_check.setChecked(True)
            self.start_date_edit.setText(self.task.start_date.strftime("%Y-%m-%d"))

        # Delegation
        if self.task.delegated_to:
            self.delegated_to_edit.setText(self.task.delegated_to)

        if self.task.follow_up_date:
            self.has_followup_check.setChecked(True)
            self.followup_date_edit.setText(self.task.follow_up_date.strftime("%Y-%m-%d"))

        # Update dependencies display
        self._update_dependencies_display()

    def _on_save_clicked(self):
        """Validate and save the task."""
        # Validate title
        title = self.title_edit.text().strip()
        if not title:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter a task title."
            )
            self.title_edit.setFocus()
            return

        # Accept the dialog
        self.accept()

    def get_updated_task(self) -> Optional[Task]:
        """
        Get the updated Task object.

        Returns:
            Task object with form data, or None if canceled
        """
        if self.result() != QDialog.Accepted:
            return None

        # Get due date (if enabled)
        due_date = None
        if self.has_due_date_check.isChecked():
            date_str = self.due_date_edit.text().strip()
            if date_str:
                try:
                    parts = date_str.split('-')
                    due_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    QMessageBox.warning(
                        self,
                        "Invalid Date",
                        "Due date must be in YYYY-MM-DD format."
                    )
                    return None

        # Get start date (if enabled)
        start_date = None
        if self.has_start_date_check.isChecked():
            date_str = self.start_date_edit.text().strip()
            if date_str:
                try:
                    parts = date_str.split('-')
                    start_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    QMessageBox.warning(
                        self,
                        "Invalid Date",
                        "Start date must be in YYYY-MM-DD format."
                    )
                    return None

        # Get follow-up date (if enabled)
        follow_up_date = None
        if self.has_followup_check.isChecked():
            date_str = self.followup_date_edit.text().strip()
            if date_str:
                try:
                    parts = date_str.split('-')
                    follow_up_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    QMessageBox.warning(
                        self,
                        "Invalid Date",
                        "Follow-up date must be in YYYY-MM-DD format."
                    )
                    return None

        # Get selected project tags
        selected_tags = []
        for i in range(self.tags_list.count()):
            item = self.tags_list.item(i)
            if item.isSelected():
                selected_tags.append(item.data(Qt.UserRole))

        # Get context
        context_id = self.context_combo.currentData()

        # Get delegation
        delegated_to = self.delegated_to_edit.text().strip() or None

        if self.is_new:
            # Create new task
            task = Task(
                title=self.title_edit.text().strip(),
                description=self.description_edit.toPlainText().strip() or None,
                base_priority=self.priority_combo.currentData(),
                due_date=due_date,
                state=TaskState.ACTIVE,
                start_date=start_date,
                delegated_to=delegated_to,
                follow_up_date=follow_up_date,
                context_id=context_id,
                project_tags=selected_tags
            )
        else:
            # Update existing task
            task = self.task
            task.title = self.title_edit.text().strip()
            task.description = self.description_edit.toPlainText().strip() or None
            task.base_priority = self.priority_combo.currentData()
            task.due_date = due_date
            task.start_date = start_date
            task.delegated_to = delegated_to
            task.follow_up_date = follow_up_date
            task.context_id = context_id
            task.project_tags = selected_tags

            # Update state (only for existing tasks)
            state_value = self.state_combo.currentData()
            task.state = TaskState(state_value)

        return task
