"""
Runtime hook for PyQt5 to set Qt plugin paths.

This hook ensures that Qt can find its platform plugins (like qwindows.dll)
at runtime when the application is frozen by PyInstaller.
"""

import os
import sys

# CRITICAL: Disable Vulkan ICD discovery BEFORE any DLL loads vulkan-1.dll.
# Without this, ggml-vulkan.dll's Vulkan init crashes with an access violation
# in the frozen PyInstaller environment. Setting VK_ICD_FILENAMES to a
# nonexistent file makes Vulkan find no drivers, so ggml skips GPU init.
if hasattr(sys, '_MEIPASS'):
    os.environ['VK_ICD_FILENAMES'] = 'CR2A_no_vulkan.json'
    os.environ['VK_DRIVER_FILES'] = 'CR2A_no_vulkan.json'

    # Add llama_cpp/lib to DLL search path so llama.dll can find ggml-*.dll
    _llama_lib = os.path.join(sys._MEIPASS, 'llama_cpp', 'lib')
    if os.path.isdir(_llama_lib):
        os.add_dll_directory(_llama_lib)
        os.environ['PATH'] = _llama_lib + os.pathsep + os.environ.get('PATH', '')

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
