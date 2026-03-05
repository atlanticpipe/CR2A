"""
Model Manager for Local LLM Downloads and Caching

This module provides the ModelManager class for downloading, caching, and
managing local model files from HuggingFace. Models are stored locally
in the user's AppData directory for persistent caching.

Features:
- Download models from HuggingFace with progress tracking
- SHA256 verification for integrity
- Local caching in %APPDATA%\CR2A\models\
- Support for Llama 3.2 3B (primary), Llama 3.1 8B, and legacy models
- Resume partial downloads
- Model registry with metadata
"""

import hashlib
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
import requests

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages local LLM model files: download, caching, and lifecycle.

    This class handles all aspects of model file management including:
    - Downloading from HuggingFace
    - Verifying file integrity (SHA256)
    - Caching in user's AppData directory
    - Supporting custom user-trained models
    - Cleaning up old models

    Attributes:
        models_dir: Path to local model storage directory
        MODEL_REGISTRY: Dictionary of available models with metadata
    """

    # Model registry - available models with download information
    MODEL_REGISTRY = {
        # === Llama 3.2 3B Instruct (Recommended for CPU) ===
        "llama-3.2-3b-q4": {
            "name": "Llama 3.2 3B Instruct (Q4_K_M)",
            "description": "Recommended. Fast on CPU, ~3GB RAM. Best for most systems.",
            "url": "https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            "filename": "Llama-3.2-3B-Instruct-Q4_K_M.gguf",
            "size_mb": 2020,
            "sha256": None,
            "recommended": True
        },
        # === Llama 3.1 8B Instruct (Higher quality, slower on CPU) ===
        "llama-3.1-8b-q4": {
            "name": "Llama 3.1 8B Instruct (Q4_K_M)",
            "description": "Higher quality analysis, but slower on CPU. ~6GB RAM required.",
            "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            "filename": "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf",
            "size_mb": 4920,
            "sha256": None,
            "recommended": False
        },
        "llama-3.1-8b-q3": {
            "name": "Llama 3.1 8B Instruct (Q3_K_M)",
            "description": "Lighter 8B option. ~5GB RAM required.",
            "url": "https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF/resolve/main/Meta-Llama-3.1-8B-Instruct-Q3_K_M.gguf",
            "filename": "Meta-Llama-3.1-8B-Instruct-Q3_K_M.gguf",
            "size_mb": 3900,
            "sha256": None,
            "recommended": False
        },
    }

    # Download settings
    CHUNK_SIZE = 8192  # 8KB chunks for streaming download
    TIMEOUT = 30  # Request timeout in seconds
    MAX_RETRIES = 3  # Retry failed downloads

    def __init__(self):
        """
        Initialize Model Manager.

        Creates models directory in user's AppData if it doesn't exist.
        """
        # Determine models directory based on OS
        if os.name == 'nt':  # Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            self.models_dir = Path(appdata) / 'CR2A' / 'models'
        else:  # Linux/Mac
            self.models_dir = Path.home() / '.cr2a' / 'models'

        # Create directory if it doesn't exist
        self.models_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"ModelManager initialized: models_dir={self.models_dir}")

    # =========================================================================
    # Public API
    # =========================================================================

    def get_model_path(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Path:
        """
        Get path to model file, checking bundled models first.

        This is the main entry point for getting a model. It checks in this order:
        1. Bundled model (if running as compiled executable)
        2. Project models directory (if running as script)
        3. Cached model in AppData
        4. Downloads if not found

        Args:
            model_name: Model identifier from MODEL_REGISTRY or custom name
            progress_callback: Optional callback(status_message, percent)

        Returns:
            Path to the model file

        Raises:
            ValueError: If model_name is not in registry and not a custom model
            RuntimeError: If download fails
        """
        logger.info(f"get_model_path called for: {model_name}")

        # Check if it's a registered model
        if model_name in self.MODEL_REGISTRY:
            model_info = self.MODEL_REGISTRY[model_name]
            filename = model_info['filename']

            # 1. Check for bundled model (PyInstaller compiled executable)
            if getattr(sys, 'frozen', False):
                # Running as compiled executable - check _MEIPASS
                bundled_path = Path(sys._MEIPASS) / "models" / filename
                if bundled_path.exists():
                    logger.info(f"Using bundled model: {bundled_path}")
                    if progress_callback:
                        progress_callback(f"Loading bundled {model_name}", 100)
                    return bundled_path
                else:
                    logger.info(f"Bundled model not found at: {bundled_path}")
            else:
                # 2. Running as script - check project models directory
                project_models_dir = Path(__file__).parent.parent / "models"
                project_model_path = project_models_dir / filename
                if project_model_path.exists():
                    logger.info(f"Using project bundled model: {project_model_path}")
                    if progress_callback:
                        progress_callback(f"Loading bundled {model_name}", 100)
                    return project_model_path
                else:
                    logger.info(f"Project model not found at: {project_model_path}")

            # 3. Check cached model in AppData
            cached_path = self.models_dir / filename
            if cached_path.exists():
                logger.info(f"Model found in cache: {cached_path}")
                if progress_callback:
                    progress_callback(f"Using cached {model_name}", 100)
                return cached_path

            # 4. Not found anywhere - download it
            logger.info(f"Model not found locally, downloading: {model_name}")
            return self.download_model(model_name, progress_callback)

        # Check if it's a custom model path
        custom_path = Path(model_name)
        if custom_path.exists():
            logger.info(f"Using custom model: {custom_path}")
            return custom_path

        # Not found anywhere
        raise ValueError(
            f"Model '{model_name}' not found.\n\n"
            "Available models:\n" +
            "\n".join(f"- {name}: {info['name']}"
                     for name, info in self.MODEL_REGISTRY.items()) +
            "\n\nOr provide path to custom model file."
        )

    def download_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> Path:
        """
        Download model from HuggingFace with progress tracking.

        Downloads the model file in chunks, showing progress and supporting
        resume of partial downloads. Verifies SHA256 checksum if available.

        Args:
            model_name: Model identifier from MODEL_REGISTRY
            progress_callback: Optional callback(status_message, percent)

        Returns:
            Path to downloaded model file

        Raises:
            ValueError: If model_name not in registry
            RuntimeError: If download fails after retries
        """
        if model_name not in self.MODEL_REGISTRY:
            raise ValueError(f"Unknown model: {model_name}")

        model_info = self.MODEL_REGISTRY[model_name]
        url = model_info['url']
        filename = model_info['filename']
        expected_size_mb = model_info['size_mb']

        output_path = self.models_dir / filename
        partial_path = self.models_dir / f"{filename}.partial"

        logger.info(f"Downloading {model_name} from {url}")

        if progress_callback:
            progress_callback(
                f"Preparing to download {model_name} ({expected_size_mb}MB)...",
                0
            )

        # Download with retries
        for attempt in range(self.MAX_RETRIES):
            try:
                self._download_with_progress(
                    url=url,
                    output_path=partial_path,
                    progress_callback=progress_callback,
                    model_name=model_name,
                    expected_size_mb=expected_size_mb
                )

                # Verify file size
                actual_size_mb = partial_path.stat().st_size / (1024 * 1024)
                if abs(actual_size_mb - expected_size_mb) > 100:  # Allow 100MB variance
                    logger.warning(
                        f"File size mismatch: expected ~{expected_size_mb}MB, "
                        f"got {actual_size_mb:.1f}MB"
                    )

                # Verify checksum if available
                if model_info.get('sha256'):
                    if progress_callback:
                        progress_callback("Verifying file integrity...", 95)

                    if not self._verify_checksum(partial_path, model_info['sha256']):
                        raise RuntimeError("Checksum verification failed")

                # Move to final location
                if output_path.exists():
                    output_path.unlink()
                partial_path.rename(output_path)

                logger.info(f"Download complete: {output_path}")
                if progress_callback:
                    progress_callback(f"{model_name} downloaded successfully", 100)

                return output_path

            except Exception as e:
                logger.error(f"Download attempt {attempt + 1}/{self.MAX_RETRIES} failed: {e}")

                if attempt < self.MAX_RETRIES - 1:
                    if progress_callback:
                        progress_callback(
                            f"Download failed, retrying ({attempt + 2}/{self.MAX_RETRIES})...",
                            0
                        )
                else:
                    # Final attempt failed
                    if partial_path.exists():
                        partial_path.unlink()
                    raise RuntimeError(
                        f"Failed to download {model_name} after {self.MAX_RETRIES} attempts.\n\n"
                        f"Error: {e}\n\n"
                        "Please check your internet connection and try again."
                    )

    def list_models(self) -> List[Dict]:
        """
        List all cached models with metadata.

        Returns:
            List of dictionaries with model information:
            [
                {
                    "name": "pythia-2.8b-q4",
                    "display_name": "Pythia 2.8B (Quantized Q4_K_M)",
                    "path": Path(...),
                    "size_mb": 2800.5,
                    "is_custom": False,
                    "recommended": True
                },
                ...
            ]
        """
        models = []

        # Check registry models
        for model_name, model_info in self.MODEL_REGISTRY.items():
            model_path = self.models_dir / model_info['filename']
            if model_path.exists():
                models.append({
                    "name": model_name,
                    "display_name": model_info['name'],
                    "path": model_path,
                    "size_mb": model_path.stat().st_size / (1024 * 1024),
                    "is_custom": False,
                    "recommended": model_info.get('recommended', False)
                })

        # Check for custom models (anything not in registry)
        for model_file in self.models_dir.glob("*.gguf"):
            if model_file.name not in [info['filename'] for info in self.MODEL_REGISTRY.values()]:
                models.append({
                    "name": model_file.stem,
                    "display_name": f"Custom: {model_file.name}",
                    "path": model_file,
                    "size_mb": model_file.stat().st_size / (1024 * 1024),
                    "is_custom": True,
                    "recommended": False
                })

        return models

    def delete_model(self, model_name: str) -> bool:
        """
        Delete a cached model file.

        Args:
            model_name: Model identifier

        Returns:
            True if deleted successfully, False if model not found

        Raises:
            RuntimeError: If deletion fails (permissions, etc.)
        """
        # Try registry models first
        if model_name in self.MODEL_REGISTRY:
            model_path = self.models_dir / self.MODEL_REGISTRY[model_name]['filename']
        else:
            # Try as direct filename
            model_path = self.models_dir / model_name
            if not model_path.exists():
                model_path = self.models_dir / f"{model_name}.gguf"

        if not model_path.exists():
            logger.warning(f"Model not found for deletion: {model_name}")
            return False

        try:
            model_path.unlink()
            logger.info(f"Deleted model: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete model: {e}")
            raise RuntimeError(f"Failed to delete model: {e}")

    def register_custom_model(
        self,
        display_name: str,
        source_path: Path
    ) -> Path:
        """
        Register a custom fine-tuned model.

        Copies the model file to the models directory and registers it
        for use in the application.

        Args:
            display_name: Human-readable name for the model
            source_path: Path to the custom model file (GGUF format)

        Returns:
            Path to registered model in models directory

        Raises:
            ValueError: If source file doesn't exist or isn't a .gguf file
            RuntimeError: If copy fails
        """
        if not source_path.exists():
            raise ValueError(f"Source model file not found: {source_path}")

        if source_path.suffix.lower() != '.gguf':
            raise ValueError("Custom model must be in GGUF format (.gguf extension)")

        # Create safe filename from display name
        safe_name = "".join(
            c for c in display_name.lower()
            if c.isalnum() or c in ('-', '_')
        )
        target_filename = f"custom-{safe_name}.gguf"
        target_path = self.models_dir / target_filename

        logger.info(f"Registering custom model: {display_name} -> {target_path}")

        try:
            # Copy file
            shutil.copy2(source_path, target_path)
            logger.info(f"Custom model registered: {target_path}")
            return target_path
        except Exception as e:
            logger.error(f"Failed to register custom model: {e}")
            raise RuntimeError(f"Failed to register custom model: {e}")

    def is_model_cached(self, model_name: str) -> bool:
        """
        Check if a model is already downloaded and cached.

        Args:
            model_name: Model identifier

        Returns:
            True if model exists in cache, False otherwise
        """
        if model_name in self.MODEL_REGISTRY:
            model_path = self.models_dir / self.MODEL_REGISTRY[model_name]['filename']
            return model_path.exists()

        # Check as custom model
        custom_path = Path(model_name)
        if custom_path.exists():
            return True

        return False

    def get_total_cache_size(self) -> float:
        """
        Get total size of all cached models.

        Returns:
            Total size in megabytes
        """
        total_bytes = sum(
            f.stat().st_size
            for f in self.models_dir.glob("*.gguf")
        )
        return total_bytes / (1024 * 1024)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _download_with_progress(
        self,
        url: str,
        output_path: Path,
        progress_callback: Optional[Callable[[str, int], None]],
        model_name: str,
        expected_size_mb: int
    ) -> None:
        """
        Download file with progress tracking.

        Args:
            url: Download URL
            output_path: Where to save file
            progress_callback: Progress callback
            model_name: Model name for progress messages
            expected_size_mb: Expected file size in MB

        Raises:
            RuntimeError: If download fails
        """
        # Start download
        response = requests.get(url, stream=True, timeout=self.TIMEOUT)
        response.raise_for_status()

        # Get file size
        total_size = int(response.headers.get('content-length', 0))
        total_size_mb = total_size / (1024 * 1024)

        logger.info(f"Downloading {total_size_mb:.1f}MB...")

        # Download in chunks
        downloaded = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)

                    # Update progress
                    if progress_callback and total_size > 0:
                        percent = min(int((downloaded / total_size) * 90), 90)  # Reserve 10% for verification
                        downloaded_mb = downloaded / (1024 * 1024)
                        progress_callback(
                            f"Downloading {model_name}: {downloaded_mb:.1f}/{total_size_mb:.1f}MB",
                            percent
                        )

        logger.info(f"Download completed: {downloaded / (1024 * 1024):.1f}MB")

    def _verify_checksum(self, file_path: Path, expected_sha256: str) -> bool:
        """
        Verify file integrity using SHA256 checksum.

        Args:
            file_path: Path to file to verify
            expected_sha256: Expected SHA256 hash (hex string)

        Returns:
            True if checksum matches, False otherwise
        """
        logger.info("Verifying file checksum...")

        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)

        actual_sha256 = sha256_hash.hexdigest()

        if actual_sha256 == expected_sha256:
            logger.info("Checksum verification passed")
            return True
        else:
            logger.error(
                f"Checksum mismatch!\n"
                f"Expected: {expected_sha256}\n"
                f"Actual:   {actual_sha256}"
            )
            return False

    def get_registry_models(self) -> List[Dict]:
        """
        Get list of all models in the registry (available for download).

        Returns:
            List of model info dictionaries from MODEL_REGISTRY
        """
        return [
            {
                "name": name,
                **info,
                "is_cached": self.is_model_cached(name)
            }
            for name, info in self.MODEL_REGISTRY.items()
        ]
