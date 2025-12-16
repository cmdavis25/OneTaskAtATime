"""
Task Form Dialog - Create and edit tasks.

This module now delegates to EnhancedTaskFormDialog for all functionality.
Phase 4: Consolidated to use enhanced form for all task operations.
"""

from typing import Optional
from ..models.task import Task
from ..database.connection import DatabaseConnection
from .task_form_enhanced import EnhancedTaskFormDialog


class TaskFormDialog(EnhancedTaskFormDialog):
    """
    Dialog for creating or editing tasks.

    This class now inherits from EnhancedTaskFormDialog to provide
    a unified task editing experience with all advanced features.

    Maintained for backward compatibility with existing code that
    imports TaskFormDialog.
    """

    def __init__(self, task: Optional[Task] = None,
                 db_connection: Optional[DatabaseConnection] = None,
                 parent=None):
        """
        Initialize the task form.

        Args:
            task: Existing task to edit, or None to create new
            db_connection: Database connection for loading contexts/tags
            parent: Parent widget
        """
        # If no db_connection provided, try to get it from parent
        if db_connection is None and hasattr(parent, 'db_connection'):
            db_connection = parent.db_connection

        # Delegate to EnhancedTaskFormDialog
        super().__init__(task=task, db_connection=db_connection, parent=parent)

    def get_task_data(self) -> Optional[dict]:
        """
        Get task data from form fields as a dictionary.

        Provided for backward compatibility.
        Returns basic task data similar to the old simple form.

        Returns:
            Dictionary with task data, or None if canceled
        """
        task = self.get_updated_task()
        if task is None:
            return None

        return {
            'title': task.title,
            'description': task.description,
            'base_priority': task.base_priority,
            'due_date': task.due_date,
        }
