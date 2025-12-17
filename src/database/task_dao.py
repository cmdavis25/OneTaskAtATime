"""
Task Data Access Object for OneTaskAtATime application.

Handles all database CRUD operations for tasks.
"""

import sqlite3
from datetime import datetime, date
from typing import List, Optional
from ..models import Task, TaskState


class TaskDAO:
    """Data Access Object for Task operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize TaskDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def create(self, task: Task) -> Task:
        """
        Insert a new task into the database.

        Args:
            task: Task object to insert (id should be None)

        Returns:
            Task object with id populated

        Raises:
            ValueError: If task already has an id
        """
        if task.id is not None:
            raise ValueError("Cannot create task that already has an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            INSERT INTO tasks (
                title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                due_date, state, start_date, delegated_to, follow_up_date,
                completed_at, context_id, last_resurfaced_at, resurface_count,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task.title,
                task.description,
                task.base_priority,
                task.priority_adjustment,
                task.comparison_count,
                task.elo_rating,
                task.due_date.isoformat() if task.due_date else None,
                task.state.value,
                task.start_date.isoformat() if task.start_date else None,
                task.delegated_to,
                task.follow_up_date.isoformat() if task.follow_up_date else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.context_id,
                task.last_resurfaced_at.isoformat() if task.last_resurfaced_at else None,
                task.resurface_count,
                now.isoformat(),
                now.isoformat()
            )
        )

        task.id = cursor.lastrowid
        task.created_at = now
        task.updated_at = now

        # Handle project tags if present
        if task.project_tags:
            self._add_project_tags(task.id, task.project_tags)

        self.db.commit()
        return task

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """
        Retrieve a task by its ID.

        Args:
            task_id: ID of task to retrieve

        Returns:
            Task object if found, None otherwise
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                   due_date, state, start_date, delegated_to, follow_up_date,
                   completed_at, context_id, last_resurfaced_at, resurface_count,
                   created_at, updated_at
            FROM tasks
            WHERE id = ?
            """,
            (task_id,)
        )

        row = cursor.fetchone()
        if not row:
            return None

        task = self._row_to_task(row)

        # Load project tags
        task.project_tags = self._get_project_tag_ids(task_id)

        # Load blocking task IDs
        task.blocking_task_ids = self._get_blocking_task_ids(task_id)

        return task

    def get_all(self, state: Optional[TaskState] = None) -> List[Task]:
        """
        Retrieve all tasks, optionally filtered by state.

        Args:
            state: Optional TaskState to filter by

        Returns:
            List of Task objects
        """
        cursor = self.db.cursor()

        if state:
            cursor.execute(
                """
                SELECT id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                       due_date, state, start_date, delegated_to, follow_up_date,
                       completed_at, context_id, last_resurfaced_at, resurface_count,
                       created_at, updated_at
                FROM tasks
                WHERE state = ?
                ORDER BY created_at DESC
                """,
                (state.value,)
            )
        else:
            cursor.execute(
                """
                SELECT id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                       due_date, state, start_date, delegated_to, follow_up_date,
                       completed_at, context_id, last_resurfaced_at, resurface_count,
                       created_at, updated_at
                FROM tasks
                ORDER BY created_at DESC
                """
            )

        tasks = []
        for row in cursor.fetchall():
            task = self._row_to_task(row)
            task.project_tags = self._get_project_tag_ids(task.id)
            task.blocking_task_ids = self._get_blocking_task_ids(task.id)
            tasks.append(task)

        return tasks

    def update(self, task: Task) -> Task:
        """
        Update an existing task in the database.

        Args:
            task: Task object with updated values (must have id)

        Returns:
            Updated Task object

        Raises:
            ValueError: If task doesn't have an id
        """
        if task.id is None:
            raise ValueError("Cannot update task without an id")

        cursor = self.db.cursor()
        now = datetime.now()

        cursor.execute(
            """
            UPDATE tasks SET
                title = ?, description = ?, base_priority = ?,
                priority_adjustment = ?, comparison_count = ?, elo_rating = ?, due_date = ?, state = ?,
                start_date = ?, delegated_to = ?, follow_up_date = ?,
                completed_at = ?, context_id = ?, last_resurfaced_at = ?,
                resurface_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                task.title,
                task.description,
                task.base_priority,
                task.priority_adjustment,
                task.comparison_count,
                task.elo_rating,
                task.due_date.isoformat() if task.due_date else None,
                task.state.value,
                task.start_date.isoformat() if task.start_date else None,
                task.delegated_to,
                task.follow_up_date.isoformat() if task.follow_up_date else None,
                task.completed_at.isoformat() if task.completed_at else None,
                task.context_id,
                task.last_resurfaced_at.isoformat() if task.last_resurfaced_at else None,
                task.resurface_count,
                now.isoformat(),
                task.id
            )
        )

        task.updated_at = now

        # Update project tags
        self._remove_all_project_tags(task.id)
        if task.project_tags:
            self._add_project_tags(task.id, task.project_tags)

        self.db.commit()
        return task

    def delete(self, task_id: int) -> bool:
        """
        Delete a task from the database.

        Args:
            task_id: ID of task to delete

        Returns:
            True if task was deleted, False if not found
        """
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        self.db.commit()
        return cursor.rowcount > 0

    def get_active_tasks(self) -> List[Task]:
        """
        Get all active tasks (not blocked by dependencies).

        Returns:
            List of active, unblocked Task objects
        """
        return self.get_all(TaskState.ACTIVE)

    def get_deferred_tasks_ready_to_activate(self, current_date: date) -> List[Task]:
        """
        Get deferred tasks whose start_date has arrived.

        Args:
            current_date: Date to check against

        Returns:
            List of Task objects ready to be activated
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                   due_date, state, start_date, delegated_to, follow_up_date,
                   completed_at, context_id, last_resurfaced_at, resurface_count,
                   created_at, updated_at
            FROM tasks
            WHERE state = 'deferred' AND start_date <= ?
            ORDER BY start_date ASC
            """,
            (current_date.isoformat(),)
        )

        tasks = []
        for row in cursor.fetchall():
            task = self._row_to_task(row)
            task.project_tags = self._get_project_tag_ids(task.id)
            task.blocking_task_ids = self._get_blocking_task_ids(task.id)
            tasks.append(task)

        return tasks

    def get_delegated_tasks_for_followup(self, current_date: date, days_before: int = 1) -> List[Task]:
        """
        Get delegated tasks whose follow-up date is approaching.

        Args:
            current_date: Current date
            days_before: Number of days before follow_up_date to include

        Returns:
            List of delegated Task objects needing follow-up
        """
        from datetime import timedelta
        check_date = current_date + timedelta(days=days_before)

        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                   due_date, state, start_date, delegated_to, follow_up_date,
                   completed_at, context_id, last_resurfaced_at, resurface_count,
                   created_at, updated_at
            FROM tasks
            WHERE state = 'delegated' AND follow_up_date <= ?
            ORDER BY follow_up_date ASC
            """,
            (check_date.isoformat(),)
        )

        tasks = []
        for row in cursor.fetchall():
            task = self._row_to_task(row)
            task.project_tags = self._get_project_tag_ids(task.id)
            task.blocking_task_ids = self._get_blocking_task_ids(task.id)
            tasks.append(task)

        return tasks

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """
        Convert a database row to a Task object.

        Args:
            row: Database row from query

        Returns:
            Task object
        """
        return Task(
            id=row[0],
            title=row[1],
            description=row[2],
            base_priority=row[3],
            priority_adjustment=row[4],
            comparison_count=row[5],
            elo_rating=row[6],
            due_date=date.fromisoformat(row[7]) if row[7] else None,
            state=TaskState(row[8]),
            start_date=date.fromisoformat(row[9]) if row[9] else None,
            delegated_to=row[10],
            follow_up_date=date.fromisoformat(row[11]) if row[11] else None,
            completed_at=datetime.fromisoformat(row[12]) if row[12] else None,
            context_id=row[13],
            last_resurfaced_at=datetime.fromisoformat(row[14]) if row[14] else None,
            resurface_count=row[15],
            created_at=datetime.fromisoformat(row[16]) if row[16] else None,
            updated_at=datetime.fromisoformat(row[17]) if row[17] else None
        )

    def _get_project_tag_ids(self, task_id: int) -> List[int]:
        """Get list of project tag IDs for a task."""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT project_tag_id FROM task_project_tags WHERE task_id = ?",
            (task_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _get_blocking_task_ids(self, task_id: int) -> List[int]:
        """Get list of task IDs that are blocking this task."""
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT blocking_task_id FROM dependencies
            WHERE blocked_task_id = ?
            AND blocking_task_id IN (SELECT id FROM tasks WHERE state != 'completed')
            """,
            (task_id,)
        )
        return [row[0] for row in cursor.fetchall()]

    def _add_project_tags(self, task_id: int, tag_ids: List[int]) -> None:
        """Add project tags to a task."""
        cursor = self.db.cursor()
        for tag_id in tag_ids:
            cursor.execute(
                "INSERT OR IGNORE INTO task_project_tags (task_id, project_tag_id) VALUES (?, ?)",
                (task_id, tag_id)
            )

    def _remove_all_project_tags(self, task_id: int) -> None:
        """Remove all project tags from a task."""
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM task_project_tags WHERE task_id = ?", (task_id,))

    def delete_all_tasks(self) -> int:
        """
        Delete all tasks from the database.

        Returns:
            Number of tasks deleted
        """
        cursor = self.db.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks")
        count = cursor.fetchone()[0]

        cursor.execute("DELETE FROM tasks")
        self.db.commit()
        return count
