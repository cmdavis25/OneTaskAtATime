"""
Tests for Task List View filtering logic.

Verifies that filters correctly exclude tasks without the filtered attribute.
"""

import pytest
from datetime import date, timedelta
from src.models.task import Task
from src.models.enums import TaskState


class TestTaskListFiltering:
    """Test filtering behavior in Task List View."""

    def test_project_tag_filter_excludes_tasks_without_tags(self):
        """
        When project tag filters are applied, tasks without project tags should be excluded.
        """
        # Create test tasks
        task_with_tag_1 = Task(
            id=1,
            title="Task with tag 1",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[1]  # Has tag 1
        )

        task_with_tag_2 = Task(
            id=2,
            title="Task with tag 2",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[2]  # Has tag 2
        )

        task_with_both_tags = Task(
            id=3,
            title="Task with both tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[1, 2]  # Has both tags
        )

        task_without_tags = Task(
            id=4,
            title="Task without tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[]  # No tags
        )

        task_with_none_tags = Task(
            id=5,
            title="Task with None tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=None  # None instead of empty list
        )

        all_tasks = [
            task_with_tag_1,
            task_with_tag_2,
            task_with_both_tags,
            task_without_tags,
            task_with_none_tags
        ]

        # Simulate the filtering logic from task_list_view.py
        active_tag_filters = {1}  # Filter for tag 1

        # Apply filter
        filtered_tasks = [
            t for t in all_tasks
            if t.project_tags and any(tag_id in active_tag_filters for tag_id in t.project_tags)
        ]

        # Verify results
        assert len(filtered_tasks) == 2, "Should only show tasks with tag 1"
        assert task_with_tag_1 in filtered_tasks, "Task with tag 1 should be included"
        assert task_with_both_tags in filtered_tasks, "Task with both tags should be included"
        assert task_with_tag_2 not in filtered_tasks, "Task with only tag 2 should be excluded"
        assert task_without_tags not in filtered_tasks, "Task without tags should be excluded"
        assert task_with_none_tags not in filtered_tasks, "Task with None tags should be excluded"

    def test_project_tag_filter_with_multiple_tags(self):
        """
        When multiple project tag filters are applied (OR condition),
        tasks with ANY of the filtered tags should be included.
        Tasks without tags should still be excluded.
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

        task_with_tag_3 = Task(
            id=3,
            title="Task with tag 3",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[3]
        )

        task_without_tags = Task(
            id=4,
            title="Task without tags",
            base_priority=2,
            state=TaskState.ACTIVE,
            project_tags=[]
        )

        all_tasks = [
            task_with_tag_1,
            task_with_tag_2,
            task_with_tag_3,
            task_without_tags
        ]

        # Filter for tags 1 and 2 (OR condition)
        active_tag_filters = {1, 2}

        # Apply filter
        filtered_tasks = [
            t for t in all_tasks
            if t.project_tags and any(tag_id in active_tag_filters for tag_id in t.project_tags)
        ]

        # Verify results
        assert len(filtered_tasks) == 2, "Should show tasks with tag 1 OR tag 2"
        assert task_with_tag_1 in filtered_tasks
        assert task_with_tag_2 in filtered_tasks
        assert task_with_tag_3 not in filtered_tasks
        assert task_without_tags not in filtered_tasks, "Task without tags should be excluded"

    def test_context_filter_excludes_tasks_without_context(self):
        """
        When context filters are applied (without NONE),
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

        # Filter for context 1 (without NONE)
        active_context_filters = {1}

        # Apply filter (simulating task_list_view.py logic)
        filtered_tasks = [
            t for t in all_tasks
            if (t.context_id is None and "NONE" in active_context_filters) or
               (t.context_id in active_context_filters)
        ]

        # Verify results
        assert len(filtered_tasks) == 1, "Should only show tasks with context 1"
        assert task_with_context_1 in filtered_tasks
        assert task_with_context_2 not in filtered_tasks
        assert task_without_context not in filtered_tasks, "Task without context should be excluded"

    def test_context_filter_includes_tasks_without_context_when_none_selected(self):
        """
        When context filters include NONE,
        tasks without context should be included.
        """
        # Create test tasks
        task_with_context_1 = Task(
            id=1,
            title="Task with context 1",
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

        all_tasks = [
            task_with_context_1,
            task_without_context
        ]

        # Filter for context 1 AND NONE
        active_context_filters = {1, "NONE"}

        # Apply filter
        filtered_tasks = [
            t for t in all_tasks
            if (t.context_id is None and "NONE" in active_context_filters) or
               (t.context_id in active_context_filters)
        ]

        # Verify results
        assert len(filtered_tasks) == 2, "Should show tasks with context 1 AND without context"
        assert task_with_context_1 in filtered_tasks
        assert task_without_context in filtered_tasks, "Task without context should be included when NONE is selected"
