"""
Project Tag Management Dialog - Manage project tags

Phase 4: Allows users to create, edit, and delete project tags.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QTextEdit, QFormLayout,
    QMessageBox, QColorDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from typing import List, Optional
from ..models.project_tag import ProjectTag
from ..database.connection import DatabaseConnection
from ..database.project_tag_dao import ProjectTagDAO
from .geometry_mixin import GeometryMixin
from .message_box import MessageBox


class ProjectTagManagementDialog(QDialog, GeometryMixin):
    """
    Dialog for managing project tags.

    Features:
    - View all project tags
    - Create new project tag
    - Edit existing project tag
    - Delete project tag (with confirmation)
    - Color picker for visual organization
    """

    tags_changed = pyqtSignal()

    def __init__(self, db_connection: DatabaseConnection, parent=None):
        """
        Initialize the project tag management dialog.

        Args:
            db_connection: Database connection
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_connection = db_connection
        self.tag_dao = ProjectTagDAO(db_connection.get_connection())
        self.tags: List[ProjectTag] = []
        self.selected_color: Optional[str] = None

        # Initialize geometry persistence
        self._init_geometry_persistence(db_connection, default_width=600, default_height=500)

        self._init_ui()
        self._load_tags()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Manage Project Tags")
        self.setMinimumWidth(650)
        self.setMinimumHeight(500)

        # Enable WhatsThis help button
        self.setWindowFlags(self.windowFlags() | Qt.WindowContextHelpButtonHint)

        # Set WhatsThis text for the dialog
        self.setWhatsThis(
            "This dialog allows you to manage project tags for organizing tasks. "
            "Tags provide flat organization without nested hierarchies. Tasks can have multiple tags. "
            "Create, edit, or delete tags, and assign colors for visual organization. Click the ? button for help."
        )

        layout = QVBoxLayout()
        layout.setSpacing(15)
        self.setLayout(layout)

        # Header
        header_label = QLabel("Manage Project Tags")
        header_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(header_label)

        info_label = QLabel(
            "Project tags provide flat organization for tasks without nested hierarchies.\n"
            "Tasks can have multiple project tags for flexible categorization."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(info_label)

        # Main content area
        content_layout = QHBoxLayout()

        # Left side: List of tags
        list_layout = QVBoxLayout()

        list_label = QLabel("Existing Project Tags:")
        list_label.setStyleSheet("font-weight: bold;")
        list_layout.addWidget(list_label)

        self.tag_list = QListWidget()
        self.tag_list.currentItemChanged.connect(self._on_tag_selected)
        self.tag_list.setWhatsThis(
            "List of all project tags in the system. Select a tag to edit its details, or use the New button to create a new tag."
        )
        list_layout.addWidget(self.tag_list)

        # List action buttons
        list_button_layout = QHBoxLayout()

        self.add_button = QPushButton("+ New")
        self.add_button.setStyleSheet("""
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
        self.add_button.clicked.connect(self._on_new_tag)
        self.add_button.setWhatsThis(
            "Create a new project tag. This clears the form so you can enter details for a new tag."
        )
        list_button_layout.addWidget(self.add_button)

        self.delete_button = QPushButton("Delete")
        self.delete_button.setStyleSheet("""
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
        self.delete_button.clicked.connect(self._on_delete_tag)
        self.delete_button.setWhatsThis(
            "Delete the selected project tag. This will remove the tag from all tasks that use it. You'll be asked to confirm before deletion."
        )
        list_button_layout.addWidget(self.delete_button)

        list_button_layout.addStretch()

        list_layout.addLayout(list_button_layout)

        content_layout.addLayout(list_layout, 1)

        # Initialize button states (will be updated when list selection changes)
        self.delete_button.setEnabled(False)

        # Right side: Edit form
        form_layout = QVBoxLayout()

        form_label = QLabel("Project Tag Details:")
        form_label.setStyleSheet("font-weight: bold;")
        form_layout.addWidget(form_label)

        form_fields = QFormLayout()

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Website Redesign, Personal Development")
        self.name_edit.setWhatsThis(
            "Enter a unique name for this project tag. Tags help organize tasks by project or area of focus."
        )
        form_fields.addRow("Name*:", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Optional description...")
        self.description_edit.setMaximumHeight(100)
        self.description_edit.setWhatsThis(
            "Optional description to provide additional context about this project tag. For example, you might describe the project scope or goals."
        )
        form_fields.addRow("Description:", self.description_edit)

        # Color picker
        color_layout = QHBoxLayout()

        self.color_display = QLabel()
        self.color_display.setFixedSize(50, 30)
        self.color_display.setStyleSheet("border: 1px solid #ccc; background-color: #cccccc;")
        color_layout.addWidget(self.color_display)

        color_btn = QPushButton("Choose Color...")
        color_btn.clicked.connect(self._on_choose_color)
        color_btn.setWhatsThis(
            "Select a color for this project tag. Colors provide visual organization when viewing tasks with multiple tags."
        )
        color_layout.addWidget(color_btn)

        color_layout.addStretch()

        form_fields.addRow("Color:", color_layout)

        form_layout.addLayout(form_fields)

        # Form action buttons
        form_button_layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_form)
        form_button_layout.addWidget(clear_btn)

        form_button_layout.addStretch()

        self.save_btn = QPushButton("Save")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.save_btn.clicked.connect(self._on_save_tag)
        self.save_btn.setWhatsThis(
            "Save the current project tag. If editing an existing tag, this updates it. If creating a new tag, this adds it to the system."
        )
        self.edit_button = self.save_btn  # Alias for test compatibility
        self.edit_button.setEnabled(False)  # Initialize as disabled
        form_button_layout.addWidget(self.save_btn)

        form_layout.addLayout(form_button_layout)
        form_layout.addStretch()

        content_layout.addLayout(form_layout, 1)

        layout.addLayout(content_layout)

        # Bottom buttons
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        bottom_layout.addWidget(self.close_button)

        layout.addLayout(bottom_layout)

        # Track current tag being edited
        self.current_tag: Optional[ProjectTag] = None

    def _load_tags(self):
        """Load all project tags from database."""
        self.tags = self.tag_dao.get_all()
        self._refresh_list()

    def load_tags(self):
        """Public method to refresh tag list (for test compatibility)."""
        self._load_tags()

    def _refresh_list(self):
        """Refresh the tag list widget."""
        self.tag_list.clear()

        for tag in self.tags:
            item = QListWidgetItem(tag.name)
            item.setData(Qt.UserRole, tag.id)

            # Show color indicator
            if tag.color:
                color = QColor(tag.color)
                item.setBackground(color)
                # Set text color based on background brightness
                brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
                if brightness < 128:
                    item.setForeground(QColor(Qt.white))

            self.tag_list.addItem(item)

        if self.tags:
            self.tag_list.setCurrentRow(0)

    def _on_tag_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """
        Handle tag selection.

        Args:
            current: Currently selected item
            previous: Previously selected item
        """
        if not current:
            self._clear_form()
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            return

        # Enable buttons when item is selected
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

        tag_id = current.data(Qt.UserRole)
        tag = self.tag_dao.get_by_id(tag_id)

        if tag:
            self.current_tag = tag
            self.name_edit.setText(tag.name)
            self.description_edit.setText(tag.description or "")

            # Set color
            if tag.color:
                self.selected_color = tag.color
                self.color_display.setStyleSheet(
                    f"border: 1px solid #ccc; background-color: {tag.color};"
                )
            else:
                self.selected_color = None
                self.color_display.setStyleSheet(
                    "border: 1px solid #ccc; background-color: #cccccc;"
                )

    def _on_new_tag(self):
        """Handle new tag button click."""
        self._clear_form()
        self.tag_list.clearSelection()
        self.edit_button.setEnabled(True)  # Enable Save button for new tag
        self.delete_button.setEnabled(False)
        self.name_edit.setFocus()

    def _on_choose_color(self):
        """Handle color picker button click."""
        initial_color = QColor(self.selected_color) if self.selected_color else QColor(Qt.gray)

        color = QColorDialog.getColor(initial_color, self, "Choose Tag Color")

        if color.isValid():
            self.selected_color = color.name()
            self.color_display.setStyleSheet(
                f"border: 1px solid #ccc; background-color: {self.selected_color};"
            )

    def _on_save_tag(self):
        """Handle save tag button click."""
        name = self.name_edit.text().strip()

        if not name:
            MessageBox.warning(
                self,
                self.db_connection.get_connection(),
                "Invalid Input",
                "Please enter a project tag name."
            )
            self.name_edit.setFocus()
            return

        description = self.description_edit.toPlainText().strip() or None

        try:
            if self.current_tag and self.current_tag.id:
                # Update existing tag
                self.current_tag.name = name
                self.current_tag.description = description
                self.current_tag.color = self.selected_color
                self.tag_dao.update(self.current_tag)
                MessageBox.information(
                    self,
                    self.db_connection.get_connection(),
                    "Success",
                    f"Project tag '{name}' updated successfully."
                )
            else:
                # Create new tag
                new_tag = ProjectTag(
                    name=name,
                    description=description,
                    color=self.selected_color
                )
                self.tag_dao.create(new_tag)
                MessageBox.information(
                    self,
                    self.db_connection.get_connection(),
                    "Success",
                    f"Project tag '{name}' created successfully."
                )

            self._load_tags()
            self._clear_form()
            self.tags_changed.emit()

        except Exception as e:
            MessageBox.critical(
                self,
                self.db_connection.get_connection(),
                "Error",
                f"Failed to save project tag: {str(e)}"
            )

    def _on_delete_tag(self):
        """Handle delete tag button click."""
        current_item = self.tag_list.currentItem()
        if not current_item:
            MessageBox.warning(
                self,
                self.db_connection.get_connection(),
                "No Selection",
                "Please select a project tag to delete."
            )
            return

        tag_id = current_item.data(Qt.UserRole)
        tag_name = current_item.text()

        reply = MessageBox.question(
            self,
            self.db_connection.get_connection(),
            "Delete Project Tag",
            f"Are you sure you want to delete project tag '{tag_name}'?\n\n"
            "This will remove the tag from all tasks.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.tag_dao.delete(tag_id)
                self._load_tags()
                self._clear_form()
                self.tags_changed.emit()
                MessageBox.information(
                    self,
                    self.db_connection.get_connection(),
                    "Success",
                    f"Project tag '{tag_name}' deleted successfully."
                )
            except Exception as e:
                MessageBox.critical(
                    self,
                    self.db_connection.get_connection(),
                    "Error",
                    f"Failed to delete project tag: {str(e)}"
                )

    def _clear_form(self):
        """Clear the edit form."""
        self.current_tag = None
        self.name_edit.clear()
        self.description_edit.clear()
        self.selected_color = None
        self.color_display.setStyleSheet(
            "border: 1px solid #ccc; background-color: #cccccc;"
        )
