"""
Postpone Dialog - Captures reasons when users delay tasks.

This dialog helps identify blockers, dependencies, and tasks that need breakdown.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QTextEdit, QDateEdit, QLineEdit,
    QFormLayout, QWidget
)
from PyQt5.QtCore import Qt, QDate
from datetime import date
from typing import Optional, Dict, Any
from ..models.task import Task
from ..models.enums import PostponeReasonType
from ..database.connection import DatabaseConnection


class PostponeDialog(QDialog):
    """
    Dialog for capturing postpone reason and collecting necessary data.

    Depending on the reason selected, shows different input fields:
    - Defer: Date picker for start_date
    - Delegate: Person name and follow-up date
    """

    def __init__(self, task_title: str, action_type: str = "defer",
                 task: Optional[Task] = None, db_connection: Optional[DatabaseConnection] = None,
                 parent=None):
        """
        Initialize the postpone dialog.

        Args:
            task_title: Title of the task being postponed
            action_type: Either "defer" or "delegate"
            task: Full Task object (optional, needed for workflows)
            db_connection: DatabaseConnection wrapper (optional, needed for workflows)
            parent: Parent widget
        """
        super().__init__(parent)
        self.task_title = task_title
        self.action_type = action_type
        self.task = task
        self.db_connection = db_connection

        # Workflow result storage
        self.blocker_result = None
        self.subtask_result = None
        self.dependency_added = False

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        if self.action_type == "defer":
            self.setWindowTitle("Defer Task")
        else:
            self.setWindowTitle("Delegate Task")

        self.setMinimumWidth(500)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Title
        title_label = QLabel(f"Task: {self.task_title}")
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(title_label)

        # Reason section
        if self.action_type == "defer":
            self._create_defer_ui(layout)
        else:
            self._create_delegate_ui(layout)

        # Notes section
        notes_label = QLabel("Additional notes (optional):")
        layout.addWidget(notes_label)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Add any additional context...")
        layout.addWidget(self.notes_edit)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        confirm_button = QPushButton("Confirm")
        confirm_button.setDefault(True)
        confirm_button.setStyleSheet("""
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
        confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(confirm_button)

        layout.addLayout(button_layout)

    def _create_defer_ui(self, layout: QVBoxLayout):
        """Create UI elements for deferring a task."""
        # Why are you deferring?
        reason_label = QLabel("Why are you deferring this task?")
        reason_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(reason_label)

        # Reason radio buttons
        self.reason_group = QButtonGroup(self)

        self.reason_not_ready = QRadioButton("Not ready to work on it yet")
        self.reason_blocker = QRadioButton("Encountered a blocker")
        self.reason_dependency = QRadioButton("Waiting on another task")
        self.reason_subtasks = QRadioButton("Needs to be broken into smaller tasks")
        self.reason_other = QRadioButton("Other reason")

        # Use integer IDs for button group
        self.reason_group.addButton(self.reason_not_ready, 0)
        self.reason_group.addButton(self.reason_blocker, 1)
        self.reason_group.addButton(self.reason_dependency, 2)
        self.reason_group.addButton(self.reason_subtasks, 3)
        self.reason_group.addButton(self.reason_other, 4)

        # Set default
        self.reason_not_ready.setChecked(True)

        layout.addWidget(self.reason_not_ready)
        layout.addWidget(self.reason_blocker)
        layout.addWidget(self.reason_dependency)
        layout.addWidget(self.reason_subtasks)
        layout.addWidget(self.reason_other)

        # Start date picker
        date_layout = QFormLayout()

        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addDays(1))
        self.start_date_edit.setMinimumDate(QDate.currentDate())

        date_layout.addRow("Start date:", self.start_date_edit)
        layout.addLayout(date_layout)

    def accept(self):
        """
        Handle acceptance and trigger workflows based on postpone reason.

        Shows follow-up dialogs for BLOCKER, DEPENDENCY, and MULTIPLE_SUBTASKS reasons.
        """
        # Only trigger workflows for defer action with task and db_connection
        if self.action_type == "defer" and self.task and self.db_connection:
            reason = self._get_selected_reason()

            # Import here to avoid circular dependency
            from .blocker_selection_dialog import BlockerSelectionDialog
            from .subtask_breakdown_dialog import SubtaskBreakdownDialog
            from .dependency_selection_dialog import DependencySelectionDialog

            if reason == PostponeReasonType.BLOCKER:
                # Show blocker selection dialog
                blocker_dialog = BlockerSelectionDialog(self.task, self.db_connection, self)
                if blocker_dialog.exec_() != QDialog.Accepted:
                    return  # User canceled blocker creation
                self.blocker_result = blocker_dialog.get_result()

            elif reason == PostponeReasonType.DEPENDENCY:
                # Reuse existing dependency selection dialog
                dep_dialog = DependencySelectionDialog(self.task, self.db_connection, self)
                if dep_dialog.exec_() != QDialog.Accepted:
                    return  # User canceled dependency selection
                # Dependencies are saved by the dialog itself
                self.dependency_added = True

            elif reason == PostponeReasonType.MULTIPLE_SUBTASKS:
                # Show subtask breakdown dialog
                subtask_dialog = SubtaskBreakdownDialog(self.task, self)
                if subtask_dialog.exec_() != QDialog.Accepted:
                    return  # User canceled subtask breakdown
                self.subtask_result = subtask_dialog.get_result()

        # Proceed with normal dialog acceptance
        super().accept()

    def _get_selected_reason(self) -> PostponeReasonType:
        """Get the currently selected postpone reason."""
        if not hasattr(self, 'reason_group'):
            return PostponeReasonType.OTHER

        # Map integer IDs to enum values
        selected_id = self.reason_group.checkedId()
        id_to_reason = {
            0: PostponeReasonType.NOT_READY,
            1: PostponeReasonType.BLOCKER,
            2: PostponeReasonType.DEPENDENCY,
            3: PostponeReasonType.MULTIPLE_SUBTASKS,
            4: PostponeReasonType.OTHER
        }
        return id_to_reason.get(selected_id, PostponeReasonType.OTHER)

    def _create_delegate_ui(self, layout: QVBoxLayout):
        """Create UI elements for delegating a task."""
        form_layout = QFormLayout()

        # Person to delegate to
        self.delegated_to_edit = QLineEdit()
        self.delegated_to_edit.setPlaceholderText("Enter name or email...")
        form_layout.addRow("Delegate to:", self.delegated_to_edit)

        # Follow-up date
        self.follow_up_date_edit = QDateEdit()
        self.follow_up_date_edit.setCalendarPopup(True)
        self.follow_up_date_edit.setDate(QDate.currentDate().addDays(7))
        self.follow_up_date_edit.setMinimumDate(QDate.currentDate())
        form_layout.addRow("Follow-up date:", self.follow_up_date_edit)

        layout.addLayout(form_layout)

    def get_result(self) -> Optional[Dict[str, Any]]:
        """
        Get the dialog result as a dictionary.

        Returns:
            Dictionary with action details and workflow results, or None if canceled
        """
        if self.result() != QDialog.Accepted:
            return None

        result = {
            'action_type': self.action_type,
            'notes': self.notes_edit.toPlainText().strip()
        }

        if self.action_type == "defer":
            # Get selected reason
            reason = self._get_selected_reason()
            result['reason'] = reason
            result['start_date'] = self.start_date_edit.date().toPyDate()

            # Include workflow results
            if self.blocker_result:
                result['blocker_result'] = self.blocker_result
            if self.subtask_result:
                result['subtask_result'] = self.subtask_result
            if self.dependency_added:
                result['dependency_added'] = True

        else:  # delegate
            result['delegated_to'] = self.delegated_to_edit.text().strip()
            result['follow_up_date'] = self.follow_up_date_edit.date().toPyDate()

            # Validation
            if not result['delegated_to']:
                return None

        return result


class DeferDialog(PostponeDialog):
    """Convenience subclass for defer action."""

    def __init__(self, task_title: str, task: Optional[Task] = None,
                 db_connection: Optional[DatabaseConnection] = None, parent=None):
        super().__init__(task_title, "defer", task, db_connection, parent)


class DelegateDialog(PostponeDialog):
    """Convenience subclass for delegate action."""

    def __init__(self, task_title: str, task: Optional[Task] = None,
                 db_connection: Optional[DatabaseConnection] = None, parent=None):
        super().__init__(task_title, "delegate", task, db_connection, parent)
