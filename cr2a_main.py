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
    # Only disable Vulkan if no GPU is detected (preserve Intel iGPU XPU).
    # Check the Windows registry for display adapters before deciding.
    _has_gpu = False
    try:
        import winreg
        _cls = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _cls) as _k:
            _i = 0
            while True:
                try:
                    winreg.EnumKey(_k, _i)
                    _has_gpu = True
                    break
                except OSError:
                    break
                _i += 1
    except Exception:
        pass
    if not _has_gpu:
        os.environ['VK_ICD_FILENAMES'] = 'CR2A_no_vulkan.json'
        os.environ['VK_DRIVER_FILES'] = 'CR2A_no_vulkan.json'

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
