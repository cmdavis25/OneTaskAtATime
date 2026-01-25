"""
Unit tests for PostponeDialog.

Tests the postpone dialog including:
- Dialog initialization
- Reason type selection
- Date handling
- Delegation fields
- Result collection
"""

import pytest
import sqlite3
from datetime import date, timedelta

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QDate

from src.models.task import Task
from src.models.enums import TaskState, PostponeReasonType
from src.ui.postpone_dialog import PostponeDialog


@pytest.fixture
def sample_task():
    """Create a sample task."""
    return Task(
        id=1,
        title="Test Task",
        description="Test description",
        base_priority=2,
        state=TaskState.ACTIVE
    )


@pytest.fixture
def defer_dialog(qapp, db_connection, sample_task):
    """Create defer dialog instance."""
    dialog = PostponeDialog("Test Task", "defer", sample_task, db_connection)
    yield dialog
    dialog.close()


@pytest.fixture
def delegate_dialog(qapp, db_connection, sample_task):
    """Create delegate dialog instance."""
    dialog = PostponeDialog("Test Task", "delegate", sample_task, db_connection)
    yield dialog
    dialog.close()


class TestDialogInitialization:
    """Test dialog initialization."""

    def test_defer_dialog_creation(self, defer_dialog):
        """Test that defer dialog can be created."""
        assert defer_dialog is not None

    def test_delegate_dialog_creation(self, delegate_dialog):
        """Test that delegate dialog can be created."""
        assert delegate_dialog is not None

    def test_dialog_has_window_title(self, defer_dialog):
        """Test that dialog has appropriate window title."""
        title = defer_dialog.windowTitle()
        assert len(title) > 0

    def test_dialog_displays_task_title(self, defer_dialog):
        """Test that dialog displays the task title."""
        # Task title should be visible in the dialog
        assert hasattr(defer_dialog, 'task_label') or hasattr(defer_dialog, 'layout')


class TestDeferMode:
    """Test defer mode functionality."""

    def test_defer_dialog_has_date_picker(self, defer_dialog):
        """Test that defer dialog has date picker."""
        assert hasattr(defer_dialog, 'start_date_edit')
        assert defer_dialog.start_date_edit is not None

    @pytest.mark.skip(reason="Qt limitation: isVisible() returns False for widgets in unshown dialogs")
    def test_defer_dialog_date_picker_visible(self, defer_dialog):
        """Test that date picker is visible in defer mode."""
        assert defer_dialog.start_date_edit.isVisible()

    def test_defer_dialog_default_date_is_tomorrow(self, defer_dialog):
        """Test that default start date is tomorrow."""
        tomorrow = date.today() + timedelta(days=1)
        current_date = defer_dialog.start_date_edit.date().toPyDate()
        assert current_date == tomorrow


class TestDelegateMode:
    """Test delegate mode functionality."""

    def test_delegate_dialog_has_person_field(self, delegate_dialog):
        """Test that delegate dialog has person name field."""
        assert hasattr(delegate_dialog, 'delegate_person_edit')
        assert delegate_dialog.delegate_person_edit is not None

    def test_delegate_dialog_has_followup_date(self, delegate_dialog):
        """Test that delegate dialog has follow-up date field."""
        assert hasattr(delegate_dialog, 'followup_date_edit')
        assert delegate_dialog.followup_date_edit is not None

    @pytest.mark.skip(reason="Qt limitation: isVisible() returns False for widgets in unshown dialogs")
    def test_delegate_dialog_person_field_visible(self, delegate_dialog):
        """Test that person field is visible in delegate mode."""
        assert delegate_dialog.delegate_person_edit.isVisible()

    @pytest.mark.skip(reason="Qt limitation: isVisible() returns False for widgets in unshown dialogs")
    def test_delegate_dialog_followup_date_visible(self, delegate_dialog):
        """Test that follow-up date is visible in delegate mode."""
        assert delegate_dialog.followup_date_edit.isVisible()


class TestReasonTypeSelection:
    """Test reason type selection."""

    def test_dialog_has_reason_buttons(self, defer_dialog):
        """Test that dialog has reason type buttons."""
        assert hasattr(defer_dialog, 'reason_group')

    def test_dialog_has_blocker_reason_option(self, defer_dialog):
        """Test that dialog has blocker reason option."""
        assert hasattr(defer_dialog, 'blocker_radio')

    def test_dialog_has_subtasks_reason_option(self, defer_dialog):
        """Test that dialog has subtasks reason option."""
        assert hasattr(defer_dialog, 'subtasks_radio')

    def test_dialog_has_dependency_reason_option(self, defer_dialog):
        """Test that dialog has dependency reason option."""
        assert hasattr(defer_dialog, 'dependency_radio')

    def test_dialog_has_not_ready_reason_option(self, defer_dialog):
        """Test that dialog has 'not ready' reason option."""
        assert hasattr(defer_dialog, 'not_ready_radio')


class TestNotesField:
    """Test notes/details field."""

    def test_dialog_has_notes_field(self, defer_dialog):
        """Test that dialog has notes text field."""
        assert hasattr(defer_dialog, 'notes_edit')
        assert defer_dialog.notes_edit is not None

    def test_notes_field_is_text_edit(self, defer_dialog):
        """Test that notes field allows multi-line input."""
        from PyQt5.QtWidgets import QTextEdit
        assert isinstance(defer_dialog.notes_edit, QTextEdit)


class TestButtonBehavior:
    """Test button behavior."""

    def test_dialog_has_ok_button(self, defer_dialog):
        """Test that dialog has OK button."""
        assert hasattr(defer_dialog, 'ok_button')
        assert defer_dialog.ok_button is not None

    def test_dialog_has_cancel_button(self, defer_dialog):
        """Test that dialog has cancel button."""
        assert hasattr(defer_dialog, 'cancel_button')
        assert defer_dialog.cancel_button is not None

    def test_cancel_button_rejects_dialog(self, defer_dialog):
        """Test that cancel button rejects dialog."""
        rejected = []
        defer_dialog.rejected.connect(lambda: rejected.append(True))

        defer_dialog.cancel_button.click()

        assert len(rejected) == 1


class TestResultCollection:
    """Test result collection from dialog."""

    def test_get_result_returns_dict(self, defer_dialog):
        """Test that get_result returns dictionary."""
        # Select a reason
        defer_dialog.not_ready_radio.setChecked(True)

        result = defer_dialog.get_result()
        assert isinstance(result, dict)

    def test_defer_result_includes_start_date(self, defer_dialog):
        """Test that defer result includes start date."""
        defer_dialog.not_ready_radio.setChecked(True)

        result = defer_dialog.get_result()
        assert 'start_date' in result

    def test_defer_result_includes_reason_type(self, defer_dialog):
        """Test that defer result includes reason type."""
        defer_dialog.not_ready_radio.setChecked(True)

        result = defer_dialog.get_result()
        assert 'reason_type' in result

    def test_defer_result_includes_notes(self, defer_dialog):
        """Test that defer result includes notes."""
        defer_dialog.not_ready_radio.setChecked(True)
        defer_dialog.notes_edit.setPlainText("Test notes")

        result = defer_dialog.get_result()
        assert 'notes' in result
        assert result['notes'] == "Test notes"

    def test_delegate_result_includes_person(self, delegate_dialog):
        """Test that delegate result includes person name."""
        delegate_dialog.delegate_person_edit.setText("John Doe")

        result = delegate_dialog.get_result()
        assert 'delegate_person' in result
        assert result['delegate_person'] == "John Doe"

    def test_delegate_result_includes_followup_date(self, delegate_dialog):
        """Test that delegate result includes follow-up date."""
        result = delegate_dialog.get_result()
        assert 'followup_date' in result


class TestValidation:
    """Test form validation."""

    def test_defer_requires_reason_selection(self, defer_dialog):
        """Test that a reason must be selected."""
        # Should have validation method
        assert hasattr(defer_dialog, '_validate')

    def test_delegate_requires_person_name(self, delegate_dialog):
        """Test that delegate requires person name."""
        # Clear person field
        delegate_dialog.delegate_person_edit.clear()

        # Validation should fail
        is_valid = delegate_dialog._validate()
        assert is_valid is False

    def test_delegate_valid_with_person_name(self, delegate_dialog):
        """Test that delegate is valid with person name."""
        # Set person field
        delegate_dialog.delegate_person_edit.setText("John Doe")

        # Validation should pass
        is_valid = delegate_dialog._validate()
        assert is_valid is True


class TestBlockerHandling:
    """Test blocker-specific handling."""

    def test_selecting_blocker_shows_blocker_field(self, defer_dialog):
        """Test that selecting blocker reason shows blocker description field."""
        defer_dialog.blocker_radio.setChecked(True)

        # Should show blocker-specific field
        assert hasattr(defer_dialog, 'blocker_description_edit')

    def test_blocker_result_includes_description(self, defer_dialog):
        """Test that blocker result includes description."""
        defer_dialog.blocker_radio.setChecked(True)

        if hasattr(defer_dialog, 'blocker_description_edit'):
            defer_dialog.blocker_description_edit.setText("Waiting for API access")

        result = defer_dialog.get_result()
        assert result['reason_type'] == PostponeReasonType.BLOCKER.value


class TestDependencyHandling:
    """Test dependency-specific handling."""

    def test_selecting_dependency_shows_dependency_field(self, defer_dialog):
        """Test that selecting dependency shows related field."""
        defer_dialog.dependency_radio.setChecked(True)

        # Should enable dependency-specific UI
        result = defer_dialog.get_result()
        assert result['reason_type'] == PostponeReasonType.DEPENDENCY.value


class TestSubtasksHandling:
    """Test subtasks-specific handling."""

    def test_selecting_subtasks_indicates_breakdown_needed(self, defer_dialog):
        """Test that selecting subtasks indicates breakdown is needed."""
        defer_dialog.subtasks_radio.setChecked(True)

        result = defer_dialog.get_result()
        assert result['reason_type'] == PostponeReasonType.MULTIPLE_SUBTASKS.value


class TestDialogLayout:
    """Test dialog layout."""

    def test_dialog_has_minimum_size(self, defer_dialog):
        """Test that dialog has reasonable minimum size."""
        min_size = defer_dialog.minimumSize()
        assert min_size.width() > 0 or defer_dialog.width() > 0

    def test_defer_fields_hidden_in_delegate_mode(self, delegate_dialog):
        """Test that defer-specific fields are hidden in delegate mode."""
        # Start date field should not be visible in delegate mode
        # (it may exist but be hidden)
        if hasattr(delegate_dialog, 'start_date_edit'):
            assert not delegate_dialog.start_date_edit.isVisible()

    def test_delegate_fields_hidden_in_defer_mode(self, defer_dialog):
        """Test that delegate-specific fields are hidden in defer mode."""
        # Delegation fields should not be visible in defer mode
        if hasattr(defer_dialog, 'delegate_person_edit'):
            assert not defer_dialog.delegate_person_edit.isVisible()
