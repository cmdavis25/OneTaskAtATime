"""
ProjectTag Data Access Object for OneTaskAtATime application.

Handles all database CRUD operations for project tags.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from ..models import ProjectTag


class ProjectTagDAO:
    """Data Access Object for ProjectTag operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize ProjectTagDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def create(self, tag: ProjectTag) -> ProjectTag:
        """
        Insert a new project tag into the database.

        Args:
            tag: ProjectTag object to insert (id should be None)

        Returns:
            ProjectTag object with id populated

        Raises:
            ValueError: If tag already has an id
            sqlite3.IntegrityError: If tag name is not unique
        """
        if tag.id is not None:
            raise ValueError("Cannot create project tag that already has an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO project_tags (name, description, color, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tag.name, tag.description, tag.color, now.isoformat(), now.isoformat())
        )

        tag.id = cursor.lastrowid
        tag.created_at = now
        tag.updated_at = now

        self.db.commit()
        return tag

    def get_by_id(self, tag_id: int) -> Optional[ProjectTag]:
        """
        Retrieve a project tag by its ID.

        Args:
            tag_id: ID of project tag to retrieve

        Returns:
            ProjectTag object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, name, description, color, created_at, updated_at
            FROM project_tags WHERE id = ?
            """,
            (tag_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_tag(row)

    def get_by_name(self, name: str) -> Optional[ProjectTag]:
        """
        Retrieve a project tag by its name.

        Args:
            name: Name of project tag to retrieve

        Returns:
            ProjectTag object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, name, description, color, created_at, updated_at
            FROM project_tags WHERE name = ?
            """,
            (name,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_tag(row)

    def get_all(self) -> List[ProjectTag]:
        """
        Retrieve all project tags.

        Returns:
            List of ProjectTag objects ordered by name
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, name, description, color, created_at, updated_at
            FROM project_tags ORDER BY name ASC
            """
        )

        return [self._row_to_tag(row) for row in cursor.fetchall()]

    def get_tags_for_task(self, task_id: int) -> List[ProjectTag]:
        """
        Get all project tags associated with a task.

        Args:
            task_id: ID of task

        Returns:
            List of ProjectTag objects
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT pt.id, pt.name, pt.description, pt.color, pt.created_at, pt.updated_at
            FROM project_tags pt
            INNER JOIN task_project_tags tpt ON pt.id = tpt.project_tag_id
            WHERE tpt.task_id = ?
            ORDER BY pt.name ASC
            """,
            (task_id,)
        )

        return [self._row_to_tag(row) for row in cursor.fetchall()]

    def update(self, tag: ProjectTag) -> ProjectTag:
        """
        Update an existing project tag in the database.

        Args:
            tag: ProjectTag object with updated values (must have id)

        Returns:
            Updated ProjectTag object

        Raises:
            ValueError: If tag doesn't have an id
            sqlite3.IntegrityError: If new name conflicts with existing tag
        """
        if tag.id is None:
            raise ValueError("Cannot update project tag without an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            UPDATE project_tags SET name = ?, description = ?, color = ?, updated_at = ?
            WHERE id = ?
            """,
            (tag.name, tag.description, tag.color, now.isoformat(), tag.id)
        )

        tag.updated_at = now
        self.db.commit()
        return tag

    def delete(self, tag_id: int) -> bool:
        """
        Delete a project tag from the database.

        Note: Task associations will be automatically removed
        due to ON DELETE CASCADE foreign key constraint.

        Args:
            tag_id: ID of project tag to delete

        Returns:
            True if tag was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM project_tags WHERE id = ?", (tag_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def _row_to_tag(self, row: sqlite3.Row) -> ProjectTag:
        """
        Convert a database row to a ProjectTag object.

        Args:
            row: Database row from query

        Returns:
            ProjectTag object
        """
        return ProjectTag(
            id=row[0],
            name=row[1],
            description=row[2],
            color=row[3],
            created_at=datetime.fromisoformat(row[4]) if row[4] else None,
            updated_at=datetime.fromisoformat(row[5]) if row[5] else None
        )
