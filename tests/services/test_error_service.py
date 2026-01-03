"""
Unit tests for ErrorService.

Tests error handling and recovery suggestion system.
"""

import pytest
import sqlite3

from src.services.error_service import ErrorService, ErrorSeverity, ErrorContext


@pytest.fixture
def error_service():
    """Create ErrorService instance."""
    return ErrorService()


def test_build_error_context_with_file_error(error_service):
    """Test building error context for file operations."""
    error = FileNotFoundError("File not found: export.json")

    context = error_service._build_error_context(
        error,
        operation="export_data",
        user_action="exporting your tasks to JSON"
    )

    assert context.error == error
    assert context.operation == "export_data"
    assert context.user_action == "exporting your tasks to JSON"
    assert len(context.recovery_suggestions) > 0
    assert context.severity == ErrorSeverity.ERROR


def test_get_recovery_suggestions_for_export(error_service):
    """Test getting recovery suggestions for export errors."""
    suggestions = error_service._get_recovery_suggestions(
        FileNotFoundError,
        "export_data"
    )

    assert len(suggestions) == 3
    assert "directory exists" in suggestions[0].lower()
    assert "different location" in suggestions[1].lower()


def test_get_recovery_suggestions_for_database_error(error_service):
    """Test getting recovery suggestions for database errors."""
    suggestions = error_service._get_recovery_suggestions(
        sqlite3.OperationalError,
        "complete_task"
    )

    assert len(suggestions) > 0
    assert any("restart" in s.lower() for s in suggestions)


def test_determine_severity_for_database_error(error_service):
    """Test severity determination for database errors."""
    severity = error_service._determine_severity(
        sqlite3.DatabaseError,
        "save_settings"
    )

    assert severity == ErrorSeverity.CRITICAL


def test_determine_severity_for_value_error(error_service):
    """Test severity determination for value errors."""
    severity = error_service._determine_severity(
        ValueError,
        "create_task"
    )

    assert severity == ErrorSeverity.WARNING


def test_format_technical_details(error_service):
    """Test formatting of technical error details."""
    error = ValueError("Invalid priority value: 5")

    details = error_service._format_technical_details(error)

    assert "Error Type: ValueError" in details
    assert "Invalid priority value: 5" in details
    assert "Stack Trace:" in details


def test_get_recovery_suggestions_fallback(error_service):
    """Test fallback to default suggestions for unknown errors."""
    # Custom error type not in mapping
    class CustomError(Exception):
        pass

    suggestions = error_service._get_recovery_suggestions(
        CustomError,
        "unknown_operation"
    )

    # Should get generic fallback
    assert len(suggestions) > 0
    assert any("try" in s.lower() or "restart" in s.lower() for s in suggestions)


def test_error_recovery_map_coverage(error_service):
    """Test that ERROR_RECOVERY_MAP has expected entries."""
    # Verify key operation-error pairs are covered
    assert ("export_data", FileNotFoundError) in error_service.ERROR_RECOVERY_MAP
    assert ("import_data", ValueError) in error_service.ERROR_RECOVERY_MAP
    assert ("complete_task", sqlite3.OperationalError) in error_service.ERROR_RECOVERY_MAP
    assert ("create_task", ValueError) in error_service.ERROR_RECOVERY_MAP


def test_default_recovery_map_coverage(error_service):
    """Test that DEFAULT_RECOVERY_MAP has expected error types."""
    assert FileNotFoundError in error_service.DEFAULT_RECOVERY_MAP
    assert PermissionError in error_service.DEFAULT_RECOVERY_MAP
    assert sqlite3.OperationalError in error_service.DEFAULT_RECOVERY_MAP
    assert ValueError in error_service.DEFAULT_RECOVERY_MAP
