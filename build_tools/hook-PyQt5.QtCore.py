"""
Custom PyInstaller hook for PyQt5.QtCore.

Overrides the built-in hook to work around broken QLibraryInfo paths.
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

hiddenimports = collect_submodules('PyQt5.QtCore')
binaries = collect_dynamic_libs('PyQt5.QtCore')
datas = collect_data_files('PyQt5.QtCore', include_py_files=False)
