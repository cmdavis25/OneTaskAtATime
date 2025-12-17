"""
PostponeSuggestionService for OneTaskAtATime application.

Analyzes postpone history to detect patterns and generate actionable suggestions.
Helps users identify tasks that are repeatedly postponed for the same reasons.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from ..models.postpone_record import PostponeRecord
from ..models.enums import PostponeReasonType, ActionTaken
from ..database.postpone_history_dao import PostponeHistoryDAO
from ..database.task_dao import TaskDAO


class SuggestionType(Enum):
    """Types of suggestions based on postpone patterns."""
    REPEATED_BLOCKER = 'repeated_blocker'
    REPEATED_DEPENDENCY = 'repeated_dependency'
    REPEATED_SUBTASKS = 'repeated_subtasks'
    STALE_TASK = 'stale_task'


@dataclass
class PostponeSuggestion:
    """
    A suggestion generated from postpone pattern analysis.

    Attributes:
        task_id: ID of the task with the pattern
        suggestion_type: Category of suggestion
        title: Brief description of the pattern
        message: Detailed explanation and recommendation
        pattern_count: Number of occurrences of this pattern
        previous_notes: Historical notes from previous postpones
        previous_actions: Actions taken in previous postpones
        priority: 1-5 (5 = most urgent)
    """
    task_id: int
    suggestion_type: SuggestionType
    title: str
    message: str
    pattern_count: int
    previous_notes: List[str]
    previous_actions: List[ActionTaken]
    priority: int = 3

    def get_historical_context(self) -> str:
        """Format previous notes as readable context."""
        if not self.previous_notes:
            return "No previous notes recorded."

        context_lines = ["Previous notes:"]
        for i, note in enumerate(self.previous_notes, 1):
            if note:
                context_lines.append(f"  {i}. {note}")
            else:
                context_lines.append(f"  {i}. (no note)")

        return "\n".join(context_lines)


class PostponeSuggestionService:
    """
    Service for analyzing postpone patterns and generating suggestions.

    Triggers:
    - 2nd occurrence of BLOCKER reason → "Why do you keep hitting blockers?"
    - 2nd occurrence of DEPENDENCY reason → "Are these dependencies real?"
    - 2nd occurrence of SUBTASKS reason → "Maybe break it down now?"
    - 3rd total postpone (any reason) → "Consider moving to Someday/Maybe or Trash?"
    """

    # Pattern detection thresholds (trigger on Nth occurrence)
    BLOCKER_THRESHOLD = 2
    DEPENDENCY_THRESHOLD = 2
    SUBTASKS_THRESHOLD = 2
    STALE_TASK_THRESHOLD = 3  # Total postpones across all reasons

    def __init__(self, db_connection):
        """
        Initialize service with database connection.

        Args:
            db_connection: Database connection (raw sqlite3 or wrapper)
        """
        # Handle both raw connection and DatabaseConnection wrapper
        if hasattr(db_connection, 'get_connection'):
            self.db = db_connection.get_connection()
        else:
            self.db = db_connection

        self.postpone_dao = PostponeHistoryDAO(self.db)
        self.task_dao = TaskDAO(self.db)

    def check_for_patterns(self, task_id: int) -> Optional[PostponeSuggestion]:
        """
        Check if a task has postpone patterns that warrant intervention.

        This should be called BEFORE showing the postpone dialog to intercept
        with a reflection dialog if patterns are detected.

        Args:
            task_id: ID of task being postponed

        Returns:
            PostponeSuggestion if pattern detected, None otherwise
        """
        history = self.postpone_dao.get_by_task_id(task_id, limit=50)

        if not history:
            return None  # First postpone, no pattern yet

        # Count postpones by reason type
        reason_counts: Dict[PostponeReasonType, int] = {}
        notes_by_reason: Dict[PostponeReasonType, List[str]] = {}
        actions_by_reason: Dict[PostponeReasonType, List[ActionTaken]] = {}

        for record in history:
            reason = record.reason_type
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

            if reason not in notes_by_reason:
                notes_by_reason[reason] = []
            if record.reason_notes:
                notes_by_reason[reason].append(record.reason_notes)

            if reason not in actions_by_reason:
                actions_by_reason[reason] = []
            actions_by_reason[reason].append(record.action_taken)

        # Check for specific reason patterns (highest priority)

        # Pattern 1: Repeated BLOCKER
        if reason_counts.get(PostponeReasonType.BLOCKER, 0) >= self.BLOCKER_THRESHOLD:
            return PostponeSuggestion(
                task_id=task_id,
                suggestion_type=SuggestionType.REPEATED_BLOCKER,
                title="Repeated Blocker Pattern Detected",
                message=(
                    f"You've postponed this task {reason_counts[PostponeReasonType.BLOCKER]} times "
                    f"due to blockers. Are these blockers still relevant? Have you created tasks "
                    f"to address them?\n\n"
                    f"Consider: Are you avoiding this task? Is it too complex? "
                    f"Should it be broken down or moved to Someday/Maybe?"
                ),
                pattern_count=reason_counts[PostponeReasonType.BLOCKER],
                previous_notes=notes_by_reason.get(PostponeReasonType.BLOCKER, []),
                previous_actions=actions_by_reason.get(PostponeReasonType.BLOCKER, []),
                priority=5  # High priority - potential avoidance
            )

        # Pattern 2: Repeated DEPENDENCY
        if reason_counts.get(PostponeReasonType.DEPENDENCY, 0) >= self.DEPENDENCY_THRESHOLD:
            return PostponeSuggestion(
                task_id=task_id,
                suggestion_type=SuggestionType.REPEATED_DEPENDENCY,
                title="Repeated Dependency Pattern Detected",
                message=(
                    f"You've postponed this task {reason_counts[PostponeReasonType.DEPENDENCY]} times "
                    f"due to dependencies. Are these dependencies making progress? "
                    f"Are they properly tracked?\n\n"
                    f"Consider: Can you break the dependency? Can you work on part of this task "
                    f"while waiting? Should this task be deferred with a specific start date?"
                ),
                pattern_count=reason_counts[PostponeReasonType.DEPENDENCY],
                previous_notes=notes_by_reason.get(PostponeReasonType.DEPENDENCY, []),
                previous_actions=actions_by_reason.get(PostponeReasonType.DEPENDENCY, []),
                priority=4  # High priority - may need restructuring
            )

        # Pattern 3: Repeated SUBTASKS
        if reason_counts.get(PostponeReasonType.MULTIPLE_SUBTASKS, 0) >= self.SUBTASKS_THRESHOLD:
            return PostponeSuggestion(
                task_id=task_id,
                suggestion_type=SuggestionType.REPEATED_SUBTASKS,
                title="Repeated Complexity Pattern Detected",
                message=(
                    f"You've postponed this task {reason_counts[PostponeReasonType.MULTIPLE_SUBTASKS]} times "
                    f"because it's too complex. It's time to break it down!\n\n"
                    f"Consider: What are the individual steps? Which step should you tackle first? "
                    f"Breaking this down will make progress feel achievable."
                ),
                pattern_count=reason_counts[PostponeReasonType.MULTIPLE_SUBTASKS],
                previous_notes=notes_by_reason.get(PostponeReasonType.MULTIPLE_SUBTASKS, []),
                previous_actions=actions_by_reason.get(PostponeReasonType.MULTIPLE_SUBTASKS, []),
                priority=5  # High priority - clear action needed
            )

        # Pattern 4: Stale task (3+ total postpones across all reasons)
        total_postpones = len(history)
        if total_postpones >= self.STALE_TASK_THRESHOLD:
            # Collect all notes and actions
            all_notes = []
            all_actions = []
            for record in history:
                if record.reason_notes:
                    all_notes.append(record.reason_notes)
                all_actions.append(record.action_taken)

            return PostponeSuggestion(
                task_id=task_id,
                suggestion_type=SuggestionType.STALE_TASK,
                title="Frequently Postponed Task",
                message=(
                    f"This task has been postponed {total_postpones} times. "
                    f"It may be time to make a decision:\n\n"
                    f"• Move to Someday/Maybe if it's not urgent\n"
                    f"• Move to Trash if it's no longer relevant\n"
                    f"• Break it down if it's too complex\n"
                    f"• Defer with a specific date if timing isn't right\n\n"
                    f"Continuing to postpone creates mental clutter."
                ),
                pattern_count=total_postpones,
                previous_notes=all_notes,
                previous_actions=all_actions,
                priority=3  # Medium priority - needs decision
            )

        return None  # No patterns detected yet

    def get_suggestions_for_all_tasks(self, limit: int = 10) -> List[PostponeSuggestion]:
        """
        Generate suggestions for all tasks with postpone patterns.

        Args:
            limit: Maximum number of suggestions to return

        Returns:
            List of suggestions, sorted by priority (highest first)
        """
        suggestions = []

        # Get all tasks with postpone history
        # We'll use the DAO to get recent postpones and extract unique task IDs
        recent_postpones = self.postpone_dao.get_recent(limit=200)

        task_ids_seen = set()
        for record in recent_postpones:
            if record.task_id not in task_ids_seen:
                task_ids_seen.add(record.task_id)

                # Check for patterns on this task
                suggestion = self.check_for_patterns(record.task_id)
                if suggestion:
                    suggestions.append(suggestion)

                    if len(suggestions) >= limit:
                        break

        # Sort by priority (highest first), then by pattern count
        suggestions.sort(key=lambda s: (s.priority, s.pattern_count), reverse=True)

        return suggestions

    def get_task_title(self, task_id: int) -> str:
        """Get task title for display in suggestions."""
        task = self.task_dao.get_by_id(task_id)
        return task.title if task else f"Task #{task_id}"

    def should_show_reflection_dialog(self, task_id: int) -> bool:
        """
        Determine if reflection dialog should be shown before postpone dialog.

        Returns True if any pattern is detected that warrants reflection.
        """
        return self.check_for_patterns(task_id) is not None
