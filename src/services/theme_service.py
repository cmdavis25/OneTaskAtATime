"""Theme management service for Qt stylesheet application.

Manages loading and applying light/dark themes to the application.
"""
import os
from typing import Optional
from PyQt5.QtWidgets import QApplication
import sqlite3


class ThemeService:
    """Service for managing application themes and stylesheets."""

    THEME_LIGHT = "light"
    THEME_DARK = "dark"
    THEME_SYSTEM = "system"

    def __init__(self, db_connection: sqlite3.Connection, app: QApplication):
        """Initialize theme service.

        Args:
            db_connection: Database connection for settings access
            app: QApplication instance to apply stylesheets to
        """
        self.db_connection = db_connection
        self.app = app
        self._theme_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "resources", "themes"
        )

    def get_current_theme(self) -> str:
        """Get the currently configured theme name.

        Returns:
            Theme name (light, dark, or system)
        """
        cursor = self.db_connection.cursor()
        cursor.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("theme",)
        )
        row = cursor.fetchone()
        return row[0] if row else self.THEME_LIGHT

    def apply_theme(self, theme_name: str) -> None:
        """Apply the specified theme to the application.

        Args:
            theme_name: Name of theme to apply (light, dark, or system)
        """
        # Resolve system theme if needed
        if theme_name == self.THEME_SYSTEM:
            theme_name = self._detect_system_theme()

        # Load and apply stylesheet
        stylesheet = self._load_stylesheet(theme_name)
        if stylesheet:
            self.app.setStyleSheet(stylesheet)
        else:
            # Fallback to no stylesheet (default Qt theme)
            self.app.setStyleSheet("")

    def _load_stylesheet(self, theme_name: str) -> Optional[str]:
        """Load stylesheet content from file.

        Args:
            theme_name: Name of theme file to load

        Returns:
            Stylesheet content as string, or None if file not found
        """
        theme_file = os.path.join(self._theme_dir, f"{theme_name}.qss")

        if not os.path.exists(theme_file):
            print(f"Warning: Theme file not found: {theme_file}")
            return None

        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading theme {theme_name}: {e}")
            return None

    def _detect_system_theme(self) -> str:
        """Detect system theme preference.

        Returns:
            THEME_LIGHT or THEME_DARK based on system settings
        """
        # Try to detect system theme on Windows
        try:
            import winreg
            registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
            key = winreg.OpenKey(
                registry,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            winreg.CloseKey(key)

            # value == 0 means dark theme, 1 means light theme
            return self.THEME_LIGHT if value == 1 else self.THEME_DARK
        except Exception:
            # Fallback to light theme if detection fails
            return self.THEME_LIGHT

    def set_theme(self, theme_name: str) -> None:
        """Set and save theme preference.

        Args:
            theme_name: Theme to set (light, dark, or system)
        """
        cursor = self.db_connection.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO settings (key, value, type, description)
               VALUES (?, ?, 'string', 'UI theme (light/dark/system)')""",
            ("theme", theme_name)
        )
        self.db_connection.commit()
        self.apply_theme(theme_name)

    def get_available_themes(self) -> list[str]:
        """Get list of available themes.

        Returns:
            List of theme names
        """
        return [self.THEME_LIGHT, self.THEME_DARK, self.THEME_SYSTEM]
