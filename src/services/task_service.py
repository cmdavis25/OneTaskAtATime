"""
Task Service - Business logic layer for task operations.

Coordinates between UI, algorithms, and database layers.
"""

from typing import List, Optional
from datetime import date, datetime
from ..models.task import Task
from ..models.enums import TaskState, PostponeReasonType, ActionTaken
from ..models.postpone_record import PostponeRecord
from ..database.task_dao import TaskDAO
from ..database.postpone_history_dao import PostponeHistoryDAO
from ..database.connection import DatabaseConnection
from ..algorithms.ranking import get_next_focus_task, get_actionable_tasks, get_tied_tasks


class TaskService:
    """
    Service layer for task operations.

    Handles business logic for task lifecycle, coordinates with DAOs and algorithms.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the task service.

        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        self.task_dao = TaskDAO(db_connection.get_connection())
        self.postpone_dao = PostponeHistoryDAO(db_connection.get_connection())

    def get_all_tasks(self) -> List[Task]:
        """
        Get all tasks from the database.

        Returns:
            List of all tasks
        """
        return self.task_dao.get_all()

    def get_active_tasks(self) -> List[Task]:
        """
        Get all active tasks.

        Returns:
            List of tasks in ACTIVE state
        """
        return self.task_dao.get_all(state=TaskState.ACTIVE)

    def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """
        Get a task by its ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            Task with the given ID, or None if not found
        """
        return self.task_dao.get_by_id(task_id)

    def get_focus_task(self) -> Optional[Task]:
        """
        Get the single task to display in Focus Mode.

        Returns:
            Top-priority task, or None if no actionable tasks or tie exists
        """
        all_tasks = self.task_dao.get_all()
        return get_next_focus_task(all_tasks)

    def get_tied_tasks(self) -> List[Task]:
        """
        Get all tasks tied for top priority.

        Returns:
            List of tied tasks (empty if no ties)
        """
        all_tasks = self.task_dao.get_all()
        return get_tied_tasks(all_tasks)

    def create_task(self, task: Task) -> Task:
        """
        Create a new task.

        Args:
            task: Task to create (id should be None)

        Returns:
            Created task with id assigned
        """
        return self.task_dao.create(task)

    def update_task(self, task: Task) -> Task:
        """
        Update an existing task.

        Args:
            task: Task to update (must have id)

        Returns:
            Updated task
        """
        return self.task_dao.update(task)

    def delete_task(self, task_id: int) -> bool:
        """
        Delete a task.

        Args:
            task_id: ID of task to delete

        Returns:
            True if deleted successfully
        """
        return self.task_dao.delete(task_id)

    def complete_task(self, task_id: int) -> Optional[Task]:
        """
        Mark a task as completed.

        Args:
            task_id: ID of task to complete

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.mark_completed()
        return self.task_dao.update(task)

    def defer_task(self, task_id: int, start_date: date,
                   reason: PostponeReasonType = PostponeReasonType.NOT_READY,
                   notes: Optional[str] = None) -> Optional[Task]:
        """
        Defer a task until a specific date.

        Args:
            task_id: ID of task to defer
            start_date: When task becomes actionable again
            reason: Why task was deferred
            notes: Optional additional context

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.defer_until(start_date)
        updated_task = self.task_dao.update(task)

        # Record postpone reason after successful state change
        postpone_record = PostponeRecord(
            task_id=task_id,
            reason_type=reason,
            reason_notes=notes,
            action_taken=ActionTaken.DEFERRED
        )
        self.postpone_dao.create(postpone_record)

        return updated_task

    def delegate_task(self, task_id: int, delegated_to: str,
                     follow_up_date: date, notes: Optional[str] = None) -> Optional[Task]:
        """
        Delegate a task to someone.

        Args:
            task_id: ID of task to delegate
            delegated_to: Person/system receiving the task
            follow_up_date: When to check on progress
            notes: Optional additional context

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.delegate_to(delegated_to, follow_up_date)
        updated_task = self.task_dao.update(task)

        # Record postpone reason after successful state change
        postpone_record = PostponeRecord(
            task_id=task_id,
            reason_type=PostponeReasonType.OTHER,  # Delegation is a form of postponement
            reason_notes=notes,
            action_taken=ActionTaken.DELEGATED
        )
        self.postpone_dao.create(postpone_record)

        return updated_task

    def move_to_someday(self, task_id: int) -> Optional[Task]:
        """
        Move task to Someday/Maybe list.

        Args:
            task_id: ID of task to move

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.move_to_someday()
        return self.task_dao.update(task)

    def move_to_trash(self, task_id: int) -> Optional[Task]:
        """
        Move task to trash.

        Args:
            task_id: ID of task to trash

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.move_to_trash()
        return self.task_dao.update(task)

    def get_tasks_by_state(self, state: TaskState) -> List[Task]:
        """
        Get all tasks in a specific state.

        Args:
            state: Task state to filter by

        Returns:
            List of tasks in that state
        """
        return self.task_dao.get_all(state=state)

    def get_overdue_tasks(self) -> List[Task]:
        """
        Get all active tasks that are overdue.

        Returns:
            List of overdue tasks
        """
        active_tasks = self.get_active_tasks()
        today = date.today()

        overdue = []
        for task in active_tasks:
            if task.due_date and task.due_date < today:
                overdue.append(task)

        return overdue

    def reset_priority_adjustment(self, task_id: int) -> Optional[Task]:
        """
        Reset a task's priority adjustment to zero.

        Args:
            task_id: ID of task to reset

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        task.priority_adjustment = 0.0
        return self.task_dao.update(task)

    def get_task_count_by_state(self) -> dict:
        """
        Get count of tasks in each state.

        Returns:
            Dictionary mapping state name to count
        """
        counts = {}
        for state in TaskState:
            tasks = self.get_tasks_by_state(state)
            counts[state.value] = len(tasks)
        return counts
