"""
Main Window - Primary application window for OneTaskAtATime

Provides the main application container with menu bar and navigation.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel,
    QMenuBar, QMenu, QAction, QStatusBar
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class MainWindow(QMainWindow):
    """
    Main application window.

    This is the primary container for the OneTaskAtATime application.
    Phase 0: Displays a placeholder welcome message.
    Future phases will integrate Focus Mode and other features.
    """

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("OneTaskAtATime")
        self.setGeometry(100, 100, 800, 600)

        self._init_ui()
        self._create_menu_bar()
        self._create_status_bar()

    def _init_ui(self):
        """Initialize the user interface."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Welcome message (placeholder for Phase 0)
        welcome_label = QLabel("OneTaskAtATime")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_font = QFont()
        welcome_font.setPointSize(24)
        welcome_font.setBold(True)
        welcome_label.setFont(welcome_font)
        layout.addWidget(welcome_label)

        # Subtitle
        subtitle_label = QLabel("Focus on executing one task at a time")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        layout.addWidget(subtitle_label)

        # Version info
        version_label = QLabel("Version 1.0.0 - Phase 0: Project Setup")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: gray;")
        layout.addWidget(version_label)

        # Add stretch to center content
        layout.addStretch()

    def _create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setStatusTip("Exit application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("About OneTaskAtATime")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """Create the status bar."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Ready")

    def _show_about(self):
        """Show about dialog (placeholder)."""
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "About OneTaskAtATime",
            "OneTaskAtATime v1.0.0\n\n"
            "A focused to-do list application designed to help users\n"
            "concentrate on executing one task at a time using\n"
            "GTD-inspired principles.\n\n"
            "Phase 0: Project Setup Complete"
        )
