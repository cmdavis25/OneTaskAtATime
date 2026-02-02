"""
Due Date Indicator Service

Provides visual indicators for task urgency based on due dates.
Uses symbols instead of colors for theme independence and accessibility.
"""

from datetime import date, timedelta
from typing import Optional
from ..models.task import Task
from ..database.settings_dao import SettingsDAO


class DueDateIndicatorService:
    """
    Service for determining and formatting due date visual indicators.

    Provides theme-independent, accessibility-friendly symbols for:
    - Overdue tasks (due date < today)
    - Tasks due today (due date == today)
    - Tasks due soon (0 < days until due <= threshold)
    """

    def __init__(self, settings_dao: SettingsDAO):
        """
        Initialize the due date indicator service.

        Args:
            settings_dao: DAO for retrieving settings
        """
        self.settings_dao = settings_dao
        self._load_settings()

    def _load_settings(self):
        """Load indicator settings from database."""
        self.enabled = self.settings_dao.get_bool('due_date_indicators_enabled', True)
        self.due_soon_threshold = self.settings_dao.get_int('due_soon_threshold_days', 3)
        self.overdue_symbol = self.settings_dao.get_str('overdue_symbol', '❗')
        self.due_today_symbol = self.settings_dao.get_str('due_today_symbol', '⚠️')
        self.due_soon_symbol = self.settings_dao.get_str('due_soon_symbol', '◆')

    def reload_settings(self):
        """Reload settings from database (call after settings change)."""
        self._load_settings()

    def get_indicator(self, task: Task) -> str:
        """
        Get the due date indicator symbol for a task.

        Args:
            task: Task to get indicator for

        Returns:
            Indicator symbol string, or empty string if no indicator
        """
        if not self.enabled or not task.due_date:
            return ""

        days_remaining = self._get_days_remaining(task.due_date)

        if days_remaining < 0:
            return self.overdue_symbol  # Overdue
        elif days_remaining == 0:
            return self.due_today_symbol  # Due today
        elif days_remaining <= self.due_soon_threshold:
            return self.due_soon_symbol  # Due soon
        else:
            return ""  # No urgency

    def get_indicator_with_label(self, task: Task) -> tuple[str, str]:
        """
        Get the indicator symbol and descriptive label for a task.

        Args:
            task: Task to get indicator for

        Returns:
            Tuple of (symbol, label) where label describes the urgency
        """
        if not self.enabled or not task.due_date:
            return ("", "")

        days_remaining = self._get_days_remaining(task.due_date)

        if days_remaining < 0:
            days_overdue = abs(days_remaining)
            label = f"{days_overdue} day{'s' if days_overdue != 1 else ''} overdue"
            return (self.overdue_symbol, label)
        elif days_remaining == 0:
            return (self.due_today_symbol, "Due today")
        elif days_remaining <= self.due_soon_threshold:
            label = f"Due in {days_remaining} day{'s' if days_remaining != 1 else ''}"
            return (self.due_soon_symbol, label)
        else:
            return ("", "")

    def _get_days_remaining(self, due_date: date) -> int:
        """
        Calculate days remaining until due date.

        Args:
            due_date: The task's due date

        Returns:
            Number of days (negative if overdue, 0 if today, positive if future)
        """
        today = date.today()
        delta = due_date - today
        return delta.days

    def is_enabled(self) -> bool:
        """
        Check if due date indicators are enabled.

        Returns:
            True if enabled, False otherwise
        """
        return self.enabled
