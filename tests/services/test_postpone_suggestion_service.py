"""Tests for PostponeSuggestionService - pattern detection and suggestion generation."""

import pytest
from datetime import datetime
from src.services.postpone_suggestion_service import (
    PostponeSuggestionService,
    PostponeSuggestion,
    SuggestionType
)
from src.models.postpone_record import PostponeRecord
from src.models.enums import PostponeReasonType, ActionTaken, TaskState
from src.models.task import Task
from src.database.postpone_history_dao import PostponeHistoryDAO
from src.database.task_dao import TaskDAO


@pytest.fixture
def suggestion_service(test_db):
    """Create PostponeSuggestionService with temporary database."""
    return PostponeSuggestionService(test_db)


@pytest.fixture
def task_dao(test_db):
    """Create TaskDAO for test setup."""
    return TaskDAO(test_db)


@pytest.fixture
def postpone_dao(test_db):
    """Create PostponeHistoryDAO for test setup."""
    return PostponeHistoryDAO(test_db)


@pytest.fixture
def sample_task(task_dao):
    """Create a sample task for testing."""
    task = Task(
        title="Test Task",
        base_priority=2,
        state=TaskState.ACTIVE
    )
    return task_dao.create(task)


class TestPatternDetection:
    """Tests for postpone pattern detection logic."""

    def test_no_pattern_on_first_postpone(self, suggestion_service, sample_task):
        """First postpone should not trigger any pattern."""
        result = suggestion_service.check_for_patterns(sample_task.id)
        assert result is None

    def test_repeated_blocker_pattern(self, suggestion_service, sample_task, postpone_dao):
        """Two BLOCKER postpones should trigger repeated blocker pattern."""
        # Create two BLOCKER postpones
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes=f"Blocker note {i+1}",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert result.suggestion_type == SuggestionType.REPEATED_BLOCKER
        assert result.pattern_count == 2
        assert result.priority == 5  # High priority
        assert len(result.previous_notes) == 2
        assert "Blocker note 1" in result.previous_notes
        assert "Blocker note 2" in result.previous_notes

    def test_repeated_dependency_pattern(self, suggestion_service, sample_task, postpone_dao):
        """Two DEPENDENCY postpones should trigger repeated dependency pattern."""
        # Create two DEPENDENCY postpones
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.DEPENDENCY,
                reason_notes=f"Dependency note {i+1}",
                action_taken=ActionTaken.ADDED_DEPENDENCY,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert result.suggestion_type == SuggestionType.REPEATED_DEPENDENCY
        assert result.pattern_count == 2
        assert result.priority == 4

    def test_repeated_subtasks_pattern(self, suggestion_service, sample_task, postpone_dao):
        """Two MULTIPLE_SUBTASKS postpones should trigger repeated complexity pattern."""
        # Create two MULTIPLE_SUBTASKS postpones
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.MULTIPLE_SUBTASKS,
                reason_notes=f"Too complex {i+1}",
                action_taken=ActionTaken.NONE,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert result.suggestion_type == SuggestionType.REPEATED_SUBTASKS
        assert result.pattern_count == 2
        assert result.priority == 5

    def test_stale_task_pattern(self, suggestion_service, sample_task, postpone_dao):
        """Three total postpones should trigger stale task pattern."""
        # Create three postpones with different reasons
        reasons = [
            PostponeReasonType.NOT_READY,
            PostponeReasonType.OTHER,
            PostponeReasonType.NOT_READY
        ]

        for reason in reasons:
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=reason,
                reason_notes=f"Note for {reason.value}",
                action_taken=ActionTaken.NONE,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert result.suggestion_type == SuggestionType.STALE_TASK
        assert result.pattern_count == 3
        assert result.priority == 3
        assert len(result.previous_notes) == 3

    def test_pattern_priority_order(self, suggestion_service, sample_task, postpone_dao):
        """BLOCKER pattern should take precedence over STALE_TASK pattern."""
        # Create 2 BLOCKER postpones + 1 OTHER (3 total)
        # This meets both BLOCKER threshold (2) and STALE threshold (3)
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes=f"Blocker {i+1}",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.OTHER,
            reason_notes="Other reason",
            action_taken=ActionTaken.NONE,
            postponed_at=datetime.now()
        )
        postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        # BLOCKER pattern should be detected first (higher priority in code)
        assert result is not None
        assert result.suggestion_type == SuggestionType.REPEATED_BLOCKER


class TestSuggestionGeneration:
    """Tests for suggestion generation and formatting."""

    def test_suggestion_message_content(self, suggestion_service, sample_task, postpone_dao):
        """Suggestion messages should provide actionable advice."""
        # Create BLOCKER pattern
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes=f"Blocker {i+1}",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert "postponed" in result.message.lower()
        assert "blocker" in result.message.lower()
        assert "consider" in result.message.lower()  # Should provide recommendations

    def test_historical_context_formatting(self, suggestion_service, sample_task, postpone_dao):
        """Historical context should format notes in readable way."""
        # Create pattern with notes
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes=f"Blocker note {i+1}",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)
        context = result.get_historical_context()

        assert "Previous notes:" in context
        assert "1." in context
        assert "2." in context
        assert "Blocker note 1" in context
        assert "Blocker note 2" in context

    def test_historical_context_with_empty_notes(self):
        """Historical context should handle missing notes gracefully."""
        suggestion = PostponeSuggestion(
            task_id=1,
            suggestion_type=SuggestionType.REPEATED_BLOCKER,
            title="Test",
            message="Test message",
            pattern_count=2,
            previous_notes=[],
            previous_actions=[ActionTaken.NONE],
            priority=3
        )

        context = suggestion.get_historical_context()
        assert "No previous notes recorded" in context


class TestBulkSuggestions:
    """Tests for generating suggestions across multiple tasks."""

    def test_get_suggestions_for_all_tasks(self, suggestion_service, task_dao, postpone_dao):
        """Should generate suggestions for all tasks with patterns."""
        # Create 3 tasks with patterns
        task_ids = []
        for i in range(3):
            task = Task(
                title=f"Task {i+1}",
                base_priority=2,
                state=TaskState.ACTIVE
            )
            created_task = task_dao.create(task)
            task_ids.append(created_task.id)

            # Give each task a BLOCKER pattern
            for j in range(2):
                record = PostponeRecord(
                    task_id=created_task.id,
                    reason_type=PostponeReasonType.BLOCKER,
                    reason_notes=f"Blocker for task {i+1}",
                    action_taken=ActionTaken.CREATED_BLOCKER,
                    postponed_at=datetime.now()
                )
                postpone_dao.create(record)

        suggestions = suggestion_service.get_suggestions_for_all_tasks(limit=10)

        assert len(suggestions) == 3
        # All should be REPEATED_BLOCKER with priority 5
        assert all(s.suggestion_type == SuggestionType.REPEATED_BLOCKER for s in suggestions)
        assert all(s.priority == 5 for s in suggestions)

    def test_suggestions_sorted_by_priority(self, suggestion_service, task_dao, postpone_dao):
        """Suggestions should be sorted by priority (highest first)."""
        # Create task with low-priority stale pattern (priority 3)
        stale_task = Task(title="Stale Task", base_priority=2, state=TaskState.ACTIVE)
        stale_task = task_dao.create(stale_task)
        for i in range(3):
            record = PostponeRecord(
                task_id=stale_task.id,
                reason_type=PostponeReasonType.NOT_READY,
                reason_notes="Not ready",
                action_taken=ActionTaken.NONE,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        # Create task with high-priority blocker pattern (priority 5)
        blocker_task = Task(title="Blocker Task", base_priority=2, state=TaskState.ACTIVE)
        blocker_task = task_dao.create(blocker_task)
        for i in range(2):
            record = PostponeRecord(
                task_id=blocker_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes="Blocker",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        suggestions = suggestion_service.get_suggestions_for_all_tasks(limit=10)

        assert len(suggestions) == 2
        # Blocker pattern (priority 5) should come first
        assert suggestions[0].task_id == blocker_task.id
        assert suggestions[0].priority == 5
        assert suggestions[1].task_id == stale_task.id
        assert suggestions[1].priority == 3

    def test_suggestions_respect_limit(self, suggestion_service, task_dao, postpone_dao):
        """Should respect the limit parameter."""
        # Create 5 tasks with patterns
        for i in range(5):
            task = Task(title=f"Task {i+1}", base_priority=2, state=TaskState.ACTIVE)
            task = task_dao.create(task)

            for j in range(2):
                record = PostponeRecord(
                    task_id=task.id,
                    reason_type=PostponeReasonType.BLOCKER,
                    reason_notes="Blocker",
                    action_taken=ActionTaken.CREATED_BLOCKER,
                    postponed_at=datetime.now()
                )
                postpone_dao.create(record)

        suggestions = suggestion_service.get_suggestions_for_all_tasks(limit=3)
        assert len(suggestions) == 3


class TestUtilityMethods:
    """Tests for utility methods."""

    def test_get_task_title(self, suggestion_service, sample_task):
        """Should retrieve task title for display."""
        title = suggestion_service.get_task_title(sample_task.id)
        assert title == "Test Task"

    def test_get_task_title_for_nonexistent_task(self, suggestion_service):
        """Should handle nonexistent tasks gracefully."""
        title = suggestion_service.get_task_title(99999)
        assert "Task #99999" in title

    def test_should_show_reflection_dialog(self, suggestion_service, sample_task, postpone_dao):
        """Should return True when patterns exist."""
        # No pattern yet
        assert suggestion_service.should_show_reflection_dialog(sample_task.id) is False

        # Create pattern
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes="Blocker",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        # Now pattern exists
        assert suggestion_service.should_show_reflection_dialog(sample_task.id) is True


class TestThresholdBehavior:
    """Tests for threshold boundary conditions."""

    def test_blocker_threshold_minus_one(self, suggestion_service, sample_task, postpone_dao):
        """One BLOCKER postpone should NOT trigger pattern."""
        record = PostponeRecord(
            task_id=sample_task.id,
            reason_type=PostponeReasonType.BLOCKER,
            reason_notes="Blocker",
            action_taken=ActionTaken.CREATED_BLOCKER,
            postponed_at=datetime.now()
        )
        postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)
        assert result is None

    def test_stale_threshold_minus_one(self, suggestion_service, sample_task, postpone_dao):
        """Two total postpones should NOT trigger stale pattern."""
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.NOT_READY,
                reason_notes="Not ready",
                action_taken=ActionTaken.NONE,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)
        assert result is None

    def test_exact_threshold_triggers_pattern(self, suggestion_service, sample_task, postpone_dao):
        """Exactly meeting threshold should trigger pattern."""
        # Exactly 2 BLOCKER postpones
        for i in range(2):
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes="Blocker",
                action_taken=ActionTaken.CREATED_BLOCKER,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)
        assert result is not None
        assert result.suggestion_type == SuggestionType.REPEATED_BLOCKER


class TestActionTakenTracking:
    """Tests for tracking actions taken during postpones."""

    def test_tracks_all_action_types(self, suggestion_service, sample_task, postpone_dao):
        """Should track all action types in previous_actions."""
        actions = [
            ActionTaken.CREATED_BLOCKER,
            ActionTaken.ADDED_DEPENDENCY,
            ActionTaken.BROKE_DOWN,
            ActionTaken.NONE
        ]

        for action in actions:
            record = PostponeRecord(
                task_id=sample_task.id,
                reason_type=PostponeReasonType.BLOCKER,
                reason_notes="Test",
                action_taken=action,
                postponed_at=datetime.now()
            )
            postpone_dao.create(record)

        result = suggestion_service.check_for_patterns(sample_task.id)

        assert result is not None
        assert len(result.previous_actions) >= 2  # At least 2 to trigger pattern
        assert ActionTaken.CREATED_BLOCKER in result.previous_actions
