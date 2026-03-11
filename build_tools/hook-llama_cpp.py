"""
PyInstaller hook for llama-cpp-python

This hook ensures that llama.cpp shared libraries and binaries are properly
collected when bundling the application with PyInstaller.

The llama-cpp-python package uses native C++ libraries (llama.cpp) which need
to be explicitly collected for the packaged application to work correctly.
"""

import os
from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files

# Collect llama.cpp shared libraries (DLLs on Windows, .so on Linux, .dylib on macOS)
# These are the compiled C++ libraries that llama-cpp-python depends on
binaries = collect_dynamic_libs('llama_cpp')

# Bundle Vulkan runtime so the app works on systems without Vulkan SDK installed
vulkan_dll = r'C:\Windows\System32\vulkan-1.dll'
if os.path.exists(vulkan_dll):
    binaries.append((vulkan_dll, '.'))

# Collect any data files that llama-cpp-python might need
# (e.g., configuration files, grammar files)
datas = collect_data_files('llama_cpp')

# Hidden imports for lazy loading
# These modules are imported dynamically at runtime and PyInstaller won't detect them
hiddenimports = [
    'llama_cpp',
    'llama_cpp.llama_cpp',
    'llama_cpp.llama',
    'llama_cpp.llama_grammar',
    'llama_cpp.llama_cache',
    'llama_cpp.llama_tokenizer',
]

# Exclude unnecessary test/dev files
# This reduces the bundle size by excluding files not needed at runtime
excludedimports = [
    'llama_cpp.server',  # Server module not needed for embedded use
]
