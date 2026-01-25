"""
OneTaskAtATime - Main Application Entry Point

A focused to-do list application designed to help users concentrate on
executing one task at a time using GTD-inspired principles.
"""

import sys
import os

# Add src directory to path for PyInstaller compatibility
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = sys._MEIPASS
else:
    # Running as script
    application_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, application_path)

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """
    Initialize and launch the OneTaskAtATime application.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("OneTaskAtATime")
    app.setOrganizationName("OneTaskAtATime")
    app.setApplicationVersion("1.0.0")

    window = MainWindow(app)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
