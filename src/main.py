"""
OneTaskAtATime - Main Application Entry Point

A focused to-do list application designed to help users concentrate on
executing one task at a time using GTD-inspired principles.
"""

import sys
from PyQt5.QtWidgets import QApplication
from .ui.main_window import MainWindow


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
