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
from ..models.enums import PostponeReasonType


class PostponeDialog(QDialog):
    """
    Dialog for capturing postpone reason and collecting necessary data.

    Depending on the reason selected, shows different input fields:
    - Defer: Date picker for start_date
    - Delegate: Person name and follow-up date
    """

    def __init__(self, task_title: str, action_type: str = "defer", parent=None):
        """
        Initialize the postpone dialog.

        Args:
            task_title: Title of the task being postponed
            action_type: Either "defer" or "delegate"
            parent: Parent widget
        """
        super().__init__(parent)
        self.task_title = task_title
        self.action_type = action_type
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

        self.reason_group.addButton(self.reason_not_ready, PostponeReasonType.NOT_READY.value)
        self.reason_group.addButton(self.reason_blocker, PostponeReasonType.BLOCKER.value)
        self.reason_group.addButton(self.reason_dependency, PostponeReasonType.DEPENDENCY.value)
        self.reason_group.addButton(self.reason_subtasks, PostponeReasonType.MULTIPLE_SUBTASKS.value)
        self.reason_group.addButton(self.reason_other, PostponeReasonType.OTHER.value)

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
            Dictionary with action details, or None if canceled
        """
        if self.result() != QDialog.Accepted:
            return None

        result = {
            'action_type': self.action_type,
            'notes': self.notes_edit.toPlainText().strip()
        }

        if self.action_type == "defer":
            # Get selected reason
            selected_id = self.reason_group.checkedId()
            if selected_id == PostponeReasonType.NOT_READY.value:
                reason = PostponeReasonType.NOT_READY
            elif selected_id == PostponeReasonType.BLOCKER.value:
                reason = PostponeReasonType.BLOCKER
            elif selected_id == PostponeReasonType.DEPENDENCY.value:
                reason = PostponeReasonType.DEPENDENCY
            elif selected_id == PostponeReasonType.MULTIPLE_SUBTASKS.value:
                reason = PostponeReasonType.MULTIPLE_SUBTASKS
            else:
                reason = PostponeReasonType.OTHER

            result['reason'] = reason
            result['start_date'] = self.start_date_edit.date().toPyDate()

        else:  # delegate
            result['delegated_to'] = self.delegated_to_edit.text().strip()
            result['follow_up_date'] = self.follow_up_date_edit.date().toPyDate()

            # Validation
            if not result['delegated_to']:
                return None

        return result


class DeferDialog(PostponeDialog):
    """Convenience subclass for defer action."""

    def __init__(self, task_title: str, parent=None):
        super().__init__(task_title, "defer", parent)


class DelegateDialog(PostponeDialog):
    """Convenience subclass for delegate action."""

    def __init__(self, task_title: str, parent=None):
        super().__init__(task_title, "delegate", parent)
