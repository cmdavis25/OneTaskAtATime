"""
Focus Mode Widget - Core single-task display for OneTaskAtATime.

Displays one task at a time with action buttons for completing, deferring,
delegating, or moving tasks to different states.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from typing import Optional
from ..models.task import Task
from ..models.enums import TaskState


class FocusModeWidget(QWidget):
    """
    Widget that displays a single task with action buttons.

    This is the core UI component of OneTaskAtATime - the focused,
    distraction-free task display.

    Signals:
        task_completed: Emitted when Complete button clicked
        task_deferred: Emitted when Defer button clicked
        task_delegated: Emitted when Delegate button clicked
        task_someday: Emitted when Someday button clicked
        task_trashed: Emitted when Trash button clicked
        task_refreshed: Emitted when user requests to refresh the displayed task
    """

    # Signals for task actions
    task_completed = pyqtSignal(int)  # task_id
    task_deferred = pyqtSignal(int)   # task_id
    task_delegated = pyqtSignal(int)  # task_id
    task_someday = pyqtSignal(int)    # task_id
    task_trashed = pyqtSignal(int)    # task_id
    task_refreshed = pyqtSignal()

    def __init__(self, parent=None):
        """Initialize the Focus Mode widget."""
        super().__init__(parent)
        self._current_task: Optional[Task] = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        self.setLayout(layout)

        # Title section
        self._create_title_section(layout)

        # Task card
        self._create_task_card(layout)

        # Action buttons
        self._create_action_buttons(layout)

        # Show empty state initially
        self._show_empty_state()

    def _create_title_section(self, layout: QVBoxLayout):
        """Create the title section at the top."""
        title_label = QLabel("Focus Mode")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        subtitle_label = QLabel("Your highest priority task right now")
        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #666;")
        layout.addWidget(subtitle_label)

    def _create_task_card(self, layout: QVBoxLayout):
        """Create the task card display area."""
        # Card frame
        self.card_frame = QFrame()
        self.card_frame.setFrameShape(QFrame.StyledPanel)
        self.card_frame.setFrameShadow(QFrame.Raised)
        self.card_frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 2px solid #ddd;
                border-radius: 8px;
                padding: 20px;
            }
        """)

        card_layout = QVBoxLayout()
        self.card_frame.setLayout(card_layout)

        # Task title
        self.task_title_label = QLabel()
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.task_title_label.setFont(title_font)
        self.task_title_label.setWordWrap(True)
        card_layout.addWidget(self.task_title_label)

        # Task metadata (priority, due date)
        self.task_metadata_label = QLabel()
        metadata_font = QFont()
        metadata_font.setPointSize(10)
        self.task_metadata_label.setFont(metadata_font)
        self.task_metadata_label.setStyleSheet("color: #555; margin-top: 5px;")
        card_layout.addWidget(self.task_metadata_label)

        # Task description
        self.task_description = QTextEdit()
        self.task_description.setReadOnly(True)
        self.task_description.setMaximumHeight(150)
        self.task_description.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 8px;
                color: #333;
            }
        """)
        card_layout.addWidget(self.task_description)

        layout.addWidget(self.card_frame)

    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create the action button section."""
        # Primary action (Complete)
        primary_layout = QHBoxLayout()
        primary_layout.addStretch()

        self.complete_button = QPushButton("✓ Complete")
        self.complete_button.setMinimumSize(180, 50)
        self.complete_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """)
        self.complete_button.clicked.connect(self._on_complete_clicked)
        primary_layout.addWidget(self.complete_button)

        primary_layout.addStretch()
        layout.addLayout(primary_layout)

        # Secondary actions (horizontal row)
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(10)

        button_style = """
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 11pt;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
        """

        self.defer_button = QPushButton("Defer")
        self.defer_button.setStyleSheet(button_style)
        self.defer_button.clicked.connect(self._on_defer_clicked)
        secondary_layout.addWidget(self.defer_button)

        self.delegate_button = QPushButton("Delegate")
        self.delegate_button.setStyleSheet(button_style)
        self.delegate_button.clicked.connect(self._on_delegate_clicked)
        secondary_layout.addWidget(self.delegate_button)

        self.someday_button = QPushButton("Someday")
        self.someday_button.setStyleSheet(button_style)
        self.someday_button.clicked.connect(self._on_someday_clicked)
        secondary_layout.addWidget(self.someday_button)

        self.trash_button = QPushButton("Trash")
        self.trash_button.setStyleSheet(button_style.replace("#6c757d", "#dc3545"))
        self.trash_button.clicked.connect(self._on_trash_clicked)
        secondary_layout.addWidget(self.trash_button)

        layout.addLayout(secondary_layout)

        # Refresh button (small, centered)
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()

        self.refresh_button = QPushButton("↻ Refresh Task List")
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #007bff;
                border: 1px solid #007bff;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #007bff;
                color: white;
            }
        """)
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        refresh_layout.addWidget(self.refresh_button)

        refresh_layout.addStretch()
        layout.addLayout(refresh_layout)

    def set_task(self, task: Optional[Task]):
        """
        Display a task in Focus Mode.

        Args:
            task: The task to display, or None to show empty state
        """
        self._current_task = task

        if task is None:
            self._show_empty_state()
        else:
            self._show_task(task)

    def _show_task(self, task: Task):
        """Display task information in the UI."""
        # Show card
        self.card_frame.show()

        # Set title
        self.task_title_label.setText(task.title)

        # Set metadata
        metadata_parts = []

        # Priority
        priority_text = task.get_priority_enum().name.capitalize()
        metadata_parts.append(f"Priority: {priority_text}")

        # Effective priority (if adjusted)
        if task.priority_adjustment > 0:
            eff_pri = task.get_effective_priority()
            metadata_parts.append(f"(Effective: {eff_pri:.2f})")

        # Due date
        if task.due_date:
            metadata_parts.append(f"Due: {task.due_date.strftime('%Y-%m-%d')}")

        self.task_metadata_label.setText(" | ".join(metadata_parts))

        # Set description
        if task.description:
            self.task_description.setText(task.description)
            self.task_description.show()
        else:
            self.task_description.hide()

        # Enable buttons
        self._enable_buttons(True)

    def _show_empty_state(self):
        """Show message when no tasks are available."""
        self.task_title_label.setText("No tasks available")
        self.task_metadata_label.setText("You're all caught up! 🎉")
        self.task_description.setText("Add a new task to get started.")
        self.task_description.show()

        # Disable action buttons
        self._enable_buttons(False)

    def _enable_buttons(self, enabled: bool):
        """Enable or disable all action buttons."""
        self.complete_button.setEnabled(enabled)
        self.defer_button.setEnabled(enabled)
        self.delegate_button.setEnabled(enabled)
        self.someday_button.setEnabled(enabled)
        self.trash_button.setEnabled(enabled)

    # Button click handlers
    def _on_complete_clicked(self):
        """Handle Complete button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_completed.emit(self._current_task.id)

    def _on_defer_clicked(self):
        """Handle Defer button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_deferred.emit(self._current_task.id)

    def _on_delegate_clicked(self):
        """Handle Delegate button click."""
        if self._current_task and self._current_task.id is not None:
            self.task_delegated.emit(self._current_task.id)

    def _on_someday_clicked(self):
        """Handle Someday button click."""
        if self._current_task and self._current_task.id is not None:
            reply = QMessageBox.question(
                self,
                "Move to Someday/Maybe?",
                f"Move '{self._current_task.title}' to Someday/Maybe?\n\n"
                "This task will be removed from active focus and resurfaced periodically.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.task_someday.emit(self._current_task.id)

    def _on_trash_clicked(self):
        """Handle Trash button click."""
        if self._current_task and self._current_task.id is not None:
            reply = QMessageBox.question(
                self,
                "Move to Trash?",
                f"Move '{self._current_task.title}' to trash?\n\n"
                "This task will be marked as unnecessary.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.task_trashed.emit(self._current_task.id)

    def _on_refresh_clicked(self):
        """Handle Refresh button click."""
        self.task_refreshed.emit()

    def get_current_task(self) -> Optional[Task]:
        """
        Get the currently displayed task.

        Returns:
            The current task, or None if no task is displayed
        """
        return self._current_task
