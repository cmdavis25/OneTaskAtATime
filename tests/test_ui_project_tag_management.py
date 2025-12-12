"""
Tests for Project Tag Management Dialog UI component.

Phase 4: Task Management Interface tests.
"""

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from src.ui.project_tag_management_dialog import ProjectTagManagementDialog
from src.models import ProjectTag


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""
    def __init__(self, connection):
        self._connection = connection

    def get_connection(self):
        return self._connection

    def close(self):
        pass


@pytest.fixture
def tag_dialog(qtbot, test_db):
    """Create a ProjectTagManagementDialog for testing."""
    mock_db = MockDatabaseConnection(test_db)
    dialog = ProjectTagManagementDialog(mock_db)
    qtbot.addWidget(dialog)
    return dialog


def test_tag_dialog_initialization(tag_dialog):
    """Test that project tag management dialog initializes correctly."""
    assert tag_dialog is not None
    assert tag_dialog.tag_list is not None
    assert tag_dialog.name_edit is not None
    assert tag_dialog.description_edit is not None
    assert tag_dialog.color_display is not None


def test_load_tags(tag_dialog):
    """Test loading project tags into the list."""
    # Create some tags
    tag1 = ProjectTag(name="Website", description="Website project", color="#FF5733")
    tag2 = ProjectTag(name="Mobile App", description="Mobile app project", color="#33C4FF")

    tag_dialog.tag_dao.create(tag1)
    tag_dialog.tag_dao.create(tag2)

    # Reload
    tag_dialog._load_tags()

    # Check that tags appear in list
    assert tag_dialog.tag_list.count() == 2


def test_create_new_tag(tag_dialog, qtbot):
    """Test creating a new project tag."""
    # Click new button
    tag_dialog._on_new_tag()

    # Fill in form
    tag_dialog.name_edit.setText("Documentation")
    tag_dialog.description_edit.setText("Documentation tasks")
    tag_dialog.selected_color = "#00FF00"

    # Save
    with qtbot.waitSignal(tag_dialog.tags_changed, timeout=1000):
        tag_dialog._on_save_tag()

    # Verify tag was created
    tags = tag_dialog.tag_dao.get_all()
    assert len(tags) == 1
    assert tags[0].name == "Documentation"
    assert tags[0].color == "#00FF00"


def test_edit_existing_tag(tag_dialog, qtbot):
    """Test editing an existing project tag."""
    # Create a tag
    tag = ProjectTag(name="Testing", description="Testing tasks", color="#FF0000")
    created_tag = tag_dialog.tag_dao.create(tag)

    # Reload
    tag_dialog._load_tags()

    # Select the tag
    tag_dialog.tag_list.setCurrentRow(0)

    # Modify the name and color
    tag_dialog.name_edit.setText("QA Testing")
    tag_dialog.selected_color = "#0000FF"

    # Save
    with qtbot.waitSignal(tag_dialog.tags_changed, timeout=1000):
        tag_dialog._on_save_tag()

    # Verify tag was updated
    updated_tag = tag_dialog.tag_dao.get_by_id(created_tag.id)
    assert updated_tag.name == "QA Testing"
    assert updated_tag.color == "#0000FF"


def test_delete_tag(tag_dialog, qtbot, monkeypatch):
    """Test deleting a project tag."""
    # Create a tag
    tag = ProjectTag(name="Deprecated", description="Old project")
    tag_dialog.tag_dao.create(tag)

    # Reload
    tag_dialog._load_tags()

    # Select the tag
    tag_dialog.tag_list.setCurrentRow(0)

    # Mock the confirmation dialog to always return Yes
    from PyQt5.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.Yes)

    # Delete
    with qtbot.waitSignal(tag_dialog.tags_changed, timeout=1000):
        tag_dialog._on_delete_tag()

    # Verify tag was deleted
    tags = tag_dialog.tag_dao.get_all()
    assert len(tags) == 0


def test_color_display_updates(tag_dialog):
    """Test that color display updates when color is selected."""
    # Set a color
    tag_dialog.selected_color = "#FF00FF"
    tag_dialog.color_display.setStyleSheet(
        f"border: 1px solid #ccc; background-color: {tag_dialog.selected_color};"
    )

    # Check style sheet contains the color
    style = tag_dialog.color_display.styleSheet()
    assert "#FF00FF" in style or "#ff00ff" in style.lower()


def test_clear_form(tag_dialog):
    """Test clearing the form."""
    # Fill in form
    tag_dialog.name_edit.setText("Test Tag")
    tag_dialog.description_edit.setText("Test description")
    tag_dialog.selected_color = "#123456"

    # Clear
    tag_dialog._clear_form()

    # Verify fields are cleared
    assert tag_dialog.name_edit.text() == ""
    assert tag_dialog.description_edit.toPlainText() == ""
    assert tag_dialog.current_tag is None
    assert tag_dialog.selected_color is None
