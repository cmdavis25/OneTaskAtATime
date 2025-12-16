"""
PostponeHistory Data Access Object for OneTaskAtATime application.

Handles all database CRUD operations for postpone history records.
"""

import sqlite3
from datetime import datetime, timedelta
from typing import List, Optional
from ..models.postpone_record import PostponeRecord
from ..models.enums import PostponeReasonType, ActionTaken


class PostponeHistoryDAO:
    """Data Access Object for PostponeHistory operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize PostponeHistoryDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def create(self, record: PostponeRecord) -> PostponeRecord:
        """
        Insert a new postpone record into the database.

        Args:
            record: PostponeRecord object to insert (id should be None)

        Returns:
            PostponeRecord object with id and postponed_at populated

        Raises:
            ValueError: If record already has an id
        """
        if record.id is not None:
            raise ValueError("Cannot create postpone record that already has an id")

        cursor = self.db.cursor()

        # Auto-set postponed_at if not provided
        if record.postponed_at is None:
            record.postponed_at = datetime.now()

        cursor.execute(
            """
            INSERT INTO postpone_history (task_id, reason_type, reason_notes, action_taken, postponed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                record.task_id,
                record.reason_type.value,
                record.reason_notes,
                record.action_taken.value,
                record.postponed_at.isoformat()
            )
        )

        record.id = cursor.lastrowid
        self.db.commit()
        return record

    def get_by_id(self, record_id: int) -> Optional[PostponeRecord]:
        """
        Retrieve a postpone record by its ID.

        Args:
            record_id: ID of postpone record to retrieve

        Returns:
            PostponeRecord object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, task_id, reason_type, reason_notes, action_taken, postponed_at
            FROM postpone_history
            WHERE id = ?
            """,
            (record_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        return self._row_to_postpone_record(row)

    def get_by_task_id(self, task_id: int, limit: int = 50) -> List[PostponeRecord]:
        """
        Retrieve postpone history for a specific task.

        Args:
            task_id: ID of task to get history for
            limit: Maximum number of records to return (default: 50)

        Returns:
            List of PostponeRecord objects ordered by postponed_at descending
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, task_id, reason_type, reason_notes, action_taken, postponed_at
            FROM postpone_history
            WHERE task_id = ?
            ORDER BY postponed_at DESC
            LIMIT ?
            """,
            (task_id, limit)
        )

        return [self._row_to_postpone_record(row) for row in cursor.fetchall()]

    def get_by_reason_type(self, reason_type: PostponeReasonType, limit: int = 100) -> List[PostponeRecord]:
        """
        Retrieve postpone records filtered by reason type.

        Args:
            reason_type: Type of postpone reason to filter by
            limit: Maximum number of records to return (default: 100)

        Returns:
            List of PostponeRecord objects ordered by postponed_at descending
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, task_id, reason_type, reason_notes, action_taken, postponed_at
            FROM postpone_history
            WHERE reason_type = ?
            ORDER BY postponed_at DESC
            LIMIT ?
            """,
            (reason_type.value, limit)
        )

        return [self._row_to_postpone_record(row) for row in cursor.fetchall()]

    def get_recent(self, days: int = 7, limit: int = 100) -> List[PostponeRecord]:
        """
        Retrieve recent postpone records within specified time window.

        Args:
            days: Number of days to look back (default: 7)
            limit: Maximum number of records to return (default: 100)

        Returns:
            List of PostponeRecord objects ordered by postponed_at descending
        """
        cursor = self.db.cursor()
        cutoff_date = datetime.now() - timedelta(days=days)

        cursor.execute(
            """
            SELECT id, task_id, reason_type, reason_notes, action_taken, postponed_at
            FROM postpone_history
            WHERE postponed_at >= ?
            ORDER BY postponed_at DESC
            LIMIT ?
            """,
            (cutoff_date.isoformat(), limit)
        )

        return [self._row_to_postpone_record(row) for row in cursor.fetchall()]

    def delete_by_task_id(self, task_id: int) -> int:
        """
        Delete all postpone records for a specific task.

        Note: This is automatically handled by ON DELETE CASCADE
        in the database schema, but provided for explicit cleanup.

        Args:
            task_id: ID of task to delete postpone records for

        Returns:
            Number of records deleted
        """
        cursor = self.db.cursor()
        cursor.execute(
            "DELETE FROM postpone_history WHERE task_id = ?",
            (task_id,)
        )
        self.db.commit()
        return cursor.rowcount

    def get_all(self) -> List[PostponeRecord]:
        """
        Retrieve all postpone records.

        Returns:
            List of all PostponeRecord objects ordered by postponed_at descending
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, task_id, reason_type, reason_notes, action_taken, postponed_at
            FROM postpone_history
            ORDER BY postponed_at DESC
            """
        )

        return [self._row_to_postpone_record(row) for row in cursor.fetchall()]

    def _row_to_postpone_record(self, row: sqlite3.Row) -> PostponeRecord:
        """
        Convert a database row to a PostponeRecord object.

        Args:
            row: Database row from query

        Returns:
            PostponeRecord object
        """
        return PostponeRecord(
            id=row[0],
            task_id=row[1],
            reason_type=PostponeReasonType(row[2]),
            reason_notes=row[3],
            action_taken=ActionTaken(row[4]),
            postponed_at=datetime.fromisoformat(row[5]) if row[5] else None
        )
