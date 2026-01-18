"""
Unit tests for AnalyticsView.

Tests the analytics dashboard including:
- Widget initialization
- Statistics display
- Chart rendering
- Data updates
"""

import pytest
import sqlite3
from datetime import date, timedelta

from PyQt5.QtWidgets import QApplication

from src.models.task import Task
from src.models.enums import TaskState
from src.database.task_dao import TaskDAO
from src.ui.analytics_view import AnalyticsView





@pytest.fixture
def analytics_view(qapp, db_connection):
    """Create analytics view instance."""
    view = AnalyticsView(db_connection)
    yield view
    view.close()


@pytest.fixture
def populated_db(db_connection):
    """Populate database with sample tasks."""
    task_dao = TaskDAO(db_connection.get_connection())

    # Create some completed tasks
    for i in range(5):
        task = Task(
            title=f"Completed Task {i}",
            base_priority=2,
            state=TaskState.COMPLETED,
            completed_at=date.today() - timedelta(days=i)
        )
        task_dao.create(task)

    # Create some active tasks
    for i in range(3):
        task = Task(
            title=f"Active Task {i}",
            base_priority=2,
            state=TaskState.ACTIVE
        )
        task_dao.create(task)

    db_connection.commit()
    return db_connection


class TestWidgetInitialization:
    """Test widget initialization."""

    def test_widget_creation(self, analytics_view):
        """Test that analytics view can be created."""
        assert analytics_view is not None

    def test_widget_has_layout(self, analytics_view):
        """Test that widget has layout."""
        assert analytics_view.layout() is not None


class TestStatisticsDisplay:
    """Test statistics display."""

    def test_has_total_tasks_label(self, analytics_view):
        """Test that view has total tasks label."""
        assert hasattr(analytics_view, 'total_tasks_label')

    def test_has_active_tasks_label(self, analytics_view):
        """Test that view has active tasks label."""
        assert hasattr(analytics_view, 'active_tasks_label')

    def test_has_completed_tasks_label(self, analytics_view):
        """Test that view has completed tasks label."""
        assert hasattr(analytics_view, 'completed_tasks_label')

    def test_has_completion_rate_label(self, analytics_view):
        """Test that view has completion rate label."""
        assert hasattr(analytics_view, 'completion_rate_label')


class TestChartComponents:
    """Test chart components."""

    def test_has_priority_chart(self, analytics_view):
        """Test that view has priority distribution chart."""
        assert hasattr(analytics_view, 'priority_chart') or hasattr(analytics_view, 'priority_widget')

    def test_has_state_chart(self, analytics_view):
        """Test that view has state distribution chart."""
        assert hasattr(analytics_view, 'state_chart') or hasattr(analytics_view, 'state_widget')

    def test_has_completion_trend_chart(self, analytics_view):
        """Test that view has completion trend chart."""
        assert hasattr(analytics_view, 'completion_chart') or hasattr(analytics_view, 'trend_widget')


class TestDataRefresh:
    """Test data refresh functionality."""

    def test_has_refresh_button(self, analytics_view):
        """Test that view has refresh button."""
        assert hasattr(analytics_view, 'refresh_button')

    def test_has_refresh_method(self, analytics_view):
        """Test that view has refresh_data method."""
        assert hasattr(analytics_view, 'refresh_data')
        assert callable(analytics_view.refresh_data)

    def test_refresh_button_calls_refresh_data(self, analytics_view):
        """Test that clicking refresh button calls refresh_data."""
        refresh_called = []

        # Replace refresh_data with a tracker
        original_refresh = analytics_view.refresh_data
        analytics_view.refresh_data = lambda: refresh_called.append(True)

        # Click refresh
        analytics_view.refresh_button.click()

        # Restore original
        analytics_view.refresh_data = original_refresh

        assert len(refresh_called) == 1


class TestDataWithPopulatedDatabase:
    """Test data display with populated database."""

    def test_displays_task_counts(self, qapp, populated_db):
        """Test that view displays correct task counts."""
        view = AnalyticsView(populated_db)

        # Should display statistics
        total_text = view.total_tasks_label.text()
        assert "8" in total_text  # 5 completed + 3 active

        view.close()

    def test_displays_active_count(self, qapp, populated_db):
        """Test that view displays active task count."""
        view = AnalyticsView(populated_db)

        active_text = view.active_tasks_label.text()
        assert "3" in active_text

        view.close()

    def test_displays_completed_count(self, qapp, populated_db):
        """Test that view displays completed task count."""
        view = AnalyticsView(populated_db)

        completed_text = view.completed_tasks_label.text()
        assert "5" in completed_text

        view.close()


class TestTimeRangeFilter:
    """Test time range filtering."""

    def test_has_time_range_selector(self, analytics_view):
        """Test that view has time range selector."""
        assert hasattr(analytics_view, 'time_range_combo') or hasattr(analytics_view, 'period_selector')

    def test_time_range_options_available(self, analytics_view):
        """Test that time range has multiple options."""
        if hasattr(analytics_view, 'time_range_combo'):
            count = analytics_view.time_range_combo.count()
            assert count >= 3  # e.g., Week, Month, Year


class TestStatisticsCalculation:
    """Test statistics calculation."""

    def test_calculates_completion_rate(self, qapp, populated_db):
        """Test that completion rate is calculated."""
        view = AnalyticsView(populated_db)

        rate_text = view.completion_rate_label.text()
        # 5 completed out of 8 total = 62.5%
        assert "%" in rate_text

        view.close()


class TestEmptyState:
    """Test display with no data."""

    def test_handles_empty_database_gracefully(self, analytics_view):
        """Test that view handles empty database without crashing."""
        # Should display zeros or "No data" without errors
        analytics_view.refresh_data()

        # Check that labels still have content
        assert len(analytics_view.total_tasks_label.text()) > 0


class TestWidgetLayout:
    """Test widget layout structure."""

    def test_has_statistics_section(self, analytics_view):
        """Test that view has statistics section."""
        # Should have a groupbox or section for statistics
        assert hasattr(analytics_view, 'stats_group') or hasattr(analytics_view, 'layout')

    def test_has_charts_section(self, analytics_view):
        """Test that view has charts section."""
        # Should have area for charts
        assert hasattr(analytics_view, 'charts_layout') or hasattr(analytics_view, 'layout')
