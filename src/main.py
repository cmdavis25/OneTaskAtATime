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
from src.services.logging_service import LoggingService
from src.services.database_path_service import DatabasePathService
from src.database.connection import DatabaseConnection
from src.database.settings_dao import SettingsDAO


def main():
    """
    Initialize and launch the OneTaskAtATime application.
    """
    # Initialize logging before anything else
    try:
        # Check for custom database path
        path_service = DatabasePathService()
        custom_db_path = path_service.load_database_path()

        # Log what path was loaded
        if custom_db_path:
            print(f"[STARTUP] Loaded custom database path: {custom_db_path}")
            is_valid, error_msg = DatabaseConnection.validate_database_file(custom_db_path)
            print(f"[STARTUP] Path validation: valid={is_valid}, error={error_msg}")
        else:
            print("[STARTUP] No custom database path found, using default")

        # Get database connection (with custom path if available)
        if custom_db_path and DatabaseConnection.validate_database_file(custom_db_path)[0]:
            print(f"[STARTUP] Creating connection with custom path: {custom_db_path}")
            db_connection = DatabaseConnection(custom_path=custom_db_path)
        else:
            print("[STARTUP] Creating connection with default path")
            db_connection = DatabaseConnection.get_instance()

        settings_dao = SettingsDAO(db_connection.get_connection())

        # Load logging settings
        logging_enabled = settings_dao.get_bool('logging_enabled', True)
        logging_level = settings_dao.get_str('logging_level', 'INFO')
        log_retention_days = settings_dao.get_int('log_retention_days', 30)
        log_max_file_size_mb = settings_dao.get_int('log_max_file_size_mb', 10)

        # Initialize logging service
        LoggingService.initialize(
            enabled=logging_enabled,
            level=logging_level,
            retention_days=log_retention_days,
            max_file_size_mb=log_max_file_size_mb
        )

        logger = LoggingService.get_logger(__name__)
        logger.info("=== OneTaskAtATime Application Starting ===")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Platform: {sys.platform}")

    except Exception as e:
        # If logging setup fails, fall back to defaults
        LoggingService.initialize()
        logger = LoggingService.get_logger(__name__)
        logger.warning(f"Failed to load logging settings from database: {e}")
        logger.info("Using default logging configuration")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("OneTaskAtATime")
        app.setOrganizationName("OneTaskAtATime")
        app.setApplicationVersion("1.0.0")

        logger.info("QApplication initialized")

        window = MainWindow(app)
        window.show()

        logger.info("Main window displayed")

        exit_code = app.exec_()

        logger.info(f"=== OneTaskAtATime Application Exiting (code: {exit_code}) ===")
        LoggingService.shutdown()

        sys.exit(exit_code)

    except Exception as e:
        if LoggingService.is_initialized():
            logger = LoggingService.get_logger(__name__)
            logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
            LoggingService.shutdown()
        raise


if __name__ == "__main__":
    main()
