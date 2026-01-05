"""
Custom MessageBox with geometry persistence.

This module provides a MessageBox class that extends QMessageBox with
automatic geometry persistence using GeometryMixin.
"""

from PyQt5.QtWidgets import QMessageBox, QWidget
from PyQt5.QtCore import QTimer
from .geometry_mixin import GeometryMixin
from typing import Optional
import sqlite3


class MessageBox(QMessageBox, GeometryMixin):
    """
    Custom MessageBox that persists its geometry.

    This class extends QMessageBox to add geometry persistence functionality,
    ensuring message boxes remember their position relative to the main window.

    Usage:
        MessageBox.information(parent, db_connection, "Title", "Message")
        MessageBox.warning(parent, db_connection, "Title", "Message")
        MessageBox.question(parent, db_connection, "Title", "Message")
        MessageBox.critical(parent, db_connection, "Title", "Message")
    """

    def __init__(self, icon: QMessageBox.Icon, title: str, text: str,
                 buttons: QMessageBox.StandardButtons,
                 db_connection: sqlite3.Connection,
                 parent: Optional[QWidget] = None,
                 default_width: int = 400,
                 default_height: int = 200):
        """
        Initialize the MessageBox.

        Args:
            icon: Message box icon (Information, Warning, Question, Critical)
            title: Window title
            text: Main message text
            buttons: Standard buttons to display
            db_connection: Database connection for geometry persistence
            parent: Parent widget
            default_width: Default width for first-time display
            default_height: Default height for first-time display
        """
        super().__init__(icon, title, text, buttons, parent)
        self._init_geometry_persistence(db_connection, default_width, default_height)

    @staticmethod
    def information(parent: Optional[QWidget],
                   db_connection: sqlite3.Connection,
                   title: str,
                   text: str,
                   buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
                   default_button: QMessageBox.StandardButton = QMessageBox.Ok) -> int:
        """
        Show an information message box with geometry persistence.

        Args:
            parent: Parent widget
            db_connection: Database connection for geometry persistence
            title: Window title
            text: Message text
            buttons: Buttons to display
            default_button: Default button

        Returns:
            The button that was clicked
        """
        msg_box = MessageBox(QMessageBox.Information, title, text, buttons,
                            db_connection, parent)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec_()

    @staticmethod
    def warning(parent: Optional[QWidget],
               db_connection: sqlite3.Connection,
               title: str,
               text: str,
               buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
               default_button: QMessageBox.StandardButton = QMessageBox.Ok) -> int:
        """
        Show a warning message box with geometry persistence.

        Args:
            parent: Parent widget
            db_connection: Database connection for geometry persistence
            title: Window title
            text: Message text
            buttons: Buttons to display
            default_button: Default button

        Returns:
            The button that was clicked
        """
        msg_box = MessageBox(QMessageBox.Warning, title, text, buttons,
                            db_connection, parent)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec_()

    @staticmethod
    def question(parent: Optional[QWidget],
                db_connection: sqlite3.Connection,
                title: str,
                text: str,
                buttons: QMessageBox.StandardButtons = QMessageBox.Yes | QMessageBox.No,
                default_button: QMessageBox.StandardButton = QMessageBox.No) -> int:
        """
        Show a question message box with geometry persistence.

        Args:
            parent: Parent widget
            db_connection: Database connection for geometry persistence
            title: Window title
            text: Message text
            buttons: Buttons to display
            default_button: Default button

        Returns:
            The button that was clicked
        """
        msg_box = MessageBox(QMessageBox.Question, title, text, buttons,
                            db_connection, parent)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec_()

    @staticmethod
    def critical(parent: Optional[QWidget],
                db_connection: sqlite3.Connection,
                title: str,
                text: str,
                buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
                default_button: QMessageBox.StandardButton = QMessageBox.Ok) -> int:
        """
        Show a critical error message box with geometry persistence.

        Args:
            parent: Parent widget
            db_connection: Database connection for geometry persistence
            title: Window title
            text: Message text
            buttons: Buttons to display
            default_button: Default button

        Returns:
            The button that was clicked
        """
        msg_box = MessageBox(QMessageBox.Critical, title, text, buttons,
                            db_connection, parent)
        msg_box.setDefaultButton(default_button)
        return msg_box.exec_()
