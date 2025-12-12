"""
Enumerations for OneTaskAtATime data models.

Defines all enum types used in the task management system.
"""

from enum import Enum


class TaskState(Enum):
    """
    Represents the current state of a task in the GTD system.
    """
    ACTIVE = 'active'           # Actionable now, appears in Focus Mode
    DEFERRED = 'deferred'       # Not actionable until start_date
    DELEGATED = 'delegated'     # Assigned to someone else
    SOMEDAY = 'someday'         # May become relevant later
    COMPLETED = 'completed'     # Finished successfully
    TRASH = 'trash'             # Deemed unnecessary

    def __str__(self) -> str:
        return self.value


class PostponeReasonType(Enum):
    """
    Reasons why a user might postpone/delay a task.
    Used to capture context and create appropriate follow-up actions.
    """
    MULTIPLE_SUBTASKS = 'multiple_subtasks'  # Task needs to be broken down
    BLOCKER = 'blocker'                      # External blocker encountered
    DEPENDENCY = 'dependency'                # Waiting on another task
    NOT_READY = 'not_ready'                  # User not prepared/motivated
    OTHER = 'other'                          # Custom reason

    def __str__(self) -> str:
        return self.value


class ActionTaken(Enum):
    """
    Actions taken when a task is postponed.
    Tracks how the system helped resolve the postponement.
    """
    BROKE_DOWN = 'broke_down'                # Task split into subtasks
    CREATED_BLOCKER = 'created_blocker'      # New task created for blocker
    ADDED_DEPENDENCY = 'added_dependency'    # Linked to upstream task
    DEFERRED = 'deferred'                    # Set start_date for later
    DELEGATED = 'delegated'                  # Assigned to someone else
    MOVED_SOMEDAY = 'moved_someday'          # Moved to someday/maybe
    NONE = 'none'                            # No specific action

    def __str__(self) -> str:
        return self.value


class Priority(Enum):
    """
    Base priority levels for tasks (before adjustments).
    """
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    def __str__(self) -> str:
        return self.name.capitalize()
