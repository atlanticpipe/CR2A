"""
Custom PyInstaller hook for PyQt5.QtWidgets.

Overrides the built-in hook to work around broken QLibraryInfo on systems
where Qt5 returns empty PrefixPath (e.g., '/plugins' instead of the real path).
"""

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

hiddenimports = collect_submodules('PyQt5.QtWidgets')
binaries = collect_dynamic_libs('PyQt5.QtWidgets')
datas = collect_data_files('PyQt5.QtWidgets', include_py_files=False)

# Manually locate the Qt5 plugins directory from the PyQt5 package
try:
    import PyQt5
    pyqt5_dir = os.path.dirname(PyQt5.__file__)

    # Try Qt5 layout first (PyQt5 >= 5.15.4), then legacy Qt layout
    for qt_subdir in ('Qt5', 'Qt'):
        plugins_dir = os.path.join(pyqt5_dir, qt_subdir, 'plugins')
        if os.path.isdir(plugins_dir):
            dest_base = os.path.join('PyQt5', qt_subdir, 'plugins')
            # Collect all plugin subdirectories
            for plugin_type in os.listdir(plugins_dir):
                plugin_path = os.path.join(plugins_dir, plugin_type)
                if os.path.isdir(plugin_path):
                    datas.append((plugin_path, os.path.join(dest_base, plugin_type)))
            break

    # Also collect Qt5 bin directory (contains Qt DLLs on Windows)
    for qt_subdir in ('Qt5', 'Qt'):
        bin_dir = os.path.join(pyqt5_dir, qt_subdir, 'bin')
        if os.path.isdir(bin_dir):
            binaries += [(os.path.join(bin_dir, f), '.') for f in os.listdir(bin_dir) if f.endswith('.dll')]
            break

except Exception as e:
    print(f"Warning: Custom PyQt5.QtWidgets hook: {e}")
