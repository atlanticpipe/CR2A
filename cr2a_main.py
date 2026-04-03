"""CR2A launcher - entry point for PyInstaller.

This script lives at the project root so that 'src' is importable
as a proper Python package. PyInstaller treats the entry point's
directory as the top-level, so placing this outside src/ ensures
'from src.X import Y' works in both development and frozen builds.
"""
import os
import sys

# In frozen builds, ensure the bundle root is on sys.path
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)

# Use software rendering for Qt so the GPU is fully available for LLM inference.
os.environ.setdefault("QT_OPENGL", "software")

# Initialize llama.cpp's Vulkan backend BEFORE PyQt5 is imported.
try:
    import llama_cpp as _llama_cpp
    _llama_cpp.llama_backend_init()
    from src.local_model_client import LocalModelClient  # noqa: F401
except Exception:
    pass

# Import and run the GUI
from src.qt_gui import main
main()
