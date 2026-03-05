"""
PyInstaller hook for pytesseract to ensure the module is properly included.

This hook ensures that pytesseract and all its submodules are collected.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect all pytesseract submodules
hiddenimports = collect_submodules('pytesseract')

# Collect any data files (though pytesseract is primarily code)
datas = collect_data_files('pytesseract', include_py_files=True)
