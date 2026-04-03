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
    # Disable Vulkan ICD discovery — prevents ggml-vulkan.dll from crashing
    # with an access violation when no Vulkan driver is available.
    os.environ['VK_ICD_FILENAMES'] = 'CR2A_no_vulkan.json'
    os.environ['VK_DRIVER_FILES'] = 'CR2A_no_vulkan.json'
    # Add llama_cpp/lib to DLL search path
    _llama_lib = os.path.join(bundle_dir, 'llama_cpp', 'lib')
    if os.path.isdir(_llama_lib):
        os.add_dll_directory(_llama_lib)
        os.environ['PATH'] = _llama_lib + os.pathsep + os.environ.get('PATH', '')

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
