"""
Enhanced Error Dialog for OneTaskAtATime.

Provides user-friendly error messages with recovery suggestions.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap

from src.services.error_service import ErrorContext, ErrorSeverity


class EnhancedErrorDialog(QDialog):
    """
    Enhanced error dialog with user-friendly messages and recovery suggestions.

    Displays errors with:
    - Severity-based icons
    - Clear, non-technical descriptions
    - Actionable recovery suggestions
    - Expandable technical details section
    """

    def __init__(self, context: ErrorContext, parent=None):
        """
        Initialize the Enhanced Error Dialog.

        Args:
            context: ErrorContext with error information
            parent: Parent widget
        """
        super().__init__(parent)
        self.context = context

        self._setup_ui()

    def _setup_ui(self):
        """Set up the user interface."""
        # Window setup
        self.setWindowTitle(self._get_title())
        self.setMinimumWidth(500)
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Error header with icon and message
        header_layout = QHBoxLayout()

        # Icon based on severity
        icon_label = QLabel()
        icon_label.setPixmap(self._get_severity_icon())
        icon_label.setAlignment(Qt.AlignTop)
        header_layout.addWidget(icon_label)

        # Error message
        message_label = QLabel(self._get_user_message())
        message_label.setWordWrap(True)
        message_label.setTextFormat(Qt.RichText)
        header_layout.addWidget(message_label, 1)

        layout.addLayout(header_layout)

        # Recovery suggestions
        if self.context.recovery_suggestions:
            suggestions_group = QGroupBox("What you can try:")
            suggestions_layout = QVBoxLayout()

            for suggestion in self.context.recovery_suggestions:
                bullet_label = QLabel(f"• {suggestion}")
                bullet_label.setWordWrap(True)
                suggestions_layout.addWidget(bullet_label)

            suggestions_group.setLayout(suggestions_layout)
            layout.addWidget(suggestions_group)

        # Technical details (collapsible)
        if self.context.tech_details:
            self.details_group = QGroupBox("Technical Details")
            self.details_group.setCheckable(True)
            self.details_group.setChecked(False)
            self.details_group.toggled.connect(self._on_details_toggled)

            details_layout = QVBoxLayout()

            self.details_text = QTextEdit()
            self.details_text.setPlainText(self.context.tech_details)
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(200)
            self.details_text.setVisible(False)
            details_layout.addWidget(self.details_text)

            self.details_group.setLayout(details_layout)
            layout.addWidget(self.details_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        if self.context.can_retry:
            retry_button = QPushButton("Retry")
            retry_button.clicked.connect(self._on_retry)
            button_layout.addWidget(retry_button)

        copy_button = QPushButton("Copy Error")
        copy_button.clicked.connect(self._on_copy_error)
        button_layout.addWidget(copy_button)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _get_title(self) -> str:
        """Get dialog title based on severity."""
        severity_titles = {
            ErrorSeverity.INFO: "Information",
            ErrorSeverity.WARNING: "Warning",
            ErrorSeverity.ERROR: "Error",
            ErrorSeverity.CRITICAL: "Critical Error"
        }
        return severity_titles.get(self.context.severity, "Error")

    def _get_severity_icon(self) -> QPixmap:
        """Get icon pixmap based on error severity."""
        # Use Qt standard icons
        style = self.style()

        if self.context.severity == ErrorSeverity.CRITICAL:
            icon = style.standardIcon(style.SP_MessageBoxCritical)
        elif self.context.severity == ErrorSeverity.ERROR:
            icon = style.standardIcon(style.SP_MessageBoxCritical)
        elif self.context.severity == ErrorSeverity.WARNING:
            icon = style.standardIcon(style.SP_MessageBoxWarning)
        else:
            icon = style.standardIcon(style.SP_MessageBoxInformation)

        return icon.pixmap(48, 48)

    def _get_user_message(self) -> str:
        """Get user-friendly error message."""
        if self.context.severity == ErrorSeverity.CRITICAL:
            prefix = "<b>Critical Error:</b> "
        elif self.context.severity == ErrorSeverity.ERROR:
            prefix = "<b>Error:</b> "
        elif self.context.severity == ErrorSeverity.WARNING:
            prefix = "<b>Warning:</b> "
        else:
            prefix = ""

        message = f"We couldn't complete {self.context.user_action}"

        # Add error specifics if available
        error_msg = str(self.context.error)
        if error_msg and error_msg != "":
            # Make error message more user-friendly
            user_friendly_msg = self._make_error_user_friendly(error_msg)
            message += f" due to: {user_friendly_msg}"
        else:
            message += "."

        return prefix + message

    def _make_error_user_friendly(self, error_msg: str) -> str:
        """
        Convert technical error message to user-friendly text.

        Args:
            error_msg: Technical error message

        Returns:
            User-friendly version
        """
        # Common technical -> user-friendly mappings
        replacements = {
            "no such table": "a database structure issue",
            "database is locked": "the database being in use by another process",
            "constraint failed": "a data validation issue",
            "foreign key constraint": "related data dependencies",
            "[Errno 2]": "file not found",
            "[Errno 13]": "permission denied",
            "[Errno 28]": "insufficient disk space",
        }

        user_msg = error_msg.lower()
        for tech_term, friendly_term in replacements.items():
            if tech_term in user_msg:
                return friendly_term

        # If no replacement found, return original (up to 100 chars)
        if len(error_msg) > 100:
            return error_msg[:100] + "..."
        return error_msg

    def _on_details_toggled(self, checked: bool):
        """Handle technical details toggle."""
        self.details_text.setVisible(checked)

    def _on_retry(self):
        """Handle retry button click."""
        # Close dialog with retry result
        self.done(2)  # Custom result code for retry

    def _on_copy_error(self):
        """Copy error details to clipboard."""
        clipboard = QApplication.clipboard()

        # Format full error information
        error_text = f"""OneTaskAtATime Error Report
{'=' * 50}

Operation: {self.context.operation}
User Action: {self.context.user_action}
Severity: {self.context.severity.value}

Error Message:
{str(self.context.error)}

Recovery Suggestions:
"""
        for i, suggestion in enumerate(self.context.recovery_suggestions, 1):
            error_text += f"{i}. {suggestion}\n"

        error_text += f"\n{self.context.tech_details}"

        clipboard.setText(error_text)

        # Show confirmation (briefly)
        self.copy_button = self.sender()
        original_text = self.copy_button.text()
        self.copy_button.setText("Copied!")
        self.copy_button.setEnabled(False)

        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._reset_copy_button(original_text))

    def _reset_copy_button(self, original_text: str):
        """Reset copy button after brief delay."""
        try:
            self.copy_button.setText(original_text)
            self.copy_button.setEnabled(True)
        except (AttributeError, RuntimeError):
            # Widget may have been destroyed
            pass
