"""
Geometry Mixin - Provides automatic geometry persistence for dialogs.

This mixin enables dialogs to remember their size and position relative
to the main window across application sessions.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QAction, QWhatsThis
from PyQt5.QtGui import QKeySequence
from typing import Optional


class GeometryMixin:
    """
    Mixin class that provides geometry persistence for QDialog subclasses.

    Usage:
        class MyDialog(QDialog, GeometryMixin):
            def __init__(self, db_connection, parent=None):
                super().__init__(parent)
                self._init_geometry_persistence(db_connection)
                # ... rest of initialization ...

    The mixin automatically:
    - Restores dialog position/size on showEvent
    - Saves position/size on closeEvent
    - Positions dialogs relative to main window
    - Handles multi-monitor configurations
    - Provides default offsets for first-time dialogs
    """

    def _init_geometry_persistence(self, db_connection,
                                   default_width: Optional[int] = None,
                                   default_height: Optional[int] = None):
        """
        Initialize geometry persistence for this dialog.

        Args:
            db_connection: DatabaseConnection instance or sqlite3.Connection
            default_width: Default width for first-time display (optional)
            default_height: Default height for first-time display (optional)
        """
        # Import here to avoid circular dependencies
        from ..database.settings_dao import SettingsDAO

        # Handle both DatabaseConnection objects and raw connections
        if hasattr(db_connection, 'get_connection'):
            self._geometry_settings_dao = SettingsDAO(db_connection.get_connection())
        else:
            self._geometry_settings_dao = SettingsDAO(db_connection)

        self._geometry_restored = False
        self._geometry_default_width = default_width
        self._geometry_default_height = default_height

        # Generate unique settings key based on class name
        self._geometry_settings_key = f'dialog_geometry_{self.__class__.__name__}'

        # Enable Shift+F1 WhatsThis shortcut for dialogs
        self._setup_whatsthis_shortcut()

    def showEvent(self, event):
        """Override showEvent to restore geometry on first show."""
        # Call parent class showEvent if it exists
        if hasattr(super(), 'showEvent'):
            super().showEvent(event)

        if not self._geometry_restored:
            self._restore_dialog_geometry()
            self._geometry_restored = True

    def hideEvent(self, event):
        """
        Override hideEvent to save geometry right before dialog is hidden.

        This is called immediately before the dialog becomes invisible,
        which is the ideal time to capture the final geometry regardless
        of how the dialog is being closed (accept, reject, or close button).
        """
        self._save_dialog_geometry()

        # Call parent class hideEvent if it exists
        if hasattr(super(), 'hideEvent'):
            super().hideEvent(event)

    def accept(self):
        """Override accept to call parent's accept method."""
        # Find and call QDialog.accept() directly by searching the MRO
        for base in self.__class__.__mro__:
            if base.__name__ == 'QDialog' and hasattr(base, 'accept'):
                base.accept(self)
                return
        # Fallback: try super() in case QDialog is accessible
        if hasattr(super(), 'accept'):
            super().accept()

    def reject(self):
        """Override reject to call parent's reject method."""
        # Find and call QDialog.reject() directly by searching the MRO
        for base in self.__class__.__mro__:
            if base.__name__ == 'QDialog' and hasattr(base, 'reject'):
                base.reject(self)
                return
        # Fallback: try super() in case QDialog is accessible
        if hasattr(super(), 'reject'):
            super().reject()

    def closeEvent(self, event):
        """Override closeEvent to call parent's closeEvent."""
        # Call parent class closeEvent if it exists
        if hasattr(super(), 'closeEvent'):
            super().closeEvent(event)

    def _restore_dialog_geometry(self):
        """Restore saved dialog geometry relative to main window."""
        try:
            saved_geometry = self._geometry_settings_dao.get(self._geometry_settings_key)

            if not saved_geometry:
                # First time - position at default offset from main window
                self._apply_default_geometry()
                return

            # Get main window position as reference
            main_window = self._get_main_window()
            if not main_window:
                # No main window - use absolute positioning
                self._apply_absolute_geometry(saved_geometry)
                return

            # Calculate absolute position from relative offset
            main_x = main_window.x()
            main_y = main_window.y()

            rel_x = saved_geometry.get('relative_x', 50)
            rel_y = saved_geometry.get('relative_y', 50)
            width = saved_geometry.get('width', self._geometry_default_width or 600)
            height = saved_geometry.get('height', self._geometry_default_height or 400)

            abs_x = main_x + rel_x
            abs_y = main_y + rel_y

            # Ensure dialog is visible on screen
            screen = QApplication.screenAt(main_window.geometry().center())
            if not screen:
                screen = QApplication.primaryScreen()

            screen_geometry = screen.availableGeometry()

            # Keep dialog within screen bounds (ensure at least 100px visible)
            if abs_x + width > screen_geometry.x() + screen_geometry.width():
                abs_x = screen_geometry.x() + screen_geometry.width() - width - 20
            if abs_y + height > screen_geometry.y() + screen_geometry.height():
                abs_y = screen_geometry.y() + screen_geometry.height() - height - 20
            if abs_x < screen_geometry.x():
                abs_x = screen_geometry.x() + 20
            if abs_y < screen_geometry.y():
                abs_y = screen_geometry.y() + 20

            # Apply geometry
            self.setGeometry(abs_x, abs_y, width, height)

        except Exception as e:
            # On any error, fall back to default geometry
            print(f"Warning: Failed to restore geometry for {self.__class__.__name__}: {e}")
            self._apply_default_geometry()

    def _save_dialog_geometry(self):
        """Save current dialog geometry relative to main window."""
        try:
            # Get main window position as reference
            main_window = self._get_main_window()
            if not main_window:
                # No main window - save absolute position
                self._save_absolute_geometry()
                return

            # Calculate relative position
            main_x = main_window.x()
            main_y = main_window.y()

            # Use geometry() (client area) for consistency with setGeometry()
            # This prevents drift caused by window decoration offsets
            geom = self.geometry()

            rel_x = geom.x() - main_x
            rel_y = geom.y() - main_y

            geometry_data = {
                'relative_x': rel_x,
                'relative_y': rel_y,
                'width': geom.width(),
                'height': geom.height()
            }

            self._geometry_settings_dao.set(
                self._geometry_settings_key,
                geometry_data,
                'json',
                f'Geometry for {self.__class__.__name__}'
            )

        except Exception as e:
            # Silently fail - don't crash on save errors
            print(f"Warning: Failed to save geometry for {self.__class__.__name__}: {e}")

    def _apply_default_geometry(self):
        """Apply default geometry on first run."""
        main_window = self._get_main_window()

        width = self._geometry_default_width or 600
        height = self._geometry_default_height or 400

        if main_window:
            # Position at default offset (50, 50) from main window
            x = main_window.x() + 50
            y = main_window.y() + 50

            # Ensure dialog fits on screen
            screen = QApplication.screenAt(main_window.geometry().center())
            if not screen:
                screen = QApplication.primaryScreen()

            screen_geometry = screen.availableGeometry()

            # Adjust if dialog would go off-screen
            if x + width > screen_geometry.x() + screen_geometry.width():
                x = screen_geometry.x() + screen_geometry.width() - width - 20
            if y + height > screen_geometry.y() + screen_geometry.height():
                y = screen_geometry.y() + screen_geometry.height() - height - 20
        else:
            # Center on screen
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.x() + (screen_geometry.width() - width) // 2
            y = screen_geometry.y() + (screen_geometry.height() - height) // 2

        self.setGeometry(x, y, width, height)

    def _apply_absolute_geometry(self, saved_geometry):
        """Apply geometry without main window reference (fallback)."""
        x = saved_geometry.get('x', 100)
        y = saved_geometry.get('y', 100)
        width = saved_geometry.get('width', self._geometry_default_width or 600)
        height = saved_geometry.get('height', self._geometry_default_height or 400)

        # Validate geometry is on-screen
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        # Ensure at least partially visible
        if x + width < screen_geometry.x() + 100 or x > screen_geometry.x() + screen_geometry.width() - 100:
            x = screen_geometry.x() + 100
        if y < screen_geometry.y() or y + height > screen_geometry.y() + screen_geometry.height():
            y = screen_geometry.y() + 100

        self.setGeometry(x, y, width, height)

    def _save_absolute_geometry(self):
        """Save absolute geometry without main window reference (fallback)."""
        dialog_geometry = self.geometry()

        geometry_data = {
            'x': dialog_geometry.x(),
            'y': dialog_geometry.y(),
            'width': dialog_geometry.width(),
            'height': dialog_geometry.height()
        }

        self._geometry_settings_dao.set(
            self._geometry_settings_key,
            geometry_data,
            'json',
            f'Geometry for {self.__class__.__name__}'
        )

    def _get_main_window(self):
        """Get reference to main window."""
        parent = self.parent()

        # Walk up parent chain to find MainWindow
        while parent:
            if parent.__class__.__name__ == 'MainWindow':
                return parent
            parent = parent.parent() if hasattr(parent, 'parent') else None

        # Fallback: Try to find MainWindow in application
        for widget in QApplication.topLevelWidgets():
            if widget.__class__.__name__ == 'MainWindow':
                return widget

        return None

    def _setup_whatsthis_shortcut(self):
        """
        Set up Shift+F1 keyboard shortcut to enter WhatsThis mode.

        This is necessary because Qt.WindowContextHelpButtonHint doesn't
        always properly register the Shift+F1 shortcut on all platforms
        (especially Windows). By explicitly adding a QAction, we ensure
        the shortcut works consistently across all platforms.
        """
        # Create WhatsThis action
        whatsthis_action = QAction(self)
        whatsthis_action.setShortcut(QKeySequence("Shift+F1"))
        whatsthis_action.triggered.connect(QWhatsThis.enterWhatsThisMode)

        # Add action to the dialog (makes shortcut active)
        self.addAction(whatsthis_action)
