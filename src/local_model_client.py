"""
Local Model Client for Contract Analysis

This module provides the LocalModelClient class for analyzing contracts using
an embedded LLM (Llama 3.1 or compatible) via llama-cpp-python. It maintains
interface compatibility with OpenAIClient while running entirely locally.

Supports:
- Llama 3.2 3B Instruct (recommended for CPU, fast)
- Llama 3.1 8B Instruct (higher quality, slower on CPU)
- Legacy Pythia models (backwards compatibility)
- Any GGUF-format model via llama-cpp-python
"""

import json
import logging
import os
import re
import sys
import multiprocessing
from pathlib import Path
from typing import Dict, Optional, Callable, List, Tuple

logger = logging.getLogger(__name__)

# Allow Vulkan GPU backend (including Intel integrated graphics).
# Intel iGPU via Vulkan is usable for inference acceleration.

# In frozen (PyInstaller) builds, add llama_cpp/lib to DLL search path
# so that llama.dll can find ggml-*.dll dependencies.
if getattr(sys, 'frozen', False):
    _llama_lib_dir = os.path.join(sys._MEIPASS, 'llama_cpp', 'lib')
    if os.path.isdir(_llama_lib_dir):
        os.add_dll_directory(_llama_lib_dir)
        os.environ['PATH'] = _llama_lib_dir + os.pathsep + os.environ.get('PATH', '')

# llama-cpp-python is an optional dependency. Import is attempted eagerly
# at runtime but deferred during PyInstaller analysis (no llama.dll in CI).
Llama = None
LLAMA_CPP_AVAILABLE = False

# IPEX-LLM provides a drop-in Llama replacement with Intel SYCL acceleration.
IpexLlama = None
IPEX_LLM_AVAILABLE = False

def _ensure_llama():
    """Import llama_cpp. Safe to call multiple times."""
    global Llama, LLAMA_CPP_AVAILABLE
    if LLAMA_CPP_AVAILABLE or Llama is not None:
        return
    try:
        from llama_cpp import Llama as _Llama
        Llama = _Llama
        LLAMA_CPP_AVAILABLE = True
    except (ImportError, OSError, RuntimeError) as e:
        logger.warning("llama-cpp-python not available: %s", e)

def _ensure_ipex():
    """Import IPEX-LLM's Llama class. Safe to call multiple times."""
    global IpexLlama, IPEX_LLM_AVAILABLE
    if IPEX_LLM_AVAILABLE or IpexLlama is not None:
        return
    try:
        os.environ.setdefault("SYCL_CACHE_PERSISTENT", "1")
        # Try newer API path first, then older ggml path
        try:
            from ipex_llm.llama_cpp import Llama as _IpexLlama
        except (ImportError, ModuleNotFoundError):
            from ipex_llm.ggml.model.llama import Llama as _IpexLlama
        IpexLlama = _IpexLlama
        IPEX_LLM_AVAILABLE = True
        logger.info("IPEX-LLM available for Intel GPU acceleration")
    except (ImportError, OSError, RuntimeError) as e:
        logger.debug("ipex-llm not available: %s", e)

# Eagerly try to load at import time
_ensure_llama()
_ensure_ipex()


def _check_vulkan_devices() -> bool:
    """
    Check whether any GPU (including Intel integrated) is available via the Windows registry.

    Returns:
        True if at least one GPU adapter is found, False otherwise.
    """
    try:
        import winreg
        CLASS_KEY = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CLASS_KEY) as class_key:
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(class_key, i)
                    try:
                        with winreg.OpenKey(class_key, subkey_name) as gpu_key:
                            desc = winreg.QueryValueEx(gpu_key, "DriverDesc")[0]
                            logger.info("GPU adapter found: %s", desc)
                            return True
                    except (FileNotFoundError, OSError):
                        pass
                    i += 1
                except OSError:
                    break
        logger.info("No GPU adapters found in registry")
        return False
    except Exception as e:
        logger.info("Registry GPU check failed: %s — defaulting to CPU-only", e)
        return False


def detect_gpu_support(preference: str = "auto") -> Tuple[bool, int, str]:
    """
    Detect the best available GPU backend for inference.

    Uses the backend registry to probe SYCL, IPEX-LLM, Vulkan, OpenCL,
    and CPU backends, returning the best match.

    Args:
        preference: "auto" or a specific backend name ("sycl", "ipex", "vulkan", etc.)

    Returns:
        (gpu_available, recommended_layers, backend_name)
        - gpu_available: True if a GPU backend is available
        - recommended_layers: -1 to offload all layers, 0 for CPU-only
        - backend_name: "sycl", "ipex", "vulkan", "opencl", "cpu", etc.
    """
    _ensure_llama()
    _ensure_ipex()

    from src.backend_registry import get_best_backend, CPU

    best = get_best_backend(preference)
    if best.available and best.name != CPU:
        logger.info("GPU backend selected: %s (%s)", best.name, best.reason)
        return True, -1, best.name
    elif best.available:
        logger.info("CPU-only inference (no GPU backend available)")
        return False, 0, "cpu"
    else:
        logger.warning("No inference backend available: %s", best.reason)
        return False, 0, "cpu"

from src.schema_loader import SchemaLoader
from src.fuzzy_matcher import FuzzyClauseMatcher


class LocalModelClient:
    """
    Client for contract analysis using a local LLM.

    Provides a local alternative to OpenAIClient, running models entirely
    on CPU without external API calls. Maintains the same interface for
    seamless integration with AnalysisEngine.

    Supports Llama 3.1 Instruct (recommended) and legacy Pythia models.
    Auto-detects the correct chat template based on model name.
    """

    # Default settings - tuned for fast CPU inference
    DEFAULT_CONTEXT_SIZE = 8192   # 8K tokens (fast on CPU; overridden per model)
    DEFAULT_TEMPERATURE = 0.0     # Deterministic for contract analysis
    MAX_TOKENS_ANALYSIS = 4000    # Contract analysis responses (keep short for speed)
    MAX_TOKENS_QUERY = 500        # Chat query responses

    # Model-specific context sizes
    MODEL_CONTEXT_SIZES = {
        "llama-3.2-3b": 8192,    # 8K context, fast on CPU
        "llama-3.1-8b": 8192,    # 8K context — 16K requires ~6GB+ RAM; 8K is safer on most machines
        "pythia": 4096,           # Legacy model
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "llama-3.2-3b-q4",
        n_ctx: int = DEFAULT_CONTEXT_SIZE,
        n_threads: Optional[int] = None,
        n_gpu_layers: Optional[int] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        ram_reserved_os_mb: Optional[int] = None,
        gpu_offload_layers: Optional[int] = None,
        gpu_backend: str = "auto",
    ):
        """
        Initialize local model client.

        Args:
            model_path: Path to GGUF model file (if None, must be set before use)
            model_name: Name identifier for the model
            n_ctx: Context window size (tokens)
            n_threads: CPU threads to use (auto-detects if None)
            n_gpu_layers: GPU layers to offload (None = auto-detect, 0 = CPU-only, -1 = all layers on GPU)
            temperature: Sampling temperature (0.0 = deterministic)
            ram_reserved_os_mb: MB reserved for OS (if set, n_ctx is computed from remaining RAM)
            gpu_offload_layers: Explicit layer count for GPU offload (overrides n_gpu_layers)
            gpu_backend: Backend preference ("auto", "sycl", "ipex", "vulkan", "opencl", "cpu")

        Raises:
            ImportError: If llama-cpp-python is not installed
        """
        _ensure_llama()
        _ensure_ipex()
        if not LLAMA_CPP_AVAILABLE and not IPEX_LLM_AVAILABLE:
            raise ImportError(
                "llama-cpp-python or ipex-llm is required for local models.\n"
                "Install with: pip install llama-cpp-python\n"
                "For Intel GPU: pip install --pre ipex-llm[cpp]"
            )

        self.model_path = Path(model_path) if model_path else None
        self.model_name = model_name
        self.n_threads = n_threads or multiprocessing.cpu_count()
        self.temperature = temperature

        # GPU layer selection: explicit offload_layers > n_gpu_layers > auto-detect
        self.gpu_backend_preference = gpu_backend
        if gpu_offload_layers is not None:
            self.n_gpu_layers = gpu_offload_layers
            gpu_available, _, detected_backend = detect_gpu_support(gpu_backend)
            self.gpu_backend = detected_backend if gpu_available else "cpu"
            logger.info("Using explicit GPU offload: %d layers (backend=%s)", gpu_offload_layers, self.gpu_backend)
        elif n_gpu_layers is not None:
            self.n_gpu_layers = n_gpu_layers
            gpu_available, _, detected_backend = detect_gpu_support(gpu_backend)
            self.gpu_backend = detected_backend if gpu_available else "cpu"
        else:
            gpu_available, recommended_layers, detected_backend = detect_gpu_support(gpu_backend)
            self.n_gpu_layers = recommended_layers
            self.gpu_backend = detected_backend
            if gpu_available:
                logger.info("Auto-detected %s backend — offloading all layers", detected_backend)
            else:
                logger.info("No GPU detected — using CPU-only inference")

        # Context size: compute from RAM budget if provided, else use defaults
        if ram_reserved_os_mb is not None:
            from src.hardware_info import compute_context_tokens, _detect_gpu
            try:
                import psutil
                total_ram_mb = int(psutil.virtual_memory().total / (1024 * 1024))
            except Exception:
                total_ram_mb = 8192
            gpu_type = "none"
            try:
                _, gpu_type, _ = _detect_gpu()
            except Exception:
                pass
            available = total_ram_mb - ram_reserved_os_mb
            computed_ctx = compute_context_tokens(
                available_ram_mb=available,
                model_key=model_name,
                gpu_offload_layers=self.n_gpu_layers if self.n_gpu_layers > 0 else 0,
                gpu_type=gpu_type,
            )
            self.n_ctx = computed_ctx
            self.DEFAULT_CONTEXT_SIZE = computed_ctx
            logger.info("Context size computed from RAM budget: %d tokens (reserved %d MB for OS)",
                        computed_ctx, ram_reserved_os_mb)
        elif n_ctx == self.DEFAULT_CONTEXT_SIZE:
            self.n_ctx = self._get_model_context_size()
            self.DEFAULT_CONTEXT_SIZE = self.n_ctx
        else:
            self.n_ctx = n_ctx
            self.DEFAULT_CONTEXT_SIZE = n_ctx

        # Lazy loading - model loads on first use
        self._model: Optional[Llama] = None
        self._model_loaded = False

        # Load schema for prompt construction
        self._schema_loader = SchemaLoader()
        self._schema_loader.load_schema()

        # Initialize fuzzy matcher for intelligent category detection
        self._fuzzy_matcher = FuzzyClauseMatcher(confidence_threshold=65.0)

        logger.info(
            f"LocalModelClient initialized: model={model_name}, "
            f"ctx={self.n_ctx}, threads={self.n_threads}, "
            f"gpu_layers={self.n_gpu_layers}, backend={self.gpu_backend}"
        )

    # =========================================================================
    # Properties (interface compatibility with OpenAIClient)
    # =========================================================================

    @property
    def model(self) -> str:
        """Model name for interface compatibility with OpenAIClient."""
        return self.model_name

    # =========================================================================
    # Public Interface (matches OpenAIClient)
    # =========================================================================

    def ensure_loaded(self, progress_callback=None) -> None:
        """
        Ensure the model is loaded. Must be called from the main thread before
        spawning background threads that call generate(), because llama_cpp's
        Llama() constructor is not safe to call from secondary threads on Windows.
        """
        if not self._model_loaded:
            if progress_callback:
                progress_callback("Loading AI model into memory...", 5)
            self._load_model(progress_callback)

    def generate(
        self,
        system_message: str,
        user_message: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate a text response from the local model.

        Unified interface matching OpenAIClient.generate(). Callers send
        system + user messages and receive raw text back. JSON parsing
        is the caller's responsibility.

        Args:
            system_message: System/instruction message for the model
            user_message: User input/prompt
            progress_callback: Optional callback for progress updates
            max_tokens: Optional max output tokens (default: MAX_TOKENS_ANALYSIS)

        Returns:
            Raw text response from the model

        Raises:
            RuntimeError: If model is not loaded or inference fails
        """
        if not self._model_loaded:
            if progress_callback:
                progress_callback("Loading AI model...", 5)
            self._load_model(progress_callback)

        return self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=max_tokens or self.MAX_TOKENS_ANALYSIS,
            progress_callback=progress_callback,
            progress_start=55,
            progress_end=85
        )

    def analyze_contract(
        self,
        contract_text: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Dict:
        """
        Analyze contract and return structured result.

        Args:
            contract_text: Extracted contract text to analyze
            progress_callback: Optional callback function(status_message, percent)

        Returns:
            Analysis result dictionary matching the CR2A schema

        Raises:
            ValueError: If contract_text is empty
            RuntimeError: If model fails to load or inference fails
        """
        if not contract_text or not contract_text.strip():
            raise ValueError("Contract text cannot be empty")

        # Load model on first use
        if not self._model_loaded:
            if progress_callback:
                progress_callback("Loading AI model into memory...", 5)
            self._load_model(progress_callback)

        if progress_callback:
            progress_callback("Preparing analysis prompt...", 10)

        # Build analysis prompt
        system_message = self._build_system_message()
        user_message = self._build_user_message(contract_text)

        if progress_callback:
            progress_callback("Running local AI inference...", 20)

        # Run inference with progress tracking
        response_text = self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=self.MAX_TOKENS_ANALYSIS,
            progress_callback=progress_callback,
            progress_start=20,
            progress_end=90
        )

        if progress_callback:
            progress_callback("Parsing response...", 95)

        # Parse JSON response
        try:
            result = self._parse_json_response(response_text)

            if progress_callback:
                progress_callback("Analysis complete", 100)

            return result
        except Exception as e:
            logger.error(f"Failed to parse model response: {e}")
            raise RuntimeError(f"Failed to parse model output: {e}")

    def process_query(
        self,
        query: str,
        context: Dict,
        conversation_history: Optional[List] = None
    ) -> str:
        """
        Process a user query about a contract.

        Args:
            query: User's natural language question about the contract
            context: Relevant contract data (clauses, risks, metadata, etc.)
            conversation_history: Optional list of previous messages

        Returns:
            Natural language response string

        Raises:
            ValueError: If query is empty or context is invalid
            RuntimeError: If model fails to load or inference fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if not context or not isinstance(context, dict):
            raise ValueError("Context must be a non-empty dictionary")

        # Load model on first use
        if not self._model_loaded:
            self._load_model()

        # Build query prompt
        system_message = self._build_query_system_message()
        user_message = self._build_query_user_message(query, context)

        # Run inference
        response_text = self._run_inference(
            system_message=system_message,
            user_message=user_message,
            max_tokens=self.MAX_TOKENS_QUERY,
            temperature=0.7  # More conversational
        )

        return response_text.strip()

    def validate_api_key(self) -> bool:
        """
        Validate model availability (no API key needed for local models).

        Returns:
            True if model file exists and can be loaded, False otherwise
        """
        if not self.model_path or not self.model_path.exists():
            logger.warning(f"Model file not found: {self.model_path}")
            return False

        try:
            if not self._model_loaded:
                self._load_model()
            return True
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _is_llama_model(self) -> bool:
        """Check if the current model is a Llama model (vs legacy Pythia)."""
        name = self.model_name.lower()
        return 'llama' in name or 'meta' in name

    def _get_model_context_size(self) -> int:
        """Auto-detect appropriate context size based on model name."""
        name = self.model_name.lower()
        for key, ctx_size in self.MODEL_CONTEXT_SIZES.items():
            if key in name:
                logger.info(f"Auto-configured context size: {ctx_size} for model {self.model_name}")
                return ctx_size
        return 8192  # Safe default for unknown models

    def _probe_gpu_in_subprocess(self) -> bool:
        """Test if GPU loading works without crashing the main process.

        Spawns a short-lived subprocess that tries to load the model with
        n_gpu_layers=1 using the selected backend. Returns True if it exits
        cleanly, False on crash (e.g., Vulkan access violation).
        """
        import subprocess

        # Choose the right import based on backend
        if self.gpu_backend == "ipex":
            import_line = "from ipex_llm.llama_cpp import Llama"
        else:
            import_line = "from llama_cpp import Llama"

        script = (
            "import sys, os\n"
            f"os.environ['PATH'] = {repr(os.environ.get('PATH', ''))}\n"
            "os.environ.setdefault('SYCL_CACHE_PERSISTENT', '1')\n"
            "try:\n"
            f"    {import_line}\n"
            f"    m = Llama(model_path={repr(str(self.model_path))}, "
            "n_ctx=512, n_gpu_layers=1, n_batch=128, verbose=False)\n"
            "    del m\n"
            "    print('OK')\n"
            "except Exception as e:\n"
            "    print(f'FAIL: {e}')\n"
            "    sys.exit(1)\n"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", script],
                capture_output=True, text=True, timeout=60,
            )
            ok = result.returncode == 0 and "OK" in result.stdout
            if ok:
                logger.info("GPU probe succeeded (%s backend)", self.gpu_backend)
            else:
                logger.warning("GPU probe failed (%s): rc=%d, out=%s, err=%s",
                               self.gpu_backend, result.returncode,
                               result.stdout.strip()[:200],
                               result.stderr.strip()[:200])
            return ok
        except Exception as e:
            logger.warning("GPU probe subprocess error: %s", e)
            return False

    def _load_model(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> None:
        """
        Load model from GGUF file (lazy loading pattern).

        Args:
            progress_callback: Optional callback for loading progress

        Raises:
            RuntimeError: If model file doesn't exist or loading fails
        """
        if self._model_loaded:
            return

        if not self.model_path or not self.model_path.exists():
            raise RuntimeError(
                f"Model file not found: {self.model_path}\n\n"
                "Please download the model first:\n"
                "Settings -> Manage Models -> Download Model"
            )

        gpu_info = f", gpu_layers={self.n_gpu_layers}, backend={self.gpu_backend}" if self.n_gpu_layers != 0 else ", CPU-only"
        logger.info(f"Loading model from: {self.model_path}{gpu_info}")

        # Determine load order: try GPU first (if configured), then CPU fallback.
        # In frozen builds, Vulkan GPU can cause access violations that kill
        # the process (uncatchable). Probe in a subprocess first.
        load_attempts = []
        if self.n_gpu_layers != 0:
            if getattr(sys, 'frozen', False):
                if self._probe_gpu_in_subprocess():
                    load_attempts.append(("gpu", self.n_gpu_layers))
                else:
                    logger.warning("GPU probe failed in subprocess, using CPU-only")
            else:
                load_attempts.append(("gpu", self.n_gpu_layers))
        load_attempts.append(("cpu", 0))

        last_error = None
        for attempt_name, gpu_layers in load_attempts:
            try:
                if attempt_name == "cpu" and self.n_gpu_layers != 0:
                    logger.warning("GPU model loading failed (%s), falling back to CPU-only: %s",
                                   self.gpu_backend, last_error)
                    if progress_callback:
                        progress_callback("GPU failed, loading on CPU...", 5)

                # Intel iGPU Vulkan crashes with default n_batch=512 on large prompts.
                # Use n_batch=128 for GPU to keep Vulkan buffer sizes manageable.
                n_batch = 128 if gpu_layers != 0 else 512

                # Select the right Llama constructor based on backend
                if self.gpu_backend == "ipex" and IPEX_LLM_AVAILABLE and gpu_layers != 0:
                    _Constructor = IpexLlama
                    logger.info("Using IPEX-LLM Llama constructor (Intel SYCL)")
                else:
                    _Constructor = Llama

                self._model = _Constructor(
                    model_path=str(self.model_path),
                    n_ctx=self.n_ctx,
                    n_threads=self.n_threads,
                    n_gpu_layers=gpu_layers,
                    n_batch=n_batch,
                    verbose=False
                )

                self._model_loaded = True

                # Verify GPU inference with a large prompt (Intel iGPU Vulkan
                # can pass small tests but crash on real-sized prompts)
                if gpu_layers != 0:
                    try:
                        logger.info("Testing GPU inference with large prompt...")
                        test_prompt = ("The contractor shall provide labor and materials " * 50)[:3000]
                        test_out = self._model.create_completion(
                            test_prompt, max_tokens=5, temperature=0.0,
                        )
                        test_text = test_out["choices"][0]["text"] if test_out.get("choices") else ""
                        self._model.reset()
                        logger.info("GPU inference test passed (output: %s)", test_text[:50])
                    except (OSError, Exception) as gpu_err:
                        logger.warning("GPU inference test failed (%s), falling back to CPU", gpu_err)
                        self._model_loaded = False
                        del self._model
                        self._model = None
                        raise RuntimeError(f"GPU inference failed: {gpu_err}")

                if gpu_layers != 0:
                    self.gpu_backend = self.gpu_backend or "gpu"
                    logger.info("Model loaded successfully (GPU-accelerated, %s)", self.gpu_backend)
                else:
                    if self.n_gpu_layers != 0:
                        # We fell back from GPU to CPU
                        self.n_gpu_layers = 0
                        self.gpu_backend = "cpu"
                        logger.info("Model loaded successfully (CPU fallback)")
                    else:
                        logger.info("Model loaded successfully (CPU-only)")

                if progress_callback:
                    status = f"Model loaded ({self.gpu_backend} GPU)" if gpu_layers != 0 else "Model loaded (CPU)"
                    progress_callback(status, 10)
                return

            except Exception as e:
                last_error = e
                logger.warning("Model load attempt (%s, gpu_layers=%s) failed: %s",
                               attempt_name, gpu_layers, e)
                continue

        logger.error(f"All model load attempts failed. Last error: {last_error}", exc_info=True)
        raise RuntimeError(
            f"Failed to load model: {last_error}\n\n"
            "Possible causes:\n"
            "- Corrupted model file (try re-downloading)\n"
            "- Insufficient memory (need 8GB+ free RAM for Llama 3.1 8B)\n"
            "- Incompatible model format (need GGUF)\n\n"
            "Try: Settings -> Manage Models -> Delete and re-download"
        )

    def _format_prompt(
        self,
        system_message: str,
        user_message: str
    ) -> str:
        """
        Format prompt using the appropriate chat template.

        Auto-detects Llama 3.1 vs Pythia based on model name.

        Args:
            system_message: System instructions
            user_message: User input

        Returns:
            Formatted prompt string
        """
        if self._is_llama_model():
            # Llama 3.1/3.2 Instruct chat template.
            # Do NOT include <|begin_of_text|> here — llama-cpp adds it automatically
            # during tokenization. Including it manually causes a duplicate that
            # degrades response quality.
            return (
                f"<|start_header_id|>system<|end_header_id|>\n\n"
                f"{system_message}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"{user_message}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>\n\n"
            )
        else:
            # Legacy Pythia template
            return (
                f"### System:\n{system_message}\n\n"
                f"### Human:\n{user_message}\n\n"
                f"### Assistant:\n"
            )

    def _get_stop_sequences(self) -> list:
        """Get appropriate stop sequences for the current model."""
        if self._is_llama_model():
            return ["<|eot_id|>", "<|end_of_text|>"]
        else:
            return ["### Human:", "### System:"]

    def _run_inference(
        self,
        system_message: str,
        user_message: str,
        max_tokens: int,
        temperature: Optional[float] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        progress_start: int = 0,
        progress_end: int = 100
    ) -> str:
        """
        Run model inference with progress tracking.

        Args:
            system_message: System instructions
            user_message: User input
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (uses default if None)
            progress_callback: Optional progress callback
            progress_start: Starting progress percentage
            progress_end: Ending progress percentage

        Returns:
            Generated text response

        Raises:
            RuntimeError: If inference fails
        """
        if not self._model_loaded:
            raise RuntimeError("Model not loaded")

        temp = temperature if temperature is not None else self.temperature

        # Format prompt with appropriate template
        prompt = self._format_prompt(system_message, user_message)
        stop_sequences = self._get_stop_sequences()

        prompt_chars = len(prompt)
        logger.info(f"Running inference: max_tokens={max_tokens}, temp={temp}, prompt_chars={prompt_chars}")

        # Hard-truncate prompt if it would exceed context window
        estimated_prompt_tokens = prompt_chars // 3  # Conservative estimate
        safe_prompt_tokens = self.n_ctx - max_tokens - 256  # 256 token safety buffer
        if estimated_prompt_tokens > safe_prompt_tokens and safe_prompt_tokens > 0:
            safe_chars = safe_prompt_tokens * 3
            logger.warning(
                f"Prompt exceeds context window: ~{estimated_prompt_tokens} tokens "
                f"+ {max_tokens} output > {self.n_ctx} context. "
                f"Truncating prompt from {prompt_chars} to {safe_chars} chars."
            )
            # Truncate the user_message portion, preserving system message framing
            prompt = prompt[:safe_chars]

        try:
            import time
            output_tokens = []
            tokens_generated = 0
            start_time = time.time()

            if progress_callback:
                progress_callback("Processing prompt (this may take a moment)...", progress_start)

            for token_output in self._model(
                prompt,
                max_tokens=max_tokens,
                temperature=temp,
                stop=stop_sequences,
                stream=True
            ):
                if isinstance(token_output, dict):
                    choice = token_output.get('choices', [{}])[0]
                    text = choice.get('text', '')
                    output_tokens.append(text)
                    tokens_generated += 1

                    # Stream token to UI
                    if token_callback and text:
                        token_callback(text)

                    # Update progress every 10 tokens (frequent updates for responsiveness)
                    if progress_callback and tokens_generated % 10 == 0:
                        elapsed = time.time() - start_time
                        tokens_per_sec = tokens_generated / max(elapsed, 0.1)
                        progress_pct = progress_start + int(
                            (tokens_generated / max_tokens) * (progress_end - progress_start)
                        )
                        progress_pct = min(progress_pct, progress_end)
                        progress_callback(
                            f"Generating ({tokens_generated} tokens, {tokens_per_sec:.1f} tok/s)...",
                            progress_pct
                        )

            response_text = ''.join(output_tokens)
            elapsed = time.time() - start_time

            logger.info(
                f"Inference complete: {tokens_generated} tokens in {elapsed:.1f}s "
                f"({tokens_generated / max(elapsed, 0.1):.1f} tok/s)"
            )

            return response_text

        except OSError as e:
            # Vulkan GPU compute crash — reload model on CPU and retry once
            if self.n_gpu_layers != 0 and not getattr(self, '_gpu_fallback_attempted', False):
                self._gpu_fallback_attempted = True
                logger.warning("GPU inference crashed (%s), reloading model on CPU...", e)
                try:
                    del self._model
                    self._model = None
                    self._model_loaded = False
                    self.n_gpu_layers = 0
                    self.gpu_backend = "cpu"
                    self.ensure_loaded()
                    logger.info("Model reloaded on CPU, retrying inference")
                    return self._run_inference(
                        system_message, user_message, max_tokens,
                        temperature, progress_callback, token_callback,
                        progress_start, progress_end,
                    )
                except Exception as reload_err:
                    logger.error("CPU fallback failed: %s", reload_err)
                    raise RuntimeError(f"GPU inference failed and CPU fallback failed: {reload_err}")
            logger.error(f"Inference failed: {e}", exc_info=True)
            raise RuntimeError(f"Local model inference failed: {e}")
        except Exception as e:
            logger.error(f"Inference failed: {e}", exc_info=True)
            raise RuntimeError(f"Local model inference failed: {e}")

    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Parse and repair JSON response from model output.

        Handles markdown code blocks, truncated responses, malformed JSON.

        Args:
            response_text: Raw model output

        Returns:
            Parsed JSON dictionary

        Raises:
            json.JSONDecodeError: If JSON cannot be parsed or repaired
        """
        text = response_text.strip()
        text = re.sub(r'^```json\s*', '', text)
        text = re.sub(r'^```\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        first_brace = text.find('{')
        last_brace = text.rfind('}')

        if first_brace == -1 or last_brace == -1:
            raise json.JSONDecodeError(
                "No JSON object found in response",
                text,
                0
            )

        text = text[first_brace:last_brace + 1]

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Initial JSON parse failed: {e}")

            # Attempt repair: close unclosed braces
            repaired = text
            open_braces = repaired.count('{')
            close_braces = repaired.count('}')

            if open_braces > close_braces:
                repaired += '}' * (open_braces - close_braces)

            # Fix trailing commas
            repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e2:
                logger.error(f"JSON repair failed: {e2}")
                logger.debug(f"Original text: {text[:500]}...")
                raise json.JSONDecodeError(
                    "Failed to parse model output as JSON",
                    text,
                    e.pos
                )

    def _build_system_message(self) -> str:
        """Build system message for contract analysis."""
        return """You are a Contract Analysis Engine specializing in comprehensive contract risk assessment.

Your task is to analyze contracts and return a structured JSON response with ALL relevant clauses found in the contract.

CRITICAL INSTRUCTIONS:

1. EXTRACT BASED ON SUBSTANCE, NOT TERMINOLOGY: Include a clause category if the contract contains provisions that address that topic, even if the exact category name is not used.

2. PRIORITIZE COMPLETENESS OVER DETAIL: It is CRITICAL to include ALL relevant clause categories found, even with brief summaries. Most contracts will have content for 30-50+ categories. Use concise summaries (1-2 sentences).

3. OUTPUT ONLY VALID JSON: No markdown, no explanations, no code blocks. Start directly with { and end with }.

4. ACCURACY: Only extract information that is explicitly stated or clearly implied in the contract.

5. BE CONCISE BUT COMPLETE: Keep individual summaries brief (1-2 sentences) to allow coverage of ALL found categories.

Output Format:
Return a JSON object with these exact keys:
- schema_version (e.g., "v1.0.0")
- contract_overview
- administrative_and_commercial_terms
- technical_and_performance_terms
- legal_risk_and_enforcement
- regulatory_and_compliance_terms
- data_technology_and_deliverables
- supplemental_operational_risks

Each clause must follow the ClauseBlock structure with all required fields."""

    def _build_user_message(self, contract_text: str) -> str:
        """Build user message for contract analysis with fuzzy category suggestions."""
        schema_description = self._schema_loader.get_schema_for_prompt()

        # Use fuzzy matching to suggest likely categories
        try:
            fuzzy_matches = self._fuzzy_matcher.find_matching_categories(
                contract_text,
                min_matches=25
            )

            suggested_categories = {}
            for match in fuzzy_matches:
                section = match.section
                if section not in suggested_categories:
                    suggested_categories[section] = []
                suggested_categories[section].append(match.category)

            fuzzy_suggestions = "\n\nFUZZY LOGIC ANALYSIS:\n\n"
            fuzzy_suggestions += "Based on semantic analysis, these categories are likely present:\n\n"

            for section, categories in suggested_categories.items():
                section_name = section.replace('_', ' ').title()
                fuzzy_suggestions += f"\n{section_name}:\n"
                for cat in categories:
                    fuzzy_suggestions += f"- {cat}\n"

            fuzzy_suggestions += "\nPriority: Focus on these categories first, then check all others systematically.\n"

        except Exception as e:
            logger.warning(f"Fuzzy matching failed: {e}")
            fuzzy_suggestions = ""

        return f"""{schema_description}
{fuzzy_suggestions}

CONTRACT TEXT:
{contract_text}

IMPORTANT:
1. Return ONLY the JSON response
2. Include ONLY clauses found in the contract
3. Omit categories not present in the contract
4. Use exact clause language from the contract
5. Provide accurate risk assessments
6. Use the fuzzy logic suggestions above as a starting point, but check ALL categories systematically

Begin JSON response:"""

    def _build_query_system_message(self) -> str:
        """Build system message for contract Q&A."""
        return """You are a Contract Analysis Assistant helping users understand contracts.

Guidelines:
- Answer questions based on the provided contract context
- Reference specific clauses when relevant
- Be clear and concise
- Use professional but accessible language
- If information isn't in the context, say so
- Don't make up information"""

    def _build_query_user_message(self, query: str, context: Dict) -> str:
        """Build user message for contract Q&A."""
        context_text = "Contract Context:\n"

        if 'contract_metadata' in context:
            metadata = context['contract_metadata']
            context_text += f"- Parties: {metadata.get('parties', 'Unknown')}\n"
            context_text += f"- Date: {metadata.get('effective_date', 'Unknown')}\n"

        # Include retrieved raw contract sections (from tri-layer retrieval)
        if '_retrieved_sections' in context and context['_retrieved_sections']:
            context_text += f"\nRelevant Contract Sections:\n{context['_retrieved_sections']}\n"

        if 'clauses' in context and context['clauses']:
            context_text += "\nAnalyzed Clauses:\n"
            for clause in context['clauses'][:10]:
                context_text += f"- {clause.get('title', 'Untitled')}\n"

        return f"""{context_text}

User Question: {query}

Please answer based on the contract context provided above."""

    # =========================================================================
    # ReAct-style tool calling (Phase 2: Chat-first UI)
    # =========================================================================

    def process_with_tools(
        self,
        user_message: str,
        tool_registry,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        token_callback: Optional[Callable[[str], None]] = None,
        max_iterations: int = 5,
    ) -> List[Dict[str, str]]:
        """
        Process a user message with ReAct-style tool calling.

        Runs a loop: generate -> check for TOOL_CALL -> execute tool ->
        feed observation back -> repeat until final answer or max iterations.

        Args:
            user_message: The user's chat message.
            tool_registry: ToolRegistry instance with available tools.
            conversation_history: Prior messages for context.
            progress_callback: Optional progress callback.
            max_iterations: Max tool call rounds (default 5).

        Returns:
            List of message dicts: [{"role": ..., "content": ...}, ...]
            Includes thoughts, tool calls, observations, and final answer.
        """
        from src.tool_registry import ToolRegistry

        if not self._model_loaded:
            self._load_model(progress_callback)

        # Assemble system prompt from markdown files
        system_prompt = tool_registry.get_system_prompt()
        skill_prompt = tool_registry.get_skill_prompt("all")
        full_system = f"{system_prompt}\n\n{skill_prompt}"

        # Build conversation context
        messages = []
        if conversation_history:
            # Include last N messages for context (keep it short for local models)
            for msg in conversation_history[-6:]:
                messages.append(msg)

        messages.append({"role": "user", "content": user_message})

        # The ReAct loop
        result_messages = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            if progress_callback:
                progress_callback(f"Thinking... (step {iteration})", int(20 + iteration * 15))

            # Build the user prompt with conversation context
            context_parts = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "user":
                    context_parts.append(f"User: {content}")
                elif role == "assistant":
                    context_parts.append(f"Assistant: {content}")
                elif role == "observation":
                    context_parts.append(f"OBSERVATION: {content}")

            user_prompt = "\n\n".join(context_parts)

            # Run inference
            try:
                response = self._run_inference(
                    system_message=full_system,
                    user_message=user_prompt,
                    max_tokens=self.MAX_TOKENS_QUERY * 2,
                    temperature=0.3,
                    token_callback=token_callback,
                )
            except Exception as e:
                result_messages.append({
                    "role": "error",
                    "content": f"AI inference failed: {e}"
                })
                break

            response = response.strip()

            # Check for tool call
            parsed = ToolRegistry.parse_tool_call(response)

            if parsed:
                tool_name, tool_args = parsed

                # Extract thought (text before TOOL_CALL)
                thought_match = re.search(r'THOUGHT:\s*(.+?)(?=TOOL_CALL:)', response, re.DOTALL)
                thought = thought_match.group(1).strip() if thought_match else ""

                if thought:
                    result_messages.append({"role": "thought", "content": thought})

                result_messages.append({
                    "role": "tool_call",
                    "content": f"{tool_name}({', '.join(f'{k}=\"{v}\"' for k, v in tool_args.items())})"
                })

                if progress_callback:
                    progress_callback(f"Running {tool_name}...", int(30 + iteration * 15))

                # Execute tool
                observation = tool_registry.execute(tool_name, tool_args)
                result_messages.append({"role": "observation", "content": observation})

                # Truncate large observations to prevent context overflow
                obs_for_context = observation
                if len(obs_for_context) > 2000:
                    obs_for_context = obs_for_context[:2000] + "\n\n[... results truncated for context ...]"

                # Feed observation back into context
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "observation", "content": obs_for_context})

                # For heavy tools (full reviews), skip additional iterations —
                # the results are already displayed to the user
                if tool_name in ("run_full_bid_review", "run_full_contract_analysis", "run_specs_extraction"):
                    result_messages.append({
                        "role": "assistant",
                        "content": "The analysis is complete. Results have been displayed above."
                    })
                    break

            else:
                # No tool call — this is the final answer
                # Strip any leftover THOUGHT: prefix
                final = re.sub(r'^THOUGHT:\s*', '', response, flags=re.MULTILINE).strip()
                result_messages.append({"role": "assistant", "content": final})
                break
        else:
            # Max iterations reached
            result_messages.append({
                "role": "assistant",
                "content": "I've reached the maximum number of analysis steps. "
                           "Here's what I found so far based on the tool results above."
            })

        if progress_callback:
            progress_callback("Complete", 100)

        return result_messages


# Backwards compatibility alias
PythiaModelClient = LocalModelClient
