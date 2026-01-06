"""Defer Task with Subtask Breakdown Command for undo/redo functionality."""

from datetime import date
from typing import Optional, List

from src.commands.base_command import Command
from src.models import Task, TaskState, Dependency
from src.database.task_dao import TaskDAO
from src.database.dependency_dao import DependencyDAO


class DeferWithSubtasksCommand(Command):
    """
    Compound command to defer a task and break it into subtasks.

    This command handles:
    1. Deferring the task (changing state to DEFERRED and setting start_date)
    2. Creating subtasks from complete Task objects
    3. Optionally moving the original task to TRASH
    4. If original is kept, creating dependencies so original is blocked by new tasks

    On undo, it:
    1. Restores the task's original state and start_date
    2. Deletes all created subtasks
    3. Removes any created dependencies
    """

    def __init__(
        self,
        task_dao: TaskDAO,
        dependency_dao: DependencyDAO,
        task_id: int,
        start_date: date,
        created_tasks: List[Task],
        delete_original: bool = False,
        reason: Optional[str] = None
    ):
        """
        Initialize the command.

        Args:
            task_dao: Task data access object
            dependency_dao: Dependency data access object
            task_id: ID of task being deferred
            start_date: Date when task should become actionable
            created_tasks: List of complete Task objects to create
            delete_original: If True, move original to TRASH; if False, keep it and add dependencies
            reason: Optional reason for deferring
        """
        self.task_dao = task_dao
        self.dependency_dao = dependency_dao
        self.task_id = task_id
        self.new_start_date = start_date
        self.created_tasks = created_tasks
        self.delete_original = delete_original
        self.reason = reason

        # State to restore on undo
        self.original_state: Optional[TaskState] = None
        self.original_start_date: Optional[date] = None
        self.task_title: Optional[str] = None
        self.created_subtask_ids: List[int] = []
        self.created_dependency_ids: List[int] = []  # Track dependencies for undo

    def execute(self) -> bool:
        """Execute the defer and subtask breakdown."""
        # Get the original task
        original = self.task_dao.get_by_id(self.task_id)
        if not original:
            return False

        # Save original state only on first execution (not on redo)
        if self.original_state is None:
            self.original_state = original.state
            self.original_start_date = original.start_date
            self.task_title = original.title

        # On redo, restore subtasks from TRASH back to ACTIVE and recreate dependencies
        if len(self.created_subtask_ids) > 0:
            for subtask_id in self.created_subtask_ids:
                subtask = self.task_dao.get_by_id(subtask_id)
                if subtask and subtask.state == TaskState.TRASH:
                    subtask.state = TaskState.ACTIVE
                    self.task_dao.update(subtask)

            # Recreate dependencies if original is kept
            if not self.delete_original:
                self.created_dependency_ids.clear()
                for subtask_id in self.created_subtask_ids:
                    # Original task is blocked by each subtask
                    dep = Dependency(
                        blocked_task_id=self.task_id,
                        blocking_task_id=subtask_id
                    )
                    created_dep = self.dependency_dao.create(dep)
                    if created_dep:
                        self.created_dependency_ids.append(created_dep.id)

        # On first execution, create subtasks from Task objects
        else:
            for task_obj in self.created_tasks:
                # Create the subtask in the database
                # Note: task_obj already has all its properties set from the dialog
                created_subtask = self.task_dao.create(task_obj)
                self.created_subtask_ids.append(created_subtask.id)

                # Copy project tags if they exist
                if task_obj.project_tags:
                    self.task_dao._add_project_tags(created_subtask.id, task_obj.project_tags)

            # Create dependencies if original is kept
            if not self.delete_original:
                for subtask_id in self.created_subtask_ids:
                    # Original task is blocked by each subtask
                    dep = Dependency(
                        blocked_task_id=self.task_id,
                        blocking_task_id=subtask_id
                    )
                    created_dep = self.dependency_dao.create(dep)
                    if created_dep:
                        self.created_dependency_ids.append(created_dep.id)

        # Update original task
        original.state = TaskState.TRASH if self.delete_original else TaskState.DEFERRED
        original.start_date = self.new_start_date

        return self.task_dao.update(original) is not None

    def undo(self) -> bool:
        """Undo the defer and subtask breakdown."""
        # Restore the task's original state
        task = self.task_dao.get_by_id(self.task_id)
        if not task:
            return False

        task.state = self.original_state
        task.start_date = self.original_start_date

        if not self.task_dao.update(task):
            return False

        # Remove all created dependencies
        for dep_id in self.created_dependency_ids:
            self.dependency_dao.delete(dep_id)
        self.created_dependency_ids.clear()

        # Move all created subtasks to TRASH
        for subtask_id in self.created_subtask_ids:
            subtask = self.task_dao.get_by_id(subtask_id)
            if subtask:
                subtask.state = TaskState.TRASH
                self.task_dao.update(subtask)

        return True

    def get_description(self) -> str:
        """Get a human-readable description of this command."""
        count = len(self.created_tasks)
        plural = 'subtask' if count == 1 else 'subtasks'
        if self.task_title:
            return f"Defer task with {count} {plural}: {self.task_title}"
        return f"Defer task with {count} {plural} (ID: {self.task_id})"
