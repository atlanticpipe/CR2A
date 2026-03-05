"""
PyInstaller hook for PyQt5 to ensure all necessary Qt DLLs and plugins are included.

This hook collects:
- Qt platform plugins (qwindows.dll)
- Qt image format plugins
- Qt style plugins
- All PyQt5 binaries and data files
"""

import os
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_submodules,
    collect_dynamic_libs,
)

# Collect all PyQt5 data files and binaries
datas = collect_data_files('PyQt5', include_py_files=False)

# Collect all PyQt5 submodules
hiddenimports = collect_submodules('PyQt5')

# Collect all PyQt5 dynamic libraries
binaries = collect_dynamic_libs('PyQt5')

# Add Qt plugins
# The most critical is the platforms plugin (qwindows.dll on Windows)
try:
    from PyQt5.QtCore import QLibraryInfo
    try:
        # Try new API (PyQt5 5.15.4+)
        plugins_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.PluginsPath)
    except AttributeError:
        # Fall back to old API
        plugins_dir = QLibraryInfo.location(QLibraryInfo.PluginsPath)

    # Add platform plugins (required for QtWidgets)
    if os.path.exists(os.path.join(plugins_dir, 'platforms')):
        datas += [(os.path.join(plugins_dir, 'platforms'), 'PyQt5/Qt5/plugins/platforms')]

    # Add image format plugins (for icons, images)
    if os.path.exists(os.path.join(plugins_dir, 'imageformats')):
        datas += [(os.path.join(plugins_dir, 'imageformats'), 'PyQt5/Qt5/plugins/imageformats')]

    # Add style plugins (for proper widget rendering)
    if os.path.exists(os.path.join(plugins_dir, 'styles')):
        datas += [(os.path.join(plugins_dir, 'styles'), 'PyQt5/Qt5/plugins/styles')]

except Exception as e:
    # If we can't import PyQt5, skip this (build environment might not have it)
    print(f"Warning: Could not collect Qt plugins: {e}")
