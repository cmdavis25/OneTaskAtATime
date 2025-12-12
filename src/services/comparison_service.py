"""
Comparison Service - Business logic for task comparison operations.

Handles the comparison-based priority adjustment system.
"""

from typing import List, Tuple, Optional
from ..models.task import Task
from ..database.task_dao import TaskDAO
from ..database.comparison_dao import ComparisonDAO
from ..database.connection import DatabaseConnection


class ComparisonService:
    """
    Service layer for task comparison operations.

    Implements the exponential decay priority adjustment algorithm.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the comparison service.

        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        self.task_dao = TaskDAO(db_connection.get_connection())
        self.comparison_dao = ComparisonDAO(db_connection.get_connection())

    def record_comparison(self, winner: Task, loser: Task) -> Tuple[Task, Task]:
        """
        Record a comparison and update the loser's priority adjustment.

        Uses exponential decay: adjustment += 0.5^N where N is comparison_losses.

        Args:
            winner: Task that was selected as higher priority
            loser: Task that was not selected

        Returns:
            Tuple of (updated_winner, updated_loser)
        """
        if winner.id is None or loser.id is None:
            raise ValueError("Both tasks must have IDs")

        # Increment loss count first
        loser.comparison_losses += 1

        # Calculate adjustment amount using exponential decay
        # Formula: 0.5^N where N = number of losses (AFTER increment)
        adjustment_increment = 0.5 ** loser.comparison_losses

        # Update loser's priority adjustment
        loser.priority_adjustment += adjustment_increment

        # Save the comparison to database
        self.comparison_dao.record_comparison(
            winner.id,
            loser.id,
            adjustment_increment
        )

        # Update loser in database
        updated_loser = self.task_dao.update(loser)

        # Winner doesn't change, but return for consistency
        return (winner, updated_loser)

    def record_multiple_comparisons(self, comparison_results: List[Tuple[Task, Task]]) -> None:
        """
        Record multiple comparisons from a comparison session.

        Args:
            comparison_results: List of (winner, loser) tuples
        """
        for winner, loser in comparison_results:
            self.record_comparison(winner, loser)

    def reset_task_priority_adjustment(self, task_id: int) -> Optional[Task]:
        """
        Reset a task's priority adjustment and comparison loss count to zero.

        Also deletes all comparison history for this task.

        Args:
            task_id: ID of task to reset

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        # Reset both adjustment and loss count
        task.priority_adjustment = 0.0
        task.comparison_losses = 0

        # Delete comparison history
        self.comparison_dao.delete_comparisons_for_task(task_id)

        # Update task
        return self.task_dao.update(task)

    def reset_all_priority_adjustments(self) -> int:
        """
        Reset priority adjustments for all tasks.

        WARNING: This clears all comparison history.

        Returns:
            Number of tasks that were reset
        """
        # Get all tasks with priority adjustments
        all_tasks = self.task_dao.get_all()
        reset_count = 0

        for task in all_tasks:
            if task.priority_adjustment > 0 or task.comparison_losses > 0:
                task.priority_adjustment = 0.0
                task.comparison_losses = 0
                self.task_dao.update(task)
                reset_count += 1

        # Clear all comparison history
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM task_comparisons")
        conn.commit()

        return reset_count

    def get_task_comparison_history(self, task_id: int) -> List[dict]:
        """
        Get comparison history for a task in a user-friendly format.

        Args:
            task_id: ID of the task

        Returns:
            List of comparison records as dictionaries
        """
        history = self.comparison_dao.get_comparison_history(task_id)

        result = []
        for other_task_id, outcome, adjustment, compared_at in history:
            other_task = self.task_dao.get_by_id(other_task_id)
            result.append({
                'other_task_id': other_task_id,
                'other_task_title': other_task.title if other_task else 'Unknown',
                'outcome': outcome,
                'adjustment': adjustment,
                'compared_at': compared_at
            })

        return result

    def calculate_adjustment_preview(self, task: Task) -> float:
        """
        Calculate what the next adjustment would be if task loses.

        Args:
            task: Task to calculate for

        Returns:
            The adjustment amount that would be applied
        """
        # Next loss would be N+1
        return 0.5 ** (task.comparison_losses + 1)
