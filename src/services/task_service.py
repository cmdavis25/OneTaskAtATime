"""
Task Service - Business logic layer for task operations.

Coordinates between UI, algorithms, and database layers.
"""

from typing import List, Optional, Set
from datetime import date, datetime
from ..models.task import Task
from ..models.enums import TaskState, PostponeReasonType, ActionTaken
from ..models.postpone_record import PostponeRecord
from ..models.recurrence_pattern import RecurrencePattern
from ..database.task_dao import TaskDAO
from ..database.postpone_history_dao import PostponeHistoryDAO
from ..database.context_dao import ContextDAO
from ..database.task_history_dao import TaskHistoryDAO
from ..database.connection import DatabaseConnection
from ..algorithms.ranking import get_next_focus_task, get_actionable_tasks, get_tied_tasks
from .recurrence_service import RecurrenceService
from .task_history_service import TaskHistoryService


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
        self.context_dao = ContextDAO(db_connection.get_connection())
        history_dao = TaskHistoryDAO(db_connection.get_connection())
        self.history_service = TaskHistoryService(history_dao)

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

    def get_focus_task(
        self,
        context_filter: Optional[int] = None,
        tag_filters: Optional[Set[int]] = None
    ) -> Optional[Task]:
        """
        Get the single task to display in Focus Mode.

        Args:
            context_filter: Optional context ID to filter by (single selection)
            tag_filters: Optional set of tag IDs to filter by (OR condition)

        Returns:
            Top-priority task, or None if no actionable tasks or tie exists
        """
        all_tasks = self.task_dao.get_all()
        return get_next_focus_task(all_tasks, context_filter=context_filter, tag_filters=tag_filters)

    def get_tied_tasks(
        self,
        context_filter: Optional[int] = None,
        tag_filters: Optional[Set[int]] = None
    ) -> List[Task]:
        """
        Get all tasks tied for top priority.

        Args:
            context_filter: Optional context ID to filter by (single selection)
            tag_filters: Optional set of tag IDs to filter by (OR condition)

        Returns:
            List of tied tasks (empty if no ties)
        """
        all_tasks = self.task_dao.get_all()
        return get_tied_tasks(all_tasks, context_filter=context_filter, tag_filters=tag_filters)

    def get_ranked_tasks(
        self,
        context_filter: Optional[int] = None,
        tag_filters: Optional[Set[int]] = None
    ) -> List[Task]:
        """
        Get all actionable tasks ranked by importance.

        Args:
            context_filter: Optional context ID to filter by (single selection)
            tag_filters: Optional set of tag IDs to filter by (OR condition)

        Returns:
            List of tasks ranked by importance (highest first)
        """
        all_tasks = self.task_dao.get_all()
        return get_actionable_tasks(all_tasks, context_filter=context_filter, tag_filters=tag_filters)

    def create_task(self, task: Task) -> Task:
        """
        Create a new task.

        Args:
            task: Task to create (id should be None)

        Returns:
            Created task with id assigned
        """
        created_task = self.task_dao.create(task)
        # Record creation in history
        self.history_service.record_task_created(created_task)
        return created_task

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

    def delete_all_tasks(self) -> int:
        """
        Delete all tasks from the database.

        Returns:
            Number of tasks deleted
        """
        return self.task_dao.delete_all_tasks()

    def delete_trash_tasks(self) -> int:
        """
        Delete all tasks in TRASH state.

        Returns:
            Number of tasks deleted
        """
        trash_tasks = self.get_tasks_by_state(TaskState.TRASH)
        count = 0
        for task in trash_tasks:
            if self.task_dao.delete(task.id):
                count += 1
        return count

    def complete_task(self, task_id: int) -> Optional[Task]:
        """
        Mark a task as completed. Generate next occurrence if recurring.

        Args:
            task_id: ID of task to complete

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        old_state = task.state
        task.mark_completed()
        completed_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.COMPLETED:
            self.history_service.record_state_change(completed_task, old_state, TaskState.COMPLETED)

        # Handle recurring logic
        if task.is_recurring:
            self._generate_next_occurrence(completed_task)

        return completed_task

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

        old_state = task.state
        task.defer_until(start_date)
        updated_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.DEFERRED:
            self.history_service.record_state_change(updated_task, old_state, TaskState.DEFERRED)

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

        old_state = task.state
        task.delegate_to(delegated_to, follow_up_date)
        updated_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.DELEGATED:
            self.history_service.record_state_change(updated_task, old_state, TaskState.DELEGATED)

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

        old_state = task.state
        task.move_to_someday()
        updated_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.SOMEDAY:
            self.history_service.record_state_change(updated_task, old_state, TaskState.SOMEDAY)

        return updated_task

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

        old_state = task.state
        task.move_to_trash()
        updated_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.TRASH:
            self.history_service.record_state_change(updated_task, old_state, TaskState.TRASH)

        return updated_task

    def activate_task(self, task_id: int) -> Optional[Task]:
        """
        Change task state to ACTIVE.

        Args:
            task_id: ID of task to activate

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        old_state = task.state
        task.state = TaskState.ACTIVE
        # Clear state-specific fields
        task.start_date = None
        task.delegated_to = None
        task.follow_up_date = None
        task.completed_at = None
        updated_task = self.task_dao.update(task)

        # Record state change in history
        if old_state != TaskState.ACTIVE:
            self.history_service.record_state_change(updated_task, old_state, TaskState.ACTIVE)

        return updated_task

    def restore_task(self, task_id: int) -> Optional[Task]:
        """
        Restore a task from trash to active state.

        Args:
            task_id: ID of task to restore

        Returns:
            Updated task, or None if not found
        """
        return self.activate_task(task_id)

    def uncomplete_task(self, task_id: int) -> Optional[Task]:
        """
        Mark a completed task as active again.

        Args:
            task_id: ID of task to uncomplete

        Returns:
            Updated task, or None if not found
        """
        task = self.task_dao.get_by_id(task_id)
        if task is None:
            return None

        if task.state == TaskState.COMPLETED:
            old_state = task.state
            task.state = TaskState.ACTIVE
            task.completed_at = None
            updated_task = self.task_dao.update(task)

            # Record state change in history
            self.history_service.record_state_change(updated_task, old_state, TaskState.ACTIVE)

            return updated_task

        return task

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

    def _generate_next_occurrence(self, completed_task: Task) -> Optional[Task]:
        """
        Generate next occurrence of recurring task.

        Steps:
        1. Check if series should end (recurrence_end_date)
        2. Parse recurrence pattern from JSON
        3. Calculate next due date
        4. Clone task with new due date
        5. Handle Elo rating based on share_elo_rating flag:
           - If True: Copy shared_elo_rating from parent
           - If False: Reset to 1500.0 (independent)
        6. Increment occurrence_count
        7. Save new task instance

        Args:
            completed_task: The task that was just completed

        Returns:
            Newly created task or None if series ended
        """
        if not completed_task.is_recurring or not completed_task.recurrence_pattern:
            return None

        # Parse recurrence pattern
        try:
            pattern = RecurrencePattern.from_json(completed_task.recurrence_pattern)
        except (ValueError, KeyError) as e:
            print(f"Error parsing recurrence pattern for task {completed_task.id}: {e}")
            return None

        # Calculate next due date from the original due date (or today if no due date)
        # This ensures consistent scheduling regardless of when task is completed
        completion_date = date.today()
        base_date = completed_task.due_date if completed_task.due_date else completion_date
        next_due_date = RecurrenceService.calculate_next_occurrence_date(pattern, base_date)

        # Check if the next due date would exceed the end date
        if completed_task.recurrence_end_date and next_due_date > completed_task.recurrence_end_date:
            return None

        # Check if we've reached the maximum number of occurrences
        if completed_task.max_occurrences and completed_task.occurrence_count + 1 >= completed_task.max_occurrences:
            return None

        # Get shared Elo values if applicable
        shared_elo, shared_count = RecurrenceService.get_shared_elo_values(completed_task)

        # Clone task for next occurrence
        next_task = RecurrenceService.clone_task_for_next_occurrence(
            completed_task,
            next_due_date,
            shared_elo=shared_elo,
            shared_comparison_count=shared_count
        )

        # Create the next occurrence in database
        created_task = self.task_dao.create(next_task)

        return created_task
