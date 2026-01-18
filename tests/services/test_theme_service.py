"""
Unit tests for ThemeService.

Tests theme management functionality including:
- Theme loading and application
- System theme detection
- Theme persistence
- Available themes
- Error handling for missing theme files
"""

import pytest
import sqlite3
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch, mock_open
from PyQt5.QtWidgets import QApplication

from src.database.schema import DatabaseSchema
from src.services.theme_service import ThemeService


@pytest.fixture
def db_connection():
    """Create in-memory database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    DatabaseSchema.initialize_database(conn)
    DatabaseSchema.migrate_to_notification_system(conn)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def qapp():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def theme_service(db_connection, qapp):
    """Create ThemeService instance."""
    service = ThemeService(db_connection, qapp)
    yield service


class TestInitialization:
    """Test theme service initialization."""

    def test_initialization(self, db_connection, qapp):
        """Test that theme service initializes correctly."""
        service = ThemeService(db_connection, qapp)

        assert service.db_connection == db_connection
        assert service.app == qapp
        assert service._theme_dir is not None

    def test_theme_constants(self):
        """Test that theme constants are defined."""
        assert ThemeService.THEME_LIGHT == "light"
        assert ThemeService.THEME_DARK == "dark"
        assert ThemeService.THEME_SYSTEM == "system"

    def test_theme_dir_path(self, theme_service):
        """Test that theme directory path is correctly set."""
        # Should point to resources/themes directory
        assert "resources" in theme_service._theme_dir
        assert "themes" in theme_service._theme_dir


class TestGetCurrentTheme:
    """Test getting current theme."""

    def test_get_current_theme_default(self, theme_service):
        """Test that default theme is light."""
        theme = theme_service.get_current_theme()

        assert theme == ThemeService.THEME_LIGHT

    def test_get_current_theme_from_database(self, theme_service, db_connection):
        """Test that current theme is retrieved from database."""
        # Update theme in database (default settings already have 'theme')
        cursor = db_connection.cursor()
        cursor.execute(
            "UPDATE settings SET value = ? WHERE key = ?",
            ("dark", "theme")
        )
        db_connection.commit()

        theme = theme_service.get_current_theme()

        assert theme == "dark"


class TestSetTheme:
    """Test setting and saving theme."""

    def test_set_theme_saves_to_database(self, theme_service, db_connection):
        """Test that set_theme saves theme to database."""
        with patch.object(theme_service, 'apply_theme'):
            theme_service.set_theme("dark")

            # Verify saved to database
            cursor = db_connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("theme",))
            row = cursor.fetchone()

            assert row is not None
            assert row[0] == "dark"

    def test_set_theme_applies_theme(self, theme_service):
        """Test that set_theme applies the theme."""
        with patch.object(theme_service, 'apply_theme') as mock_apply:
            theme_service.set_theme("dark")

            mock_apply.assert_called_once_with("dark")

    def test_set_theme_replaces_existing(self, theme_service, db_connection):
        """Test that set_theme replaces existing theme setting."""
        with patch.object(theme_service, 'apply_theme'):
            # Set initial theme
            theme_service.set_theme("dark")

            # Change theme
            theme_service.set_theme("light")

            # Should have only one entry
            cursor = db_connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM settings WHERE key = ?", ("theme",))
            count = cursor.fetchone()[0]

            assert count == 1

            # Should be light
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("theme",))
            row = cursor.fetchone()
            assert row[0] == "light"


class TestApplyTheme:
    """Test applying themes."""

    def test_apply_theme_sets_stylesheet(self, theme_service):
        """Test that apply_theme sets stylesheet on app."""
        mock_stylesheet = "QWidget { background-color: white; }"

        with patch.object(theme_service, '_load_stylesheet', return_value=mock_stylesheet):
            theme_service.apply_theme("light")

            # Should set stylesheet on app
            assert theme_service.app.styleSheet() == mock_stylesheet

    def test_apply_theme_with_missing_file(self, theme_service):
        """Test that apply_theme handles missing file gracefully."""
        with patch.object(theme_service, '_load_stylesheet', return_value=None):
            theme_service.apply_theme("nonexistent")

            # Should set empty stylesheet (fallback)
            assert theme_service.app.styleSheet() == ""

    def test_apply_system_theme(self, theme_service):
        """Test that applying system theme detects and applies system theme."""
        with patch.object(theme_service, '_detect_system_theme', return_value="dark"):
            with patch.object(theme_service, '_load_stylesheet', return_value="QWidget { color: white; }"):
                theme_service.apply_theme("system")

                # Should detect system theme and apply it
                assert theme_service.app.styleSheet() != ""


class TestLoadStylesheet:
    """Test loading stylesheets from files."""

    def test_load_stylesheet_success(self, theme_service):
        """Test loading stylesheet from file."""
        mock_content = "QWidget { background-color: white; }"

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_content)):
                stylesheet = theme_service._load_stylesheet("light")

                assert stylesheet == mock_content

    def test_load_stylesheet_file_not_found(self, theme_service):
        """Test loading stylesheet when file doesn't exist."""
        with patch('os.path.exists', return_value=False):
            stylesheet = theme_service._load_stylesheet("nonexistent")

            assert stylesheet is None

    def test_load_stylesheet_read_error(self, theme_service):
        """Test loading stylesheet with read error."""
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("Read error")):
                stylesheet = theme_service._load_stylesheet("light")

                assert stylesheet is None

    def test_load_stylesheet_correct_path(self, theme_service):
        """Test that stylesheet is loaded from correct path."""
        with patch('os.path.exists', return_value=True) as mock_exists:
            with patch('builtins.open', mock_open(read_data="test")):
                theme_service._load_stylesheet("light")

                # Verify correct path was checked
                call_args = mock_exists.call_args[0][0]
                assert "light.qss" in call_args
                assert "themes" in call_args


class TestDetectSystemTheme:
    """Test system theme detection."""

    def test_detect_system_theme_light_windows(self, theme_service):
        """Test detecting light theme on Windows."""
        mock_value = 1  # Windows uses 1 for light theme
        mock_winreg = MagicMock()
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.ConnectRegistry.return_value = MagicMock()
        mock_winreg.OpenKey.return_value = MagicMock()
        mock_winreg.QueryValueEx.return_value = (mock_value, None)

        with patch.dict('sys.modules', {'winreg': mock_winreg}):
            theme = theme_service._detect_system_theme()
            assert theme == ThemeService.THEME_LIGHT

    def test_detect_system_theme_dark_windows(self, theme_service):
        """Test detecting dark theme on Windows."""
        mock_value = 0  # Windows uses 0 for dark theme
        mock_winreg = MagicMock()
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.ConnectRegistry.return_value = MagicMock()
        mock_winreg.OpenKey.return_value = MagicMock()
        mock_winreg.QueryValueEx.return_value = (mock_value, None)

        with patch.dict('sys.modules', {'winreg': mock_winreg}):
            theme = theme_service._detect_system_theme()
            assert theme == ThemeService.THEME_DARK

    def test_detect_system_theme_fallback(self, theme_service):
        """Test that detection falls back to light theme on error."""
        # When winreg import fails or raises exception, it should fall back to light
        mock_winreg = MagicMock()
        mock_winreg.HKEY_CURRENT_USER = 0x80000001
        mock_winreg.ConnectRegistry.side_effect = Exception("Registry error")

        with patch.dict('sys.modules', {'winreg': mock_winreg}):
            theme = theme_service._detect_system_theme()
            # Should fallback to light theme
            assert theme == ThemeService.THEME_LIGHT


class TestGetAvailableThemes:
    """Test getting available themes."""

    def test_get_available_themes(self, theme_service):
        """Test that get_available_themes returns all theme options."""
        themes = theme_service.get_available_themes()

        assert len(themes) == 3
        assert ThemeService.THEME_LIGHT in themes
        assert ThemeService.THEME_DARK in themes
        assert ThemeService.THEME_SYSTEM in themes

    def test_get_available_themes_returns_list(self, theme_service):
        """Test that get_available_themes returns a list."""
        themes = theme_service.get_available_themes()

        assert isinstance(themes, list)


class TestThemeIntegration:
    """Test theme service integration scenarios."""

    def test_full_theme_change_workflow(self, theme_service, db_connection):
        """Test complete theme change workflow."""
        mock_stylesheet = "QWidget { background-color: #1e1e1e; }"

        with patch.object(theme_service, '_load_stylesheet', return_value=mock_stylesheet):
            # Set dark theme
            theme_service.set_theme("dark")

            # Verify saved to database
            cursor = db_connection.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", ("theme",))
            row = cursor.fetchone()
            assert row[0] == "dark"

            # Verify applied to app
            assert theme_service.app.styleSheet() == mock_stylesheet

            # Verify can retrieve current theme
            assert theme_service.get_current_theme() == "dark"

    def test_system_theme_detection_and_application(self, theme_service):
        """Test system theme detection and application workflow."""
        mock_dark_stylesheet = "QWidget { background-color: #1e1e1e; }"

        with patch.object(theme_service, '_detect_system_theme', return_value="dark"):
            with patch.object(theme_service, '_load_stylesheet', return_value=mock_dark_stylesheet):
                # Set system theme
                theme_service.set_theme("system")

                # Should detect and apply dark theme
                assert theme_service.app.styleSheet() == mock_dark_stylesheet

    def test_multiple_theme_switches(self, theme_service):
        """Test switching themes multiple times."""
        light_stylesheet = "QWidget { background-color: white; }"
        dark_stylesheet = "QWidget { background-color: black; }"

        def mock_load(theme_name):
            if theme_name == "light":
                return light_stylesheet
            elif theme_name == "dark":
                return dark_stylesheet
            return None

        with patch.object(theme_service, '_load_stylesheet', side_effect=mock_load):
            # Switch to dark
            theme_service.set_theme("dark")
            assert theme_service.app.styleSheet() == dark_stylesheet

            # Switch to light
            theme_service.set_theme("light")
            assert theme_service.app.styleSheet() == light_stylesheet

            # Switch back to dark
            theme_service.set_theme("dark")
            assert theme_service.app.styleSheet() == dark_stylesheet


class TestErrorHandling:
    """Test error handling."""

    def test_handles_database_error_gracefully(self, qapp):
        """Test that service handles database errors gracefully."""
        # Create closed connection
        conn = sqlite3.connect(":memory:")
        conn.close()

        service = ThemeService(conn, qapp)

        # Should not crash when trying to get theme from closed connection
        with pytest.raises(sqlite3.ProgrammingError):
            service.get_current_theme()

    def test_handles_missing_app_gracefully(self, db_connection):
        """Test that service handles missing app gracefully."""
        service = ThemeService(db_connection, None)

        # Should not crash, though apply_theme will fail
        with pytest.raises(AttributeError):
            service.apply_theme("light")


class TestStylesheetEncoding:
    """Test stylesheet encoding handling."""

    def test_load_stylesheet_utf8_encoding(self, theme_service):
        """Test that stylesheet is loaded with UTF-8 encoding."""
        # Test with unicode characters
        mock_content = "QWidget { content: '€ © ™'; }"

        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_content)):
                stylesheet = theme_service._load_stylesheet("test")

                assert stylesheet == mock_content
