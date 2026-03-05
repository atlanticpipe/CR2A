"""
Runtime hook for PyQt5 to set Qt plugin paths.

This hook ensures that Qt can find its platform plugins (like qwindows.dll)
at runtime when the application is frozen by PyInstaller.
"""

import os
import sys

# Set the Qt plugin path to the bundled plugins directory
if hasattr(sys, '_MEIPASS'):
    # Running as a PyInstaller bundle
    qt_plugins_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt5', 'plugins')

    # Set environment variable for Qt to find plugins
    os.environ['QT_PLUGIN_PATH'] = qt_plugins_path

    # Also try the alternate location
    if not os.path.exists(qt_plugins_path):
        qt_plugins_path = os.path.join(sys._MEIPASS, 'PyQt5', 'Qt', 'plugins')
        if os.path.exists(qt_plugins_path):
            os.environ['QT_PLUGIN_PATH'] = qt_plugins_path
