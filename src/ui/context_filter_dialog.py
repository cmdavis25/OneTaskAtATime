"""
Context Filter Dialog - Manage active context filters

Phase 4 Enhancement: Provides a dual-list interface for selecting context filters.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel
)
from PyQt5.QtCore import Qt
from typing import List, Set
from ..models.context import Context
from ..database.connection import DatabaseConnection
from ..database.context_dao import ContextDAO


class ContextFilterDialog(QDialog):
    """
    Dialog for selecting context filters.

    Features:
    - View available contexts
    - Add contexts to active filters
    - Remove contexts from active filters
    - Transfer contexts between lists

    Args:
        active_filter_ids: Set of currently active context IDs (use 'NONE' for no context filter)
        db_connection: Database connection
        parent: Parent widget
    """

    def __init__(self, active_filter_ids: Set, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the context filter dialog.

        Args:
            active_filter_ids: Set of currently active context IDs (can include 'NONE')
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.context_dao = ContextDAO(db_connection.get_connection())

        self.all_contexts: List[Context] = []
        self.active_filter_ids: Set = set(active_filter_ids)  # Make a copy

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manage Context Filters")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Manage Context Filters")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Select which contexts to show in the task list. "
            "Tasks matching any active filter will be displayed."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: Available contexts
        available_layout = QVBoxLayout()

        available_label = QLabel("Available Contexts:")
        available_label.setStyleSheet("font-weight: bold;")
        available_layout.addWidget(available_label)

        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SingleSelection)
        available_layout.addWidget(self.available_list)

        add_btn = QPushButton("Add to Filter →")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        add_btn.clicked.connect(self._on_add_filter)
        available_layout.addWidget(add_btn)

        content_layout.addLayout(available_layout, 1)

        # Right side: Active filters
        filters_layout = QVBoxLayout()

        filters_label = QLabel("Active Context Filters:")
        filters_label.setStyleSheet("font-weight: bold;")
        filters_layout.addWidget(filters_label)

        self.filters_list = QListWidget()
        self.filters_list.setSelectionMode(QListWidget.SingleSelection)
        filters_layout.addWidget(self.filters_list)

        # Button layout for Remove and Clear
        filter_button_layout = QHBoxLayout()

        remove_btn = QPushButton("← Remove from Filter")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        remove_btn.clicked.connect(self._on_remove_filter)
        filter_button_layout.addWidget(remove_btn)

        clear_filters_btn = QPushButton("Clear Filters")
        clear_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: black;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)
        clear_filters_btn.clicked.connect(self._on_clear_filters)
        filter_button_layout.addWidget(clear_filters_btn)

        filters_layout.addLayout(filter_button_layout)

        content_layout.addLayout(filters_layout, 1)

        layout.addLayout(content_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setDefault(True)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 24px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        apply_btn.clicked.connect(self.accept)
        bottom_layout.addWidget(apply_btn)

        layout.addLayout(bottom_layout)

    def _load_data(self):
        """Load contexts."""
        # Load all contexts
        self.all_contexts = self.context_dao.get_all()

        self._refresh_lists()

    def _refresh_lists(self):
        """Refresh both lists."""
        self._refresh_available_contexts()
        self._refresh_filters_list()

    def _refresh_available_contexts(self):
        """Refresh the available contexts list."""
        self.available_list.clear()

        # Add special "No Context" option if not already in filters
        if "NONE" not in self.active_filter_ids:
            item = QListWidgetItem("(No Context)")
            item.setData(Qt.UserRole, "NONE")
            self.available_list.addItem(item)

        # Add all contexts that are not in active filters
        for context in self.all_contexts:
            if context.id not in self.active_filter_ids:
                item = QListWidgetItem(context.name)
                item.setData(Qt.UserRole, context.id)
                self.available_list.addItem(item)

    def _refresh_filters_list(self):
        """Refresh the active filters list."""
        self.filters_list.clear()

        # Add "No Context" if it's in the active filters
        if "NONE" in self.active_filter_ids:
            item = QListWidgetItem("(No Context)")
            item.setData(Qt.UserRole, "NONE")
            self.filters_list.addItem(item)

        # Add all contexts that are in active filters
        for context in self.all_contexts:
            if context.id in self.active_filter_ids:
                item = QListWidgetItem(context.name)
                item.setData(Qt.UserRole, context.id)
                self.filters_list.addItem(item)

    def _on_add_filter(self):
        """Handle add to filter button click."""
        current_item = self.available_list.currentItem()
        if not current_item:
            return

        context_id = current_item.data(Qt.UserRole)

        # Add to active filters
        self.active_filter_ids.add(context_id)

        # Refresh lists
        self._refresh_lists()

    def _on_remove_filter(self):
        """Handle remove from filter button click."""
        current_item = self.filters_list.currentItem()
        if not current_item:
            return

        context_id = current_item.data(Qt.UserRole)

        # Remove from active filters
        self.active_filter_ids.discard(context_id)

        # Refresh lists
        self._refresh_lists()

    def _on_clear_filters(self):
        """Clear all active context filters."""
        self.active_filter_ids.clear()

        # Refresh lists
        self._refresh_lists()

    def get_active_filter_ids(self) -> Set:
        """
        Get the set of active filter IDs.

        Returns:
            Set of context IDs (can include 'NONE' for no context filter)
        """
        return self.active_filter_ids
