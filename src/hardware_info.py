"""
Hardware detection module for CR2A.

Detects CPU, RAM, and GPU information to support the hardware-aware
settings page. Uses Windows registry for GPU detection (no Vulkan API
calls) and psutil for RAM/CPU info.
"""

import logging
import platform
import sys
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Runtime overhead estimate for llama.cpp process (thread stacks, allocator, etc.)
RUNTIME_OVERHEAD_MB = 300


@dataclass
class HardwareInfo:
    """Detected system hardware profile."""
    cpu_name: str = "Unknown CPU"
    cpu_cores: int = 1          # physical cores
    cpu_threads: int = 1        # logical threads
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    gpu_name: Optional[str] = None
    gpu_type: str = "none"      # "discrete", "integrated", "none"
    gpu_vram_mb: Optional[int] = None  # dedicated VRAM (discrete only)


def detect_hardware() -> HardwareInfo:
    """
    Detect system hardware: CPU, RAM, and GPU.

    Returns:
        HardwareInfo with detected values. All fields have safe fallbacks
        so this never raises.
    """
    info = HardwareInfo()

    # --- CPU ---
    info.cpu_name = _detect_cpu_name()
    info.cpu_cores, info.cpu_threads = _detect_cpu_counts()

    # --- RAM ---
    info.total_ram_mb, info.available_ram_mb = _detect_ram()

    # --- GPU ---
    info.gpu_name, info.gpu_type, info.gpu_vram_mb = _detect_gpu()

    logger.info(
        "Hardware detected: CPU=%s (%dC/%dT), RAM=%d MB total / %d MB available, "
        "GPU=%s (%s, VRAM=%s MB)",
        info.cpu_name, info.cpu_cores, info.cpu_threads,
        info.total_ram_mb, info.available_ram_mb,
        info.gpu_name or "none", info.gpu_type,
        info.gpu_vram_mb if info.gpu_vram_mb is not None else "shared"
    )
    return info


def estimate_os_ram_mb() -> int:
    """
    Return current OS RAM usage in MB (total - available).

    This is a snapshot; call once and cache the result.
    """
    try:
        import psutil
        mem = psutil.virtual_memory()
        return int((mem.total - mem.available) / (1024 * 1024))
    except Exception:
        return 2048  # safe fallback


def compute_context_tokens(
    available_ram_mb: int,
    model_key: str,
    gpu_offload_layers: int = 0,
    gpu_type: str = "none",
) -> int:
    """
    Compute the maximum context window (n_ctx) that fits in the given RAM budget.

    Args:
        available_ram_mb: RAM available for the model (total - OS reserved)
        model_key: Key into MODEL_REGISTRY (e.g. "llama-3.2-3b-q4")
        gpu_offload_layers: Number of layers offloaded to GPU
        gpu_type: "discrete", "integrated", or "none"

    Returns:
        Estimated max n_ctx, clamped to [512, max_context].
    """
    from src.model_manager import ModelManager
    registry = ModelManager.MODEL_REGISTRY
    model_info = registry.get(model_key)
    if not model_info:
        return 8192  # safe default

    size_mb = model_info["size_mb"]
    kv_bytes_per_token = model_info.get("kv_bytes_per_token", 131072)
    mb_per_layer = model_info.get("mb_per_layer", 100)
    max_context = model_info.get("max_context", 131072)

    # For integrated GPU, offloaded layers still use system RAM (shared memory).
    # For discrete GPU, offloaded layers are in dedicated VRAM, freeing system RAM.
    if gpu_type == "discrete" and gpu_offload_layers > 0:
        weight_ram_mb = size_mb - (gpu_offload_layers * mb_per_layer)
        weight_ram_mb = max(weight_ram_mb, model_info.get("embedding_overhead_mb", 200))
    else:
        weight_ram_mb = size_mb

    remaining_mb = available_ram_mb - weight_ram_mb - RUNTIME_OVERHEAD_MB
    if remaining_mb <= 0:
        return 512

    kv_mb_per_token = kv_bytes_per_token / (1024 * 1024)
    max_tokens = int(remaining_mb / kv_mb_per_token)
    return max(512, min(max_tokens, max_context))


def get_ram_breakdown(
    total_model_ram_mb: int,
    model_key: str,
    gpu_offload_layers: int = 0,
    gpu_type: str = "none",
) -> dict:
    """
    Compute a breakdown of how model RAM is used.

    Returns:
        Dict with keys: weights_mb, gpu_offload_mb, context_cache_mb, estimated_tokens
    """
    from src.model_manager import ModelManager
    registry = ModelManager.MODEL_REGISTRY
    model_info = registry.get(model_key)
    if not model_info:
        return {
            "weights_mb": 0, "gpu_offload_mb": 0,
            "context_cache_mb": 0, "estimated_tokens": 0,
        }

    size_mb = model_info["size_mb"]
    mb_per_layer = model_info.get("mb_per_layer", 100)
    kv_bytes_per_token = model_info.get("kv_bytes_per_token", 131072)
    max_context = model_info.get("max_context", 131072)

    # GPU offload portion (relevant to display for integrated GPUs)
    gpu_offload_mb = gpu_offload_layers * mb_per_layer

    # For discrete, offloaded layers don't consume system RAM
    if gpu_type == "discrete":
        weights_in_ram = size_mb - gpu_offload_mb
        weights_in_ram = max(weights_in_ram, model_info.get("embedding_overhead_mb", 200))
        gpu_offload_display_mb = 0  # not shown in RAM bar for discrete
    else:
        weights_in_ram = size_mb
        gpu_offload_display_mb = gpu_offload_mb  # shown as part of RAM usage

    remaining_mb = total_model_ram_mb - weights_in_ram - gpu_offload_display_mb - RUNTIME_OVERHEAD_MB
    remaining_mb = max(0, remaining_mb)

    kv_mb_per_token = kv_bytes_per_token / (1024 * 1024)
    estimated_tokens = int(remaining_mb / kv_mb_per_token) if kv_mb_per_token > 0 else 0
    estimated_tokens = max(0, min(estimated_tokens, max_context))

    context_cache_mb = estimated_tokens * kv_mb_per_token

    return {
        "weights_mb": weights_in_ram,
        "gpu_offload_mb": gpu_offload_display_mb,
        "context_cache_mb": round(context_cache_mb, 1),
        "estimated_tokens": estimated_tokens,
    }


# ---------------------------------------------------------------------------
# Internal detection helpers
# ---------------------------------------------------------------------------

def _detect_cpu_name() -> str:
    """Get human-readable CPU name."""
    # Windows registry gives the best friendly name
    if sys.platform == "win32":
        try:
            import winreg
            key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
                if name:
                    return name
        except Exception:
            pass

    # Fallback to platform.processor()
    name = platform.processor()
    if name and name.strip():
        return name.strip()

    return "Unknown CPU"


def _detect_cpu_counts() -> tuple:
    """Return (physical_cores, logical_threads)."""
    try:
        import psutil
        physical = psutil.cpu_count(logical=False) or 1
        logical = psutil.cpu_count(logical=True) or physical
        return physical, logical
    except Exception:
        import multiprocessing
        count = multiprocessing.cpu_count()
        return count, count


def _detect_ram() -> tuple:
    """Return (total_ram_mb, available_ram_mb)."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        total = int(mem.total / (1024 * 1024))
        available = int(mem.available / (1024 * 1024))
        return total, available
    except Exception:
        return 0, 0


def _detect_gpu() -> tuple:
    """
    Detect GPU name, type, and VRAM via Windows registry.

    Returns:
        (gpu_name, gpu_type, gpu_vram_mb)
        gpu_type is "discrete", "integrated", or "none"
        gpu_vram_mb is int for discrete, None for integrated/none
    """
    if sys.platform != "win32":
        return None, "none", None

    try:
        import winreg
        CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"

        gpus = []  # list of (name, type, vram_mb)

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CLASS_KEY) as class_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(class_key, i)
                    try:
                        with winreg.OpenKey(class_key, subkey_name) as gpu_key:
                            desc = winreg.QueryValueEx(gpu_key, "DriverDesc")[0]
                            gpu_type = _classify_gpu(desc)
                            vram_mb = _read_gpu_vram(gpu_key) if gpu_type == "discrete" else None
                            gpus.append((desc, gpu_type, vram_mb))
                    except (FileNotFoundError, OSError):
                        pass
                    i += 1
                except OSError:
                    break

        if not gpus:
            return None, "none", None

        # Prefer discrete over integrated
        discrete = [g for g in gpus if g[1] == "discrete"]
        if discrete:
            return discrete[0]

        integrated = [g for g in gpus if g[1] == "integrated"]
        if integrated:
            return integrated[0]

        return gpus[0][0], "none", None

    except Exception as e:
        logger.info("GPU detection failed: %s", e)
        return None, "none", None


def _classify_gpu(desc: str) -> str:
    """Classify a GPU adapter description as discrete or integrated."""
    desc_lower = desc.lower()

    # NVIDIA is always discrete
    if "nvidia" in desc_lower:
        return "discrete"

    # AMD discrete GPUs (not APU integrated)
    if "amd" in desc_lower or "radeon" in desc_lower:
        # AMD APU integrated GPUs typically say "Radeon(TM) Graphics" or "Radeon Vega"
        if "radeon(tm) graphics" in desc_lower or "radeon vega" in desc_lower:
            return "integrated"
        return "discrete"

    # Intel classification
    if "intel" in desc_lower:
        # Intel Arc discrete GPUs
        if "arc" in desc_lower:
            # Arc A-series discrete: A310, A370M, A380, A550M, A580, A750, A770
            arc_discrete_markers = ["a3", "a5", "a7"]
            for marker in arc_discrete_markers:
                if marker in desc_lower:
                    return "discrete"
            # Arc integrated (Meteor Lake, Lunar Lake) — no A-series number
            return "integrated"
        # Intel UHD, Iris, Iris Xe, Iris Plus — all integrated
        return "integrated"

    return "integrated"  # default to integrated for unknown


def _read_gpu_vram(gpu_key) -> Optional[int]:
    """Read dedicated VRAM size from registry GPU subkey. Returns MB or None."""
    import winreg

    # Try qwMemorySize (REG_QWORD, 64-bit) first
    for value_name in ("HardwareInformation.qwMemorySize", "HardwareInformation.MemorySize"):
        try:
            value, _ = winreg.QueryValueEx(gpu_key, value_name)
            if isinstance(value, int) and value > 0:
                return value // (1024 * 1024)
            if isinstance(value, bytes):
                # REG_BINARY — interpret as little-endian integer
                return int.from_bytes(value, byteorder="little") // (1024 * 1024)
        except (FileNotFoundError, OSError):
            continue

    return None
