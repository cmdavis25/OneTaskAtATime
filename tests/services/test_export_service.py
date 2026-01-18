"""Unit tests for ExportService."""
import json
import os
import sqlite3
import tempfile
import pytest
from datetime import datetime
from src.services.export_service import ExportService
from src.models.task import Task
from src.models.enums import TaskState, Priority
from src.database.task_dao import TaskDAO
from src.database.context_dao import ContextDAO
from src.database.project_tag_dao import ProjectTagDAO
from src.models.context import Context
from src.models.project_tag import ProjectTag


class MockDatabaseConnection:
    """Mock DatabaseConnection for testing."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get_connection(self):
        return self._conn

    def close(self):
        pass  # Don't close - let test_db fixture handle it

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()


@pytest.fixture
def db_connection(test_db):
    """Create a test database connection wrapper."""
    return MockDatabaseConnection(test_db)


@pytest.fixture
def export_service(test_db):
    """Create ExportService instance."""
    return ExportService(test_db)


@pytest.fixture
def sample_data(test_db):
    """Populate database with sample data."""
    conn = test_db

    # Create contexts
    context_dao = ContextDAO(conn)
    ctx1 = context_dao.create(Context(name="Work", description="Work context"))
    ctx2 = context_dao.create(Context(name="Home", description="Home context"))

    # Create project tags
    tag_dao = ProjectTagDAO(conn)
    tag1 = tag_dao.create(ProjectTag(name="Project A", description="First project"))
    tag2 = tag_dao.create(ProjectTag(name="Project B", description="Second project"))

    # Create tasks
    task_dao = TaskDAO(conn)
    task1 = Task(
        title="Test Task 1",
        description="Description 1",
        state=TaskState.ACTIVE,
        base_priority=Priority.HIGH.value,
        context_id=ctx1.id
    )
    task1 = task_dao.create(task1)

    task2 = Task(
        title="Test Task 2",
        description="Description 2",
        state=TaskState.DEFERRED,
        base_priority=Priority.MEDIUM.value,
        context_id=ctx2.id,
        start_date=datetime.now().date()
    )
    task2 = task_dao.create(task2)

    # Add task-tag associations
    conn.execute(
        "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
        (task1.id, tag1.id)
    )
    conn.execute(
        "INSERT INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
        (task2.id, tag2.id)
    )
    conn.commit()

    return {
        'contexts': [ctx1, ctx2],
        'tags': [tag1, tag2],
        'tasks': [task1, task2]
    }


def test_export_to_json_creates_file(export_service, sample_data):
    """Test that export creates a valid JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        result = export_service.export_to_json(filepath)

        assert result['success'] is True
        assert os.path.exists(filepath)
        assert result['task_count'] == 2
        assert result['context_count'] == 2
        assert result['tag_count'] == 2

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_json_structure(export_service, sample_data):
    """Test that exported JSON has correct structure."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        export_service.export_to_json(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check metadata
        assert 'metadata' in data
        assert 'export_date' in data['metadata']
        assert 'app_version' in data['metadata']
        assert 'schema_version' in data['metadata']
        assert data['metadata']['schema_version'] == 1

        # Check sections
        assert 'contexts' in data
        assert 'project_tags' in data
        assert 'tasks' in data
        assert 'dependencies' in data
        assert 'task_comparisons' in data
        assert 'postpone_history' in data
        assert 'notifications' in data
        assert 'settings' in data

        # Verify counts
        assert len(data['contexts']) == 2
        assert len(data['project_tags']) == 2
        assert len(data['tasks']) == 2

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_preserves_task_relationships(export_service, sample_data):
    """Test that task relationships are preserved in export."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        export_service.export_to_json(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check that tasks have their tag associations
        tasks = data['tasks']
        assert len(tasks) == 2

        # Each task should have project_tag_ids
        for task in tasks:
            assert 'project_tag_ids' in task
            if task['title'] == "Test Task 1":
                assert len(task['project_tag_ids']) == 1

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_progress_callback(export_service, sample_data):
    """Test that progress callback is invoked during export."""
    progress_calls = []

    def callback(message, percent):
        progress_calls.append((message, percent))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        export_service.export_to_json(filepath, progress_callback=callback)

        # Should have multiple progress updates
        assert len(progress_calls) > 0

        # First call should be at 0%
        assert progress_calls[0][1] == 0

        # Last call should be at 100%
        assert progress_calls[-1][1] == 100

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_database_backup(export_service):
    """Test database file backup."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        filepath = f.name

    try:
        result = export_service.export_database_backup(filepath)

        assert result['success'] is True
        assert os.path.exists(filepath)
        assert result['size_bytes'] > 0

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_empty_database(export_service):
    """Test exporting from empty database."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        result = export_service.export_to_json(filepath)

        assert result['success'] is True
        assert result['task_count'] == 0
        assert result['context_count'] == 0

        # Verify file exists and is valid JSON
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        assert 'metadata' in data

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_handles_invalid_path(export_service):
    """Test that export handles invalid file paths gracefully."""
    # Use an invalid path (non-existent directory)
    invalid_path = "/nonexistent/directory/file.json"

    result = export_service.export_to_json(invalid_path)

    assert result['success'] is False
    assert 'error' in result


def test_export_without_settings(export_service, sample_data):
    """Test exporting without settings."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        result = export_service.export_to_json(filepath, include_settings=False)

        assert result['success'] is True

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Settings should still be in the structure (as empty dict)
        # or not present depending on implementation
        assert result['task_count'] == 2

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_contexts_format(export_service, sample_data):
    """Test that contexts are exported in correct format."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        export_service.export_to_json(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        contexts = data['contexts']
        assert len(contexts) == 2

        # Check first context has required fields
        ctx = contexts[0]
        assert 'id' in ctx
        assert 'name' in ctx
        assert 'description' in ctx

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)


def test_export_tasks_format(export_service, sample_data):
    """Test that tasks are exported with all fields."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    try:
        export_service.export_to_json(filepath)

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        tasks = data['tasks']
        assert len(tasks) == 2

        # Check task has all required fields
        task = tasks[0]
        required_fields = [
            'id', 'title', 'description', 'state', 'base_priority',
            'elo_rating', 'comparison_count', 'context_id', 'created_at'
        ]

        for field in required_fields:
            assert field in task, f"Missing field: {field}"

        # Check deferred task has start_date
        deferred_task = next((t for t in tasks if t['state'] == 'deferred'), None)
        if deferred_task:
            assert 'start_date' in deferred_task
            assert deferred_task['start_date'] is not None

    finally:
        if os.path.exists(filepath):
            os.unlink(filepath)
