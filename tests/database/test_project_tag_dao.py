"""
Unit tests for ProjectTagDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from datetime import datetime

from src.database.schema import DatabaseSchema
from src.database.project_tag_dao import ProjectTagDAO
from src.models import ProjectTag


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def db_connection(temp_db):
    """Create a database connection for testing."""
    conn = sqlite3.connect(temp_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    yield conn
    conn.close()


@pytest.fixture
def project_tag_dao(db_connection):
    """Create a ProjectTagDAO instance for testing."""
    return ProjectTagDAO(db_connection)


class TestProjectTagDAO:
    """Tests for ProjectTagDAO class."""

    def test_create_basic_tag(self, project_tag_dao):
        """Test creating a basic project tag."""
        tag = ProjectTag(name="Work")
        created_tag = project_tag_dao.create(tag)

        assert created_tag.id is not None
        assert created_tag.name == "Work"
        assert created_tag.created_at is not None
        assert created_tag.updated_at is not None

    def test_create_tag_with_all_fields(self, project_tag_dao):
        """Test creating a project tag with all fields populated."""
        tag = ProjectTag(
            name="Personal",
            description="Personal tasks and errands",
            color="#FF5733"
        )
        created_tag = project_tag_dao.create(tag)

        assert created_tag.id is not None
        assert created_tag.name == "Personal"
        assert created_tag.description == "Personal tasks and errands"
        assert created_tag.color == "#FF5733"

    def test_create_tag_with_existing_id_raises_error(self, project_tag_dao):
        """Test that creating a tag with an ID raises an error."""
        tag = ProjectTag(name="Test", id=1)

        with pytest.raises(ValueError, match="Cannot create project tag that already has an id"):
            project_tag_dao.create(tag)

    def test_create_duplicate_name_raises_error(self, project_tag_dao):
        """Test that creating a tag with duplicate name raises an error."""
        tag1 = ProjectTag(name="Unique")
        project_tag_dao.create(tag1)

        tag2 = ProjectTag(name="Unique")
        with pytest.raises(sqlite3.IntegrityError):
            project_tag_dao.create(tag2)

    def test_get_by_id(self, project_tag_dao):
        """Test retrieving a project tag by ID."""
        tag = ProjectTag(name="Test Tag")
        created_tag = project_tag_dao.create(tag)

        retrieved_tag = project_tag_dao.get_by_id(created_tag.id)

        assert retrieved_tag is not None
        assert retrieved_tag.id == created_tag.id
        assert retrieved_tag.name == created_tag.name

    def test_get_by_id_not_found(self, project_tag_dao):
        """Test retrieving a non-existent tag."""
        tag = project_tag_dao.get_by_id(9999)
        assert tag is None

    def test_get_by_name(self, project_tag_dao):
        """Test retrieving a project tag by name."""
        tag = ProjectTag(name="FindMe")
        created_tag = project_tag_dao.create(tag)

        retrieved_tag = project_tag_dao.get_by_name("FindMe")

        assert retrieved_tag is not None
        assert retrieved_tag.id == created_tag.id
        assert retrieved_tag.name == "FindMe"

    def test_get_by_name_not_found(self, project_tag_dao):
        """Test retrieving a non-existent tag by name."""
        tag = project_tag_dao.get_by_name("NonExistent")
        assert tag is None

    def test_get_all_tags(self, project_tag_dao):
        """Test retrieving all project tags."""
        project_tag_dao.create(ProjectTag(name="Alpha"))
        project_tag_dao.create(ProjectTag(name="Beta"))
        project_tag_dao.create(ProjectTag(name="Gamma"))

        tags = project_tag_dao.get_all()

        assert len(tags) == 3
        assert all(isinstance(t, ProjectTag) for t in tags)
        # Should be sorted by name
        assert tags[0].name == "Alpha"
        assert tags[1].name == "Beta"
        assert tags[2].name == "Gamma"

    def test_get_all_empty(self, project_tag_dao):
        """Test retrieving all tags when none exist."""
        tags = project_tag_dao.get_all()
        assert tags == []

    def test_get_tags_for_task(self, project_tag_dao, db_connection):
        """Test getting project tags associated with a task."""
        # Create tags
        tag1 = project_tag_dao.create(ProjectTag(name="Work"))
        tag2 = project_tag_dao.create(ProjectTag(name="Urgent"))

        # Create a task
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO tasks (title, state) VALUES (?, ?)", ("Test Task", "active"))
        task_id = cursor.lastrowid

        # Associate tags with task
        cursor.execute(
            "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
            (task_id, tag1.id)
        )
        cursor.execute(
            "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
            (task_id, tag2.id)
        )
        db_connection.commit()

        # Get tags for task
        tags = project_tag_dao.get_tags_for_task(task_id)

        assert len(tags) == 2
        tag_names = [t.name for t in tags]
        assert "Work" in tag_names
        assert "Urgent" in tag_names

    def test_get_tags_for_task_no_tags(self, project_tag_dao, db_connection):
        """Test getting tags for a task with no tags."""
        # Create a task with no tags
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO tasks (title, state) VALUES (?, ?)", ("No Tags", "active"))
        task_id = cursor.lastrowid
        db_connection.commit()

        tags = project_tag_dao.get_tags_for_task(task_id)
        assert tags == []

    def test_update_tag(self, project_tag_dao):
        """Test updating a project tag."""
        tag = project_tag_dao.create(ProjectTag(name="Original"))

        tag.name = "Updated"
        tag.description = "New description"
        tag.color = "#00FF00"

        updated_tag = project_tag_dao.update(tag)

        assert updated_tag.name == "Updated"
        assert updated_tag.description == "New description"
        assert updated_tag.color == "#00FF00"

        # Verify in database
        retrieved = project_tag_dao.get_by_id(tag.id)
        assert retrieved.name == "Updated"

    def test_update_tag_without_id_raises_error(self, project_tag_dao):
        """Test that updating a tag without an ID raises an error."""
        tag = ProjectTag(name="Test")

        with pytest.raises(ValueError, match="Cannot update project tag without an id"):
            project_tag_dao.update(tag)

    def test_delete_tag(self, project_tag_dao):
        """Test deleting a project tag."""
        tag = project_tag_dao.create(ProjectTag(name="To Delete"))

        result = project_tag_dao.delete(tag.id)
        assert result is True

        # Verify deleted
        retrieved = project_tag_dao.get_by_id(tag.id)
        assert retrieved is None

    def test_delete_nonexistent_tag(self, project_tag_dao):
        """Test deleting a non-existent tag."""
        result = project_tag_dao.delete(9999)
        assert result is False

    def test_delete_tag_cascades_to_task_associations(self, project_tag_dao, db_connection):
        """Test that deleting a tag removes task associations."""
        # Create tag
        tag = project_tag_dao.create(ProjectTag(name="Cascade Test"))

        # Create a task and associate with tag
        cursor = db_connection.cursor()
        cursor.execute("INSERT INTO tasks (title, state) VALUES (?, ?)", ("Test Task", "active"))
        task_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
            (task_id, tag.id)
        )
        db_connection.commit()

        # Verify association exists
        cursor.execute(
            "SELECT COUNT(*) FROM task_project_tags WHERE project_tag_id = ?",
            (tag.id,)
        )
        assert cursor.fetchone()[0] == 1

        # Delete tag
        project_tag_dao.delete(tag.id)

        # Verify association was removed
        cursor.execute(
            "SELECT COUNT(*) FROM task_project_tags WHERE project_tag_id = ?",
            (tag.id,)
        )
        assert cursor.fetchone()[0] == 0
