"""
Welcome Wizard for OneTaskAtATime.

Multi-page wizard for first-time user onboarding.
"""

import sqlite3
from PyQt5.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout,
    QLabel, QCheckBox
)

from .geometry_mixin import GeometryMixin


class WelcomeWizard(QWizard, GeometryMixin):
    """
    Welcome wizard for first-time users.

    Guides users through:
    1. Welcome introduction
    2. Understanding Focus Mode and views
    3. Learning Focus Mode actions
    4. Final tips and completion
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

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=450)

        self.setWindowTitle("Welcome to OneTaskAtATime")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(600, 450)

        # Add pages
        self.addPage(WelcomePage())
        self.addPage(ViewsAndNavigationPage())
        self.addPage(FocusModePage())
        self.addPage(FinalPage())


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


class GettingStartedPage(QWizardPage):
    """Page explaining how to create tasks."""

    def __init__(self):
        super().__init__()

        self.setTitle("Getting Started")
        self.setSubTitle("Creating and managing your tasks")

        layout = QVBoxLayout()

        content = QLabel(
            "<p><b>Creating Tasks:</b></p>"
            "<p>To add a new task, use one of these methods:</p>"
            "<ul>"
            "<li>Press <b>Ctrl+N</b> (quick keyboard shortcut)</li>"
            "<li>Click <b>Tasks → New Task</b> in the menu</li>"
            "</ul>"
            "<p>When creating a task, you can specify:</p>"
            "<ul>"
            "<li><b>Title</b> - What needs to be done</li>"
            "<li><b>Description</b> - Additional details or notes</li>"
            "<li><b>Priority</b> - High, Medium, or Low</li>"
            "<li><b>Due Date</b> - When it needs to be completed</li>"
            "<li><b>Context</b> - Where or how you'll do it (e.g., @office, @home)</li>"
            "<li><b>Tags</b> - Project or category labels</li>"
            "</ul>"
            "<p><i>After this wizard, try creating your first task with <b>Ctrl+N</b>!</i></p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        layout.addStretch()
        self.setLayout(layout)


class ViewsAndNavigationPage(QWizardPage):
    """Page explaining Focus Mode vs Task List views."""

    def __init__(self):
        super().__init__()

        self.setTitle("Views and Navigation")
        self.setSubTitle("Understanding Focus Mode and Task List")

        layout = QVBoxLayout()

        content = QLabel(
            "<p>OneTaskAtATime has two main views:</p>"
            "<p><b>Focus Mode (Ctrl+1):</b></p>"
            "<ul>"
            "<li>Shows <b>ONE task at a time</b> - your highest-priority task</li>"
            "<li>Helps you concentrate on execution without distraction</li>"
            "<li>This is where you spend most of your time!</li>"
            "</ul>"
            "<p><b>Task List (Ctrl+2):</b></p>"
            "<ul>"
            "<li>Shows <b>all active tasks</b> in priority order</li>"
            "<li>Use this for reviewing, editing, and organizing tasks</li>"
            "<li>Edit any task by selecting it and pressing <b>Enter</b></li>"
            "</ul>"
            "<p><b>Quick Tip:</b> Use <b>Ctrl+1</b> and <b>Ctrl+2</b> to switch between views anytime!</p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        layout.addStretch()
        self.setLayout(layout)


class FocusModePage(QWizardPage):
    """Page explaining Focus Mode."""

    def __init__(self):
        super().__init__()

        self.setTitle("Focus Mode Actions")
        self.setSubTitle("What you can do with your current task")

        layout = QVBoxLayout()

        content = QLabel(
            "<p>In <b>Focus Mode</b>, you have several actions for your current task:</p>"
            "<ul>"
            "<li><b>Complete</b> (Alt+C) - Mark task as done and move to the next one</li>"
            "<li><b>Defer</b> (Alt+D) - Postpone with a start date (not ready to work on it yet)</li>"
            "<li><b>Delegate</b> (Alt+G) - Assign to someone else with a follow-up date</li>"
            "<li><b>Someday/Maybe</b> (Alt+S) - Move to 'someday' list (not committed yet)</li>"
            "<li><b>Trash</b> (Alt+X) - No longer relevant or needed</li>"
            "</ul>"
            "<p><b>Smart Tracking:</b> When you defer or postpone a task, the app asks why. "
            "This helps identify blockers and dependencies so you can address them!</p>"
            "<p><i>Remember: The goal is to complete tasks, not endlessly postpone them.</i></p>"
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
            "<p><b>Essential Keyboard Shortcuts:</b></p>"
            "<ul>"
            "<li><b>Ctrl+N</b> - Create a new task</li>"
            "<li><b>Ctrl+1</b> - Switch to Focus Mode</li>"
            "<li><b>Ctrl+2</b> - Switch to Task List</li>"
            "<li><b>Ctrl+?</b> - View all keyboard shortcuts</li>"
            "<li><b>Ctrl+,</b> - Open settings</li>"
            "<li><b>F1</b> - Get help</li>"
            "<li><b>F5</b> - Refresh the current view</li>"
            "</ul>"
            "<p><b>Additional Tips:</b></p>"
            "<ul>"
            "<li>Use <b>Manage → Contexts</b> and <b>Manage → Tags</b> to organize tasks by location or project</li>"
            "<li>Review postponed tasks regularly to identify blockers</li>"
            "<li>Use <b>Ctrl+Z</b> to undo and <b>Ctrl+Y</b> to redo</li>"
            "</ul>"
            "<p style='margin-top: 20px;'><b>Remember:</b> The goal is to focus on ONE task at a time, "
            "not to manage endless lists!</p>"
            "<p style='margin-top: 10px;'><i>You can re-run this wizard anytime from "
            "<b>Settings → Advanced → Re-run Welcome Wizard</b></i></p>"
        )
        content.setWordWrap(True)
        layout.addWidget(content)

        # Tutorial checkbox
        self.show_tutorial_checkbox = QCheckBox("Show tutorial on first launch")
        self.show_tutorial_checkbox.setChecked(True)
        layout.addWidget(self.show_tutorial_checkbox)

        layout.addStretch()
        self.setLayout(layout)
