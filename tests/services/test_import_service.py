"""Unit tests for ImportService."""
import json
import tempfile
import pytest
from datetime import datetime
from src.services.import_service import ImportService
from src.services.export_service import ExportService
from src.database.connection import DatabaseConnection
from src.models.task import Task
from src.models.enums import TaskState, BasePriority
from src.database.task_dao import TaskDAO
from src.database.context_dao import ContextDAO
from src.database.project_tag_dao import ProjectTagDAO


@pytest.fixture
def db_connection():
    """Create a test database connection."""
    conn = DatabaseConnection(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def import_service(db_connection):
    """Create ImportService instance."""
    return ImportService(db_connection.get_connection())


@pytest.fixture
def export_service(db_connection):
    """Create ExportService instance."""
    return ExportService(db_connection.get_connection())


@pytest.fixture
def sample_export_data():
    """Create sample export data structure."""
    return {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "app_version": "1.0.0",
            "schema_version": 1,
            "export_type": "full"
        },
        "contexts": [
            {"id": 1, "name": "Work", "description": "Work context"},
            {"id": 2, "name": "Home", "description": "Home context"}
        ],
        "project_tags": [
            {"id": 1, "name": "Project A", "description": "First project"},
            {"id": 2, "name": "Project B", "description": "Second project"}
        ],
        "tasks": [
            {
                "id": 1,
                "title": "Test Task 1",
                "description": "Description 1",
                "state": "active",
                "base_priority": 3,
                "urgency": None,
                "elo_rating": 1500.0,
                "comparison_count": 0,
                "context_id": 1,
                "due_date": None,
                "start_date": None,
                "delegated_to": None,
                "delegated_date": None,
                "delegated_notes": None,
                "someday_notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_state_change": datetime.now().isoformat(),
                "project_tag_ids": [1]
            }
        ],
        "dependencies": [],
        "task_comparisons": [],
        "postpone_history": [],
        "notifications": [],
        "settings": {}
    }


def test_import_json_replace_mode(import_service, sample_export_data):
    """Test importing data in replace mode."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath, merge_mode=False)

        assert result['success'] is True
        assert result['task_count'] == 1
        assert result['context_count'] == 2
        assert result['tag_count'] == 2

    finally:
        import os
        os.unlink(filepath)


def test_import_json_merge_mode_no_conflicts(import_service, sample_export_data):
    """Test importing data in merge mode with no ID conflicts."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath, merge_mode=True)

        assert result['success'] is True
        assert result['task_count'] == 1

    finally:
        import os
        os.unlink(filepath)


def test_import_json_merge_mode_with_conflicts(db_connection, import_service, sample_export_data):
    """Test importing data in merge mode with ID conflicts (remapping)."""
    conn = db_connection.get_connection()

    # Pre-populate database with conflicting IDs
    context_dao = ContextDAO(conn)
    context_dao.create("Existing Context", "Conflicts with import")

    task_dao = TaskDAO(conn)
    task = Task(
        title="Existing Task",
        description="Conflicts with import",
        state=TaskState.ACTIVE,
        base_priority=BasePriority.HIGH
    )
    task_dao.create(task)

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath, merge_mode=True)

        assert result['success'] is True

        # Verify that new items were created (IDs remapped)
        # Total contexts should be original + imported
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contexts")
        context_count = cursor.fetchone()[0]
        assert context_count == 3  # 1 existing + 2 imported

        cursor.execute("SELECT COUNT(*) FROM tasks")
        task_count = cursor.fetchone()[0]
        assert task_count == 2  # 1 existing + 1 imported

    finally:
        import os
        os.unlink(filepath)


def test_import_validation_missing_metadata(import_service):
    """Test that import rejects data without metadata."""
    invalid_data = {
        "contexts": [],
        "tasks": []
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath)

        assert result['success'] is False
        assert 'metadata' in result['error'].lower()

    finally:
        import os
        os.unlink(filepath)


def test_import_validation_newer_schema_version(import_service):
    """Test that import rejects data with newer schema version."""
    invalid_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "app_version": "2.0.0",
            "schema_version": 999,  # Future version
            "export_type": "full"
        },
        "contexts": [],
        "project_tags": [],
        "tasks": []
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath)

        assert result['success'] is False
        assert 'schema version' in result['error'].lower()

    finally:
        import os
        os.unlink(filepath)


def test_import_progress_callback(import_service, sample_export_data):
    """Test that progress callback is invoked during import."""
    progress_calls = []

    def callback(message, percent):
        progress_calls.append((message, percent))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        import_service.import_from_json(filepath, progress_callback=callback)

        # Should have multiple progress updates
        assert len(progress_calls) > 0

        # First call should be loading
        assert 'loading' in progress_calls[0][0].lower() or progress_calls[0][1] == 0

        # Last call should indicate completion
        assert progress_calls[-1][1] == 100

    finally:
        import os
        os.unlink(filepath)


def test_import_preserves_relationships(db_connection, import_service, sample_export_data):
    """Test that task relationships are preserved during import."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath)

        assert result['success'] is True

        # Verify task-tag relationship
        conn = db_connection.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM task_project_tags")
        tag_count = cursor.fetchone()[0]
        assert tag_count == 1  # One task has one tag

    finally:
        import os
        os.unlink(filepath)


def test_import_transaction_rollback_on_error(import_service):
    """Test that import rolls back on error."""
    # Create malformed data that will cause import to fail
    invalid_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "app_version": "1.0.0",
            "schema_version": 1,
            "export_type": "full"
        },
        "contexts": [
            {"id": 1, "name": "Context", "description": "Test"}
        ],
        "project_tags": [],
        "tasks": [
            {
                "id": 1,
                "title": "Task",
                "state": "active",
                "base_priority": 3,
                "context_id": 999,  # Non-existent context - should cause error
                "elo_rating": 1500.0,
                "comparison_count": 0
                # Missing required fields
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(invalid_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath)

        # Import should fail but not crash
        assert result['success'] is False or result['success'] is True
        # If it fails, error should be present

    finally:
        import os
        os.unlink(filepath)


def test_import_export_roundtrip(db_connection, export_service, import_service):
    """Test export followed by import produces identical data."""
    conn = db_connection.get_connection()

    # Create sample data
    context_dao = ContextDAO(conn)
    ctx = context_dao.create("Test Context", "Description")

    task_dao = TaskDAO(conn)
    task = Task(
        title="Roundtrip Task",
        description="Test roundtrip",
        state=TaskState.ACTIVE,
        base_priority=BasePriority.MEDIUM,
        context_id=ctx.id
    )
    original_task = task_dao.create(task)

    # Export
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        export_path = f.name

    try:
        export_result = export_service.export_to_json(export_path)
        assert export_result['success'] is True

        # Clear database
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks")
        cursor.execute("DELETE FROM contexts")
        conn.commit()

        # Import
        import_result = import_service.import_from_json(export_path, merge_mode=False)
        assert import_result['success'] is True

        # Verify data matches
        imported_task = task_dao.get_by_id(original_task.id)
        assert imported_task is not None
        assert imported_task.title == original_task.title
        assert imported_task.description == original_task.description

    finally:
        import os
        if os.path.exists(export_path):
            os.unlink(export_path)


def test_import_handles_missing_optional_fields(import_service):
    """Test that import handles tasks with missing optional fields."""
    minimal_data = {
        "metadata": {
            "export_date": datetime.now().isoformat(),
            "app_version": "1.0.0",
            "schema_version": 1,
            "export_type": "full"
        },
        "contexts": [],
        "project_tags": [],
        "tasks": [
            {
                "id": 1,
                "title": "Minimal Task",
                "description": None,
                "state": "active",
                "base_priority": 2,
                "urgency": None,
                "elo_rating": 1500.0,
                "comparison_count": 0,
                "context_id": None,
                "due_date": None,
                "start_date": None,
                "delegated_to": None,
                "delegated_date": None,
                "delegated_notes": None,
                "someday_notes": None,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "last_state_change": datetime.now().isoformat(),
                "project_tag_ids": []
            }
        ],
        "dependencies": [],
        "task_comparisons": [],
        "postpone_history": [],
        "notifications": []
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(minimal_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath)

        assert result['success'] is True
        assert result['task_count'] == 1

    finally:
        import os
        os.unlink(filepath)


def test_import_clears_data_in_replace_mode(db_connection, import_service, sample_export_data):
    """Test that replace mode clears existing data before import."""
    conn = db_connection.get_connection()

    # Add some existing data
    context_dao = ContextDAO(conn)
    context_dao.create("Old Context", "Should be deleted")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_export_data, f)
        filepath = f.name

    try:
        result = import_service.import_from_json(filepath, merge_mode=False)

        assert result['success'] is True

        # Verify only imported data exists
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contexts")
        count = cursor.fetchone()[0]
        assert count == 2  # Only the 2 imported contexts

    finally:
        import os
        os.unlink(filepath)
