"""
GPU Backend Registry for CR2A

Detects which inference backends are available at runtime and ranks them
by performance for Intel GPU acceleration.

Supported backends:
  - SYCL/oneAPI  (best Intel GPU performance, requires oneAPI runtime)
  - IPEX-LLM     (pre-built SYCL wheels, easiest Intel GPU path)
  - Vulkan       (works on most GPUs, bundled with llama-cpp-python)
  - OpenCL       (legacy, deprecated by Intel)
  - CPU          (always available fallback)
"""

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Backend identifiers
CPU = "cpu"
VULKAN = "vulkan"
SYCL = "sycl"
OPENCL = "opencl"
IPEX_LLM = "ipex"

# Priority order (higher = preferred).  SYCL and IPEX use Intel's native
# GPU compute stack; Vulkan is a general-purpose fallback.
_PRIORITY = {
    SYCL: 50,
    IPEX_LLM: 40,
    VULKAN: 30,
    OPENCL: 20,
    CPU: 10,
}

VALID_BACKENDS = frozenset(_PRIORITY.keys())


@dataclass
class BackendInfo:
    """Information about a single inference backend."""
    name: str               # One of the constants above
    available: bool         # True if usable right now
    priority: int           # Higher = preferred
    reason: str             # Human-readable status
    install_hint: str = ""  # How to install / enable this backend


def _llama_cpp_lib_dir() -> Optional[Path]:
    """Return the llama_cpp/lib directory, or None."""
    try:
        import llama_cpp
        lib = Path(llama_cpp.__file__).parent / "lib"
        return lib if lib.is_dir() else None
    except ImportError:
        return None


def _has_dll(name: str, lib_dir: Optional[Path] = None) -> bool:
    """Check if a DLL exists in the llama_cpp lib dir."""
    if lib_dir is None:
        lib_dir = _llama_cpp_lib_dir()
    if lib_dir is None:
        return False
    return (lib_dir / name).exists()


def _check_gpu_in_registry() -> bool:
    """Check Windows registry for any GPU adapter (including Intel iGPU)."""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        cls_key = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls_key) as key:
            i = 0
            while True:
                try:
                    winreg.EnumKey(key, i)
                    return True
                except OSError:
                    break
                i += 1
    except Exception:
        pass
    return False


def _dll_on_system(name: str) -> bool:
    """Check if a DLL is loadable from the system (PATH / System32)."""
    if sys.platform != "win32":
        return False
    sys32 = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    if (sys32 / name).exists():
        return True
    # Check PATH
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and (Path(d) / name).exists():
            return True
    return False


# ── Individual backend probes ──────────────────────────────────────────


def _probe_cpu() -> BackendInfo:
    try:
        import llama_cpp  # noqa: F401
        return BackendInfo(CPU, True, _PRIORITY[CPU], "Always available", "")
    except ImportError:
        return BackendInfo(CPU, False, _PRIORITY[CPU],
                           "llama-cpp-python not installed",
                           "pip install llama-cpp-python")


def _probe_vulkan() -> BackendInfo:
    lib_dir = _llama_cpp_lib_dir()
    has_dll = _has_dll("ggml-vulkan.dll", lib_dir)
    has_gpu = _check_gpu_in_registry()
    has_loader = _dll_on_system("vulkan-1.dll")

    if has_dll and has_gpu and has_loader:
        return BackendInfo(VULKAN, True, _PRIORITY[VULKAN],
                           "Vulkan GPU compute available", "")
    parts = []
    if not has_dll:
        parts.append("ggml-vulkan.dll not in llama_cpp")
    if not has_gpu:
        parts.append("no GPU detected")
    if not has_loader:
        parts.append("vulkan-1.dll not found")
    return BackendInfo(VULKAN, False, _PRIORITY[VULKAN],
                       "; ".join(parts) or "unavailable",
                       "Install llama-cpp-python with Vulkan support")


def _probe_sycl() -> BackendInfo:
    lib_dir = _llama_cpp_lib_dir()
    has_dll = _has_dll("ggml-sycl.dll", lib_dir)
    has_oneapi = bool(os.environ.get("ONEAPI_ROOT"))
    has_ze = _dll_on_system("ze_loader.dll")

    if has_dll and (has_oneapi or has_ze):
        return BackendInfo(SYCL, True, _PRIORITY[SYCL],
                           "SYCL/oneAPI GPU compute available", "")
    parts = []
    if not has_dll:
        parts.append("ggml-sycl.dll not in llama_cpp")
    if not has_oneapi and not has_ze:
        parts.append("Intel oneAPI runtime not detected")
    hint = ("Install Intel oneAPI Base Toolkit and rebuild llama-cpp-python "
            "with CMAKE_ARGS=\"-DGGML_SYCL=on\"")
    return BackendInfo(SYCL, False, _PRIORITY[SYCL],
                       "; ".join(parts) or "unavailable", hint)


def _probe_opencl() -> BackendInfo:
    lib_dir = _llama_cpp_lib_dir()
    has_dll = _has_dll("ggml-opencl.dll", lib_dir)
    has_runtime = _dll_on_system("OpenCL.dll")

    if has_dll and has_runtime:
        return BackendInfo(OPENCL, True, _PRIORITY[OPENCL],
                           "OpenCL GPU compute available (legacy)", "")
    parts = []
    if not has_dll:
        parts.append("ggml-opencl.dll not in llama_cpp")
    if not has_runtime:
        parts.append("OpenCL.dll not found")
    hint = ("Rebuild llama-cpp-python with CMAKE_ARGS=\"-DGGML_OPENCL=on\" "
            "and install Intel OpenCL runtime")
    return BackendInfo(OPENCL, False, _PRIORITY[OPENCL],
                       "; ".join(parts) or "unavailable", hint)


def _probe_ipex_llm() -> BackendInfo:
    try:
        import ipex_llm  # noqa: F401
        # The newer API (ipex_llm.llama_cpp) supports GGUF v3 models.
        # The older API (ipex_llm.ggml.model.llama) does NOT — it only
        # reads the legacy GGML format and silently fails on GGUF v3.
        try:
            from ipex_llm.llama_cpp import Llama as _  # noqa: F401
            return BackendInfo(IPEX_LLM, True, _PRIORITY[IPEX_LLM],
                               "IPEX-LLM Intel GPU acceleration available", "")
        except (ImportError, ModuleNotFoundError):
            # Only the old ggml API is available — incompatible with GGUF v3
            return BackendInfo(IPEX_LLM, False, _PRIORITY[IPEX_LLM],
                               "ipex-llm installed but too old for GGUF v3 models",
                               "Upgrade: pip install --pre --upgrade ipex-llm[cpp]")
    except ImportError:
        return BackendInfo(IPEX_LLM, False, _PRIORITY[IPEX_LLM],
                           "ipex-llm package not installed",
                           "pip install --pre ipex-llm[cpp]")
    except Exception as e:
        return BackendInfo(IPEX_LLM, False, _PRIORITY[IPEX_LLM],
                           f"ipex-llm import error: {e}",
                           "pip install --pre ipex-llm[cpp]")


# ── Public API ─────────────────────────────────────────────────────────


def detect_available_backends() -> List[BackendInfo]:
    """Probe all backends and return a list sorted by priority (highest first)."""
    backends = [
        _probe_sycl(),
        _probe_ipex_llm(),
        _probe_vulkan(),
        _probe_opencl(),
        _probe_cpu(),
    ]
    for b in backends:
        level = logging.INFO if b.available else logging.DEBUG
        logger.log(level, "Backend %-8s: %s (%s)",
                   b.name, "available" if b.available else "unavailable", b.reason)
    return sorted(backends, key=lambda b: b.priority, reverse=True)


def get_best_backend(preference: str = "auto") -> BackendInfo:
    """Return the best available backend, optionally honouring a preference.

    Args:
        preference: "auto" to pick the highest-priority available backend,
                    or a specific backend name to try that first.
    Returns:
        BackendInfo for the selected backend (falls back to CPU).
    """
    backends = detect_available_backends()

    if preference != "auto" and preference in VALID_BACKENDS:
        for b in backends:
            if b.name == preference:
                if b.available:
                    logger.info("Using preferred backend: %s", b.name)
                    return b
                logger.warning("Preferred backend %s unavailable: %s", b.name, b.reason)
                break

    # Auto: return first available
    for b in backends:
        if b.available and b.name != CPU:
            logger.info("Auto-selected backend: %s", b.name)
            return b

    # CPU fallback
    cpu = next((b for b in backends if b.name == CPU), None)
    if cpu and cpu.available:
        logger.info("Falling back to CPU")
        return cpu

    # Nothing works
    return BackendInfo(CPU, False, 0, "No inference backend available",
                       "pip install llama-cpp-python")


def get_display_name(backend_name: str) -> str:
    """Human-readable name for UI display."""
    return {
        CPU: "CPU Only",
        VULKAN: "Vulkan",
        SYCL: "SYCL/oneAPI",
        OPENCL: "OpenCL",
        IPEX_LLM: "IPEX-LLM",
    }.get(backend_name, backend_name)
