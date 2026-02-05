"""
Configuration Manager Module

Handles loading and saving application configuration including OpenAI API key
with obfuscation for the Unified CR2A Application.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import base64
import hashlib


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration and settings persistence.
    
    This class handles reading and writing configuration files in JSON format,
    with obfuscated storage of the OpenAI API key. Configuration is stored in
    %APPDATA%/CR2A/config.json on Windows.
    """
    
    # Default configuration values
    DEFAULT_CONFIG = {
        "window_width": 1024,
        "window_height": 768,
        "theme": "light",
        "max_file_size": 250 * 1024 * 1024,  # 250 MB default
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
        self._obfuscation_key = self._get_obfuscation_key()
        logger.debug("ConfigManager initialized with path: %s", self.config_path)
    
    def _get_obfuscation_key(self) -> bytes:
        """
        Get obfuscation key for API key storage.
        
        The key is derived from a machine-specific identifier to provide
        basic obfuscation. This is not cryptographically secure but prevents
        casual inspection of the API key.
        
        Returns:
            Obfuscation key bytes
        """
        machine_id = os.environ.get('COMPUTERNAME', 'default_machine')
        key_material = f"CR2A_{machine_id}_key".encode()
        return hashlib.sha256(key_material).digest()
    
    def _obfuscate(self, data: str) -> str:
        """
        Obfuscate a string using XOR with the obfuscation key.
        
        Args:
            data: String to obfuscate
            
        Returns:
            Base64-encoded obfuscated string
        """
        data_bytes = data.encode('utf-8')
        key = self._obfuscation_key
        obfuscated = bytes(b ^ key[i % len(key)] for i, b in enumerate(data_bytes))
        return base64.urlsafe_b64encode(obfuscated).decode('ascii')
    
    def _deobfuscate(self, data: str) -> str:
        """
        Deobfuscate a string that was obfuscated with _obfuscate.
        
        Args:
            data: Base64-encoded obfuscated string
            
        Returns:
            Original string
        """
        obfuscated = base64.urlsafe_b64decode(data.encode('ascii'))
        key = self._obfuscation_key
        deobfuscated = bytes(b ^ key[i % len(key)] for i, b in enumerate(obfuscated))
        return deobfuscated.decode('utf-8')
    
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
    
    def get_openai_key(self) -> Optional[str]:
        """
        Get OpenAI API key from config.
        
        The API key is stored obfuscated and is deobfuscated when retrieved.
        
        Returns:
            Deobfuscated API key or None if not configured
        """
        obfuscated_key = self.config.get("openai_api_key_encrypted")
        
        if not obfuscated_key:
            logger.debug("No OpenAI API key found in config")
            return None
        
        try:
            deobfuscated_key = self._deobfuscate(obfuscated_key)
            logger.debug("OpenAI API key retrieved from config")
            return deobfuscated_key
        except Exception as e:
            logger.error("Error deobfuscating API key: %s", e)
            return None
    
    def set_openai_key(self, api_key: str) -> None:
        """
        Set OpenAI API key in config.
        
        The API key is obfuscated before storage.
        
        Args:
            api_key: OpenAI API key to store
        """
        try:
            obfuscated_key = self._obfuscate(api_key)
            self.config["openai_api_key_encrypted"] = obfuscated_key
            logger.debug("OpenAI API key obfuscated and stored in config")
        except Exception as e:
            logger.error("Error obfuscating API key: %s", e)
            raise
    
    def validate_config(self) -> Tuple[bool, list[str]]:
        """
        Validate configuration completeness and correctness.
        
        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        
        api_key = self.get_openai_key()
        if not api_key:
            errors.append("OpenAI API key is missing")
        elif not self._validate_api_key_format(api_key):
            errors.append("OpenAI API key format is invalid (must start with 'sk-')")
        
        width = self.config.get("window_width", 0)
        height = self.config.get("window_height", 0)
        if width < 800 or height < 600:
            errors.append("Window dimensions must be at least 800x600")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_api_key_format(self, api_key: str) -> bool:
        """
        Validate OpenAI API key format.
        
        Args:
            api_key: API key to validate
            
        Returns:
            True if format is valid, False otherwise
        """
        return api_key.startswith("sk-") and len(api_key) >= 20
    
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
            Maximum file size in bytes (default: 200 MB)
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
    
    def get_all_settings(self) -> Dict[str, Any]:
        """
        Get all configuration settings.
        
        Note: The obfuscated API key is not included in the returned dictionary.
        Use get_openai_key() to retrieve the deobfuscated API key.
        
        Returns:
            Configuration dictionary (without sensitive data)
        """
        config_copy = self.config.copy()
        config_copy.pop("openai_api_key_encrypted", None)
        return config_copy
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        logger.info("Resetting configuration to defaults")
        self.config = self.DEFAULT_CONFIG.copy()
