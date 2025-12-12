"""
Tests for Context Management Dialog UI component.

Phase 4: Task Management Interface tests.
"""

import pytest
from PyQt5.QtCore import Qt
from src.ui.context_management_dialog import ContextManagementDialog
from src.models import Context


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""
    def __init__(self, connection):
        self._connection = connection

    def get_connection(self):
        return self._connection

    def close(self):
        pass


@pytest.fixture
def context_dialog(qtbot, test_db):
    """Create a ContextManagementDialog for testing."""
    mock_db = MockDatabaseConnection(test_db)
    dialog = ContextManagementDialog(mock_db)
    qtbot.addWidget(dialog)
    return dialog


def test_context_dialog_initialization(context_dialog):
    """Test that context management dialog initializes correctly."""
    assert context_dialog is not None
    assert context_dialog.context_list is not None
    assert context_dialog.name_edit is not None
    assert context_dialog.description_edit is not None


def test_load_contexts(context_dialog):
    """Test loading contexts into the list."""
    # Create some contexts
    context1 = Context(name="@computer", description="At computer")
    context2 = Context(name="@phone", description="Phone calls")

    context_dialog.context_dao.create(context1)
    context_dialog.context_dao.create(context2)

    # Reload
    context_dialog._load_contexts()

    # Check that contexts appear in list
    assert context_dialog.context_list.count() == 2


def test_create_new_context(context_dialog, qtbot):
    """Test creating a new context."""
    # Click new button
    context_dialog._on_new_context()

    # Fill in form
    context_dialog.name_edit.setText("@errands")
    context_dialog.description_edit.setText("Running errands")

    # Save
    with qtbot.waitSignal(context_dialog.contexts_changed, timeout=1000):
        context_dialog._on_save_context()

    # Verify context was created
    contexts = context_dialog.context_dao.get_all()
    assert len(contexts) == 1
    assert contexts[0].name == "@errands"


def test_edit_existing_context(context_dialog, qtbot):
    """Test editing an existing context."""
    # Create a context
    context = Context(name="@office", description="At the office")
    created_context = context_dialog.context_dao.create(context)

    # Reload
    context_dialog._load_contexts()

    # Select the context
    context_dialog.context_list.setCurrentRow(0)

    # Modify the name
    context_dialog.name_edit.setText("@office-updated")

    # Save
    with qtbot.waitSignal(context_dialog.contexts_changed, timeout=1000):
        context_dialog._on_save_context()

    # Verify context was updated
    updated_context = context_dialog.context_dao.get_by_id(created_context.id)
    assert updated_context.name == "@office-updated"


def test_delete_context(context_dialog, qtbot, monkeypatch):
    """Test deleting a context."""
    # Create a context
    context = Context(name="@gym", description="At the gym")
    context_dialog.context_dao.create(context)

    # Reload
    context_dialog._load_contexts()

    # Select the context
    context_dialog.context_list.setCurrentRow(0)

    # Mock the confirmation dialog to always return Yes
    from PyQt5.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)

    # Delete
    with qtbot.waitSignal(context_dialog.contexts_changed, timeout=1000):
        context_dialog._on_delete_context()

    # Verify context was deleted
    contexts = context_dialog.context_dao.get_all()
    assert len(contexts) == 0


def test_clear_form(context_dialog):
    """Test clearing the form."""
    # Fill in form
    context_dialog.name_edit.setText("@test")
    context_dialog.description_edit.setText("Test description")

    # Clear
    context_dialog._clear_form()

    # Verify fields are cleared
    assert context_dialog.name_edit.text() == ""
    assert context_dialog.description_edit.toPlainText() == ""
    assert context_dialog.current_context is None
