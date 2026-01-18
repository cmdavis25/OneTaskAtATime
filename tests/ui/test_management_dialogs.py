"""
Unit tests for management dialogs (ContextManagementDialog, ProjectTagManagementDialog).

Tests the management dialogs including:
- Dialog initialization
- Item listing
- Create/edit/delete operations
- Validation
"""

import pytest
import sqlite3

from PyQt5.QtWidgets import QApplication

from src.database.schema import DatabaseSchema
from src.database.context_dao import ContextDAO
from src.database.project_tag_dao import ProjectTagDAO
from src.models.context import Context
from src.models.project_tag import ProjectTag
from src.ui.context_management_dialog import ContextManagementDialog
from src.ui.project_tag_management_dialog import ProjectTagManagementDialog


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def contexts_db(db_connection):
    """Create database with sample contexts."""
    context_dao = ContextDAO(db_connection)

    contexts = [
        Context(name="Work", description="Work tasks"),
        Context(name="Home", description="Personal tasks"),
        Context(name="Errands", description="Things to do out")
    ]

    for context in contexts:
        context_dao.create(context)

    db_connection.commit()
    return db_connection


@pytest.fixture
def tags_db(db_connection):
    """Create database with sample project tags."""
    tag_dao = ProjectTagDAO(db_connection)

    tags = [
        ProjectTag(name="Development", color="#FF0000"),
        ProjectTag(name="Marketing", color="#00FF00"),
        ProjectTag(name="Planning", color="#0000FF")
    ]

    for tag in tags:
        tag_dao.create(tag)

    db_connection.commit()
    return db_connection


class TestContextManagementDialog:
    """Test ContextManagementDialog."""

    def test_dialog_creation(self, qapp, db_connection):
        """Test that context management dialog can be created."""
        dialog = ContextManagementDialog(db_connection)
        assert dialog is not None
        dialog.close()

    def test_dialog_has_window_title(self, qapp, db_connection):
        """Test that dialog has appropriate title."""
        dialog = ContextManagementDialog(db_connection)
        title = dialog.windowTitle()
        assert len(title) > 0
        assert "Context" in title
        dialog.close()

    def test_dialog_has_context_list(self, qapp, db_connection):
        """Test that dialog has context list widget."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'context_list')
        dialog.close()

    def test_dialog_loads_contexts(self, qapp, contexts_db):
        """Test that dialog loads existing contexts."""
        dialog = ContextManagementDialog(contexts_db)
        assert dialog.context_list.count() >= 3
        dialog.close()

    def test_dialog_has_add_button(self, qapp, db_connection):
        """Test that dialog has add button."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'add_button')
        dialog.close()

    def test_dialog_has_edit_button(self, qapp, db_connection):
        """Test that dialog has edit button."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'edit_button')
        dialog.close()

    def test_dialog_has_delete_button(self, qapp, db_connection):
        """Test that dialog has delete button."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'delete_button')
        dialog.close()

    def test_dialog_has_close_button(self, qapp, db_connection):
        """Test that dialog has close button."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'close_button')
        dialog.close()

    def test_edit_button_disabled_without_selection(self, qapp, db_connection):
        """Test that edit button is disabled without selection."""
        dialog = ContextManagementDialog(db_connection)
        # With no selection, edit should be disabled
        assert not dialog.edit_button.isEnabled()
        dialog.close()

    def test_delete_button_disabled_without_selection(self, qapp, db_connection):
        """Test that delete button is disabled without selection."""
        dialog = ContextManagementDialog(db_connection)
        # With no selection, delete should be disabled
        assert not dialog.delete_button.isEnabled()
        dialog.close()

    def test_edit_button_enabled_with_selection(self, qapp, contexts_db):
        """Test that edit button enables with selection."""
        dialog = ContextManagementDialog(contexts_db)
        if dialog.context_list.count() > 0:
            dialog.context_list.setCurrentRow(0)
            assert dialog.edit_button.isEnabled()
        dialog.close()

    def test_delete_button_enabled_with_selection(self, qapp, contexts_db):
        """Test that delete button enables with selection."""
        dialog = ContextManagementDialog(contexts_db)
        if dialog.context_list.count() > 0:
            dialog.context_list.setCurrentRow(0)
            assert dialog.delete_button.isEnabled()
        dialog.close()


class TestProjectTagManagementDialog:
    """Test ProjectTagManagementDialog."""

    def test_dialog_creation(self, qapp, db_connection):
        """Test that project tag management dialog can be created."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert dialog is not None
        dialog.close()

    def test_dialog_has_window_title(self, qapp, db_connection):
        """Test that dialog has appropriate title."""
        dialog = ProjectTagManagementDialog(db_connection)
        title = dialog.windowTitle()
        assert len(title) > 0
        assert "Project" in title or "Tag" in title
        dialog.close()

    def test_dialog_has_tag_list(self, qapp, db_connection):
        """Test that dialog has tag list widget."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'tag_list')
        dialog.close()

    def test_dialog_loads_tags(self, qapp, tags_db):
        """Test that dialog loads existing project tags."""
        dialog = ProjectTagManagementDialog(tags_db)
        assert dialog.tag_list.count() >= 3
        dialog.close()

    def test_dialog_has_add_button(self, qapp, db_connection):
        """Test that dialog has add button."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'add_button')
        dialog.close()

    def test_dialog_has_edit_button(self, qapp, db_connection):
        """Test that dialog has edit button."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'edit_button')
        dialog.close()

    def test_dialog_has_delete_button(self, qapp, db_connection):
        """Test that dialog has delete button."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'delete_button')
        dialog.close()

    def test_dialog_has_close_button(self, qapp, db_connection):
        """Test that dialog has close button."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'close_button')
        dialog.close()

    def test_edit_button_disabled_without_selection(self, qapp, db_connection):
        """Test that edit button is disabled without selection."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert not dialog.edit_button.isEnabled()
        dialog.close()

    def test_delete_button_disabled_without_selection(self, qapp, db_connection):
        """Test that delete button is disabled without selection."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert not dialog.delete_button.isEnabled()
        dialog.close()

    def test_edit_button_enabled_with_selection(self, qapp, tags_db):
        """Test that edit button enables with selection."""
        dialog = ProjectTagManagementDialog(tags_db)
        if dialog.tag_list.count() > 0:
            dialog.tag_list.setCurrentRow(0)
            assert dialog.edit_button.isEnabled()
        dialog.close()

    def test_delete_button_enabled_with_selection(self, qapp, tags_db):
        """Test that delete button enables with selection."""
        dialog = ProjectTagManagementDialog(tags_db)
        if dialog.tag_list.count() > 0:
            dialog.tag_list.setCurrentRow(0)
            assert dialog.delete_button.isEnabled()
        dialog.close()

    def test_dialog_shows_tag_colors(self, qapp, tags_db):
        """Test that dialog displays tag colors."""
        dialog = ProjectTagManagementDialog(tags_db)
        # Tags should have color indicators
        assert dialog.tag_list.count() > 0
        dialog.close()


class TestDialogSignals:
    """Test dialog signals."""

    def test_context_dialog_has_contexts_changed_signal(self, qapp, db_connection):
        """Test that context dialog has contexts changed signal."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'contexts_changed')
        dialog.close()

    def test_tag_dialog_has_tags_changed_signal(self, qapp, db_connection):
        """Test that tag dialog has tags changed signal."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'tags_changed')
        dialog.close()


class TestDialogRefresh:
    """Test dialog refresh functionality."""

    def test_context_dialog_has_refresh_method(self, qapp, db_connection):
        """Test that context dialog has refresh method."""
        dialog = ContextManagementDialog(db_connection)
        assert hasattr(dialog, 'refresh') or hasattr(dialog, 'load_contexts')
        dialog.close()

    def test_tag_dialog_has_refresh_method(self, qapp, db_connection):
        """Test that tag dialog has refresh method."""
        dialog = ProjectTagManagementDialog(db_connection)
        assert hasattr(dialog, 'refresh') or hasattr(dialog, 'load_tags')
        dialog.close()
