"""
Comparison Data Access Object for OneTaskAtATime application.

Handles database operations for task comparison history.
"""

import sqlite3
from datetime import datetime
from typing import List, Tuple


class ComparisonDAO:
    """Data Access Object for task comparison operations."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize ComparisonDAO with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection

    def record_comparison(self, winner_id: int, loser_id: int, adjustment_amount: float) -> int:
        """
        Record a comparison result in the database.

        Args:
            winner_id: ID of the task that won the comparison
            loser_id: ID of the task that lost the comparison
            adjustment_amount: Amount subtracted from loser's priority

        Returns:
            ID of the created comparison record
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            INSERT INTO task_comparisons (winner_task_id, loser_task_id, adjustment_amount, compared_at)
            VALUES (?, ?, ?, ?)
            """,
            (winner_id, loser_id, adjustment_amount, datetime.now().isoformat())
        )
        self.db.commit()
        return cursor.lastrowid

    def get_comparison_history(self, task_id: int) -> List[Tuple[int, str, float, str]]:
        """
        Get comparison history for a specific task.

        Args:
            task_id: ID of the task

        Returns:
            List of tuples (other_task_id, result, adjustment, compared_at)
            where result is 'won' or 'lost'
        """
        cursor = self.db.cursor()

        # Get comparisons where this task won
        cursor.execute(
            """
            SELECT loser_task_id, 'won', adjustment_amount, compared_at
            FROM task_comparisons
            WHERE winner_task_id = ?
            ORDER BY compared_at DESC
            """,
            (task_id,)
        )
        won_comparisons = cursor.fetchall()

        # Get comparisons where this task lost
        cursor.execute(
            """
            SELECT winner_task_id, 'lost', adjustment_amount, compared_at
            FROM task_comparisons
            WHERE loser_task_id = ?
            ORDER BY compared_at DESC
            """,
            (task_id,)
        )
        lost_comparisons = cursor.fetchall()

        # Combine and sort by date
        all_comparisons = won_comparisons + lost_comparisons
        all_comparisons.sort(key=lambda x: x[3], reverse=True)

        return all_comparisons

    def get_all_comparisons(self, limit: int = 100) -> List[Tuple[int, int, int, float, str]]:
        """
        Get all comparison records.

        Args:
            limit: Maximum number of records to return

        Returns:
            List of tuples (id, winner_id, loser_id, adjustment, compared_at)
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            SELECT id, winner_task_id, loser_task_id, adjustment_amount, compared_at
            FROM task_comparisons
            ORDER BY compared_at DESC
            LIMIT ?
            """,
            (limit,)
        )
        return cursor.fetchall()

    def delete_comparisons_for_task(self, task_id: int) -> int:
        """
        Delete all comparison records involving a task.

        This is typically called when resetting a task's priority adjustment.

        Args:
            task_id: ID of the task

        Returns:
            Number of comparison records deleted
        """
        cursor = self.db.cursor()
        cursor.execute(
            """
            DELETE FROM task_comparisons
            WHERE winner_task_id = ? OR loser_task_id = ?
            """,
            (task_id, task_id)
        )
        self.db.commit()
        return cursor.rowcount
