"""
Context Data Access Object for OneTaskAtATime application.

Handles all database CRUD operations for contexts.
"""

import sqlite3
from datetime import datetime
from typing import List, Optional
from ..models import Context


class ContextDAO:
    """Data Access Object for Context operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize ContextDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def create(self, context: Context) -> Context:
        """
        Insert a new context into the database.

        Args:
            context: Context object to insert (id should be None)

        Returns:
            Context object with id populated

        Raises:
            ValueError: If context already has an id
            sqlite3.IntegrityError: If context name is not unique
        """
        if context.id is not None:
            raise ValueError("Cannot create context that already has an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO contexts (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (context.name, context.description, now.isoformat(), now.isoformat())
        )

        context.id = cursor.lastrowid
        context.created_at = now
        context.updated_at = now

        self.db.commit()
        return context

    def get_by_id(self, context_id: int) -> Optional[Context]:
        """
        Retrieve a context by its ID.

        Args:
            context_id: ID of context to retrieve

        Returns:
            Context object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, name, description, created_at, updated_at FROM contexts WHERE id = ?",
            (context_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_context(row)

    def get_by_name(self, name: str) -> Optional[Context]:
        """
        Retrieve a context by its name.

        Args:
            name: Name of context to retrieve

        Returns:
            Context object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, name, description, created_at, updated_at FROM contexts WHERE name = ?",
            (name,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_context(row)

    def get_all(self) -> List[Context]:
        """
        Retrieve all contexts.

        Returns:
            List of Context objects ordered by name
        """
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT id, name, description, created_at, updated_at FROM contexts ORDER BY name ASC"
        )

        return [self._row_to_context(row) for row in cursor.fetchall()]

    def update(self, context: Context) -> Context:
        """
        Update an existing context in the database.

        Args:
            context: Context object with updated values (must have id)

        Returns:
            Updated Context object

        Raises:
            ValueError: If context doesn't have an id
            sqlite3.IntegrityError: If new name conflicts with existing context
        """
        if context.id is None:
            raise ValueError("Cannot update context without an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            UPDATE contexts SET name = ?, description = ?, updated_at = ?
            WHERE id = ?
            """,
            (context.name, context.description, now.isoformat(), context.id)
        )

        context.updated_at = now
        self.db.commit()
        return context

    def delete(self, context_id: int) -> bool:
        """
        Delete a context from the database.

        Note: Tasks using this context will have context_id set to NULL
        due to ON DELETE SET NULL foreign key constraint.

        Args:
            context_id: ID of context to delete

        Returns:
            True if context was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM contexts WHERE id = ?", (context_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def _row_to_context(self, row: sqlite3.Row) -> Context:
        """
        Convert a database row to a Context object.

        Args:
            row: Database row from query

        Returns:
            Context object
        """
        return Context(
            id=row[0],
            name=row[1],
            description=row[2],
            created_at=datetime.fromisoformat(row[3]) if row[3] else None,
            updated_at=datetime.fromisoformat(row[4]) if row[4] else None
        )
