"""
Help Dialog for OneTaskAtATime.

Comprehensive help system with searchable content.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QWidget, QTextBrowser, QPushButton, QLineEdit, QLabel, QToolButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from .geometry_mixin import GeometryMixin
import re


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

        # Store original tab content for search restoration
        self._original_content = {}
        self._tab_browsers = {}
        self._original_tab_titles = {}  # Store original tab titles

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
        self.search_box.textChanged.connect(self._on_search_changed)

        # Clear button for search box
        self.clear_button = QToolButton()
        self.clear_button.setText("✕")
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        self.clear_button.setToolTip("Clear search")
        self.clear_button.clicked.connect(self._clear_search)
        self.clear_button.hide()  # Initially hidden

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        search_layout.addWidget(self.clear_button)
        layout.addLayout(search_layout)

        # Tab widget for categories
        self.tab_widget = QTabWidget()

        # Add tabs with content - store content and browsers for search
        self._add_help_tab("Getting Started", self._get_getting_started_content())
        self._add_help_tab("Focus Mode", self._get_focus_mode_content())
        self._add_help_tab("Task Management", self._get_task_management_content())
        self._add_help_tab("Priority System", self._get_priority_system_content())
        self._add_help_tab("Keyboard Shortcuts", self._get_shortcuts_content())
        self._add_help_tab("FAQ", self._get_faq_content())

        layout.addWidget(self.tab_widget)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _add_help_tab(self, tab_name: str, html_content: str):
        """
        Add a help tab with searchable content.

        Args:
            tab_name: Name of the tab
            html_content: HTML content for the tab
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        browser = QTextBrowser()
        browser.setHtml(html_content)
        browser.setOpenExternalLinks(True)

        layout.addWidget(browser)

        # Store original content, browser reference, and tab title for search
        self._original_content[tab_name] = html_content
        self._tab_browsers[tab_name] = browser
        self._original_tab_titles[tab_name] = tab_name

        self.tab_widget.addTab(widget, tab_name)

    def _get_getting_started_content(self) -> str:
        """Get Getting Started tab content."""
        return """
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

<h4>Context-Sensitive Help</h4>
<p>Most dialogs have a <strong>?</strong> button in the title bar.
Click it, then click any field to see specific help for that element.</p>
<p>You can also press <strong>Shift+F1</strong> to enter WhatsThis mode.</p>
        """

    def _get_focus_mode_content(self) -> str:
        """Get Focus Mode tab content."""
        return """
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
        """

    def _get_task_management_content(self) -> str:
        """Get Task Management tab content."""
        return """
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
        """

    def _get_priority_system_content(self) -> str:
        """Get Priority System tab content."""
        return """
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
        """

    def _get_shortcuts_content(self) -> str:
        """Get Keyboard Shortcuts tab content."""
        return """
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
<li><b>Shift+F1:</b> WhatsThis Help Mode</li>
</ul>
        """

    def _get_faq_content(self) -> str:
        """Get FAQ tab content."""
        return """
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
        """

    def _on_search_changed(self, text: str):
        """
        Handle search text changes.

        Args:
            text: Search query
        """
        # Show/hide clear button based on text
        if text:
            self.clear_button.show()
        else:
            self.clear_button.hide()
            # Restore original content when search is cleared
            self._restore_original_content()
            return

        # Perform search
        query = text.strip()
        if not query:
            self._restore_original_content()
            return

        # Search across all tabs and highlight matches
        total_matches = 0
        first_match_tab = None
        tab_match_counts = {}

        for tab_name, browser in self._tab_browsers.items():
            original_html = self._original_content[tab_name]
            highlighted_html, match_count = self._highlight_search_matches(original_html, query)

            # Update browser content
            browser.setHtml(highlighted_html)

            # Store match count for this tab
            tab_match_counts[tab_name] = match_count
            total_matches += match_count
            if match_count > 0 and first_match_tab is None:
                first_match_tab = tab_name

        # Update tab titles with match counts
        for i in range(self.tab_widget.count()):
            current_title = self.tab_widget.tabText(i)
            # Remove any existing count in parentheses
            base_title = current_title.split(' (')[0]

            if base_title in tab_match_counts:
                match_count = tab_match_counts[base_title]
                if match_count > 0:
                    self.tab_widget.setTabText(i, f"{base_title} ({match_count})")
                else:
                    self.tab_widget.setTabText(i, base_title)

        # Update placeholder text with match count
        if total_matches > 0:
            self.search_box.setPlaceholderText(f"{total_matches} result{'s' if total_matches != 1 else ''} found")
            # Switch to first tab with matches
            if first_match_tab:
                for i in range(self.tab_widget.count()):
                    tab_text = self.tab_widget.tabText(i)
                    base_title = tab_text.split(' (')[0]
                    if base_title == first_match_tab:
                        self.tab_widget.setCurrentIndex(i)
                        break
        else:
            self.search_box.setPlaceholderText("No results found")

    def _highlight_search_matches(self, html_content: str, query: str) -> tuple:
        """
        Highlight search matches in HTML content.

        Args:
            html_content: Original HTML content
            query: Search query (case-insensitive)

        Returns:
            Tuple of (highlighted_html, match_count)
        """
        # Escape special regex characters in query
        escaped_query = re.escape(query)

        # Pattern to match the query outside of HTML tags
        # This prevents matching inside tag names or attributes
        pattern = re.compile(f'({escaped_query})', re.IGNORECASE)

        match_count = 0

        def replace_match(match):
            nonlocal match_count
            match_count += 1
            return f'<mark style="background-color: #FFEB3B; color: #000000; padding: 2px 0px;">{match.group(1)}</mark>'

        # Simple approach: split on tags and only highlight text between tags
        # This avoids highlighting inside HTML tags
        parts = re.split(r'(<[^>]+>)', html_content)
        highlighted_parts = []

        for part in parts:
            if part.startswith('<') and part.endswith('>'):
                # This is an HTML tag, don't highlight
                highlighted_parts.append(part)
            else:
                # This is text content, highlight matches
                highlighted_parts.append(pattern.sub(replace_match, part))

        highlighted_html = ''.join(highlighted_parts)
        return highlighted_html, match_count

    def _clear_search(self):
        """Clear the search box."""
        self.search_box.clear()

    def _restore_original_content(self):
        """Restore original content and tab titles."""
        for tab_name, browser in self._tab_browsers.items():
            original_html = self._original_content[tab_name]
            browser.setHtml(original_html)

        # Restore original tab titles (remove match counts)
        for i in range(self.tab_widget.count()):
            current_title = self.tab_widget.tabText(i)
            base_title = current_title.split(' (')[0]
            self.tab_widget.setTabText(i, base_title)

        self.search_box.setPlaceholderText("Type to search help topics...")
