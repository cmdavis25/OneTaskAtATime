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
        blocker_task_id: Optional[int] = None,
        new_blocker_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or select a blocking task and establish dependency.

        Either blocker_task_id (existing) or new_blocker_title (create new) must be provided.

        Args:
            task_id: ID of task being blocked
            notes: Optional notes about the blocker
            blocker_task_id: ID of existing task to use as blocker
            new_blocker_title: Title for new blocker task to create

        Returns:
            Dictionary with:
                - success (bool): Whether operation succeeded
                - blocker_task_id (int): ID of blocker task
                - message (str): User-friendly result message
        """
        try:
            # Validate inputs
            if blocker_task_id is None and new_blocker_title is None:
                return {
                    'success': False,
                    'message': 'Must provide either existing blocker task ID or new blocker title'
                }

            # Get the blocked task
            blocked_task = self.task_dao.get_by_id(task_id)
            if not blocked_task:
                return {
                    'success': False,
                    'message': f'Task {task_id} not found'
                }

            # Create new blocker or use existing
            if new_blocker_title:
                # Create new blocker task in ACTIVE state (needs immediate attention)
                # Inherit key fields from blocked task
                blocker_task = Task(
                    title=new_blocker_title,
                    description=notes,
                    base_priority=blocked_task.base_priority,  # Inherit priority
                    priority_adjustment=blocked_task.priority_adjustment,  # Inherit adjustment
                    due_date=blocked_task.due_date,  # Inherit urgency
                    context_id=blocked_task.context_id,  # Inherit context
                    state=TaskState.ACTIVE
                )
                blocker_task = self.task_dao.create(blocker_task)
                blocker_task_id = blocker_task.id

                # Copy project tags
                if blocked_task.project_tags:
                    self.task_dao._add_project_tags(blocker_task.id, blocked_task.project_tags)

                blocker_name = new_blocker_title
            else:
                # Verify existing blocker task exists
                blocker_task = self.task_dao.get_by_id(blocker_task_id)
                if not blocker_task:
                    return {
                        'success': False,
                        'message': f'Blocker task {blocker_task_id} not found'
                    }
                blocker_name = blocker_task.title

            # Create dependency relationship
            dependency = Dependency(
                blocked_task_id=task_id,
                blocking_task_id=blocker_task_id
            )
            self.dependency_dao.create(dependency)

            # Record the postpone action
            self.record_postpone(
                task_id,
                PostponeReasonType.BLOCKER,
                notes,
                ActionTaken.CREATED_BLOCKER
            )

            return {
                'success': True,
                'blocker_task_id': blocker_task_id,
                'message': f"Blocker created: '{blocker_name}' now blocks this task"
            }

        except ValueError as e:
            # Circular dependency or validation error
            return {
                'success': False,
                'message': f'Cannot create blocker: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }

    def handle_dependency_workflow(
        self,
        task_id: int,
        notes: Optional[str] = None,
        dependency_task_ids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Add existing tasks as dependencies for the specified task.

        Args:
            task_id: ID of task being blocked
            notes: Optional notes about the dependencies
            dependency_task_ids: List of task IDs that block this task

        Returns:
            Dictionary with:
                - success (bool): Whether operation succeeded
                - count (int): Number of dependencies added
                - message (str): User-friendly result message
        """
        try:
            if not dependency_task_ids:
                return {
                    'success': False,
                    'count': 0,
                    'message': 'No dependency tasks specified'
                }

            # Verify blocked task exists
            blocked_task = self.task_dao.get_by_id(task_id)
            if not blocked_task:
                return {
                    'success': False,
                    'count': 0,
                    'message': f'Task {task_id} not found'
                }

            # Add each dependency
            added_count = 0
            for blocking_task_id in dependency_task_ids:
                try:
                    dependency = Dependency(
                        blocked_task_id=task_id,
                        blocking_task_id=blocking_task_id
                    )
                    self.dependency_dao.create(dependency)
                    added_count += 1
                except ValueError:
                    # Circular dependency or duplicate - skip this one
                    continue

            # Record the postpone action
            if added_count > 0:
                self.record_postpone(
                    task_id,
                    PostponeReasonType.DEPENDENCY,
                    notes,
                    ActionTaken.ADDED_DEPENDENCY
                )

            plural = 'dependency' if added_count == 1 else 'dependencies'
            return {
                'success': True,
                'count': added_count,
                'message': f'{added_count} {plural} added, task is now blocked'
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
