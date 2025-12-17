"""
Tests for Focus Mode filtering logic in ranking.py.

Verifies that get_actionable_tasks correctly filters based on context and project tags.
"""

import pytest
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState
from src.algorithms.ranking import get_actionable_tasks


class TestFocusModeFiltering:
    """Test filtering behavior in Focus Mode (ranking.py)."""

    def test_tag_filter_excludes_tasks_without_tags(self):
        """
        When tag filters are applied in Focus Mode,
        tasks without tags should be excluded.
        """
        # Create test tasks
        task_with_tag_1 = Task(
            id=1,
            title="Task with tag 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[1]
        )

        task_with_tag_2 = Task(
            id=2,
            title="Task with tag 2",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[2]
        )

        task_without_tags = Task(
            id=3,
            title="Task without tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[]
        )

        task_with_none_tags = Task(
            id=4,
            title="Task with None tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=None
        )

        all_tasks = [
            task_with_tag_1,
            task_with_tag_2,
            task_without_tags,
            task_with_none_tags
        ]

        # Apply tag filter for tag 1
        tag_filters = {1}
        actionable = get_actionable_tasks(all_tasks, tag_filters=tag_filters)

        # Verify results
        assert len(actionable) == 1, "Should only show tasks with tag 1"
        assert task_with_tag_1 in actionable
        assert task_with_tag_2 not in actionable
        assert task_without_tags not in actionable, "Task without tags should be excluded"
        assert task_with_none_tags not in actionable, "Task with None tags should be excluded"

    def test_context_filter_excludes_tasks_without_context(self):
        """
        When context filter is applied in Focus Mode (without NONE),
        tasks without context should be excluded.
        """
        # Create test tasks
        task_with_context_1 = Task(
            id=1,
            title="Task with context 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=1
        )

        task_with_context_2 = Task(
            id=2,
            title="Task with context 2",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=2
        )

        task_without_context = Task(
            id=3,
            title="Task without context",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=None
        )

        all_tasks = [
            task_with_context_1,
            task_with_context_2,
            task_without_context
        ]

        # Apply context filter for context 1
        context_filter = 1
        actionable = get_actionable_tasks(all_tasks, context_filter=context_filter)

        # Verify results
        assert len(actionable) == 1, "Should only show tasks with context 1"
        assert task_with_context_1 in actionable
        assert task_with_context_2 not in actionable
        assert task_without_context not in actionable, "Task without context should be excluded"

    def test_context_filter_includes_tasks_without_context_when_none_selected(self):
        """
        When context filter is set to NONE in Focus Mode,
        only tasks without context should be shown.
        """
        # Create test tasks
        task_with_context = Task(
            id=1,
            title="Task with context",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=1
        )

        task_without_context = Task(
            id=2,
            title="Task without context",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=None
        )

        all_tasks = [task_with_context, task_without_context]

        # Apply NONE context filter
        context_filter = "NONE"
        actionable = get_actionable_tasks(all_tasks, context_filter=context_filter)

        # Verify results
        assert len(actionable) == 1, "Should only show tasks without context"
        assert task_without_context in actionable
        assert task_with_context not in actionable

    def test_combined_filters(self):
        """
        When both context and tag filters are applied,
        tasks must match both to be included.
        """
        # Create test tasks
        task_match_both = Task(
            id=1,
            title="Match both",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=1,
            project_tags=[1]
        )

        task_match_context_only = Task(
            id=2,
            title="Match context only",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=1,
            project_tags=[2]
        )

        task_match_tag_only = Task(
            id=3,
            title="Match tag only",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=2,
            project_tags=[1]
        )

        task_match_neither = Task(
            id=4,
            title="Match neither",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=2,
            project_tags=[2]
        )

        task_no_tags = Task(
            id=5,
            title="No tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            context_id=1,
            project_tags=[]
        )

        all_tasks = [
            task_match_both,
            task_match_context_only,
            task_match_tag_only,
            task_match_neither,
            task_no_tags
        ]

        # Apply both filters
        context_filter = 1
        tag_filters = {1}
        actionable = get_actionable_tasks(
            all_tasks,
            context_filter=context_filter,
            tag_filters=tag_filters
        )

        # Verify results
        assert len(actionable) == 1, "Should only show tasks matching both filters"
        assert task_match_both in actionable
        assert task_match_context_only not in actionable, "Wrong tag"
        assert task_match_tag_only not in actionable, "Wrong context"
        assert task_match_neither not in actionable, "Wrong both"
        assert task_no_tags not in actionable, "Has context but no tags"
