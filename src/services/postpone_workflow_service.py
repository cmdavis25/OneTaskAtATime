"""
PostponeWorkflow Service for OneTaskAtATime application.

Coordinates business logic for postpone-triggered workflows including
blocker creation, dependency management, and subtask breakdown.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
from ..database.task_dao import TaskDAO
from ..database.dependency_dao import DependencyDAO
from ..database.postpone_history_dao import PostponeHistoryDAO
from ..models.task import Task
from ..models.dependency import Dependency
from ..models.postpone_record import PostponeRecord
from ..models.enums import TaskState, PostponeReasonType, ActionTaken


class PostponeWorkflowService:
    """Coordinates workflows triggered by postpone actions."""

    def __init__(self, db_connection: sqlite3.Connection):
        """
        Initialize PostponeWorkflowService with database connection.

        Args:
            db_connection: Active SQLite database connection
        """
        self.db = db_connection
        self.task_dao = TaskDAO(db_connection)
        self.dependency_dao = DependencyDAO(db_connection)
        self.postpone_dao = PostponeHistoryDAO(db_connection)

    def record_postpone(
        self,
        task_id: int,
        reason: PostponeReasonType,
        notes: Optional[str] = None,
        action_taken: ActionTaken = ActionTaken.NONE
    ) -> PostponeRecord:
        """
        Save a postpone event to history.

        Args:
            task_id: ID of task being postponed
            reason: Category of postponement reason
            notes: Optional explanation from user
            action_taken: What action was taken in response

        Returns:
            Created PostponeRecord with id populated
        """
        record = PostponeRecord(
            task_id=task_id,
            reason_type=reason,
            reason_notes=notes,
            action_taken=action_taken,
            postponed_at=datetime.now()
        )

        return self.postpone_dao.create(record)

    def handle_blocker_workflow(
        self,
        task_id: int,
        notes: Optional[str] = None,
        blocking_task_ids: Optional[List[int]] = None,
        created_blocking_task_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Add blocking tasks (dependencies) for the specified task.

        This unified workflow handles both creating new blocking tasks and selecting
        existing tasks. The DependencySelectionDialog creates tasks and saves
        dependencies directly, so this method primarily records the postpone action.

        Args:
            task_id: ID of task being blocked
            notes: Optional notes about the blockers/dependencies
            blocking_task_ids: List of all task IDs that block this task
            created_blocking_task_ids: Subset of blocking_task_ids that were newly created

        Returns:
            Dictionary with:
                - success (bool): Whether operation succeeded
                - count (int): Number of dependencies added
                - message (str): User-friendly result message
        """
        try:
            if not blocking_task_ids:
                return {
                    'success': False,
                    'count': 0,
                    'message': 'No blocking tasks specified'
                }

            # Verify blocked task exists
            blocked_task = self.task_dao.get_by_id(task_id)
            if not blocked_task:
                return {
                    'success': False,
                    'count': 0,
                    'message': f'Task {task_id} not found'
                }

            # Dependencies are already saved by DependencySelectionDialog
            # Just record the postpone action with appropriate action type
            created_blocking_task_ids = created_blocking_task_ids or []

            if created_blocking_task_ids:
                # At least one new blocking task was created
                action_taken = ActionTaken.CREATED_BLOCKER
            else:
                # Only existing tasks were selected
                action_taken = ActionTaken.ADDED_DEPENDENCY

            self.record_postpone(
                task_id,
                PostponeReasonType.BLOCKER,
                notes,
                action_taken
            )

            count = len(blocking_task_ids)
            plural = 'blocking task' if count == 1 else 'blocking tasks'
            return {
                'success': True,
                'count': count,
                'message': f'{count} {plural} added, task is now blocked'
            }

        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'message': f'Unexpected error: {str(e)}'
            }

    def handle_subtask_breakdown(
        self,
        original_task_id: int,
        notes: Optional[str] = None,
        subtask_titles: Optional[List[str]] = None,
        delete_original: bool = False
    ) -> Dict[str, Any]:
        """
        Break a task into multiple subtasks with field inheritance.

        New subtasks inherit: base_priority, due_date, context_id, project_tags
        New subtasks DO NOT inherit: comparison_losses, priority_adjustment, description

        Args:
            original_task_id: ID of task to break down
            notes: Optional notes about the breakdown
            subtask_titles: List of titles for new subtasks
            delete_original: If True, move original to TRASH; if False, keep it

        Returns:
            Dictionary with:
                - success (bool): Whether operation succeeded
                - task_ids (List[int]): IDs of created subtasks
                - message (str): User-friendly result message
        """
        try:
            if not subtask_titles or len(subtask_titles) == 0:
                return {
                    'success': False,
                    'task_ids': [],
                    'message': 'No subtask titles provided'
                }

            # Get original task
            original = self.task_dao.get_by_id(original_task_id)
            if not original:
                return {
                    'success': False,
                    'task_ids': [],
                    'message': f'Task {original_task_id} not found'
                }

            # Create subtasks inheriting key fields
            created_task_ids = []
            for title in subtask_titles:
                # Skip empty titles
                if not title.strip():
                    continue

                subtask = Task(
                    title=title.strip(),
                    base_priority=original.base_priority,
                    due_date=original.due_date,
                    context_id=original.context_id,
                    state=TaskState.ACTIVE,
                    # Reset priority adjustment and comparison losses
                    priority_adjustment=0.0,
                    comparison_losses=0
                )

                # Create subtask
                created_subtask = self.task_dao.create(subtask)
                created_task_ids.append(created_subtask.id)

                # Copy project tags
                if original.project_tags:
                    self.task_dao._add_project_tags(created_subtask.id, original.project_tags)

            # Handle original task based on user preference
            if delete_original:
                original.state = TaskState.TRASH
                self.task_dao.update(original)
                action_message = "original task moved to trash"
            else:
                action_message = "original task kept"

            # Record the postpone action
            self.record_postpone(
                original_task_id,
                PostponeReasonType.MULTIPLE_SUBTASKS,
                notes,
                ActionTaken.BROKE_DOWN
            )

            count = len(created_task_ids)
            plural = 'task' if count == 1 else 'tasks'
            return {
                'success': True,
                'task_ids': created_task_ids,
                'message': f'{count} new {plural} created, {action_message}'
            }

        except Exception as e:
            return {
                'success': False,
                'task_ids': [],
                'message': f'Unexpected error: {str(e)}'
            }

    def get_postpone_history(
        self,
        task_id: int,
        limit: int = 10
    ) -> List[PostponeRecord]:
        """
        Retrieve postpone history for a task for analysis.

        Args:
            task_id: ID of task to get history for
            limit: Maximum number of records to retrieve

        Returns:
            List of PostponeRecord objects ordered by date descending
        """
        return self.postpone_dao.get_by_task_id(task_id, limit)
