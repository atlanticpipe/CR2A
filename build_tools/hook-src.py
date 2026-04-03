"""PyInstaller hook for the src package.

Collects all submodules so 'from src.X import Y' works in frozen builds.
"""
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules('src')
