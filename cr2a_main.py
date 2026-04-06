"""CR2A launcher - entry point for PyInstaller.

This script lives at the project root so that 'src' is importable
as a proper Python package. PyInstaller treats the entry point's
directory as the top-level, so placing this outside src/ ensures
'from src.X import Y' works in both development and frozen builds.
"""
import os
import sys

# In frozen builds, ensure the bundle root is on sys.path
# and disable Vulkan BEFORE any DLL loads ggml-vulkan.dll.
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    if bundle_dir not in sys.path:
        sys.path.insert(0, bundle_dir)
    # Add llama_cpp/lib to DLL search path
    _llama_lib = os.path.join(bundle_dir, 'llama_cpp', 'lib')
    if os.path.isdir(_llama_lib):
        os.add_dll_directory(_llama_lib)
        os.environ['PATH'] = _llama_lib + os.pathsep + os.environ.get('PATH', '')
    # Remove bundled vulkan-1.dll so the system Vulkan loader is used.
    # The bundled copy fails to find ICD drivers; the system one works.
    _bundled_vulkan = os.path.join(bundle_dir, 'vulkan-1.dll')
    if os.path.exists(_bundled_vulkan):
        try:
            os.remove(_bundled_vulkan)
        except OSError:
            pass

# Use software rendering for Qt so the GPU is fully available for LLM inference.
os.environ.setdefault("QT_OPENGL", "software")

# Initialize llama.cpp backend BEFORE PyQt5 is imported.
try:
    import llama_cpp as _llama_cpp
    _llama_cpp.llama_backend_init()
except Exception:
    pass

# Import and run the GUI
from src.qt_gui import main
main()
