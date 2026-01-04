"""
ReflectionDialog for OneTaskAtATime application.

Mandatory reflection dialog shown when postpone patterns are detected.
Forces user to consciously explain repeated postponement or take disposition action.
"""

from typing import Optional, Dict, Any
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QMessageBox, QGroupBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from ..services.postpone_suggestion_service import PostponeSuggestion, SuggestionType
from ..models.enums import TaskState
from .geometry_mixin import GeometryMixin


class ReflectionDialog(QDialog, GeometryMixin):
    """
    Blocking modal dialog for mandatory reflection on postpone patterns.

    Unlike dismissible notifications, this dialog:
    - MUST be addressed before continuing with postpone
    - Requires 20-character minimum explanation OR disposition action
    - Shows historical context from previous postpones
    - Provides direct action buttons (Someday/Maybe, Trash, Continue with reflection)

    This design prevents unconscious postpone loops and forces intentional decisions.
    """

    MIN_REFLECTION_LENGTH = 20  # Character minimum for thoughtful reflection

    def __init__(self, suggestion: PostponeSuggestion, task_title: str, parent=None):
        """
        Initialize reflection dialog.

        Args:
            suggestion: The detected pattern and suggestion details
            task_title: Title of the task being postponed
            parent: Parent widget
        """
        super().__init__(parent)
        self.suggestion = suggestion
        self.task_title = task_title
        self.reflection_text = ""
        self.disposition_action: Optional[TaskState] = None

        # Initialize geometry persistence (get db_connection from parent if available)
        if parent and hasattr(parent, 'db_connection'):
            self._init_geometry_persistence(parent.db_connection, default_width=600, default_height=500)

        self.setWindowTitle("Reflection Required")
        self.setModal(True)  # Blocking dialog
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        self._init_ui()

    def _init_ui(self):
        """Initialize UI components."""
        layout = QVBoxLayout(self)

        # Warning header
        header = QLabel("⚠️ Pattern Detected - Reflection Required")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet("color: #dc3545; padding: 10px;")
        layout.addWidget(header)

        # Task title
        task_label = QLabel(f"Task: {self.task_title}")
        task_font = QFont()
        task_font.setPointSize(11)
        task_font.setBold(True)
        task_label.setFont(task_font)
        task_label.setWordWrap(True)
        task_label.setStyleSheet("padding: 5px; background-color: #f8f9fa; border-radius: 3px;")
        layout.addWidget(task_label)

        # Pattern summary
        pattern_box = QGroupBox(self.suggestion.title)
        pattern_layout = QVBoxLayout()

        message_label = QLabel(self.suggestion.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("padding: 10px;")
        pattern_layout.addWidget(message_label)

        pattern_box.setLayout(pattern_layout)
        layout.addWidget(pattern_box)

        # Historical context (scrollable)
        if self.suggestion.previous_notes:
            context_box = QGroupBox("Previous Postpone Notes")
            context_layout = QVBoxLayout()

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setMaximumHeight(150)

            context_widget = QWidget()
            context_widget_layout = QVBoxLayout()

            historical_context = self.suggestion.get_historical_context()
            context_label = QLabel(historical_context)
            context_label.setWordWrap(True)
            context_label.setStyleSheet("padding: 8px; font-family: monospace;")
            context_widget_layout.addWidget(context_label)

            context_widget.setLayout(context_widget_layout)
            scroll_area.setWidget(context_widget)

            context_layout.addWidget(scroll_area)
            context_box.setLayout(context_layout)
            layout.addWidget(context_box)

        # Reflection input
        reflection_box = QGroupBox("Your Reflection (Required)")
        reflection_layout = QVBoxLayout()

        instruction = QLabel(
            f"To continue postponing, explain WHY this pattern keeps happening "
            f"(minimum {self.MIN_REFLECTION_LENGTH} characters):"
        )
        instruction.setWordWrap(True)
        instruction.setStyleSheet("padding: 5px; font-weight: bold;")
        reflection_layout.addWidget(instruction)

        self.reflection_input = QTextEdit()
        self.reflection_input.setPlaceholderText(
            "Example: 'This task requires access to the staging server, "
            "which has been down for maintenance. I'm checking daily for availability.'"
        )
        self.reflection_input.setMinimumHeight(100)
        self.reflection_input.textChanged.connect(self._on_reflection_changed)
        reflection_layout.addWidget(self.reflection_input)

        self.char_count_label = QLabel(f"0 / {self.MIN_REFLECTION_LENGTH} characters")
        self.char_count_label.setStyleSheet("color: #6c757d; padding: 3px;")
        reflection_layout.addWidget(self.char_count_label)

        reflection_box.setLayout(reflection_layout)
        layout.addWidget(reflection_box)

        # Action buttons
        button_box = QGroupBox("Choose an Action")
        button_layout = QVBoxLayout()

        # Disposition actions (immediate resolution)
        disposition_label = QLabel("Or take action to resolve this pattern:")
        disposition_label.setStyleSheet("font-weight: bold; padding: 5px;")
        button_layout.addWidget(disposition_label)

        disposition_button_layout = QHBoxLayout()

        self.someday_button = QPushButton("📅 Move to Someday/Maybe")
        self.someday_button.setToolTip("Not urgent - defer indefinitely for later review")
        self.someday_button.clicked.connect(lambda: self._handle_disposition(TaskState.SOMEDAY))
        disposition_button_layout.addWidget(self.someday_button)

        self.trash_button = QPushButton("🗑️ Move to Trash")
        self.trash_button.setToolTip("No longer relevant - archive this task")
        self.trash_button.clicked.connect(lambda: self._handle_disposition(TaskState.TRASH))
        disposition_button_layout.addWidget(self.trash_button)

        button_layout.addLayout(disposition_button_layout)

        # Or continue with reflection
        continue_label = QLabel("Or continue postponing with reflection:")
        continue_label.setStyleSheet("font-weight: bold; padding: 5px; padding-top: 10px;")
        button_layout.addWidget(continue_label)

        continue_button_layout = QHBoxLayout()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setToolTip("Abort the postpone operation")
        self.cancel_button.clicked.connect(self.reject)
        continue_button_layout.addWidget(self.cancel_button)

        self.continue_button = QPushButton("Continue with Reflection")
        self.continue_button.setToolTip(f"Requires {self.MIN_REFLECTION_LENGTH}+ character explanation")
        self.continue_button.setEnabled(False)  # Disabled until valid reflection
        self.continue_button.clicked.connect(self._handle_continue)
        self.continue_button.setStyleSheet(
            "background-color: #28a745; color: white; font-weight: bold; padding: 8px;"
        )
        continue_button_layout.addWidget(self.continue_button)

        button_layout.addLayout(continue_button_layout)

        button_box.setLayout(button_layout)
        layout.addWidget(button_box)

        # Add stretch to push buttons to bottom
        layout.addStretch()

    def _on_reflection_changed(self):
        """Update character count and enable/disable continue button."""
        text = self.reflection_input.toPlainText().strip()
        char_count = len(text)

        self.char_count_label.setText(f"{char_count} / {self.MIN_REFLECTION_LENGTH} characters")

        if char_count >= self.MIN_REFLECTION_LENGTH:
            self.char_count_label.setStyleSheet("color: #28a745; font-weight: bold; padding: 3px;")
            self.continue_button.setEnabled(True)
        else:
            self.char_count_label.setStyleSheet("color: #dc3545; padding: 3px;")
            self.continue_button.setEnabled(False)

    def _handle_disposition(self, new_state: TaskState):
        """
        Handle disposition action (Someday/Maybe or Trash).

        Args:
            new_state: TaskState to move task to
        """
        state_name = "Someday/Maybe" if new_state == TaskState.SOMEDAY_MAYBE else "Trash"

        # Confirm action
        reply = QMessageBox.question(
            self,
            "Confirm Action",
            f"Move '{self.task_title}' to {state_name}?\n\n"
            f"This will resolve the postpone pattern by removing the task from your active list.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.disposition_action = new_state
            self.accept()

    def _handle_continue(self):
        """Handle continue with reflection (validates input)."""
        text = self.reflection_input.toPlainText().strip()

        if len(text) < self.MIN_REFLECTION_LENGTH:
            QMessageBox.warning(
                self,
                "Reflection Too Short",
                f"Please provide a thoughtful reflection of at least {self.MIN_REFLECTION_LENGTH} characters.\n\n"
                f"This helps you understand why you keep postponing this task."
            )
            return

        self.reflection_text = text
        self.accept()

    def get_result(self) -> Dict[str, Any]:
        """
        Get the result of the reflection dialog.

        Returns:
            Dictionary with:
            - 'disposition': TaskState if user chose disposition action, None otherwise
            - 'reflection': User's reflection text (if continuing)
            - 'cancelled': True if user cancelled
        """
        if self.result() == QDialog.Rejected:
            return {
                'disposition': None,
                'reflection': '',
                'cancelled': True
            }

        return {
            'disposition': self.disposition_action,
            'reflection': self.reflection_text,
            'cancelled': False
        }
