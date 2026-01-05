"""Delete Task Command for undo/redo functionality."""

from typing import Optional
import copy

from src.commands.base_command import Command
from src.models.task import Task
from src.database.task_dao import TaskDAO


class DeleteTaskCommand(Command):
    """Command to delete a task (move to trash)."""

    def __init__(self, task_dao: TaskDAO, task_id: int):
        self.task_dao = task_dao
        self.task_id = task_id
        self.deleted_task: Optional[Task] = None

    def execute(self) -> bool:
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        # Save complete task for potential undo
        self.deleted_task = copy.deepcopy(task)

        # Delete from database
        return self.task_dao.delete(self.task_id)

    def undo(self) -> bool:
        if not self.deleted_task:
            return False

        # Restore the deleted task with its original ID
        # We need to bypass the normal create() method which rejects tasks with IDs
        # Instead, we use a direct SQL INSERT
        try:
            cursor = self.task_dao.db.cursor()
            task = self.deleted_task

            cursor.execute(
                """
                INSERT INTO tasks (
                    id, title, description, base_priority, priority_adjustment, comparison_count, elo_rating,
                    due_date, state, start_date, delegated_to, follow_up_date,
                    completed_at, context_id, last_resurfaced_at, resurface_count,
                    is_recurring, recurrence_pattern, recurrence_parent_id, share_elo_rating,
                    shared_elo_rating, shared_comparison_count, recurrence_end_date, occurrence_count,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task.id,
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
                    1 if task.is_recurring else 0,
                    task.recurrence_pattern,
                    task.recurrence_parent_id,
                    1 if task.share_elo_rating else 0,
                    task.shared_elo_rating,
                    task.shared_comparison_count,
                    task.recurrence_end_date.isoformat() if task.recurrence_end_date else None,
                    task.occurrence_count,
                    task.created_at.isoformat() if task.created_at else None,
                    task.updated_at.isoformat() if task.updated_at else None
                )
            )

            # Restore project tags if present
            if task.project_tags:
                self.task_dao._add_project_tags(task.id, task.project_tags)

            self.task_dao.db.commit()
            return True

        except Exception as e:
            print(f"Error restoring deleted task: {e}")
            return False

    def get_description(self) -> str:
        if self.deleted_task:
            return f"Delete task: {self.deleted_task.title}"
        return f"Delete task (ID: {self.task_id})"
