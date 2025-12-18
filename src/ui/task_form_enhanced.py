"""
Enhanced Task Form Dialog - Comprehensive task creation and editing

Phase 4: Full-featured task form with contexts, project tags, and all fields.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QComboBox, QFormLayout,
    QCheckBox, QListWidget, QListWidgetItem, QGroupBox, QScrollArea,
    QWidget, QMessageBox, QCalendarWidget, QSpinBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon
from datetime import date
from typing import Optional, List
from ..models.task import Task
from ..models.context import Context
from ..models.project_tag import ProjectTag
from ..models.enums import Priority, TaskState
from ..models.recurrence_pattern import RecurrencePattern, RecurrenceType
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
        self.advanced_recurrence_pattern: Optional[RecurrencePattern] = None  # Stores advanced pattern from dialog

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
        context_layout = QHBoxLayout()
        self.context_combo = QComboBox()
        self.context_combo.addItem("(No Context)", None)
        for context in self.contexts:
            self.context_combo.addItem(context.name, context.id)
        context_layout.addWidget(self.context_combo)

        new_context_btn = QPushButton("+ New")
        new_context_btn.setMaximumWidth(60)
        new_context_btn.clicked.connect(self._on_new_context)
        context_layout.addWidget(new_context_btn)

        org_layout.addRow("Context:", context_layout)

        # Project Tags
        tags_container = QVBoxLayout()

        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QListWidget.MultiSelection)
        self.tags_list.setMaximumHeight(100)
        for tag in self.project_tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.UserRole, tag.id)
            self.tags_list.addItem(item)
        tags_container.addWidget(self.tags_list)

        new_tag_btn = QPushButton("+ New Project Tag")
        new_tag_btn.clicked.connect(self._on_new_project_tag)
        tags_container.addWidget(new_tag_btn)

        org_layout.addRow("Project Tags:", tags_container)

        org_group.setLayout(org_layout)
        form_layout.addWidget(org_group)

        # === State & Scheduling ===
        state_group = QGroupBox("State & Scheduling")
        state_layout = QFormLayout()
        state_layout.setSpacing(10)

        # State (available for both new and existing tasks)
        self.state_combo = QComboBox()
        self.state_combo.addItem("Active", TaskState.ACTIVE.value)
        self.state_combo.addItem("Deferred", TaskState.DEFERRED.value)
        self.state_combo.addItem("Delegated", TaskState.DELEGATED.value)
        self.state_combo.addItem("Someday/Maybe", TaskState.SOMEDAY.value)
        self.state_combo.addItem("Completed", TaskState.COMPLETED.value)
        self.state_combo.addItem("Trash", TaskState.TRASH.value)
        self.state_combo.currentTextChanged.connect(self._on_state_changed)
        # Default to Active for new tasks
        if self.is_new:
            self.state_combo.setCurrentIndex(0)  # Active
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

        # === Recurrence ===
        recurrence_group = QGroupBox("Recurrence")
        recurrence_layout = QVBoxLayout()
        recurrence_layout.setSpacing(10)

        # Enable recurrence checkbox
        self.is_recurring_check = QCheckBox("Make this a recurring task")
        self.is_recurring_check.stateChanged.connect(self._on_recurring_toggled)
        recurrence_layout.addWidget(self.is_recurring_check)

        # Recurrence options container
        self.recurrence_options_widget = QWidget()
        recurrence_options_layout = QFormLayout()
        recurrence_options_layout.setSpacing(10)

        # Pattern type selector
        pattern_layout = QHBoxLayout()
        self.recurrence_type_combo = QComboBox()
        self.recurrence_type_combo.addItem("Daily", RecurrenceType.DAILY.value)
        self.recurrence_type_combo.addItem("Weekly", RecurrenceType.WEEKLY.value)
        self.recurrence_type_combo.addItem("Monthly", RecurrenceType.MONTHLY.value)
        self.recurrence_type_combo.addItem("Yearly", RecurrenceType.YEARLY.value)
        self.recurrence_type_combo.addItem("Custom", RecurrenceType.CUSTOM.value)
        self.recurrence_type_combo.currentIndexChanged.connect(self._on_recurrence_type_changed)
        pattern_layout.addWidget(self.recurrence_type_combo)

        # Interval spinner
        interval_container = QHBoxLayout()
        interval_container.addWidget(QLabel("every"))
        self.recurrence_interval_spin = QSpinBox()
        self.recurrence_interval_spin.setMinimum(1)
        self.recurrence_interval_spin.setMaximum(365)
        self.recurrence_interval_spin.setValue(1)
        interval_container.addWidget(self.recurrence_interval_spin)
        self.recurrence_interval_label = QLabel("day(s)")
        interval_container.addWidget(self.recurrence_interval_label)
        interval_container.addStretch()
        pattern_layout.addLayout(interval_container)
        pattern_layout.addStretch()

        recurrence_options_layout.addRow("Pattern:", pattern_layout)

        # Advanced pattern button
        advanced_layout = QHBoxLayout()
        self.recurrence_details_btn = QPushButton("Advanced Pattern...")
        self.recurrence_details_btn.clicked.connect(self._on_recurrence_details_clicked)
        advanced_layout.addWidget(self.recurrence_details_btn)
        advanced_layout.addStretch()
        recurrence_options_layout.addRow("", advanced_layout)

        # Elo sharing checkbox
        self.share_elo_check = QCheckBox("Share priority rating across all occurrences")
        self.share_elo_check.setToolTip(
            "When enabled, all instances of this recurring task share the same Elo rating.\n"
            "When disabled, each occurrence starts with a fresh Elo rating of 1500."
        )
        recurrence_options_layout.addRow("", self.share_elo_check)

        # End date (optional)
        end_date_layout = QHBoxLayout()
        self.has_recurrence_end_check = QCheckBox("Stop recurring after")
        self.has_recurrence_end_check.stateChanged.connect(self._on_recurrence_end_toggled)
        end_date_layout.addWidget(self.has_recurrence_end_check)

        self.recurrence_end_date_edit = QLineEdit()
        self.recurrence_end_date_edit.setPlaceholderText("YYYY-MM-DD")
        self.recurrence_end_date_edit.setMaximumWidth(120)
        self.recurrence_end_date_edit.setEnabled(False)
        end_date_layout.addWidget(self.recurrence_end_date_edit)

        self.recurrence_end_calendar_btn = QPushButton("📅")
        self.recurrence_end_calendar_btn.setMaximumWidth(40)
        self.recurrence_end_calendar_btn.setEnabled(False)
        self.recurrence_end_calendar_btn.clicked.connect(lambda: self._show_calendar(self.recurrence_end_date_edit))
        end_date_layout.addWidget(self.recurrence_end_calendar_btn)

        end_date_layout.addStretch()
        recurrence_options_layout.addRow("End date:", end_date_layout)

        self.recurrence_options_widget.setLayout(recurrence_options_layout)
        self.recurrence_options_widget.setEnabled(False)  # Disabled by default
        recurrence_layout.addWidget(self.recurrence_options_widget)

        # Info label
        self.recurrence_info_label = QLabel(
            "Note: Recurring tasks must have a due date. The next occurrence will be created when you complete this task."
        )
        self.recurrence_info_label.setWordWrap(True)
        self.recurrence_info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 8px; background-color: #f8f9fa;")
        self.recurrence_info_label.setVisible(False)
        recurrence_layout.addWidget(self.recurrence_info_label)

        recurrence_group.setLayout(recurrence_layout)
        form_layout.addWidget(recurrence_group)

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

    def _on_recurring_toggled(self, state: int):
        """Enable/disable recurrence options based on checkbox."""
        enabled = state == Qt.Checked
        self.recurrence_options_widget.setEnabled(enabled)
        self.recurrence_info_label.setVisible(enabled)

        # Validate due date if recurring is enabled
        if enabled and not self.has_due_date_check.isChecked():
            QMessageBox.warning(
                self,
                "Due Date Required",
                "Recurring tasks must have a due date. Please set a due date first."
            )
            self.is_recurring_check.setChecked(False)
            return

    def _on_recurrence_type_changed(self, index: int):
        """Update interval label based on selected recurrence type."""
        recurrence_type = self.recurrence_type_combo.currentData()

        if recurrence_type == RecurrenceType.DAILY.value:
            self.recurrence_interval_label.setText("day(s)")
        elif recurrence_type == RecurrenceType.WEEKLY.value:
            self.recurrence_interval_label.setText("week(s)")
        elif recurrence_type == RecurrenceType.MONTHLY.value:
            self.recurrence_interval_label.setText("month(s)")
        elif recurrence_type == RecurrenceType.YEARLY.value:
            self.recurrence_interval_label.setText("year(s)")
        else:  # CUSTOM
            self.recurrence_interval_label.setText("period(s)")

    def _on_recurrence_details_clicked(self):
        """Open advanced pattern configuration dialog."""
        from .recurrence_pattern_dialog import RecurrencePatternDialog

        # Get current due date for preview
        current_due_date = None
        if self.has_due_date_check.isChecked():
            date_str = self.due_date_edit.text().strip()
            if date_str:
                try:
                    parts = date_str.split('-')
                    current_due_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    pass

        # Get current pattern if editing
        current_pattern = None
        try:
            pattern_type = RecurrenceType(self.recurrence_type_combo.currentData())
            interval = self.recurrence_interval_spin.value()
            current_pattern = RecurrencePattern(type=pattern_type, interval=interval)
        except Exception:
            pass

        # Open dialog
        dialog = RecurrencePatternDialog(
            pattern=current_pattern,
            current_due_date=current_due_date,
            parent=self
        )

        if dialog.exec_():
            # User saved the pattern
            pattern = dialog.get_pattern()
            if pattern:
                # Store the advanced pattern
                self.advanced_recurrence_pattern = pattern

                # Update the basic form controls to match
                for i in range(self.recurrence_type_combo.count()):
                    if self.recurrence_type_combo.itemData(i) == pattern.type.value:
                        self.recurrence_type_combo.setCurrentIndex(i)
                        break

                self.recurrence_interval_spin.setValue(pattern.interval)

                QMessageBox.information(
                    self,
                    "Pattern Saved",
                    f"Advanced pattern configured:\n{pattern.to_human_readable()}"
                )

    def _on_recurrence_end_toggled(self, state: int):
        """Enable/disable recurrence end date field based on checkbox."""
        enabled = state == Qt.Checked
        self.recurrence_end_date_edit.setEnabled(enabled)
        self.recurrence_end_calendar_btn.setEnabled(enabled)

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

    def _on_new_context(self):
        """Handle creating a new context."""
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            "New Context",
            "Enter context name (e.g., @computer, @home):"
        )

        if not ok or not name.strip():
            return

        name = name.strip()

        # Check if context already exists
        if not self.db_connection:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return

        try:
            context_dao = ContextDAO(self.db_connection.get_connection())
            existing = context_dao.get_by_name(name)

            if existing:
                QMessageBox.warning(
                    self,
                    "Duplicate Context",
                    f"A context named '{name}' already exists."
                )
                return

            # Create new context
            new_context = Context(name=name)
            created_context = context_dao.create(new_context)

            # Reload contexts
            self._load_reference_data()

            # Rebuild context combo
            current_selection = self.context_combo.currentData()
            self.context_combo.clear()
            self.context_combo.addItem("(No Context)", None)
            for context in self.contexts:
                self.context_combo.addItem(context.name, context.id)

            # Select the newly created context
            for i in range(self.context_combo.count()):
                if self.context_combo.itemData(i) == created_context.id:
                    self.context_combo.setCurrentIndex(i)
                    break

            QMessageBox.information(
                self,
                "Success",
                f"Context '{name}' created successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create context: {str(e)}"
            )

    def _on_new_project_tag(self):
        """Handle creating a new project tag."""
        from PyQt5.QtWidgets import QInputDialog, QColorDialog

        name, ok = QInputDialog.getText(
            self,
            "New Project Tag",
            "Enter project tag name:"
        )

        if not ok or not name.strip():
            return

        name = name.strip()

        # Check if tag already exists
        if not self.db_connection:
            QMessageBox.warning(self, "Error", "Database connection not available.")
            return

        try:
            tag_dao = ProjectTagDAO(self.db_connection.get_connection())
            existing = tag_dao.get_by_name(name)

            if existing:
                QMessageBox.warning(
                    self,
                    "Duplicate Project Tag",
                    f"A project tag named '{name}' already exists."
                )
                return

            # Optionally select a color
            color = QColorDialog.getColor()
            color_hex = None
            if color.isValid():
                color_hex = color.name()

            # Create new project tag
            new_tag = ProjectTag(name=name, color=color_hex)
            created_tag = tag_dao.create(new_tag)

            # Reload project tags
            self._load_reference_data()

            # Rebuild tags list
            selected_tags = []
            for i in range(self.tags_list.count()):
                item = self.tags_list.item(i)
                if item.isSelected():
                    selected_tags.append(item.data(Qt.UserRole))

            self.tags_list.clear()
            for tag in self.project_tags:
                item = QListWidgetItem(tag.name)
                item.setData(Qt.UserRole, tag.id)
                # Restore selection state
                if tag.id in selected_tags or tag.id == created_tag.id:
                    item.setSelected(True)
                self.tags_list.addItem(item)

            QMessageBox.information(
                self,
                "Success",
                f"Project tag '{name}' created successfully."
            )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to create project tag: {str(e)}"
            )

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

        # State
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

        # Recurrence
        if self.task.is_recurring:
            self.is_recurring_check.setChecked(True)

            # Parse and load recurrence pattern
            if self.task.recurrence_pattern:
                try:
                    pattern = RecurrencePattern.from_json(self.task.recurrence_pattern)

                    # Store as advanced pattern if it has advanced configuration
                    if pattern.days_of_week or pattern.day_of_month is not None or \
                       pattern.week_of_month is not None or pattern.weekday_of_month is not None:
                        self.advanced_recurrence_pattern = pattern

                    # Set type
                    for i in range(self.recurrence_type_combo.count()):
                        if self.recurrence_type_combo.itemData(i) == pattern.type.value:
                            self.recurrence_type_combo.setCurrentIndex(i)
                            break

                    # Set interval
                    self.recurrence_interval_spin.setValue(pattern.interval)

                except Exception as e:
                    print(f"Error loading recurrence pattern: {e}")

            # Elo sharing
            if self.task.share_elo_rating:
                self.share_elo_check.setChecked(True)

            # End date
            if self.task.recurrence_end_date:
                self.has_recurrence_end_check.setChecked(True)
                self.recurrence_end_date_edit.setText(self.task.recurrence_end_date.strftime("%Y-%m-%d"))

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

        # Get state
        state_value = self.state_combo.currentData()
        task_state = TaskState(state_value)

        # Get recurrence fields
        is_recurring = self.is_recurring_check.isChecked()
        recurrence_pattern = None
        recurrence_end_date = None
        share_elo_rating = False

        if is_recurring:
            # Validate that due date is set
            if not due_date:
                QMessageBox.warning(
                    self,
                    "Invalid Recurrence",
                    "Recurring tasks must have a due date."
                )
                return None

            # Build recurrence pattern
            try:
                # Use advanced pattern if configured via dialog
                if self.advanced_recurrence_pattern:
                    pattern = self.advanced_recurrence_pattern
                else:
                    # Use basic pattern from form
                    pattern_type = RecurrenceType(self.recurrence_type_combo.currentData())
                    interval = self.recurrence_interval_spin.value()

                    pattern = RecurrencePattern(
                        type=pattern_type,
                        interval=interval
                    )

                recurrence_pattern = pattern.to_json()
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create recurrence pattern: {str(e)}"
                )
                return None

            # Get Elo sharing preference
            share_elo_rating = self.share_elo_check.isChecked()

            # Get end date
            if self.has_recurrence_end_check.isChecked():
                end_date_str = self.recurrence_end_date_edit.text().strip()
                if end_date_str:
                    try:
                        parts = end_date_str.split('-')
                        recurrence_end_date = date(int(parts[0]), int(parts[1]), int(parts[2]))

                        # Validate end date is after due date
                        if recurrence_end_date <= due_date:
                            QMessageBox.warning(
                                self,
                                "Invalid End Date",
                                "Recurrence end date must be after the due date."
                            )
                            return None
                    except (ValueError, IndexError):
                        QMessageBox.warning(
                            self,
                            "Invalid Date",
                            "Recurrence end date must be in YYYY-MM-DD format."
                        )
                        return None

        if self.is_new:
            # Create new task
            task = Task(
                title=self.title_edit.text().strip(),
                description=self.description_edit.toPlainText().strip() or None,
                base_priority=self.priority_combo.currentData(),
                due_date=due_date,
                state=task_state,
                start_date=start_date,
                delegated_to=delegated_to,
                follow_up_date=follow_up_date,
                context_id=context_id,
                project_tags=selected_tags,
                is_recurring=is_recurring,
                recurrence_pattern=recurrence_pattern,
                share_elo_rating=share_elo_rating,
                recurrence_end_date=recurrence_end_date
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
            task.state = task_state
            task.is_recurring = is_recurring
            task.recurrence_pattern = recurrence_pattern
            task.share_elo_rating = share_elo_rating
            task.recurrence_end_date = recurrence_end_date

        return task
