"""
Dependency Data Access Object for OneTaskAtATime application.

Handles all database operations for task dependencies.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional, Set
from ..models import Dependency


class DependencyDAO:
    """Data Access Object for Dependency operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize DependencyDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def add_dependency(self, blocked_task_id: int, blocking_task_id: int) -> Dependency:
        """
        Convenience method to add a dependency between two tasks.

        Args:
            blocked_task_id: ID of task that is blocked
            blocking_task_id: ID of task that blocks it

        Returns:
            Created Dependency object

        Raises:
            ValueError: If creates circular dependency, is duplicate, or is self-dependency
        """
        # Check for self-dependency
        if blocked_task_id == blocking_task_id:
            raise ValueError(
                f"Task cannot depend on itself (self-dependency not allowed for task {blocked_task_id})"
            )

        dependency = Dependency(
            blocked_task_id=blocked_task_id,
            blocking_task_id=blocking_task_id
        )
        return self.create(dependency)

    def create(self, dependency: Dependency) -> Dependency:
        """
        Insert a new dependency into the database.

        Args:
            dependency: Dependency object to insert (id should be None)

        Returns:
            Dependency object with id populated

        Raises:
            ValueError: If dependency already has an id, creates circular dependency, or is duplicate
        """
        if dependency.id is not None:
            raise ValueError("Cannot create dependency that already has an id")

        # Check for duplicate dependency
        existing_deps = self.get_dependencies_for_task(dependency.blocked_task_id)
        for existing_dep in existing_deps:
            if existing_dep.blocking_task_id == dependency.blocking_task_id:
                raise ValueError(
                    f"Dependency already exists: task {dependency.blocked_task_id} "
                    f"is already blocked by task {dependency.blocking_task_id}"
                )

        # Check for circular dependencies
        if self._would_create_cycle(dependency.blocked_task_id, dependency.blocking_task_id):
            raise ValueError(
                f"Cannot create dependency: would create circular dependency between "
                f"tasks {dependency.blocked_task_id} and {dependency.blocking_task_id}"
            )

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO dependencies (blocked_task_id, blocking_task_id, created_at)
            VALUES (?, ?, ?)
            """,
            (dependency.blocked_task_id, dependency.blocking_task_id, now.isoformat())
        )

        dependency.id = cursor.lastrowid
        dependency.created_at = now

        self.db.commit()
        return dependency

    def get_by_id(self, dependency_id: int) -> Optional[Dependency]:
        """
        Retrieve a dependency by its ID.

        Args:
            dependency_id: ID of dependency to retrieve

        Returns:
            Dependency object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, blocked_task_id, blocking_task_id, created_at
            FROM dependencies WHERE id = ?
            """,
            (dependency_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_dependency(row)

    def get_dependencies_for_task(self, task_id: int) -> List[Dependency]:
        """
        Get all dependencies where the specified task is blocked.

        Args:
            task_id: ID of blocked task

        Returns:
            List of Dependency objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, blocked_task_id, blocking_task_id, created_at
            FROM dependencies
            WHERE blocked_task_id = ?
            """,
            (task_id,)
        )

        return [self._row_to_dependency(row) for row in cursor.fetchall()]

    def get_dependencies(self, task_id: int) -> List[Dependency]:
        """
        Alias for get_dependencies_for_task() for backward compatibility.

        Args:
            task_id: ID of blocked task

        Returns:
            List of Dependency objects where this task is blocked
        """
        return self.get_dependencies_for_task(task_id)

    def get_blocking_tasks(self, task_id: int) -> List[Dependency]:
        """
        Get all dependencies where the specified task is blocking others.

        Args:
            task_id: ID of blocking task

        Returns:
            List of Dependency objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, blocked_task_id, blocking_task_id, created_at
            FROM dependencies
            WHERE blocking_task_id = ?
            """,
            (task_id,)
        )

        return [self._row_to_dependency(row) for row in cursor.fetchall()]

    def delete(self, dependency_id: int) -> bool:
        """
        Delete a dependency from the database.

        Args:
            dependency_id: ID of dependency to delete

        Returns:
            True if dependency was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM dependencies WHERE id = ?", (dependency_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def delete_by_tasks(self, blocked_task_id: int, blocking_task_id: int) -> bool:
        """
        Delete a dependency by the task IDs involved.

        Args:
            blocked_task_id: ID of blocked task
            blocking_task_id: ID of blocking task

        Returns:
            True if dependency was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute(
            "DELETE FROM dependencies WHERE blocked_task_id = ? AND blocking_task_id = ?",
            (blocked_task_id, blocking_task_id)
        )
        self.db.commit()
        return cursor.rowcount > 0

    def _would_create_cycle(self, blocked_task_id: int, blocking_task_id: int) -> bool:
        """
        Check if adding a dependency would create a circular dependency.

        Uses depth-first search to detect cycles.

        Args:
            blocked_task_id: ID of task that would be blocked
            blocking_task_id: ID of task that would be blocking

        Returns:
            True if cycle would be created, False otherwise
        """
        # If blocking_task_id is already blocked by blocked_task_id (directly or indirectly),
        # then adding this dependency would create a cycle
        visited: Set[int] = set()
        return self._has_path(blocking_task_id, blocked_task_id, visited)

    def _has_path(self, from_task: int, to_task: int, visited: Set[int]) -> bool:
        """
        Check if there's a dependency path from from_task to to_task.

        Args:
            from_task: Starting task ID
            to_task: Target task ID
            visited: Set of already visited task IDs (prevents infinite loops)

        Returns:
            True if path exists, False otherwise
        """
        if from_task == to_task:
            return True

        if from_task in visited:
            return False

        visited.add(from_task)

        # Get all tasks that from_task is blocked by
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT blocking_task_id FROM dependencies WHERE blocked_task_id = ?",
            (from_task,)
        )

        for row in cursor.fetchall():
            blocking_task = row[0]
            if self._has_path(blocking_task, to_task, visited):
                return True

        return False

    def _row_to_dependency(self, row: sqlite3.Row) -> Dependency:
        """
        Convert a database row to a Dependency object.

        Args:
            row: Database row from query

        Returns:
            Dependency object
        """
        return Dependency(
            id=row[0],
            blocked_task_id=row[1],
            blocking_task_id=row[2],
            created_at=datetime.fromisoformat(row[3]) if row[3] else None
        )
