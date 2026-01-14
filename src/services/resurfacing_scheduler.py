"""
Background scheduler for task resurfacing using APScheduler.

This module manages periodic background jobs for:
- Auto-activating deferred tasks when start_date arrives
- Reminding users of delegated tasks needing follow-up
- Triggering periodic reviews of Someday/Maybe tasks
- Analyzing postponement patterns for intervention
"""

import sqlite3
import logging
from typing import Optional
from datetime import datetime, time

from PyQt5.QtCore import QObject, pyqtSignal
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

from ..models.task import Task
from .resurfacing_service import ResurfacingService
from ..database.settings_dao import SettingsDAO


# Configure logging
logger = logging.getLogger(__name__)


class ResurfacingScheduler(QObject):
    """
    Manages APScheduler background jobs for task resurfacing.

    This scheduler runs in a separate thread and emits Qt signals to communicate
    with the main UI thread. All jobs are configurable via application settings.
    """

    # Qt signals emitted to UI thread
    deferred_tasks_activated = pyqtSignal(list)  # List[Task]
    delegated_followup_needed = pyqtSignal(list)  # List[Task]
    someday_review_triggered = pyqtSignal()
    postpone_intervention_needed = pyqtSignal(list)  # List[PostponeSuggestion]

    def __init__(self, db_connection: sqlite3.Connection, notification_manager):
        """
        Initialize the resurfacing scheduler.

        Args:
            db_connection: Active SQLite database connection
            notification_manager: NotificationManager instance for creating notifications
        """
        super().__init__()

        self.db_connection = db_connection
        self.notification_manager = notification_manager
        self.resurfacing_service = ResurfacingService(db_connection, notification_manager)
        self.settings_dao = SettingsDAO(db_connection)

        # Create background scheduler
        self.scheduler = BackgroundScheduler(
            timezone='UTC',
            job_defaults={
                'coalesce': True,  # Combine missed runs
                'max_instances': 1,  # Prevent overlapping runs
                'misfire_grace_time': 900  # 15 minutes grace period
            }
        )

        # Add event listener for job execution monitoring
        self.scheduler.add_listener(
            self._job_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )

        self._is_running = False

    def start(self):
        """
        Start the background scheduler and configure all jobs.

        This method should be called once during application initialization.
        Jobs are configured based on current application settings.
        """
        if self._is_running:
            logger.warning("Scheduler already running")
            return

        logger.info("Starting resurfacing scheduler...")

        # Add all jobs with current settings
        self._configure_jobs()

        # Start the scheduler
        self.scheduler.start()
        self._is_running = True

        logger.info("Resurfacing scheduler started successfully")

        # Run immediate checks on startup (don't wait for first interval)
        logger.info("Running immediate startup checks...")
        self._job_check_deferred_tasks()
        self._job_check_delegated_tasks()

    def stop(self):
        """
        Stop the scheduler (alias for shutdown).
        """
        self.shutdown()

    def shutdown(self, wait: bool = True, timeout: int = 5):
        """
        Shutdown the scheduler gracefully.

        Args:
            wait: Whether to wait for jobs to complete
            timeout: Maximum seconds to wait for shutdown
        """
        if not self._is_running:
            return

        logger.info("Shutting down resurfacing scheduler...")

        try:
            self.scheduler.shutdown(wait=wait)
            self._is_running = False
            logger.info("Scheduler shutdown complete")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}")

    def reload_settings(self):
        """
        Reload job configurations from updated settings.

        This is called when the user changes settings in the Settings dialog.
        It removes all existing jobs and reconfigures them with new settings.
        """
        if not self._is_running:
            return

        logger.info("Reloading scheduler settings...")

        # Remove all existing jobs
        self.scheduler.remove_all_jobs()

        # Reconfigure with new settings
        self._configure_jobs()

        logger.info("Scheduler settings reloaded")

    # ========== PUBLIC MANUAL TRIGGER METHODS ==========

    def check_deferred_tasks(self):
        """
        Manually trigger checking for deferred tasks that are ready to activate.

        Returns:
            List of activated tasks
        """
        return self._job_check_deferred_tasks()

    def check_delegated_tasks(self):
        """
        Manually trigger checking for delegated tasks needing follow-up.

        Returns:
            List of tasks needing follow-up
        """
        return self._job_check_delegated_tasks()

    def check_someday_tasks(self):
        """
        Manually trigger someday/maybe review.
        """
        return self._job_trigger_someday_review()

    def _configure_jobs(self):
        """
        Configure all scheduled jobs based on current settings.

        Jobs:
        1. check_deferred_tasks - Hourly interval (configurable)
        2. check_delegated_tasks - Daily at specific time
        3. trigger_someday_review - Periodic interval
        4. analyze_postponements - Daily at specific time
        """
        # Job 1: Check deferred tasks (hourly by default)
        deferred_check_hours = self.settings_dao.get_int('deferred_check_hours', default=1)
        self.scheduler.add_job(
            func=self._job_check_deferred_tasks,
            trigger=IntervalTrigger(hours=deferred_check_hours),
            id='check_deferred_tasks',
            name='Check Deferred Tasks',
            replace_existing=True
        )
        logger.info(f"Configured: Check deferred tasks every {deferred_check_hours} hour(s)")

        # Job 2: Check delegated tasks (daily at 9:00 AM by default)
        delegated_check_time = self.settings_dao.get_str('delegated_check_time', default='09:00')
        hour, minute = self._parse_time_string(delegated_check_time)
        self.scheduler.add_job(
            func=self._job_check_delegated_tasks,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='check_delegated_tasks',
            name='Check Delegated Tasks',
            replace_existing=True
        )
        logger.info(f"Configured: Check delegated tasks daily at {delegated_check_time}")

        # Job 3: Trigger someday review (every 7 days by default)
        someday_review_days = self.settings_dao.get_int('someday_review_days', default=7)
        self.scheduler.add_job(
            func=self._job_trigger_someday_review,
            trigger=IntervalTrigger(days=someday_review_days),
            id='trigger_someday_review',
            name='Trigger Someday Review',
            replace_existing=True
        )
        logger.info(f"Configured: Trigger someday review every {someday_review_days} day(s)")

        # Job 4: Analyze postponement patterns (daily at 6:00 PM by default)
        postpone_analysis_time = self.settings_dao.get_str('postpone_analysis_time', default='18:00')
        hour, minute = self._parse_time_string(postpone_analysis_time)
        self.scheduler.add_job(
            func=self._job_analyze_postponements,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='analyze_postponements',
            name='Analyze Postponements',
            replace_existing=True
        )
        logger.info(f"Configured: Analyze postponements daily at {postpone_analysis_time}")

    def _parse_time_string(self, time_str: str) -> tuple[int, int]:
        """
        Parse a time string in HH:MM format.

        Args:
            time_str: Time string like "09:00" or "18:30"

        Returns:
            Tuple of (hour, minute)
        """
        try:
            parts = time_str.split(':')
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            logger.error(f"Invalid time format: {time_str}, using 09:00")
            return 9, 0

    # ========== JOB EXECUTION METHODS ==========

    def _job_check_deferred_tasks(self):
        """
        Job: Check for deferred tasks that are ready to activate.

        Runs hourly (configurable). Activates tasks with start_date <= today.
        """
        logger.info("Running job: Check deferred tasks")

        try:
            activated_tasks = self.resurfacing_service.activate_ready_deferred_tasks()

            if activated_tasks:
                logger.info(f"Activated {len(activated_tasks)} deferred task(s)")
                # Emit signal to UI thread
                self.deferred_tasks_activated.emit(activated_tasks)
            else:
                logger.debug("No deferred tasks ready to activate")

        except Exception as e:
            logger.error(f"Error checking deferred tasks: {e}", exc_info=True)

    def _job_check_delegated_tasks(self):
        """
        Job: Check for delegated tasks needing follow-up.

        Runs daily at configured time. Finds tasks with follow_up_date <= today.
        """
        logger.info("Running job: Check delegated tasks")

        try:
            followup_tasks = self.resurfacing_service.check_delegated_followups()

            if followup_tasks:
                logger.info(f"Found {len(followup_tasks)} delegated task(s) needing follow-up")
                # Emit signal to UI thread
                self.delegated_followup_needed.emit(followup_tasks)
            else:
                logger.debug("No delegated tasks need follow-up")

        except Exception as e:
            logger.error(f"Error checking delegated tasks: {e}", exc_info=True)

    def _job_trigger_someday_review(self):
        """
        Job: Trigger someday/maybe task review.

        Runs periodically (every N days). Checks if review interval has elapsed.
        """
        logger.info("Running job: Trigger someday review")

        try:
            should_trigger = self.resurfacing_service.should_trigger_someday_review()

            if should_trigger:
                logger.info("Triggering someday review")
                # Emit signal to UI thread
                self.someday_review_triggered.emit()
            else:
                logger.debug("Someday review not due yet")

        except Exception as e:
            logger.error(f"Error triggering someday review: {e}", exc_info=True)

    def _job_analyze_postponements(self):
        """
        Job: Analyze postponement patterns and create intervention notifications.

        Runs daily at configured time. Identifies tasks with concerning postponement patterns.
        """
        logger.info("Running job: Analyze postponements")

        try:
            suggestions = self.resurfacing_service.analyze_postponement_patterns()

            if suggestions:
                logger.info(f"Found {len(suggestions)} task(s) needing postponement intervention")
                # Emit signal to UI thread
                self.postpone_intervention_needed.emit(suggestions)
            else:
                logger.debug("No postponement interventions needed")

        except Exception as e:
            logger.error(f"Error analyzing postponements: {e}", exc_info=True)

    def _job_listener(self, event):
        """
        Event listener for job execution monitoring.

        Logs job execution and errors for debugging.
        """
        if event.exception:
            logger.error(
                f"Job '{event.job_id}' raised an exception: {event.exception}",
                exc_info=True
            )
        else:
            logger.debug(f"Job '{event.job_id}' executed successfully")
