"""
Comparison Service - Business logic for task comparison operations.

Handles the Elo-based priority adjustment system.
"""

from typing import List, Tuple, Optional
from ..models.task import Task
from ..database.task_dao import TaskDAO
from ..database.comparison_dao import ComparisonDAO
from ..database.settings_dao import SettingsDAO
from ..database.connection import DatabaseConnection


class ComparisonService:
    """
    Service layer for task comparison operations.

    Implements the Elo rating system with tiered base priority bands.
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
        self.settings_dao = SettingsDAO(db_connection.get_connection())

    def record_comparison(self, winner: Task, loser: Task) -> Tuple[Task, Task]:
        """
        Record a comparison and update both tasks' Elo ratings.

        Uses standard Elo rating formula with K-factor based on comparison count.
        Tasks must have the same base_priority (comparisons only within same tier).

        Args:
            winner: Task that was selected as higher priority
            loser: Task that was not selected

        Returns:
            Tuple of (updated_winner, updated_loser)

        Raises:
            ValueError: If tasks don't have IDs or have different base_priorities
        """
        if winner.id is None or loser.id is None:
            raise ValueError("Both tasks must have IDs")

        # CRITICAL: Validate same base_priority tier
        if winner.base_priority != loser.base_priority:
            raise ValueError(
                f"Cannot compare tasks with different base priorities: "
                f"winner={winner.base_priority}, loser={loser.base_priority}. "
                f"Comparisons only allowed within same priority tier."
            )

        # Get K-factors from settings
        k_base = self.settings_dao.get('elo_k_factor', 16)
        k_new = self.settings_dao.get('elo_k_factor_new', 32)
        new_threshold = self.settings_dao.get('elo_new_task_threshold', 10)

        # Use higher K-factor for new tasks (faster learning)
        k_winner = k_new if winner.comparison_count < new_threshold else k_base
        k_loser = k_new if loser.comparison_count < new_threshold else k_base

        # Calculate expected scores using Elo formula
        # E_A = 1 / (1 + 10^((R_B - R_A) / 400))
        expected_winner = 1.0 / (1.0 + 10.0 ** ((loser.elo_rating - winner.elo_rating) / 400.0))
        expected_loser = 1.0 - expected_winner

        # Calculate rating changes (winner scores 1, loser scores 0)
        # New_R = Old_R + K * (Actual - Expected)
        elo_change_winner = k_winner * (1.0 - expected_winner)
        elo_change_loser = k_loser * (0.0 - expected_loser)  # Negative change

        # Update Elo ratings
        winner.elo_rating += elo_change_winner
        loser.elo_rating += elo_change_loser

        # Increment comparison counts
        winner.comparison_count += 1
        loser.comparison_count += 1

        # Save the comparison to database (store absolute value of loser's change)
        self.comparison_dao.record_comparison(
            winner.id,
            loser.id,
            abs(elo_change_loser)
        )

        # Update both tasks in database
        updated_winner = self.task_dao.update(winner)
        updated_loser = self.task_dao.update(loser)

        return (updated_winner, updated_loser)

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
        Reset a task's Elo rating and comparison count to defaults.

        Also deletes all comparison history for this task.

        Args:
            task_id: ID of task to reset

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        # Reset Elo to default starting rating
        task.elo_rating = 1500.0
        task.comparison_count = 0

        # Also reset deprecated fields (for backward compatibility during transition)
        task.priority_adjustment = 0.0

        # Delete comparison history
        self.comparison_dao.delete_comparisons_for_task(task_id)

        # Update task
        return self.task_dao.update(task)

    def reset_all_priority_adjustments(self) -> int:
        """
        Reset Elo ratings and comparison counts for all tasks.

        WARNING: This clears all comparison history.

        Returns:
            Number of tasks that were reset
        """
        # Get all tasks
        all_tasks = self.task_dao.get_all()
        reset_count = 0

        for task in all_tasks:
            # Reset if Elo is not at default or comparison_count > 0
            if task.elo_rating != 1500.0 or task.comparison_count > 0:
                task.elo_rating = 1500.0
                task.comparison_count = 0
                task.priority_adjustment = 0.0  # Also reset deprecated field
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

    def calculate_elo_change_preview(self, task: Task, opponent_elo: float) -> dict:
        """
        Calculate what the Elo change would be for a comparison outcome.

        Args:
            task: Task to calculate for
            opponent_elo: Elo rating of the opponent task

        Returns:
            Dictionary with 'if_win' and 'if_lose' Elo changes
        """
        # Get K-factor from settings
        k_base = self.settings_dao.get('elo_k_factor', 16)
        k_new = self.settings_dao.get('elo_k_factor_new', 32)
        new_threshold = self.settings_dao.get('elo_new_task_threshold', 10)

        k_factor = k_new if task.comparison_count < new_threshold else k_base

        # Calculate expected score
        expected = 1.0 / (1.0 + 10.0 ** ((opponent_elo - task.elo_rating) / 400.0))

        # Calculate changes for both outcomes
        elo_if_win = k_factor * (1.0 - expected)
        elo_if_lose = k_factor * (0.0 - expected)  # Negative

        return {
            'if_win': elo_if_win,
            'if_lose': elo_if_lose,
            'expected_score': expected,
            'k_factor': k_factor
        }
