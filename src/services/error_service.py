"""
Error Service for OneTaskAtATime.

Provides centralized error handling with context-aware recovery suggestions.
"""

import sqlite3
import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple, Dict
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """
    Context information for an error.

    Contains all information needed to present user-friendly error
    messages with actionable recovery suggestions.
    """
    error: Exception
    operation: str  # "export_data", "complete_task", etc.
    user_action: str  # "completing task", "exporting data"
    recovery_suggestions: List[str]
    severity: ErrorSeverity
    can_retry: bool = False
    tech_details: Optional[str] = None


class ErrorService(QObject):
    """
    Service for handling errors with context-aware messaging.

    Provides user-friendly error dialogs with recovery suggestions
    based on the error type and operation context.
    """

    error_occurred = pyqtSignal(ErrorContext)

    # Mapping of (operation, error_type) -> recovery suggestions
    ERROR_RECOVERY_MAP: Dict[Tuple[str, type], List[str]] = {
        ("export_data", FileNotFoundError): [
            "Verify the export directory exists",
            "Try selecting a different location",
            "Check disk space availability"
        ],
        ("export_data", PermissionError): [
            "Check file permissions for the export directory",
            "Try running the application as administrator",
            "Select a different export location"
        ],
        ("export_data", OSError): [
            "Check available disk space",
            "Verify the file path is not too long",
            "Ensure the destination is not read-only"
        ],
        ("import_data", FileNotFoundError): [
            "Verify the import file exists",
            "Check the file path is correct",
            "Ensure the file has not been moved or deleted"
        ],
        ("import_data", ValueError): [
            "Verify JSON file format is valid",
            "Check schema version compatibility",
            "Try exporting from the source again"
        ],
        ("import_data", PermissionError): [
            "Check file read permissions",
            "Try running the application as administrator",
            "Copy the file to a different location"
        ],
        ("complete_task", sqlite3.OperationalError): [
            "Restart the application",
            "Run database integrity check in Tools menu",
            "Restore from recent backup if issue persists"
        ],
        ("complete_task", sqlite3.IntegrityError): [
            "Ensure task exists in database",
            "Refresh the task list",
            "Restart the application if issue continues"
        ],
        ("create_task", ValueError): [
            "Check all required fields are filled",
            "Verify date formats are correct",
            "Ensure priority is set correctly"
        ],
        ("create_task", sqlite3.IntegrityError): [
            "Check that context and tags exist",
            "Verify there are no duplicate task titles (if unique constraint exists)",
            "Refresh the application data"
        ],
        ("update_task", sqlite3.OperationalError): [
            "Ensure task still exists",
            "Refresh the task list",
            "Restart the application"
        ],
        ("delete_task", sqlite3.IntegrityError): [
            "Remove dependencies on this task first",
            "Check for related recurring tasks",
            "Consult the task history for references"
        ],
        ("load_tasks", sqlite3.DatabaseError): [
            "Run database integrity check",
            "Restore from backup",
            "Contact support if issue persists"
        ],
        ("save_settings", PermissionError): [
            "Check application data directory permissions",
            "Run as administrator",
            "Check antivirus is not blocking writes"
        ],
        ("database_connection", sqlite3.OperationalError): [
            "Ensure database file is not locked by another process",
            "Check file permissions",
            "Restart the application"
        ],
    }

    # Default recovery suggestions for common error types
    DEFAULT_RECOVERY_MAP: Dict[type, List[str]] = {
        FileNotFoundError: [
            "Verify the file or directory exists",
            "Check the path is correct",
            "Ensure proper permissions"
        ],
        PermissionError: [
            "Check file/directory permissions",
            "Try running as administrator",
            "Verify antivirus is not blocking access"
        ],
        sqlite3.OperationalError: [
            "Restart the application",
            "Check database file is not corrupted",
            "Restore from backup if needed"
        ],
        ValueError: [
            "Check input values are valid",
            "Verify data format is correct",
            "Review the operation parameters"
        ],
        ConnectionError: [
            "Check network connection",
            "Verify server is accessible",
            "Try again in a few moments"
        ],
    }

    def __init__(self):
        """Initialize the Error Service."""
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def handle_error(
        self,
        error: Exception,
        operation: str,
        user_action: str,
        parent_widget: Optional[QWidget] = None,
        can_retry: bool = False
    ) -> None:
        """
        Handle an error with context-aware messaging.

        Args:
            error: The exception that occurred
            operation: Technical operation name (e.g., "export_data")
            user_action: User-friendly action description (e.g., "exporting your tasks")
            parent_widget: Parent widget for error dialog
            can_retry: Whether the operation can be retried
        """
        context = self._build_error_context(error, operation, user_action, can_retry)
        self._log_error(context)
        self._show_error_dialog(context, parent_widget)
        self.error_occurred.emit(context)

    def _build_error_context(
        self,
        error: Exception,
        operation: str,
        user_action: str,
        can_retry: bool = False
    ) -> ErrorContext:
        """
        Build error context with recovery suggestions.

        Args:
            error: The exception that occurred
            operation: Technical operation name
            user_action: User-friendly action description
            can_retry: Whether the operation can be retried

        Returns:
            ErrorContext with all relevant information
        """
        error_type = type(error)
        recovery_suggestions = self._get_recovery_suggestions(error_type, operation)
        severity = self._determine_severity(error_type, operation)
        tech_details = self._format_technical_details(error)

        return ErrorContext(
            error=error,
            operation=operation,
            user_action=user_action,
            recovery_suggestions=recovery_suggestions,
            severity=severity,
            can_retry=can_retry,
            tech_details=tech_details
        )

    def _get_recovery_suggestions(self, error_type: type, operation: str) -> List[str]:
        """
        Get context-specific recovery suggestions.

        Args:
            error_type: Type of error that occurred
            operation: Operation that was being performed

        Returns:
            List of recovery suggestions
        """
        # Try to find operation-specific suggestions
        for (op, err_type), suggestions in self.ERROR_RECOVERY_MAP.items():
            if op == operation and err_type == error_type:
                return suggestions.copy()

        # Fall back to error-type defaults
        for err_type, suggestions in self.DEFAULT_RECOVERY_MAP.items():
            if error_type == err_type or issubclass(error_type, err_type):
                return suggestions.copy()

        # Generic fallback
        return [
            "Try the operation again",
            "Restart the application",
            "Contact support if issue persists"
        ]

    def _determine_severity(self, error_type: type, operation: str) -> ErrorSeverity:
        """
        Determine error severity based on type and operation.

        Args:
            error_type: Type of error
            operation: Operation being performed

        Returns:
            ErrorSeverity level
        """
        # Critical errors (data loss risk)
        if issubclass(error_type, sqlite3.DatabaseError):
            if "database" in operation or "save" in operation:
                return ErrorSeverity.CRITICAL

        # Errors (operation failed)
        if issubclass(error_type, (sqlite3.Error, PermissionError, FileNotFoundError)):
            return ErrorSeverity.ERROR

        # Warnings (might recover automatically)
        if issubclass(error_type, ValueError):
            return ErrorSeverity.WARNING

        # Default to ERROR
        return ErrorSeverity.ERROR

    def _format_technical_details(self, error: Exception) -> str:
        """
        Format technical error details for advanced users.

        Args:
            error: The exception

        Returns:
            Formatted technical details string
        """
        import traceback

        error_class = error.__class__.__name__
        error_message = str(error)
        trace = traceback.format_exc()

        return f"""Error Type: {error_class}
Error Message: {error_message}

Stack Trace:
{trace}"""

    def _log_error(self, context: ErrorContext):
        """
        Log error to application log.

        Args:
            context: Error context to log
        """
        log_message = f"Error during {context.operation}: {context.error}"

        if context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=context.error)
        elif context.severity == ErrorSeverity.ERROR:
            self.logger.error(log_message, exc_info=context.error)
        elif context.severity == ErrorSeverity.WARNING:
            self.logger.warning(log_message, exc_info=context.error)
        else:
            self.logger.info(log_message, exc_info=context.error)

    def _show_error_dialog(self, context: ErrorContext, parent: Optional[QWidget] = None):
        """
        Show error dialog to user.

        Args:
            context: Error context
            parent: Parent widget for dialog
        """
        # Import here to avoid circular dependency
        from src.ui.enhanced_error_dialog import EnhancedErrorDialog

        dialog = EnhancedErrorDialog(context, parent)
        dialog.exec_()
