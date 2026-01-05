"""
Help Dialog for OneTaskAtATime.

Comprehensive help system with searchable content.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QTextBrowser, QPushButton, QLineEdit, QLabel
)
from PyQt5.QtCore import Qt
from .geometry_mixin import GeometryMixin


class HelpDialog(QDialog, GeometryMixin):
    """
    Help dialog with tabbed content and search functionality.

    Provides help on:
    - Getting Started
    - Focus Mode
    - Task Management
    - Priority System
    - Keyboard Shortcuts
    - FAQ
    """

    def __init__(self, parent=None):
        """
        Initialize the Help Dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=800, default_height=600)
        else:
            # Set flag to prevent GeometryMixin.showEvent from failing
            self._geometry_restored = True

        self.setWindowTitle("OneTaskAtATime Help")
        self.setMinimumSize(800, 600)
        self.setModal(False)

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)

        # Header
        header_label = QLabel("<h2>OneTaskAtATime Help</h2>")
        layout.addWidget(header_label)

        # Search box
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Type to search help topics...")
        self.search_box.textChanged.connect(self._on_search)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)

        # Tab widget for categories
        self.tab_widget = QTabWidget()

        # Add tabs with content
        self.tab_widget.addTab(self._create_getting_started_tab(), "Getting Started")
        self.tab_widget.addTab(self._create_focus_mode_tab(), "Focus Mode")
        self.tab_widget.addTab(self._create_task_management_tab(), "Task Management")
        self.tab_widget.addTab(self._create_priority_system_tab(), "Priority System")
        self.tab_widget.addTab(self._create_shortcuts_tab(), "Keyboard Shortcuts")
        self.tab_widget.addTab(self._create_faq_tab(), "FAQ")

        layout.addWidget(self.tab_widget)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _create_getting_started_tab(self) -> QWidget:
        """Create Getting Started tab."""
        return self._create_text_tab("""
<h3>Getting Started with OneTaskAtATime</h3>

<h4>Quick Introduction</h4>
<p>OneTaskAtATime is designed to help you focus on executing <b>one task at a time</b>
rather than managing endless to-do lists.</p>

<h4>Core Concepts</h4>
<ul>
<li><b>Focus Mode:</b> Shows only your highest-priority task</li>
<li><b>Task States:</b> Active, Deferred, Delegated, Someday/Maybe, Completed, Trash</li>
<li><b>Smart Prioritization:</b> Combines base priority with Elo-based refinement and urgency</li>
<li><b>Task Resurfacing:</b> Automatically reminds you about deferred and delegated tasks</li>
</ul>

<h4>Basic Workflow</h4>
<ol>
<li>Create tasks with <b>Ctrl+N</b></li>
<li>Assign priority (High, Medium, Low) and due dates</li>
<li>Use <b>Focus Mode</b> (Ctrl+F) to work on the most important task</li>
<li>Complete (Ctrl+Shift+C), Defer (Ctrl+D), or take other actions</li>
<li>The app automatically shows you the next highest-priority task</li>
</ol>
        """)

    def _create_focus_mode_tab(self) -> QWidget:
        """Create Focus Mode tab."""
        return self._create_text_tab("""
<h3>Focus Mode</h3>

<p>Focus Mode presents <b>ONE task at a time</b> - your highest-priority task.</p>

<h4>Actions</h4>

<p><b>Complete (Ctrl+Shift+C)</b><br>
Marks the task as done and automatically shows the next task.</p>

<p><b>Defer (Ctrl+D)</b><br>
Postpone the task with a start date. The app tracks postponement patterns
and suggests interventions if needed.</p>

<p><b>Delegate (Ctrl+Shift+D)</b><br>
Assign to someone else with a follow-up date. You'll be reminded when
follow-up is due.</p>

<p><b>Someday/Maybe (Ctrl+M)</b><br>
Move to Someday/Maybe list for tasks you're not ready to commit to.
These are periodically resurfaced for review.</p>

<p><b>Move to Trash (Ctrl+Delete)</b><br>
For tasks that are no longer relevant.</p>

<h4>Why Focus Mode?</h4>
<p>By showing only one task, Focus Mode eliminates decision fatigue and
helps you make progress on what truly matters.</p>
        """)

    def _create_task_management_tab(self) -> QWidget:
        """Create Task Management tab."""
        return self._create_text_tab("""
<h3>Task Management</h3>

<h4>Creating Tasks</h4>
<p>Press <b>Ctrl+N</b> to create a new task. Fill in:</p>
<ul>
<li><b>Title:</b> Brief description of the task</li>
<li><b>Description:</b> Optional details</li>
<li><b>Priority:</b> High, Medium, or Low</li>
<li><b>Due Date:</b> Optional deadline</li>
<li><b>Context:</b> Work environment (e.g., @computer, @phone)</li>
<li><b>Project Tags:</b> Organize by project</li>
</ul>

<h4>Organizing Tasks</h4>
<p><b>Contexts:</b> Each task can have ONE context representing where/how you can do it.</p>
<p><b>Project Tags:</b> Each task can have MULTIPLE tags for project organization.</p>
<p><b>Dependencies:</b> Link tasks that must be completed in order.</p>

<h4>Task History</h4>
<p>View complete audit log of all changes to a task with <b>Ctrl+H</b>.</p>
        """)

    def _create_priority_system_tab(self) -> QWidget:
        """Create Priority System tab."""
        return self._create_text_tab("""
<h3>Priority System</h3>

<h4>How Ranking Works</h4>
<p>Tasks are ranked by <b>Importance</b>:</p>
<p style="text-align: center;"><b>Importance = Priority × Urgency</b></p>

<h4>Priority Component</h4>
<p><b>Base Priority:</b> You assign High (3), Medium (2), or Low (1)</p>
<p><b>Elo Rating:</b> Refined through head-to-head comparisons (1000-2000 range)</p>
<p><b>Effective Priority:</b> Elo rating is mapped within priority tier bands:
<ul>
<li>High (3): effective priority between 2.0-3.0</li>
<li>Medium (2): effective priority between 1.0-2.0</li>
<li>Low (1): effective priority between 0.0-1.0</li>
</ul>
</p>

<h4>Urgency Component</h4>
<p>Based on due date - tasks with sooner due dates get higher urgency scores.</p>

<h4>Comparison-Based Ranking</h4>
<p>When multiple tasks have equal Importance, the app asks you to compare them.
Your choice updates Elo ratings using a chess-like algorithm. Over time, this
refines the ranking to match your true preferences.</p>
        """)

    def _create_shortcuts_tab(self) -> QWidget:
        """Create Keyboard Shortcuts tab."""
        return self._create_text_tab("""
<h3>Keyboard Shortcuts</h3>

<h4>General</h4>
<ul>
<li><b>Ctrl+N:</b> New Task</li>
<li><b>Ctrl+Shift+E:</b> Export Data</li>
<li><b>Ctrl+Shift+I:</b> Import Data</li>
<li><b>Ctrl+,:</b> Settings</li>
<li><b>F1:</b> Help</li>
<li><b>Ctrl+?:</b> Keyboard Shortcuts Cheatsheet</li>
<li><b>Ctrl+Q:</b> Exit</li>
<li><b>Ctrl+Z:</b> Undo</li>
<li><b>Ctrl+Y:</b> Redo</li>
</ul>

<h4>Navigation</h4>
<ul>
<li><b>Alt+F:</b> Focus Mode</li>
<li><b>Alt+L:</b> Task List</li>
<li><b>F5:</b> Refresh</li>
</ul>

<h4>Focus Mode Actions</h4>
<ul>
<li><b>Alt+C:</b> Complete Task</li>
<li><b>Alt+D:</b> Defer Task</li>
<li><b>Alt+G:</b> Delegate Task</li>
<li><b>Alt+S:</b> Move to Someday/Maybe</li>
<li><b>Alt+T:</b> Move to Trash</li>
</ul>

<h4>Task List</h4>
<ul>
<li><b>Enter:</b> Edit Selected Task</li>
</ul>

<h4>Dialogs</h4>
<ul>
<li><b>Enter:</b> Confirm/OK</li>
<li><b>Esc:</b> Cancel/Close</li>
<li><b>Tab:</b> Next Field</li>
<li><b>Shift+Tab:</b> Previous Field</li>
</ul>
        """)

    def _create_faq_tab(self) -> QWidget:
        """Create FAQ tab."""
        return self._create_text_tab("""
<h3>Frequently Asked Questions</h3>

<h4>Why can't I see all my tasks at once?</h4>
<p>Focus Mode is designed to reduce decision fatigue by showing only your
highest-priority task. You can always view the full task list with Ctrl+L.</p>

<h4>How does the Elo rating work?</h4>
<p>When tasks have equal importance, you'll be asked to compare them. Your choice
updates both tasks' Elo ratings using a chess-like algorithm. Tasks that consistently
win comparisons get higher ratings within their priority tier.</p>

<h4>What happens to deferred tasks?</h4>
<p>Deferred tasks become active again on their start date. The app also tracks
postponement patterns and suggests interventions if you repeatedly defer the same task.</p>

<h4>Can I use this without keyboard shortcuts?</h4>
<p>Yes! All functionality is accessible via mouse/touch. However, keyboard shortcuts
make the workflow much faster.</p>

<h4>How do I back up my data?</h4>
<p>Use File > Export Data to save all tasks as JSON. You can import this file later
with File > Import Data.</p>

<h4>Is my data secure?</h4>
<p>All data is stored locally on your computer in an SQLite database. Nothing is
sent to external servers.</p>
        """)

    def _create_text_tab(self, html_content: str) -> QWidget:
        """
        Create a tab with HTML text content.

        Args:
            html_content: HTML content to display

        Returns:
            QWidget containing the content
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = QTextBrowser()
        browser.setHtml(html_content)
        browser.setOpenExternalLinks(True)

        layout.addWidget(browser)

        return widget

    def _on_search(self, text: str):
        """
        Handle search text changes.

        Args:
            text: Search query
        """
        # TODO: Implement search functionality across all tabs
        # For now, this is a placeholder
        pass
