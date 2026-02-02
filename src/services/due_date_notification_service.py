"""
Due Date Notification Service

Monitors tasks for approaching and overdue due dates and sends notifications.
Checks at startup and periodically while running.
"""

import logging
from datetime import date, timedelta
from typing import Set, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from ..models.task import Task
from ..models.enums import TaskState
from ..models.notification import NotificationType
from ..database.connection import DatabaseConnection
from ..database.task_dao import TaskDAO
from ..database.settings_dao import SettingsDAO
from .toast_notification_service import ToastNotificationService


logger = logging.getLogger(__name__)


class DueDateNotificationService:
    """
    Service for monitoring task due dates and sending notifications.

    Features:
    - Checks for overdue, due today, and due soon tasks
    - Notifies on startup
    - Periodic checks while running (configurable interval)
    - Deduplication to avoid repeat notifications in same session
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize the due date notification service.

        Args:
            db_connection: Database connection instance
        """
        self.db_connection = db_connection
        self.task_dao = TaskDAO(db_connection.get_connection())
        self.settings_dao = SettingsDAO(db_connection.get_connection())
        self.toast_service = ToastNotificationService(db_connection)

        # Track notified tasks in current session to avoid duplicates
        self.notified_tasks: Set[int] = set()

        # Scheduler for periodic checks
        self.scheduler: BackgroundScheduler = None

        # Load settings
        self._load_settings()

    def _load_settings(self):
        """Load notification settings from database."""
        self.enabled = self.settings_dao.get_bool('due_date_notifications_enabled', True)
        self.check_interval_minutes = self.settings_dao.get_int('due_date_check_interval_minutes', 60)
        self.notify_overdue = self.settings_dao.get_bool('notify_overdue_tasks', True)
        self.notify_due_today = self.settings_dao.get_bool('notify_due_today_tasks', True)
        self.notify_due_soon = self.settings_dao.get_bool('notify_due_soon_tasks', True)
        self.due_soon_days = self.settings_dao.get_int('due_soon_notification_days', 3)

    def start(self):
        """
        Start the notification service.

        Performs initial check and starts periodic scheduler.
        """
        if not self.enabled:
            logger.info("Due date notifications are disabled")
            return

        logger.info("Starting due date notification service")

        # Perform initial check
        self.check_due_dates()

        # Start periodic scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.check_due_dates,
            trigger=IntervalTrigger(minutes=self.check_interval_minutes),
            id='due_date_check',
            name='Check task due dates',
            replace_existing=True
        )
        self.scheduler.start()

        logger.info(f"Scheduled due date checks every {self.check_interval_minutes} minutes")

    def stop(self):
        """Stop the notification service and scheduler."""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Due date notification service stopped")

    def check_due_dates(self):
        """
        Check for tasks with approaching or overdue due dates and notify.

        This method:
        1. Queries active tasks with due dates
        2. Categorizes them (overdue, due today, due soon)
        3. Sends notifications for each category
        4. Tracks notified tasks to avoid duplicates
        """
        if not self.enabled:
            return

        try:
            # Get all active tasks with due dates
            all_tasks = self.task_dao.get_all(state=TaskState.ACTIVE)
            tasks_with_due_dates = [t for t in all_tasks if t.due_date]

            if not tasks_with_due_dates:
                logger.debug("No active tasks with due dates")
                return

            today = date.today()
            overdue_tasks = []
            due_today_tasks = []
            due_soon_tasks = []

            # Categorize tasks
            for task in tasks_with_due_dates:
                # Skip if already notified in this session
                if task.id in self.notified_tasks:
                    continue

                days_until_due = (task.due_date - today).days

                if days_until_due < 0:
                    overdue_tasks.append(task)
                elif days_until_due == 0:
                    due_today_tasks.append(task)
                elif 0 < days_until_due <= self.due_soon_days:
                    due_soon_tasks.append(task)

            # Send notifications
            if self.notify_overdue and overdue_tasks:
                self._notify_overdue_tasks(overdue_tasks)

            if self.notify_due_today and due_today_tasks:
                self._notify_due_today_tasks(due_today_tasks)

            if self.notify_due_soon and due_soon_tasks:
                self._notify_due_soon_tasks(due_soon_tasks)

        except Exception as e:
            logger.error(f"Error checking due dates: {e}", exc_info=True)

    def _notify_overdue_tasks(self, tasks: List[Task]):
        """
        Send notifications for overdue tasks.

        Args:
            tasks: List of overdue tasks
        """
        for task in tasks:
            days_overdue = (date.today() - task.due_date).days
            title = "Task Overdue"
            message = f"{task.title}\nDue: {task.due_date.strftime('%Y-%m-%d')} ({days_overdue} day{'s' if days_overdue != 1 else ''} overdue)"

            success = self.toast_service.show_toast(
                title=title,
                message=message,
                type=NotificationType.WARNING,
                duration=10
            )

            if success and task.id:
                self.notified_tasks.add(task.id)
                logger.info(f"Notified: Overdue task '{task.title}'")

    def _notify_due_today_tasks(self, tasks: List[Task]):
        """
        Send notifications for tasks due today.

        Args:
            tasks: List of tasks due today
        """
        for task in tasks:
            title = "Task Due Today"
            message = f"{task.title}\nDue: {task.due_date.strftime('%Y-%m-%d')}"

            success = self.toast_service.show_toast(
                title=title,
                message=message,
                type=NotificationType.INFO,
                duration=7
            )

            if success and task.id:
                self.notified_tasks.add(task.id)
                logger.info(f"Notified: Task due today '{task.title}'")

    def _notify_due_soon_tasks(self, tasks: List[Task]):
        """
        Send notifications for tasks due soon.

        Args:
            tasks: List of tasks due soon
        """
        for task in tasks:
            days_until_due = (task.due_date - date.today()).days
            title = "Task Due Soon"
            message = f"{task.title}\nDue: {task.due_date.strftime('%Y-%m-%d')} (in {days_until_due} day{'s' if days_until_due != 1 else ''})"

            success = self.toast_service.show_toast(
                title=title,
                message=message,
                type=NotificationType.INFO,
                duration=5
            )

            if success and task.id:
                self.notified_tasks.add(task.id)
                logger.info(f"Notified: Task due soon '{task.title}'")

    def reset_notifications(self):
        """
        Reset the notification tracking.

        Call this to allow re-notification of tasks (e.g., on new day).
        """
        self.notified_tasks.clear()
        logger.info("Reset due date notification tracking")

    def reload_settings(self):
        """Reload settings from database."""
        self._load_settings()

        # Restart scheduler if interval changed
        if self.scheduler and self.scheduler.running:
            self.stop()
            self.start()
