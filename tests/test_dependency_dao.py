"""
Unit tests for DependencyDAO.
"""

import pytest
import sqlite3
import tempfile
import os
from src.database.schema import DatabaseSchema
from src.database.dependency_dao import DependencyDAO
from src.database.task_dao import TaskDAO
from src.models import Dependency, Task


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
def dependency_dao(db_connection):
    """Create a DependencyDAO instance for testing."""
    return DependencyDAO(db_connection)


@pytest.fixture
def task_dao(db_connection):
    """Create a TaskDAO instance for testing."""
    return TaskDAO(db_connection)


class TestDependencyDAO:
    """Tests for DependencyDAO class."""

    def test_create_dependency(self, dependency_dao, task_dao):
        """Test creating a dependency."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        dep = Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id)
        created = dependency_dao.create(dep)

        assert created.id is not None
        assert created.blocked_task_id == task2.id
        assert created.blocking_task_id == task1.id
        assert created.created_at is not None

    def test_create_dependency_with_existing_id_raises_error(self, dependency_dao):
        """Test that creating a dependency with an ID raises an error."""
        dep = Dependency(blocked_task_id=1, blocking_task_id=2, id=1)

        with pytest.raises(ValueError, match="Cannot create dependency that already has an id"):
            dependency_dao.create(dep)

    def test_create_circular_dependency_raises_error(self, dependency_dao, task_dao):
        """Test that creating a circular dependency raises an error."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        # Create A -> B
        dependency_dao.create(Dependency(blocked_task_id=task1.id, blocking_task_id=task2.id))

        # Try to create B -> A (circular)
        with pytest.raises(ValueError, match="circular dependency"):
            dependency_dao.create(Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id))

    def test_create_indirect_circular_dependency_raises_error(self, dependency_dao, task_dao):
        """Test that creating an indirect circular dependency raises an error."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))
        task3 = task_dao.create(Task(title="Task 3"))

        # Create A -> B -> C
        dependency_dao.create(Dependency(blocked_task_id=task1.id, blocking_task_id=task2.id))
        dependency_dao.create(Dependency(blocked_task_id=task2.id, blocking_task_id=task3.id))

        # Try to create C -> A (circular via B)
        with pytest.raises(ValueError, match="circular dependency"):
            dependency_dao.create(Dependency(blocked_task_id=task3.id, blocking_task_id=task1.id))

    def test_get_by_id(self, dependency_dao, task_dao):
        """Test retrieving a dependency by ID."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        created = dependency_dao.create(
            Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id)
        )
        retrieved = dependency_dao.get_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.blocked_task_id == task2.id
        assert retrieved.blocking_task_id == task1.id

    def test_get_by_id_not_found(self, dependency_dao):
        """Test retrieving a non-existent dependency."""
        dep = dependency_dao.get_by_id(9999)
        assert dep is None

    def test_get_dependencies_for_task(self, dependency_dao, task_dao):
        """Test getting all dependencies for a blocked task."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))
        task3 = task_dao.create(Task(title="Task 3"))

        # Task 3 is blocked by both Task 1 and Task 2
        dependency_dao.create(Dependency(blocked_task_id=task3.id, blocking_task_id=task1.id))
        dependency_dao.create(Dependency(blocked_task_id=task3.id, blocking_task_id=task2.id))

        deps = dependency_dao.get_dependencies_for_task(task3.id)

        assert len(deps) == 2
        blocking_ids = {d.blocking_task_id for d in deps}
        assert blocking_ids == {task1.id, task2.id}

    def test_get_blocking_tasks(self, dependency_dao, task_dao):
        """Test getting all tasks that a task is blocking."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))
        task3 = task_dao.create(Task(title="Task 3"))

        # Task 1 is blocking both Task 2 and Task 3
        dependency_dao.create(Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id))
        dependency_dao.create(Dependency(blocked_task_id=task3.id, blocking_task_id=task1.id))

        deps = dependency_dao.get_blocking_tasks(task1.id)

        assert len(deps) == 2
        blocked_ids = {d.blocked_task_id for d in deps}
        assert blocked_ids == {task2.id, task3.id}

    def test_delete_dependency(self, dependency_dao, task_dao):
        """Test deleting a dependency."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        dep = dependency_dao.create(
            Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id)
        )

        result = dependency_dao.delete(dep.id)
        assert result is True

        # Verify deleted
        retrieved = dependency_dao.get_by_id(dep.id)
        assert retrieved is None

    def test_delete_nonexistent_dependency(self, dependency_dao):
        """Test deleting a non-existent dependency."""
        result = dependency_dao.delete(9999)
        assert result is False

    def test_delete_by_tasks(self, dependency_dao, task_dao):
        """Test deleting a dependency by task IDs."""
        task1 = task_dao.create(Task(title="Task 1"))
        task2 = task_dao.create(Task(title="Task 2"))

        dependency_dao.create(Dependency(blocked_task_id=task2.id, blocking_task_id=task1.id))

        result = dependency_dao.delete_by_tasks(task2.id, task1.id)
        assert result is True

        # Verify deleted
        deps = dependency_dao.get_dependencies_for_task(task2.id)
        assert len(deps) == 0

    def test_dependency_string_representation(self):
        """Test Dependency string methods."""
        dep = Dependency(blocked_task_id=2, blocking_task_id=1, id=1)

        assert "Task 2 blocked by Task 1" in str(dep)
        assert "Dependency" in repr(dep)
        assert "blocked=2" in repr(dep)
        assert "blocking=1" in repr(dep)
