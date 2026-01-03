"""
Data Access Object for TaskHistoryEvent model.

Handles all database operations for task history audit log.
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional

from src.models.task_history_event import TaskHistoryEvent
from src.models.enums import TaskEventType


class TaskHistoryDAO:
    """
    Data Access Object for task history events.

    Provides methods to create, retrieve, and query task history events
    for comprehensive audit logging and timeline views.
    """

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize the TaskHistoryDAO.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db_connection = db_connection

    def create_event(self, event: TaskHistoryEvent) -> TaskHistoryEvent:
        """
        Create a new task history event in the database.

        Args:
            event: TaskHistoryEvent to create

        Returns:
            The created TaskHistoryEvent with populated ID

        Raises:
            sqlite3.Error: If database operation fails
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            INSERT INTO task_history (
                task_id, event_type, event_timestamp, old_value,
                new_value, changed_by, context_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.task_id,
                event.event_type.value,
                event.event_timestamp,
                event.old_value,
                event.new_value,
                event.changed_by,
                event.context_data
            )
        )

        self.db_connection.commit()
        event.id = cursor.lastrowid
        return event

    def get_by_id(self, event_id: int) -> Optional[TaskHistoryEvent]:
        """
        Retrieve a task history event by its ID.

        Args:
            event_id: ID of the event to retrieve

        Returns:
            TaskHistoryEvent if found, None otherwise
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT id, task_id, event_type, event_timestamp, old_value,
                   new_value, changed_by, context_data
            FROM task_history
            WHERE id = ?
            """,
            (event_id,)
        )

        row = cursor.fetchone()
        return self._row_to_event(row) if row else None

    def get_by_task_id(self, task_id: int, limit: int = 100) -> List[TaskHistoryEvent]:
        """
        Retrieve all history events for a specific task.

        Args:
            task_id: ID of the task
            limit: Maximum number of events to retrieve (default 100)

        Returns:
            List of TaskHistoryEvent objects, ordered by timestamp DESC
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT id, task_id, event_type, event_timestamp, old_value,
                   new_value, changed_by, context_data
            FROM task_history
            WHERE task_id = ?
            ORDER BY event_timestamp DESC
            LIMIT ?
            """,
            (task_id, limit)
        )

        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_recent(self, limit: int = 50) -> List[TaskHistoryEvent]:
        """
        Retrieve the most recent history events across all tasks.

        Args:
            limit: Maximum number of events to retrieve (default 50)

        Returns:
            List of TaskHistoryEvent objects, ordered by timestamp DESC
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT id, task_id, event_type, event_timestamp, old_value,
                   new_value, changed_by, context_data
            FROM task_history
            ORDER BY event_timestamp DESC
            LIMIT ?
            """,
            (limit,)
        )

        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_by_type(self, event_type: TaskEventType, limit: int = 100) -> List[TaskHistoryEvent]:
        """
        Retrieve history events of a specific type.

        Args:
            event_type: Type of events to retrieve
            limit: Maximum number of events to retrieve (default 100)

        Returns:
            List of TaskHistoryEvent objects, ordered by timestamp DESC
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT id, task_id, event_type, event_timestamp, old_value,
                   new_value, changed_by, context_data
            FROM task_history
            WHERE event_type = ?
            ORDER BY event_timestamp DESC
            LIMIT ?
            """,
            (event_type.value, limit)
        )

        return [self._row_to_event(row) for row in cursor.fetchall()]

    def get_date_range(self, start_date: date, end_date: date) -> List[TaskHistoryEvent]:
        """
        Retrieve history events within a date range.

        Args:
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of TaskHistoryEvent objects, ordered by timestamp DESC
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT id, task_id, event_type, event_timestamp, old_value,
                   new_value, changed_by, context_data
            FROM task_history
            WHERE DATE(event_timestamp) BETWEEN ? AND ?
            ORDER BY event_timestamp DESC
            """,
            (start_date, end_date)
        )

        return [self._row_to_event(row) for row in cursor.fetchall()]

    def delete_by_task_id(self, task_id: int) -> bool:
        """
        Delete all history events for a specific task.

        Note: This is typically handled by CASCADE DELETE when task is deleted,
        but provided for manual cleanup if needed.

        Args:
            task_id: ID of the task

        Returns:
            True if any rows were deleted, False otherwise
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            "DELETE FROM task_history WHERE task_id = ?",
            (task_id,)
        )

        self.db_connection.commit()
        return cursor.rowcount > 0

    def get_count_by_task(self, task_id: int) -> int:
        """
        Get the total number of history events for a task.

        Args:
            task_id: ID of the task

        Returns:
            Count of history events
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM task_history WHERE task_id = ?",
            (task_id,)
        )

        result = cursor.fetchone()
        return result[0] if result else 0

    def get_count_by_type(self, task_id: int, event_type: TaskEventType) -> int:
        """
        Get the count of a specific event type for a task.

        Args:
            task_id: ID of the task
            event_type: Type of event to count

        Returns:
            Count of events of specified type
        """
        cursor = self.db_connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM task_history
            WHERE task_id = ? AND event_type = ?
            """,
            (task_id, event_type.value)
        )

        result = cursor.fetchone()
        return result[0] if result else 0

    def _row_to_event(self, row: tuple) -> TaskHistoryEvent:
        """
        Convert a database row to a TaskHistoryEvent object.

        Args:
            row: Tuple from database query

        Returns:
            TaskHistoryEvent object
        """
        return TaskHistoryEvent(
            id=row[0],
            task_id=row[1],
            event_type=TaskEventType(row[2]),
            event_timestamp=datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3],
            old_value=row[4],
            new_value=row[5],
            changed_by=row[6],
            context_data=row[7]
        )
