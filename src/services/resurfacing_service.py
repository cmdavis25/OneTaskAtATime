"""
Task Resurfacing Service for OneTaskAtATime application.

Business logic for resurfacing deferred, delegated, and someday tasks.
Works in conjunction with ResurfacingScheduler for automated task management.
"""

import sqlite3
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

from ..models.task import Task, TaskState
from ..database.task_dao import TaskDAO
from ..database.settings_dao import SettingsDAO
from .postpone_suggestion_service import PostponeSuggestionService, PostponeSuggestion


# Configure logging
logger = logging.getLogger(__name__)


class ResurfacingService:
    """
    Business logic for task resurfacing operations.

    This service handles:
    - Auto-activating deferred tasks when start_date arrives
    - Identifying delegated tasks needing follow-up
    - Determining when to trigger Someday/Maybe reviews
    - Analyzing postponement patterns for intervention
    """

    def __init__(self, db_connection: sqlite3.Connection, notification_manager=None):
        """
        Initialize the resurfacing service.

        Args:
            db_connection: Active SQLite database connection
            notification_manager: Optional NotificationManager for creating notifications
        """
        self.db_connection = db_connection
        self.notification_manager = notification_manager
        self.task_dao = TaskDAO(db_connection)
        self.settings_dao = SettingsDAO(db_connection)
        self.postpone_suggestion_service = PostponeSuggestionService(db_connection)

    def activate_ready_deferred_tasks(self) -> List[Task]:
        """
        Activate deferred tasks whose start_date has arrived.

        This method:
        1. Queries tasks with state=DEFERRED and start_date <= today
        2. Sets state to ACTIVE
        3. Clears start_date field
        4. Updates last_resurfaced_at and resurface_count
        5. Creates notification if notification_manager is available

        Returns:
            List of activated Task objects
        """
        current_date = date.today()
        logger.info(f"Checking for deferred tasks ready to activate (date: {current_date})")

        # Get tasks ready to activate
        ready_tasks = self.task_dao.get_deferred_tasks_ready_to_activate(current_date)

        if not ready_tasks:
            logger.debug("No deferred tasks ready to activate")
            return []

        activated_tasks = []
        now = datetime.now()

        for task in ready_tasks:
            try:
                # Update task state
                task.state = TaskState.ACTIVE
                task.start_date = None
                task.last_resurfaced_at = now
                task.resurface_count = (task.resurface_count or 0) + 1

                # Save to database
                self.task_dao.update(task)

                activated_tasks.append(task)
                logger.info(f"Activated deferred task: {task.title} (ID: {task.id})")

            except Exception as e:
                logger.error(f"Error activating task {task.id}: {e}", exc_info=True)

        # Create notification if tasks were activated
        if activated_tasks and self.notification_manager:
            try:
                # Check if notifications are enabled for this event
                notify_enabled = self.settings_dao.get_bool('notify_deferred_activation', default=True)

                if notify_enabled:
                    from ..models.notification import NotificationType

                    self.notification_manager.create_notification(
                        type=NotificationType.INFO,
                        title="Tasks Ready to Work",
                        message=f"{len(activated_tasks)} deferred task(s) are now active.",
                        action_type='open_focus',
                        action_data={'task_ids': [t.id for t in activated_tasks]}
                    )
            except Exception as e:
                logger.error(f"Error creating notification: {e}", exc_info=True)

        logger.info(f"Activated {len(activated_tasks)} deferred task(s)")
        return activated_tasks

    def check_delegated_followups(self) -> List[Task]:
        """
        Check for delegated tasks needing follow-up.

        This method:
        1. Queries tasks with state=DELEGATED and follow_up_date <= today
        2. Updates last_resurfaced_at for tracking
        3. Creates notification if notification_manager is available

        Returns:
            List of Task objects needing follow-up
        """
        current_date = date.today()
        logger.info(f"Checking for delegated tasks needing follow-up (date: {current_date})")

        # Get tasks needing follow-up (days_before=0 means on or after follow-up date)
        followup_tasks = self.task_dao.get_delegated_tasks_for_followup(current_date, days_before=0)

        if not followup_tasks:
            logger.debug("No delegated tasks need follow-up")
            return []

        # Update last_resurfaced_at for tracking
        now = datetime.now()
        for task in followup_tasks:
            try:
                task.last_resurfaced_at = now
                task.resurface_count = (task.resurface_count or 0) + 1
                self.task_dao.update(task)

                logger.info(f"Delegated task needs follow-up: {task.title} (ID: {task.id})")

            except Exception as e:
                logger.error(f"Error updating task {task.id}: {e}", exc_info=True)

        # Create notification if tasks need follow-up
        if followup_tasks and self.notification_manager:
            try:
                # Check if notifications are enabled for this event
                notify_enabled = self.settings_dao.get_bool('notify_delegated_followup', default=True)

                if notify_enabled:
                    from ..models.notification import NotificationType

                    self.notification_manager.create_notification(
                        type=NotificationType.INFO,
                        title="Follow-up Required",
                        message=f"{len(followup_tasks)} delegated task(s) have reached their follow-up date.",
                        action_type='open_review_delegated',
                        action_data={'task_ids': [t.id for t in followup_tasks]}
                    )
            except Exception as e:
                logger.error(f"Error creating notification: {e}", exc_info=True)

        logger.info(f"Found {len(followup_tasks)} delegated task(s) needing follow-up")
        return followup_tasks

    def should_trigger_someday_review(self) -> bool:
        """
        Check if it's time to trigger a Someday/Maybe review.

        This method checks:
        1. The last_someday_review_at setting
        2. The someday_review_days interval setting
        3. Returns True if interval has elapsed or never reviewed

        Returns:
            True if review should be triggered, False otherwise
        """
        logger.info("Checking if someday review should be triggered")

        # Get settings
        last_review = self.settings_dao.get_datetime('last_someday_review_at', default=None)
        review_interval_days = self.settings_dao.get_int('someday_review_days', default=7)

        # If never reviewed, trigger review
        if last_review is None:
            logger.info("No previous someday review found - triggering review")
            return True

        # Check if interval has elapsed
        days_since_review = (datetime.now() - last_review).days

        if days_since_review >= review_interval_days:
            logger.info(f"Someday review interval elapsed ({days_since_review} days >= {review_interval_days} days)")
            return True

        logger.debug(f"Someday review not due yet ({days_since_review} days < {review_interval_days} days)")
        return False

    def analyze_postponement_patterns(self) -> List[PostponeSuggestion]:
        """
        Analyze postponement patterns and generate intervention suggestions.

        This method:
        1. Uses PostponeSuggestionService to analyze all tasks
        2. Filters suggestions based on intervention threshold
        3. Creates notifications for tasks needing intervention

        Returns:
            List of PostponeSuggestion objects for tasks needing intervention
        """
        logger.info("Analyzing postponement patterns")

        try:
            # Get intervention threshold
            intervention_threshold = self.settings_dao.get_int('postpone_intervention_threshold', default=3)

            # Get suggestions from postpone service
            all_suggestions = self.postpone_suggestion_service.get_suggestions_for_all_tasks(limit=20)

            # Filter suggestions that meet intervention threshold
            intervention_suggestions = [
                s for s in all_suggestions
                if s.pattern_count >= intervention_threshold
            ]

            if not intervention_suggestions:
                logger.debug("No tasks need postponement intervention")
                return []

            # Create notifications for interventions
            if self.notification_manager:
                try:
                    # Check if notifications are enabled for this event
                    notify_enabled = self.settings_dao.get_bool('notify_postpone_intervention', default=True)

                    if notify_enabled:
                        from ..models.notification import NotificationType

                        for suggestion in intervention_suggestions:
                            # Get task for title
                            task = self.task_dao.get_by_id(suggestion.task_id)
                            if task:
                                self.notification_manager.create_notification(
                                    type=NotificationType.WARNING,
                                    title="Task Needs Attention",
                                    message=f"Task '{task.title}' postponed {suggestion.pattern_count} times. Review?",
                                    action_type='open_postpone_analytics',
                                    action_data={
                                        'task_id': suggestion.task_id,
                                        'pattern_count': suggestion.pattern_count
                                    }
                                )

                except Exception as e:
                    logger.error(f"Error creating intervention notifications: {e}", exc_info=True)

            logger.info(f"Found {len(intervention_suggestions)} task(s) needing postponement intervention")
            return intervention_suggestions

        except Exception as e:
            logger.error(f"Error analyzing postponement patterns: {e}", exc_info=True)
            return []

    def get_someday_tasks(self) -> List[Task]:
        """
        Get all tasks in Someday/Maybe state.

        Returns:
            List of Task objects in SOMEDAY state
        """
        logger.debug("Getting someday tasks")

        try:
            tasks = self.task_dao.get_all(state=TaskState.SOMEDAY)
            logger.debug(f"Found {len(tasks)} someday task(s)")
            return tasks

        except Exception as e:
            logger.error(f"Error getting someday tasks: {e}", exc_info=True)
            return []

    def update_someday_review_timestamp(self) -> None:
        """
        Update the last_someday_review_at setting to current time.

        This should be called when the user completes a Someday review
        (regardless of whether they activate, keep, or trash any tasks).
        """
        logger.info("Updating someday review timestamp")

        try:
            now = datetime.now()
            self.settings_dao.set(
                'last_someday_review_at',
                now.isoformat(),
                'datetime',
                'Last someday review timestamp'
            )
            logger.info(f"Updated last_someday_review_at to {now.isoformat()}")

        except Exception as e:
            logger.error(f"Error updating someday review timestamp: {e}", exc_info=True)
