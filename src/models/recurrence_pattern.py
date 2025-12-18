"""
Recurrence pattern model for recurring tasks.

Defines structured patterns for task recurrence with support for:
- Daily, weekly, monthly, yearly patterns
- Custom/advanced patterns (cron-like)
- JSON serialization for database storage
- Next occurrence date calculation
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional, List
import json
import calendar


class RecurrenceType(Enum):
    """Types of recurrence patterns."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class RecurrencePattern:
    """
    Structured recurrence pattern for recurring tasks.

    Attributes:
        type: Type of recurrence pattern
        interval: Number of periods between occurrences (e.g., every 2 weeks)
        days_of_week: List of weekdays (0=Monday, 6=Sunday) for weekly patterns
        day_of_month: Day of month (1-31) for monthly patterns
        week_of_month: Week number (1-4) for Nth weekday patterns
        weekday_of_month: Weekday (0-6) for Nth weekday patterns
        custom_expression: Cron-like or natural language expression for custom patterns
    """
    type: RecurrenceType
    interval: int = 1
    days_of_week: List[int] = field(default_factory=list)  # 0=Mon, 6=Sun
    day_of_month: Optional[int] = None  # 1-31
    week_of_month: Optional[int] = None  # 1-4 (or -1 for last)
    weekday_of_month: Optional[int] = None  # 0=Mon, 6=Sun
    custom_expression: Optional[str] = None

    def to_json(self) -> str:
        """Serialize pattern to JSON string for database storage."""
        data = {
            "type": self.type.value,
            "interval": self.interval,
        }

        if self.days_of_week:
            data["days_of_week"] = self.days_of_week
        if self.day_of_month is not None:
            data["day_of_month"] = self.day_of_month
        if self.week_of_month is not None:
            data["week_of_month"] = self.week_of_month
        if self.weekday_of_month is not None:
            data["weekday_of_month"] = self.weekday_of_month
        if self.custom_expression:
            data["custom_expression"] = self.custom_expression

        return json.dumps(data)

    @staticmethod
    def from_json(json_str: str) -> 'RecurrencePattern':
        """Deserialize pattern from JSON string."""
        data = json.loads(json_str)

        return RecurrencePattern(
            type=RecurrenceType(data["type"]),
            interval=data.get("interval", 1),
            days_of_week=data.get("days_of_week", []),
            day_of_month=data.get("day_of_month"),
            week_of_month=data.get("week_of_month"),
            weekday_of_month=data.get("weekday_of_month"),
            custom_expression=data.get("custom_expression")
        )

    def calculate_next_date(self, from_date: date) -> date:
        """
        Calculate the next occurrence date based on the pattern.

        Args:
            from_date: The reference date (usually task completion date)

        Returns:
            The next occurrence date
        """
        if self.type == RecurrenceType.DAILY:
            return self._calculate_daily_next(from_date)
        elif self.type == RecurrenceType.WEEKLY:
            return self._calculate_weekly_next(from_date)
        elif self.type == RecurrenceType.MONTHLY:
            return self._calculate_monthly_next(from_date)
        elif self.type == RecurrenceType.YEARLY:
            return self._calculate_yearly_next(from_date)
        else:  # CUSTOM
            # For now, default to daily
            # Future: Parse cron expression or custom logic
            return from_date + timedelta(days=1)

    def _calculate_daily_next(self, from_date: date) -> date:
        """Calculate next date for daily pattern."""
        return from_date + timedelta(days=self.interval)

    def _calculate_weekly_next(self, from_date: date) -> date:
        """Calculate next date for weekly pattern."""
        if not self.days_of_week:
            # No specific days, just add weeks
            return from_date + timedelta(weeks=self.interval)

        # Find next occurrence on specified weekdays
        current_weekday = from_date.weekday()

        # Find next target weekday in current week
        next_weekday = None
        for day in sorted(self.days_of_week):
            if day > current_weekday:
                next_weekday = day
                break

        if next_weekday is not None:
            # Next occurrence is in the same week
            days_ahead = next_weekday - current_weekday
            return from_date + timedelta(days=days_ahead)
        else:
            # Next occurrence is in a future week
            # Jump to next interval and find first target weekday
            weeks_to_add = self.interval
            days_to_add = weeks_to_add * 7

            # Get first target weekday
            first_target = sorted(self.days_of_week)[0]

            # Calculate days from Monday of target week to target weekday
            next_date = from_date + timedelta(days=days_to_add)
            next_monday = next_date - timedelta(days=next_date.weekday())
            return next_monday + timedelta(days=first_target)

    def _calculate_monthly_next(self, from_date: date) -> date:
        """Calculate next date for monthly pattern."""
        # Use dateutil for robust month arithmetic
        try:
            from dateutil.relativedelta import relativedelta
        except ImportError:
            # Fallback: simple month addition (may have issues)
            return self._calculate_monthly_next_simple(from_date)

        if self.day_of_month is not None:
            # Simple day-of-month pattern
            next_date = from_date + relativedelta(months=self.interval)

            # Adjust for months with fewer days
            max_day = calendar.monthrange(next_date.year, next_date.month)[1]
            target_day = min(self.day_of_month, max_day)

            return next_date.replace(day=target_day)

        elif self.week_of_month is not None and self.weekday_of_month is not None:
            # Nth weekday pattern (e.g., 2nd Tuesday)
            next_date = from_date + relativedelta(months=self.interval)
            return self._get_nth_weekday_of_month(
                next_date.year,
                next_date.month,
                self.week_of_month,
                self.weekday_of_month
            )

        else:
            # Default: same day next month
            return from_date + relativedelta(months=self.interval)

    def _calculate_monthly_next_simple(self, from_date: date) -> date:
        """Fallback monthly calculation without dateutil."""
        target_day = self.day_of_month or from_date.day

        # Add months
        month = from_date.month + self.interval
        year = from_date.year

        while month > 12:
            month -= 12
            year += 1

        # Adjust for months with fewer days
        max_day = calendar.monthrange(year, month)[1]
        day = min(target_day, max_day)

        return date(year, month, day)

    def _calculate_yearly_next(self, from_date: date) -> date:
        """Calculate next date for yearly pattern."""
        try:
            from dateutil.relativedelta import relativedelta
            return from_date + relativedelta(years=self.interval)
        except ImportError:
            # Fallback: simple year addition
            next_year = from_date.year + self.interval

            # Handle Feb 29 in leap years
            if from_date.month == 2 and from_date.day == 29:
                if not calendar.isleap(next_year):
                    return date(next_year, 2, 28)

            return from_date.replace(year=next_year)

    def _get_nth_weekday_of_month(self, year: int, month: int,
                                    week_num: int, weekday: int) -> date:
        """
        Get the Nth occurrence of a weekday in a month.

        Args:
            year: Year
            month: Month (1-12)
            week_num: Week number (1-4, or -1 for last)
            weekday: Day of week (0=Monday, 6=Sunday)

        Returns:
            Date of the Nth weekday
        """
        # Get first day of month
        first_day = date(year, month, 1)
        first_weekday = first_day.weekday()

        # Calculate days until first occurrence of target weekday
        days_until_first = (weekday - first_weekday) % 7
        first_occurrence = first_day + timedelta(days=days_until_first)

        if week_num == -1:
            # Last occurrence of weekday in month
            # Start from first occurrence and add weeks until we exceed month
            current = first_occurrence
            last_valid = current

            while True:
                next_occurrence = current + timedelta(weeks=1)
                if next_occurrence.month != month:
                    break
                last_valid = next_occurrence
                current = next_occurrence

            return last_valid
        else:
            # Nth occurrence (1-based)
            weeks_to_add = week_num - 1
            return first_occurrence + timedelta(weeks=weeks_to_add)

    def to_human_readable(self) -> str:
        """
        Convert pattern to human-readable string.

        Returns:
            Human-readable description of the pattern
        """
        if self.type == RecurrenceType.DAILY:
            if self.interval == 1:
                return "Every day"
            else:
                return f"Every {self.interval} days"

        elif self.type == RecurrenceType.WEEKLY:
            day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

            if not self.days_of_week:
                if self.interval == 1:
                    return "Every week"
                else:
                    return f"Every {self.interval} weeks"

            days_str = ", ".join([day_names[d] for d in sorted(self.days_of_week)])

            if self.interval == 1:
                return f"Every week on {days_str}"
            else:
                return f"Every {self.interval} weeks on {days_str}"

        elif self.type == RecurrenceType.MONTHLY:
            if self.day_of_month is not None:
                suffix = self._get_ordinal_suffix(self.day_of_month)
                if self.interval == 1:
                    return f"Monthly on the {self.day_of_month}{suffix}"
                else:
                    return f"Every {self.interval} months on the {self.day_of_month}{suffix}"

            elif self.week_of_month is not None and self.weekday_of_month is not None:
                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday",
                            "Friday", "Saturday", "Sunday"]
                week_names = ["1st", "2nd", "3rd", "4th"]

                week_str = "last" if self.week_of_month == -1 else week_names[self.week_of_month - 1]
                day_str = day_names[self.weekday_of_month]

                if self.interval == 1:
                    return f"Monthly on the {week_str} {day_str}"
                else:
                    return f"Every {self.interval} months on the {week_str} {day_str}"

        elif self.type == RecurrenceType.YEARLY:
            if self.interval == 1:
                return "Every year"
            else:
                return f"Every {self.interval} years"

        else:  # CUSTOM
            return f"Custom: {self.custom_expression or 'undefined'}"

    def _get_ordinal_suffix(self, day: int) -> str:
        """Get ordinal suffix for a day number (st, nd, rd, th)."""
        if 10 <= day % 100 <= 20:
            return "th"
        else:
            return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
