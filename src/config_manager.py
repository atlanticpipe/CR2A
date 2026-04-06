"""
Configuration Manager Module

Handles loading and saving application configuration for the CR2A Application.
Supports local Llama models and Claude API backends for AI analysis.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration and settings persistence.

    Configuration is stored in %APPDATA%/CR2A/config.json on Windows.
    """

    # Default configuration values
    DEFAULT_CONFIG = {
        "window_width": 1024,
        "window_height": 768,
        "theme": "light",
        "max_file_size": 250 * 1024 * 1024,  # 250 MB default
        "large_file_threshold_mb": 10,  # Disable multi-pass for files > 10MB
        # Local model settings (Llama 3.1 8B)
        "local_model_name": "llama-3.1-8b-q4",  # Default model (8B for better accuracy)
        "local_model_threads": None,  # None = auto-detect CPU cores
        "local_model_path": None,  # Custom model path (overrides model_name)
        "gpu_mode": "auto",  # "auto" = auto-detect, "cpu" = force CPU-only, "gpu" = force GPU
        "gpu_backend": "auto",  # "auto", "vulkan", "sycl", "opencl", "ipex", "cpu"
        "ram_reserved_os_mb": None,  # None = auto-detect; MB of RAM reserved for OS
        "gpu_offload_layers": None,  # None = auto-detect; explicit layer count for GPU offload
        # AI backend settings
        "ai_backend": "local",  # "local" = local Llama model, "claude" = Anthropic Claude API
        "claude_model": "claude-sonnet",  # "claude-sonnet" or "claude-opus"
        "anthropic_api_key_encrypted": None,  # Fernet-encrypted API key (machine-bound)
        "fallback_to_local": False,  # Auto-fallback to local model if API unavailable
        "show_cost_estimate": True,  # Show cost estimate dialog before Claude analysis
        # Storage settings for multi-user network drive support
        "storage_mode": "local",  # "local" = %APPDATA%, "shared" = network drive
        "shared_storage_path": None,  # Path to network drive (e.g., "F:\\ContractAnalysis")
        "storage_description": None,  # User-friendly description (e.g., "FileCloud F: Drive")
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Optional custom path to configuration file.
                        If None, uses %APPDATA%/CR2A/config.json
        """
        if config_path is None:
            # Use %APPDATA%/CR2A/config.json on Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            config_dir = Path(appdata) / 'CR2A'
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = config_dir / 'config.json'
        else:
            self.config_path = Path(config_path)

        self.config: Dict[str, Any] = self.DEFAULT_CONFIG.copy()
        logger.debug("ConfigManager initialized with path: %s", self.config_path)

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        If the config file doesn't exist or is corrupted, returns default
        configuration without raising an error.

        Returns:
            Configuration dictionary
        """
        logger.info("Loading configuration from: %s", self.config_path)

        if not self.config_path.exists():
            logger.info("Config file not found, using defaults")
            return self.config.copy()

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)

            self.config = self.DEFAULT_CONFIG.copy()
            self.config.update(loaded_config)

            # Ensure max_file_size exists for backward compatibility
            if "max_file_size" not in self.config:
                logger.info("max_file_size not found in config, using default: %d bytes (%.0f MB)",
                           self.DEFAULT_CONFIG["max_file_size"],
                           self.DEFAULT_CONFIG["max_file_size"] / (1024 * 1024))
                self.config["max_file_size"] = self.DEFAULT_CONFIG["max_file_size"]


            logger.info("Configuration loaded successfully")
            return self.config.copy()

        except json.JSONDecodeError as e:
            logger.warning("Error parsing config file: %s. Using defaults.", e)
            return self.config.copy()
        except Exception as e:
            logger.warning("Error loading config file: %s. Using defaults.", e)
            return self.config.copy()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save configuration to file.

        Args:
            config: Optional configuration dictionary to save.
                   If None, saves current internal config.

        Returns:
            True if saved successfully, False otherwise
        """
        logger.info("Saving configuration to: %s", self.config_path)

        try:
            if config is not None:
                self.config.update(config)

            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)

            logger.info("Configuration saved successfully")
            return True

        except Exception as e:
            logger.error("Error saving config file: %s", e)
            return False

    def validate_config(self) -> Tuple[bool, list[str]]:
        """
        Validate configuration completeness and correctness.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        width = self.config.get("window_width", 0)
        height = self.config.get("window_height", 0)
        if width < 800 or height < 600:
            errors.append("Window dimensions must be at least 800x600")

        is_valid = len(errors) == 0
        return is_valid, errors

    def get_window_settings(self) -> Dict[str, int]:
        """
        Get window size settings.

        Returns:
            Dictionary with window_width and window_height
        """
        return {
            "window_width": self.config.get("window_width", self.DEFAULT_CONFIG["window_width"]),
            "window_height": self.config.get("window_height", self.DEFAULT_CONFIG["window_height"]),
        }

    def set_window_settings(self, width: int, height: int) -> None:
        """
        Set window size settings.

        Args:
            width: Window width in pixels
            height: Window height in pixels
        """
        self.config["window_width"] = width
        self.config["window_height"] = height
        logger.debug("Window settings updated: %dx%d", width, height)

    def get_theme(self) -> str:
        """
        Get UI theme setting.

        Returns:
            Theme string ("light" or "dark")
        """
        return self.config.get("theme", self.DEFAULT_CONFIG["theme"])

    def set_theme(self, theme: str) -> None:
        """
        Set UI theme.

        Args:
            theme: Theme string ("light" or "dark")
        """
        if theme not in ("light", "dark"):
            logger.warning("Invalid theme: %s. Using default.", theme)
            theme = self.DEFAULT_CONFIG["theme"]

        self.config["theme"] = theme
        logger.debug("Theme set to: %s", theme)

    def get_max_file_size(self) -> int:
        """
        Get configured maximum file size in bytes.

        Returns:
            Maximum file size in bytes (default: 250 MB)
        """
        return self.config.get("max_file_size", self.DEFAULT_CONFIG["max_file_size"])

    def set_max_file_size(self, size_bytes: int) -> None:
        """
        Set maximum file size.

        Args:
            size_bytes: Maximum file size in bytes
        """
        if size_bytes < 1024 * 1024:  # Minimum 1 MB
            logger.warning("File size too small: %d bytes. Using minimum 1 MB.", size_bytes)
            size_bytes = 1024 * 1024

        self.config["max_file_size"] = size_bytes
        logger.debug("Max file size set to: %d bytes (%.2f MB)", size_bytes, size_bytes / (1024*1024))

    def get_large_file_threshold_mb(self) -> int:
        """
        Get threshold for disabling multi-pass analysis (in MB).

        Returns:
            Threshold in megabytes (default: 10 MB)
        """
        return self.config.get("large_file_threshold_mb",
                              self.DEFAULT_CONFIG["large_file_threshold_mb"])

    def set_large_file_threshold_mb(self, threshold_mb: int) -> None:
        """
        Set large file threshold for disabling multi-pass.

        Args:
            threshold_mb: Threshold in megabytes (minimum 1 MB)
        """
        if threshold_mb < 1:
            logger.warning("Threshold too small: %d MB. Using minimum 1 MB.", threshold_mb)
            threshold_mb = 1

        self.config["large_file_threshold_mb"] = threshold_mb
        logger.info("Large file threshold set to: %d MB", threshold_mb)

    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all configuration settings.

        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        logger.info("Resetting configuration to defaults")
        self.config = self.DEFAULT_CONFIG.copy()

    # =========================================================================
    # Local Model Settings
    # =========================================================================

    def get_local_model_name(self) -> str:
        """
        Get name of local model to use.

        Returns:
            Model name (e.g., "llama-3.2-3b-q4")
        """
        return self.config.get("local_model_name", self.DEFAULT_CONFIG["local_model_name"])

    def set_local_model_name(self, model_name: str) -> None:
        """
        Set local model name.

        Args:
            model_name: Model identifier (e.g., "llama-3.2-3b-q4")
        """
        self.config["local_model_name"] = model_name
        logger.info(f"Local model name set to: {model_name}")

    def get_local_model_threads(self) -> Optional[int]:
        """
        Get number of CPU threads to use for local model inference.

        Returns:
            Number of threads, or None to auto-detect
        """
        return self.config.get("local_model_threads", self.DEFAULT_CONFIG["local_model_threads"])

    def set_local_model_threads(self, threads: Optional[int]) -> None:
        """
        Set number of CPU threads for local model.

        Args:
            threads: Number of threads, or None to auto-detect
        """
        if threads is not None and threads < 1:
            logger.warning("Invalid thread count: %d. Using auto-detect.", threads)
            threads = None

        self.config["local_model_threads"] = threads
        logger.info(f"Local model threads set to: {threads or 'auto-detect'}")

    def get_local_model_path(self) -> Optional[str]:
        """
        Get custom path to local model file (overrides model_name).

        Returns:
            Path to custom model file, or None to use model_name
        """
        return self.config.get("local_model_path", self.DEFAULT_CONFIG["local_model_path"])

    def set_local_model_path(self, model_path: Optional[str]) -> None:
        """
        Set custom path to local model file.

        Args:
            model_path: Path to custom GGUF model file, or None to use model_name
        """
        self.config["local_model_path"] = model_path
        logger.info(f"Local model path set to: {model_path}")

    def get_gpu_mode(self) -> str:
        """
        Get GPU mode setting.

        Returns:
            "auto" (auto-detect), "cpu" (force CPU-only), or "gpu" (force GPU)
        """
        return self.config.get("gpu_mode", self.DEFAULT_CONFIG["gpu_mode"])

    def set_gpu_mode(self, mode: str) -> None:
        """
        Set GPU mode.

        Args:
            mode: "auto", "cpu", or "gpu"
        """
        if mode not in ("auto", "cpu", "gpu"):
            logger.warning("Invalid GPU mode: %s. Using auto.", mode)
            mode = "auto"
        self.config["gpu_mode"] = mode
        logger.info(f"GPU mode set to: {mode}")

    def get_gpu_backend(self) -> str:
        """Get GPU backend preference ("auto", "vulkan", "sycl", "opencl", "ipex", "cpu")."""
        return self.config.get("gpu_backend", self.DEFAULT_CONFIG["gpu_backend"])

    def set_gpu_backend(self, backend: str) -> None:
        """Set GPU backend preference."""
        valid = ("auto", "vulkan", "sycl", "opencl", "ipex", "cpu")
        if backend not in valid:
            logger.warning("Invalid GPU backend: %s. Using auto.", backend)
            backend = "auto"
        self.config["gpu_backend"] = backend
        logger.info("GPU backend set to: %s", backend)

    def get_ram_reserved_os_mb(self) -> Optional[int]:
        """Get MB of RAM reserved for OS, or None for auto-detect."""
        return self.config.get("ram_reserved_os_mb", self.DEFAULT_CONFIG["ram_reserved_os_mb"])

    def set_ram_reserved_os_mb(self, mb: Optional[int]) -> None:
        """Set MB of RAM reserved for OS. Minimum 2048 if not None."""
        if mb is not None and mb < 2048:
            logger.warning("RAM reserved for OS too low (%d MB). Setting to 2048.", mb)
            mb = 2048
        self.config["ram_reserved_os_mb"] = mb
        logger.info(f"RAM reserved for OS set to: {mb or 'auto-detect'} MB")

    def get_gpu_offload_layers(self) -> Optional[int]:
        """Get explicit GPU offload layer count, or None for auto-detect."""
        return self.config.get("gpu_offload_layers", self.DEFAULT_CONFIG["gpu_offload_layers"])

    def set_gpu_offload_layers(self, layers: Optional[int]) -> None:
        """Set GPU offload layer count. Must be >= 0 if not None."""
        if layers is not None and layers < 0:
            logger.warning("Invalid GPU offload layers: %d. Setting to 0.", layers)
            layers = 0
        self.config["gpu_offload_layers"] = layers
        logger.info(f"GPU offload layers set to: {layers if layers is not None else 'auto-detect'}")

    def get_local_model_settings(self) -> Dict[str, Any]:
        """
        Get all local model settings as a dictionary.

        Returns:
            Dictionary with local model configuration
        """
        return {
            "local_model_name": self.get_local_model_name(),
            "local_model_threads": self.get_local_model_threads(),
            "local_model_path": self.get_local_model_path(),
            "gpu_mode": self.get_gpu_mode(),
            "gpu_backend": self.get_gpu_backend(),
            "ram_reserved_os_mb": self.get_ram_reserved_os_mb(),
            "gpu_offload_layers": self.get_gpu_offload_layers(),
        }

    # =========================================================================
    # AI Backend Settings (Local vs Claude API)
    # =========================================================================

    def get_ai_backend(self) -> str:
        """Get AI backend: 'local' or 'claude'."""
        return self.config.get("ai_backend", self.DEFAULT_CONFIG["ai_backend"])

    def set_ai_backend(self, backend: str) -> None:
        """Set AI backend. Must be 'local' or 'claude'."""
        if backend not in ("local", "claude"):
            logger.warning("Invalid AI backend: %s. Using 'local'.", backend)
            backend = "local"
        self.config["ai_backend"] = backend
        logger.info(f"AI backend set to: {backend}")

    def get_claude_model(self) -> str:
        """Get Claude model tier: 'claude-sonnet' or 'claude-opus'."""
        return self.config.get("claude_model", self.DEFAULT_CONFIG["claude_model"])

    def set_claude_model(self, model: str) -> None:
        """Set Claude model tier."""
        if model not in ("claude-sonnet", "claude-opus"):
            logger.warning("Invalid Claude model: %s. Using 'claude-sonnet'.", model)
            model = "claude-sonnet"
        self.config["claude_model"] = model
        logger.info(f"Claude model set to: {model}")

    def get_anthropic_api_key_encrypted(self) -> Optional[str]:
        """Get encrypted Anthropic API key, or None if not stored."""
        return self.config.get("anthropic_api_key_encrypted")

    def set_anthropic_api_key_encrypted(self, encrypted_key: Optional[str]) -> None:
        """Set encrypted Anthropic API key."""
        self.config["anthropic_api_key_encrypted"] = encrypted_key

    def get_fallback_to_local(self) -> bool:
        """Get whether to auto-fallback to local model if API unavailable."""
        return self.config.get("fallback_to_local", self.DEFAULT_CONFIG["fallback_to_local"])

    def set_fallback_to_local(self, fallback: bool) -> None:
        """Set auto-fallback behavior."""
        self.config["fallback_to_local"] = bool(fallback)

    def get_show_cost_estimate(self) -> bool:
        """Get whether to show cost estimate before Claude analysis."""
        return self.config.get("show_cost_estimate", self.DEFAULT_CONFIG["show_cost_estimate"])

    def set_show_cost_estimate(self, show: bool) -> None:
        """Set cost estimate dialog visibility."""
        self.config["show_cost_estimate"] = bool(show)

    # ===== Storage Settings (Multi-User Network Drive Support) =====

    def get_storage_mode(self) -> str:
        """
        Get storage mode: "local" or "shared".

        Returns:
            "local" for %APPDATA% storage, "shared" for network drive storage
        """
        return self.config.get("storage_mode", self.DEFAULT_CONFIG["storage_mode"])

    def set_storage_mode(self, mode: str) -> None:
        """
        Set storage mode.

        Args:
            mode: "local" for %APPDATA% storage, "shared" for network drive

        Raises:
            ValueError: If mode is not "local" or "shared"
        """
        if mode not in ["local", "shared"]:
            raise ValueError(f"Invalid storage mode: {mode}. Must be 'local' or 'shared'")

        self.config["storage_mode"] = mode
        logger.info(f"Storage mode set to: {mode}")

    def get_shared_storage_path(self) -> Optional[str]:
        """
        Get path to shared network drive for storage.

        Returns:
            Path to network drive (e.g., "F:\\ContractAnalysis"), or None if not configured
        """
        return self.config.get("shared_storage_path", self.DEFAULT_CONFIG["shared_storage_path"])

    def set_shared_storage_path(self, path: Optional[str]) -> None:
        """
        Set path to shared network drive.

        Args:
            path: Path to network drive (e.g., "F:\\ContractAnalysis"), or None to clear
        """
        self.config["shared_storage_path"] = path
        if path:
            logger.info(f"Shared storage path set to: {path}")
        else:
            logger.info("Shared storage path cleared")

    def get_storage_description(self) -> Optional[str]:
        """
        Get user-friendly description of storage location.

        Returns:
            Description string (e.g., "FileCloud F: Drive"), or None
        """
        return self.config.get("storage_description", self.DEFAULT_CONFIG["storage_description"])

    def set_storage_description(self, description: Optional[str]) -> None:
        """
        Set user-friendly description of storage location.

        Args:
            description: Description string (e.g., "FileCloud F: Drive")
        """
        self.config["storage_description"] = description
        logger.info(f"Storage description set to: {description}")

    def get_effective_storage_root(self) -> Path:
        """
        Get the effective storage root directory based on current settings.

        Returns:
            Path to storage root directory

        Raises:
            ValueError: If shared mode is configured but path is not set
        """
        mode = self.get_storage_mode()

        if mode == "local":
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(appdata) / 'CR2A'

        elif mode == "shared":
            shared_path = self.get_shared_storage_path()
            if not shared_path:
                raise ValueError(
                    "Shared storage mode is enabled but no network path is configured. "
                    "Please configure the shared storage path in settings."
                )
            return Path(shared_path)

        else:
            logger.warning(f"Unknown storage mode '{mode}', falling back to local")
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            return Path(appdata) / 'CR2A'

    def get_storage_settings(self) -> Dict[str, Any]:
        """
        Get all storage settings as a dictionary.

        Returns:
            Dictionary with storage configuration
        """
        return {
            "storage_mode": self.get_storage_mode(),
            "shared_storage_path": self.get_shared_storage_path(),
            "storage_description": self.get_storage_description(),
            "effective_storage_root": str(self.get_effective_storage_root())
        }
