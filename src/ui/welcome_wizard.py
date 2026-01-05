"""
Welcome Wizard for OneTaskAtATime.

Multi-page wizard for first-time user onboarding.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QRadioButton, QButtonGroup,
    QDateEdit, QCheckBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from src.models.task import Task
from src.models.enums import Priority, TaskState
from src.database.task_dao import TaskDAO
from .geometry_mixin import GeometryMixin


class WelcomeWizard(QWizard, GeometryMixin):
    """
    Welcome wizard for first-time users.

    Guides users through:
    1. Welcome introduction
    2. Creating their first task
    3. Understanding Focus Mode
    4. Learning the priority system
    5. Final tips and completion
    """

    def __init__(self, db_connection: sqlite3.Connection, parent=None):
        """
        Initialize the Welcome Wizard.

        Args:
            db_connection: Active database connection
            parent: Parent widget
        """
        super().__init__(parent)

        self.db_connection = db_connection
        self.task_dao = TaskDAO(db_connection)

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=450)

        self.setWindowTitle("Welcome to OneTaskAtATime")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 450)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(CreateFirstTaskPage())
        self.addPage(FocusModePage())
        self.addPage(PrioritySystemPage())
        self.addPage(FinalPage())

    def done(self, result):
        """Handle wizard completion."""
        if result == QWizard.Accepted:
            # Create the first task if user filled it in
            create_page = self.page(1)  # CreateFirstTaskPage
            if create_page.task_title.text():
                self._create_first_task(create_page)

        super().done(result)

    def _create_first_task(self, page):
        """Create the user's first task from wizard input."""
        task = Task(
            title=page.task_title.text(),
            description=page.task_description.toPlainText(),
            base_priority=page.get_selected_priority(),
            state=TaskState.ACTIVE
        )

        # Set due date if provided
        if page.due_date_edit.date() != QDate.currentDate():
            task.due_date = page.due_date_edit.date().toPyDate()

        self.task_dao.create(task)


class WelcomePage(QWizardPage):
    """Welcome introduction page."""

    def __init__(self):
        super().__init__()

        self.setTitle("Welcome to OneTaskAtATime!")
        self.setSubTitle("Let's get you started with focused task management")

        layout = QVBoxLayout()

        intro_text = QLabel(
            "<p><b>OneTaskAtATime</b> helps you focus on executing <b>ONE task at a time</b>.</p>"
            "<p>Key principles:</p>"
            "<ul>"
            "<li><b>Focus Mode</b> shows only your highest-priority task</li>"
            "<li><b>Smart ranking</b> eliminates the 'everything is urgent' problem</li>"
            "<li><b>Task resurfacing</b> prevents things from falling through the cracks</li>"
            "</ul>"
        )
        intro_text.setWordWrap(True)
        layout.addWidget(intro_text)

        layout.addStretch()
        self.setLayout(layout)


class CreateFirstTaskPage(QWizardPage):
    """Page for creating first task."""

    def __init__(self):
        super().__init__()

        self.setTitle("Create Your First Task")
        self.setSubTitle("Let's add something you need to get done")

        layout = QVBoxLayout()

        # Task title
        layout.addWidget(QLabel("Task Title:"))
        self.task_title = QLineEdit()
        self.task_title.setPlaceholderText("e.g., Review quarterly report")
        layout.addWidget(self.task_title)

        # Description
        layout.addWidget(QLabel("Description (optional):"))
        self.task_description = QTextEdit()
        self.task_description.setMaximumHeight(80)
        self.task_description.setPlaceholderText("Add any notes or details...")
        layout.addWidget(self.task_description)

        # Priority
        layout.addWidget(QLabel("Priority:"))
        priority_layout = QHBoxLayout()

        self.priority_group = QButtonGroup()
        self.low_radio = QRadioButton("Low")
        self.medium_radio = QRadioButton("Medium")
        self.high_radio = QRadioButton("High")

        self.priority_group.addButton(self.low_radio, 1)
        self.priority_group.addButton(self.medium_radio, 2)
        self.priority_group.addButton(self.high_radio, 3)

        self.medium_radio.setChecked(True)

        priority_layout.addWidget(self.low_radio)
        priority_layout.addWidget(self.medium_radio)
        priority_layout.addWidget(self.high_radio)
        priority_layout.addStretch()

        layout.addLayout(priority_layout)

        # Due date
        layout.addWidget(QLabel("Due Date (optional):"))
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setDate(QDate.currentDate())
        self.due_date_edit.setCalendarPopup(True)
        layout.addWidget(self.due_date_edit)

        layout.addStretch()
        self.setLayout(layout)

    def get_selected_priority(self) -> int:
        """Get selected priority value."""
        return self.priority_group.checkedId()


class FocusModePage(QWizardPage):
    """Page explaining Focus Mode."""

    def __init__(self):
        super().__init__()

        self.setTitle("Focus Mode Overview")
        self.setSubTitle("Your primary workspace for getting things done")

        layout = QVBoxLayout()

        content = QLabel(
            "<p><b>Focus Mode</b> shows ONE task at a time - your highest-priority task.</p>"
            "<p>Actions you can take:</p>"
            "<ul>"
            "<li><b>Complete</b> (Ctrl+Shift+C) - Mark done and move to next task</li>"
            "<li><b>Defer</b> (Ctrl+D) - Postpone with a start date</li>"
            "<li><b>Delegate</b> (Ctrl+Shift+D) - Assign to someone else</li>"
            "<li><b>Someday/Maybe</b> (Ctrl+M) - Not ready to commit yet</li>"
            "<li><b>Trash</b> (Ctrl+Delete) - No longer relevant</li>"
            "</ul>"
            "<p>The app tracks why you delay tasks to help identify blockers!</p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        layout.addStretch()
        self.setLayout(layout)


class PrioritySystemPage(QWizardPage):
    """Page explaining priority ranking."""

    def __init__(self):
        super().__init__()

        self.setTitle("How Task Ranking Works")
        self.setSubTitle("Smart prioritization without the overwhelm")

        layout = QVBoxLayout()

        content = QLabel(
            "<p>Tasks are ranked by <b>Importance</b>:</p>"
            "<p style='text-align: center;'><b>Importance = Priority × Urgency</b></p>"
            "<p><b>Priority:</b> Based on your setting (High/Medium/Low) refined by Elo comparisons</p>"
            "<p><b>Urgency:</b> Based on due date (sooner = more urgent)</p>"
            "<p>When tasks tie, you'll be asked to compare them side-by-side!</p>"
            "<p>The system learns from your choices and gets better at showing you the right task.</p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        layout.addStretch()
        self.setLayout(layout)


class FinalPage(QWizardPage):
    """Final page with tips."""

    def __init__(self):
        super().__init__()

        self.setTitle("You're All Set!")
        self.setSubTitle("Ready to start focusing?")

        layout = QVBoxLayout()

        content = QLabel(
            "<p>Quick tips to get started:</p>"
            "<ul>"
            "<li>Press <b>F1</b> for help anytime</li>"
            "<li>Press <b>Ctrl+?</b> to see all keyboard shortcuts</li>"
            "<li>Use <b>Manage > Contexts</b> and <b>Manage > Tags</b> to organize tasks</li>"
            "<li>View settings with <b>Ctrl+,</b></li>"
            "</ul>"
            "<p><b>Remember:</b> The goal is to focus on ONE task at a time, not to manage endless lists!</p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        self.show_tutorial_checkbox = QCheckBox("Show tutorial tips next time")
        self.show_tutorial_checkbox.setChecked(False)
        layout.addWidget(self.show_tutorial_checkbox)

        layout.addStretch()
        self.setLayout(layout)
