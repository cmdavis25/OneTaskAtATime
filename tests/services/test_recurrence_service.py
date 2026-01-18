"""
Unit tests for RecurrenceService.

Tests recurring task logic including:
- Next occurrence date calculation
- Task cloning for next occurrence
- Recurrence continuation conditions
- Shared Elo handling
- Pattern formatting
"""

import pytest
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState
from src.models.recurrence_pattern import RecurrencePattern, RecurrenceType
from src.services.recurrence_service import RecurrenceService


class TestCalculateNextOccurrenceDate:
    """Test next occurrence date calculations."""

    def test_daily_pattern_single_day(self):
        """Test daily pattern with interval of 1."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=1)
        from_date = date(2024, 1, 15)

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        assert result == date(2024, 1, 16)

    def test_daily_pattern_multiple_days(self):
        """Test daily pattern with interval > 1."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=3)
        from_date = date(2024, 1, 15)

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        assert result == date(2024, 1, 18)

    def test_weekly_pattern_no_specific_days(self):
        """Test weekly pattern without specific days."""
        pattern = RecurrencePattern(type=RecurrenceType.WEEKLY, interval=1)
        from_date = date(2024, 1, 15)  # Monday

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        assert result == date(2024, 1, 22)  # Next Monday

    def test_weekly_pattern_with_specific_days(self):
        """Test weekly pattern with specific days of week."""
        # Every week on Tuesday (1) and Thursday (3)
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            interval=1,
            days_of_week=[1, 3]
        )
        from_date = date(2024, 1, 15)  # Monday

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        # Next occurrence should be Tuesday Jan 16
        assert result == date(2024, 1, 16)

    def test_weekly_pattern_next_week(self):
        """Test weekly pattern when next occurrence is next week."""
        # Every week on Monday (0)
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            interval=1,
            days_of_week=[0]
        )
        from_date = date(2024, 1, 15)  # Monday

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        # Next Monday is Jan 22 (current day doesn't count)
        assert result == date(2024, 1, 22)

    def test_monthly_pattern_day_of_month(self):
        """Test monthly pattern with specific day of month."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY,
            interval=1,
            day_of_month=15
        )
        from_date = date(2024, 1, 15)

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        assert result == date(2024, 2, 15)

    def test_monthly_pattern_end_of_short_month(self):
        """Test monthly pattern adjusts for months with fewer days."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY,
            interval=1,
            day_of_month=31
        )
        from_date = date(2024, 1, 31)

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        # February 2024 has 29 days (leap year)
        assert result == date(2024, 2, 29)

    def test_yearly_pattern(self):
        """Test yearly pattern."""
        pattern = RecurrencePattern(type=RecurrenceType.YEARLY, interval=1)
        from_date = date(2024, 3, 15)

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        assert result == date(2025, 3, 15)

    def test_yearly_pattern_leap_year(self):
        """Test yearly pattern handles leap year to non-leap year."""
        pattern = RecurrencePattern(type=RecurrenceType.YEARLY, interval=1)
        from_date = date(2024, 2, 29)  # Leap year

        result = RecurrenceService.calculate_next_occurrence_date(pattern, from_date)

        # 2025 is not a leap year, so Feb 28
        assert result == date(2025, 2, 28)


class TestShouldContinueRecurrence:
    """Test recurrence continuation logic."""

    def test_non_recurring_task_returns_false(self):
        """Test that non-recurring task returns False."""
        task = Task(title="One-time Task", base_priority=2, is_recurring=False)

        result = RecurrenceService.should_continue_recurrence(task, date.today())

        assert result is False

    def test_recurring_task_without_end_date_continues(self):
        """Test that recurring task without end date continues."""
        task = Task(
            title="Recurring Task",
            base_priority=2,
            is_recurring=True,
            recurrence_end_date=None
        )

        result = RecurrenceService.should_continue_recurrence(task, date.today())

        assert result is True

    def test_recurring_task_before_end_date_continues(self):
        """Test that recurring task before end date continues."""
        task = Task(
            title="Recurring Task",
            base_priority=2,
            is_recurring=True,
            recurrence_end_date=date.today() + timedelta(days=30)
        )

        result = RecurrenceService.should_continue_recurrence(task, date.today())

        assert result is True

    def test_recurring_task_at_end_date_stops(self):
        """Test that recurring task at end date stops."""
        end_date = date.today()
        task = Task(
            title="Recurring Task",
            base_priority=2,
            is_recurring=True,
            recurrence_end_date=end_date
        )

        result = RecurrenceService.should_continue_recurrence(task, end_date)

        assert result is False

    def test_recurring_task_past_end_date_stops(self):
        """Test that recurring task past end date stops."""
        end_date = date.today() - timedelta(days=1)
        task = Task(
            title="Recurring Task",
            base_priority=2,
            is_recurring=True,
            recurrence_end_date=end_date
        )

        result = RecurrenceService.should_continue_recurrence(task, date.today())

        assert result is False


class TestCloneTaskForNextOccurrence:
    """Test task cloning for next occurrence."""

    def test_clone_basic_properties(self):
        """Test that basic properties are cloned correctly."""
        original = Task(
            title="Original Task",
            description="Test description",
            base_priority=2,
            due_date=date(2024, 1, 15),
            state=TaskState.COMPLETED,
            is_recurring=True
        )
        original.id = 1

        next_due = date(2024, 1, 22)
        cloned = RecurrenceService.clone_task_for_next_occurrence(original, next_due)

        assert cloned.title == original.title
        assert cloned.description == original.description
        assert cloned.base_priority == original.base_priority
        assert cloned.due_date == next_due
        assert cloned.state == TaskState.ACTIVE  # Always starts active
        assert cloned.is_recurring == original.is_recurring

    def test_clone_sets_parent_id(self):
        """Test that clone sets recurrence_parent_id."""
        original = Task(
            title="Parent Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True
        )
        original.id = 5

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        # If original has no parent, it becomes the parent
        assert cloned.recurrence_parent_id == 5

    def test_clone_preserves_parent_chain(self):
        """Test that clone preserves existing parent chain."""
        original = Task(
            title="Child Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            recurrence_parent_id=1  # Already has a parent
        )
        original.id = 10

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        # Should keep original parent, not use current task as parent
        assert cloned.recurrence_parent_id == 1

    def test_clone_increments_occurrence_count(self):
        """Test that clone increments occurrence count."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            occurrence_count=3
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        assert cloned.occurrence_count == 4

    def test_clone_with_shared_elo(self):
        """Test cloning with shared Elo rating."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            share_elo_rating=True,
            elo_rating=1600.0,
            comparison_count=10
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(
            original,
            date(2024, 1, 22),
            shared_elo=1650.0,
            shared_comparison_count=12
        )

        # Should use shared values when share_elo_rating is True
        assert cloned.elo_rating == 1650.0
        assert cloned.comparison_count == 12
        assert cloned.shared_elo_rating == 1650.0
        assert cloned.shared_comparison_count == 12

    def test_clone_without_shared_elo(self):
        """Test cloning without shared Elo (independent rating)."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            share_elo_rating=False,
            elo_rating=1600.0,
            comparison_count=10
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(
            original,
            date(2024, 1, 22),
            shared_elo=1650.0,
            shared_comparison_count=12
        )

        # Should reset to defaults when share_elo_rating is False
        assert cloned.elo_rating == 1500.0
        assert cloned.comparison_count == 0

    def test_clone_copies_context(self):
        """Test that clone copies context."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            context_id=5
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        assert cloned.context_id == 5

    def test_clone_copies_recurrence_pattern(self):
        """Test that clone copies recurrence pattern."""
        pattern = RecurrencePattern(type=RecurrenceType.WEEKLY, interval=2)
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            recurrence_pattern=pattern.to_json()
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        assert cloned.recurrence_pattern == original.recurrence_pattern

    def test_clone_copies_end_date(self):
        """Test that clone copies recurrence end date."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            recurrence_end_date=date(2024, 12, 31)
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        assert cloned.recurrence_end_date == date(2024, 12, 31)

    def test_clone_copies_project_tags(self):
        """Test that clone copies project tags."""
        original = Task(
            title="Task",
            base_priority=2,
            due_date=date(2024, 1, 15),
            is_recurring=True,
            project_tags=[1, 2, 3]
        )
        original.id = 1

        cloned = RecurrenceService.clone_task_for_next_occurrence(original, date(2024, 1, 22))

        assert cloned.project_tags == [1, 2, 3]
        # Ensure it's a copy, not the same list
        assert cloned.project_tags is not original.project_tags


class TestGetSharedEloValues:
    """Test shared Elo value retrieval."""

    def test_non_shared_returns_none(self):
        """Test that non-shared task returns None values."""
        task = Task(
            title="Task",
            base_priority=2,
            share_elo_rating=False,
            elo_rating=1600.0
        )

        elo, count = RecurrenceService.get_shared_elo_values(task)

        assert elo is None
        assert count is None

    def test_shared_with_pool_values(self):
        """Test shared task with existing pool values."""
        task = Task(
            title="Task",
            base_priority=2,
            share_elo_rating=True,
            elo_rating=1600.0,
            comparison_count=10,
            shared_elo_rating=1650.0,
            shared_comparison_count=15
        )

        elo, count = RecurrenceService.get_shared_elo_values(task)

        assert elo == 1650.0
        assert count == 15

    def test_shared_without_pool_uses_current(self):
        """Test shared task without pool values uses current values."""
        task = Task(
            title="Task",
            base_priority=2,
            share_elo_rating=True,
            elo_rating=1600.0,
            comparison_count=10,
            shared_elo_rating=None,
            shared_comparison_count=None
        )

        elo, count = RecurrenceService.get_shared_elo_values(task)

        assert elo == 1600.0
        assert count == 10


class TestFormatRecurrencePattern:
    """Test pattern formatting."""

    def test_format_daily_single(self):
        """Test formatting daily pattern with interval 1."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=1)

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert result == "Every day"

    def test_format_daily_multiple(self):
        """Test formatting daily pattern with interval > 1."""
        pattern = RecurrencePattern(type=RecurrenceType.DAILY, interval=3)

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert result == "Every 3 days"

    def test_format_weekly_no_days(self):
        """Test formatting weekly pattern without specific days."""
        pattern = RecurrencePattern(type=RecurrenceType.WEEKLY, interval=1)

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert result == "Every week"

    def test_format_weekly_with_days(self):
        """Test formatting weekly pattern with specific days."""
        pattern = RecurrencePattern(
            type=RecurrenceType.WEEKLY,
            interval=1,
            days_of_week=[0, 2, 4]  # Mon, Wed, Fri
        )

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert "Mon" in result
        assert "Wed" in result
        assert "Fri" in result

    def test_format_monthly(self):
        """Test formatting monthly pattern."""
        pattern = RecurrencePattern(
            type=RecurrenceType.MONTHLY,
            interval=1,
            day_of_month=15
        )

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert "15th" in result
        assert "Monthly" in result

    def test_format_yearly(self):
        """Test formatting yearly pattern."""
        pattern = RecurrencePattern(type=RecurrenceType.YEARLY, interval=1)

        result = RecurrenceService.format_recurrence_pattern(pattern.to_json())

        assert result == "Every year"

    def test_format_empty_pattern(self):
        """Test formatting empty/null pattern."""
        result = RecurrenceService.format_recurrence_pattern(None)

        assert result == ""

    def test_format_invalid_pattern(self):
        """Test formatting invalid JSON pattern."""
        result = RecurrenceService.format_recurrence_pattern("not valid json")

        assert result == "Invalid pattern"
