"""
Service for managing task history and audit logging.

Provides high-level operations for recording and retrieving task history events.
"""

import json
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from src.models.task import Task
from src.models.task_history_event import TaskHistoryEvent
from src.models.enums import TaskState, TaskEventType, Priority
from src.database.task_history_dao import TaskHistoryDAO


class TaskHistoryService:
    """
    Service for managing task history and audit logging.

    Provides methods to record various task events and retrieve
    formatted history timelines.
    """

    def __init__(self, history_dao: TaskHistoryDAO):
        """
        Initialize the TaskHistoryService.

        Args:
            history_dao: TaskHistoryDAO instance for database access
        """
        self.history_dao = history_dao

    def record_task_created(self, task: Task, changed_by: str = "user") -> TaskHistoryEvent:
        """
        Record a task creation event.

        Args:
            task: The created task
            changed_by: Who created the task (user, system, scheduler)

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task.id,
            event_type=TaskEventType.CREATED,
            new_value=self._serialize_task_snapshot(task),
            changed_by=changed_by,
            context_data=json.dumps({
                "title": task.title,
                "priority": task.base_priority,
                "state": task.state.value
            })
        )
        return self.history_dao.create_event(event)

    def record_task_edited(self, task: Task, old_task: Task, changed_by: str = "user") -> Optional[TaskHistoryEvent]:
        """
        Record a task edit event with field-level changes.

        Args:
            task: The updated task
            old_task: The task before updates
            changed_by: Who edited the task

        Returns:
            The created TaskHistoryEvent, or None if no changes detected
        """
        changes = self._detect_changes(old_task, task)
        if not changes:
            return None

        event = TaskHistoryEvent(
            task_id=task.id,
            event_type=TaskEventType.EDITED,
            old_value=self._serialize_task_snapshot(old_task),
            new_value=self._serialize_task_snapshot(task),
            changed_by=changed_by,
            context_data=json.dumps(changes)
        )
        return self.history_dao.create_event(event)

    def record_state_change(
        self,
        task: Task,
        old_state: TaskState,
        new_state: TaskState,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a task state change event.

        Args:
            task: The task whose state changed
            old_state: Previous state
            new_state: New state
            changed_by: Who changed the state

        Returns:
            The created TaskHistoryEvent
        """
        # Map state changes to specific event types
        event_type_map = {
            TaskState.COMPLETED: TaskEventType.COMPLETED,
            TaskState.DEFERRED: TaskEventType.DEFERRED,
            TaskState.DELEGATED: TaskEventType.DELEGATED,
            TaskState.SOMEDAY: TaskEventType.MOVED_TO_SOMEDAY,
            TaskState.TRASH: TaskEventType.MOVED_TO_TRASH,
            TaskState.ACTIVE: TaskEventType.ACTIVATED
        }

        event_type = event_type_map.get(new_state, TaskEventType.EDITED)

        event = TaskHistoryEvent(
            task_id=task.id,
            event_type=event_type,
            old_value=old_state.value,
            new_value=new_state.value,
            changed_by=changed_by,
            context_data=json.dumps({
                "from": old_state.value,
                "to": new_state.value
            })
        )
        return self.history_dao.create_event(event)

    def record_priority_change(
        self,
        task: Task,
        old_priority: int,
        new_priority: int,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a priority change event.

        Args:
            task: The task whose priority changed
            old_priority: Previous base priority (1, 2, or 3)
            new_priority: New base priority (1, 2, or 3)
            changed_by: Who changed the priority

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task.id,
            event_type=TaskEventType.PRIORITY_CHANGED,
            old_value=str(old_priority),
            new_value=str(new_priority),
            changed_by=changed_by,
            context_data=json.dumps({
                "old_priority": old_priority,
                "new_priority": new_priority,
                "old_priority_name": Priority(old_priority).name,
                "new_priority_name": Priority(new_priority).name
            })
        )
        return self.history_dao.create_event(event)

    def record_due_date_change(
        self,
        task: Task,
        old_date: Optional[date],
        new_date: Optional[date],
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a due date change event.

        Args:
            task: The task whose due date changed
            old_date: Previous due date (None if not set)
            new_date: New due date (None if removed)
            changed_by: Who changed the due date

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task.id,
            event_type=TaskEventType.DUE_DATE_CHANGED,
            old_value=old_date.isoformat() if old_date else None,
            new_value=new_date.isoformat() if new_date else None,
            changed_by=changed_by,
            context_data=json.dumps({
                "old_date": old_date.isoformat() if old_date else None,
                "new_date": new_date.isoformat() if new_date else None
            })
        )
        return self.history_dao.create_event(event)

    def record_dependency_added(
        self,
        task_id: int,
        dependency_id: int,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a dependency added event.

        Args:
            task_id: ID of the blocked task
            dependency_id: ID of the blocking task
            changed_by: Who added the dependency

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task_id,
            event_type=TaskEventType.DEPENDENCY_ADDED,
            new_value=str(dependency_id),
            changed_by=changed_by,
            context_data=json.dumps({"blocking_task_id": dependency_id})
        )
        return self.history_dao.create_event(event)

    def record_dependency_removed(
        self,
        task_id: int,
        dependency_id: int,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a dependency removed event.

        Args:
            task_id: ID of the blocked task
            dependency_id: ID of the blocking task that was removed
            changed_by: Who removed the dependency

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task_id,
            event_type=TaskEventType.DEPENDENCY_REMOVED,
            old_value=str(dependency_id),
            changed_by=changed_by,
            context_data=json.dumps({"blocking_task_id": dependency_id})
        )
        return self.history_dao.create_event(event)

    def record_tag_change(
        self,
        task_id: int,
        tag_name: str,
        added: bool,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a tag added or removed event.

        Args:
            task_id: ID of the task
            tag_name: Name of the tag
            added: True if tag was added, False if removed
            changed_by: Who changed the tag

        Returns:
            The created TaskHistoryEvent
        """
        event_type = TaskEventType.TAG_ADDED if added else TaskEventType.TAG_REMOVED

        event = TaskHistoryEvent(
            task_id=task_id,
            event_type=event_type,
            new_value=tag_name if added else None,
            old_value=tag_name if not added else None,
            changed_by=changed_by,
            context_data=json.dumps({"tag_name": tag_name})
        )
        return self.history_dao.create_event(event)

    def record_context_changed(
        self,
        task_id: int,
        old_context_id: Optional[int],
        new_context_id: Optional[int],
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a context change event.

        Args:
            task_id: ID of the task
            old_context_id: Previous context ID (None if not set)
            new_context_id: New context ID (None if removed)
            changed_by: Who changed the context

        Returns:
            The created TaskHistoryEvent
        """
        event = TaskHistoryEvent(
            task_id=task_id,
            event_type=TaskEventType.CONTEXT_CHANGED,
            old_value=str(old_context_id) if old_context_id else None,
            new_value=str(new_context_id) if new_context_id else None,
            changed_by=changed_by,
            context_data=json.dumps({
                "old_context_id": old_context_id,
                "new_context_id": new_context_id
            })
        )
        return self.history_dao.create_event(event)

    def record_comparison_result(
        self,
        task_id: int,
        won: bool,
        opponent_id: int,
        old_elo: float,
        new_elo: float,
        changed_by: str = "user"
    ) -> TaskHistoryEvent:
        """
        Record a comparison result event.

        Args:
            task_id: ID of the task that was compared
            won: True if this task won, False if lost
            opponent_id: ID of the opponent task
            old_elo: Elo rating before comparison
            new_elo: Elo rating after comparison
            changed_by: Who performed the comparison

        Returns:
            The created TaskHistoryEvent
        """
        event_type = TaskEventType.COMPARISON_WON if won else TaskEventType.COMPARISON_LOST

        event = TaskHistoryEvent(
            task_id=task_id,
            event_type=event_type,
            old_value=str(old_elo),
            new_value=str(new_elo),
            changed_by=changed_by,
            context_data=json.dumps({
                "opponent_id": opponent_id,
                "won": won,
                "old_elo": old_elo,
                "new_elo": new_elo,
                "elo_change": new_elo - old_elo
            })
        )
        return self.history_dao.create_event(event)

    def get_timeline(self, task_id: int, limit: int = 100) -> List[TaskHistoryEvent]:
        """
        Get the complete timeline of events for a task.

        Args:
            task_id: ID of the task
            limit: Maximum number of events to retrieve

        Returns:
            List of TaskHistoryEvent objects in chronological order
        """
        return self.history_dao.get_by_task_id(task_id, limit)

    def get_formatted_summary(self, event: TaskHistoryEvent) -> str:
        """
        Get a human-readable summary of a history event.

        Args:
            event: The TaskHistoryEvent to format

        Returns:
            Formatted string describing the event
        """
        return self._format_event_message(event)

    def _serialize_task_snapshot(self, task: Task) -> str:
        """
        Serialize a task to JSON for storage in history.

        Args:
            task: Task to serialize

        Returns:
            JSON string representation of task
        """
        snapshot = {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "base_priority": task.base_priority,
            "elo_rating": task.elo_rating,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "state": task.state.value,
            "context_id": task.context_id,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        return json.dumps(snapshot)

    def _detect_changes(self, old_task: Task, new_task: Task) -> Dict[str, Any]:
        """
        Detect which fields changed between two task versions.

        Args:
            old_task: Task before changes
            new_task: Task after changes

        Returns:
            Dictionary of changed fields with old and new values
        """
        changes = {}

        if old_task.title != new_task.title:
            changes["title"] = {"old": old_task.title, "new": new_task.title}

        if old_task.description != new_task.description:
            changes["description"] = {"old": old_task.description, "new": new_task.description}

        if old_task.base_priority != new_task.base_priority:
            changes["base_priority"] = {"old": old_task.base_priority, "new": new_task.base_priority}

        if old_task.due_date != new_task.due_date:
            changes["due_date"] = {
                "old": old_task.due_date.isoformat() if old_task.due_date else None,
                "new": new_task.due_date.isoformat() if new_task.due_date else None
            }

        if old_task.context_id != new_task.context_id:
            changes["context_id"] = {"old": old_task.context_id, "new": new_task.context_id}

        return changes

    def _format_event_message(self, event: TaskHistoryEvent) -> str:
        """
        Format a history event as a human-readable message.

        Args:
            event: The TaskHistoryEvent to format

        Returns:
            Formatted message string
        """
        if event.event_type == TaskEventType.CREATED:
            try:
                context = json.loads(event.context_data) if event.context_data else {}
                priority_name = Priority(context.get("priority", 2)).name.capitalize()
                return f"Task created with priority {priority_name}"
            except (json.JSONDecodeError, ValueError):
                return "Task created"

        elif event.event_type == TaskEventType.EDITED:
            try:
                changes = json.loads(event.context_data) if event.context_data else {}
                if not changes:
                    return "Task edited"

                change_list = []
                for field, values in changes.items():
                    if field == "title":
                        change_list.append(f"title updated")
                    elif field == "description":
                        change_list.append(f"description updated")
                    elif field == "base_priority":
                        old_name = Priority(values["old"]).name.capitalize()
                        new_name = Priority(values["new"]).name.capitalize()
                        change_list.append(f"priority changed from {old_name} to {new_name}")
                    else:
                        change_list.append(f"{field} changed")

                return "Task edited: " + ", ".join(change_list)
            except (json.JSONDecodeError, ValueError):
                return "Task edited"

        elif event.event_type == TaskEventType.COMPLETED:
            return "Task completed"

        elif event.event_type == TaskEventType.DEFERRED:
            return "Task deferred"

        elif event.event_type == TaskEventType.DELEGATED:
            return "Task delegated"

        elif event.event_type == TaskEventType.ACTIVATED:
            return "Task activated"

        elif event.event_type == TaskEventType.MOVED_TO_SOMEDAY:
            return "Moved to Someday/Maybe"

        elif event.event_type == TaskEventType.MOVED_TO_TRASH:
            return "Moved to trash"

        elif event.event_type == TaskEventType.RESTORED:
            return "Task restored"

        elif event.event_type == TaskEventType.PRIORITY_CHANGED:
            try:
                context = json.loads(event.context_data) if event.context_data else {}
                old_name = context.get("old_priority_name", "")
                new_name = context.get("new_priority_name", "")
                return f"Priority changed from {old_name} to {new_name}"
            except (json.JSONDecodeError, ValueError):
                return f"Priority changed from {event.old_value} to {event.new_value}"

        elif event.event_type == TaskEventType.DUE_DATE_CHANGED:
            old_date = event.old_value if event.old_value else "none"
            new_date = event.new_value if event.new_value else "none"
            return f"Due date changed from {old_date} to {new_date}"

        elif event.event_type == TaskEventType.DEPENDENCY_ADDED:
            return f"Dependency added (blocking task ID: {event.new_value})"

        elif event.event_type == TaskEventType.DEPENDENCY_REMOVED:
            return f"Dependency removed (blocking task ID: {event.old_value})"

        elif event.event_type == TaskEventType.TAG_ADDED:
            return f"Tag added: {event.new_value}"

        elif event.event_type == TaskEventType.TAG_REMOVED:
            return f"Tag removed: {event.old_value}"

        elif event.event_type == TaskEventType.CONTEXT_CHANGED:
            old_ctx = event.old_value if event.old_value and event.old_value != "None" else "none"
            new_ctx = event.new_value if event.new_value and event.new_value != "None" else "none"
            return f"Context changed from {old_ctx} to {new_ctx}"

        elif event.event_type == TaskEventType.COMPARISON_WON:
            try:
                context = json.loads(event.context_data) if event.context_data else {}
                elo_change = context.get("elo_change", 0)
                return f"Won comparison (Elo +{elo_change:.1f})"
            except (json.JSONDecodeError, ValueError):
                return "Won comparison"

        elif event.event_type == TaskEventType.COMPARISON_LOST:
            try:
                context = json.loads(event.context_data) if event.context_data else {}
                elo_change = context.get("elo_change", 0)
                return f"Lost comparison (Elo {elo_change:.1f})"
            except (json.JSONDecodeError, ValueError):
                return "Lost comparison"

        else:
            return f"Event: {event.event_type.value}"
