"""
API Key Manager — Secure storage and retrieval of API keys.

Checks ANTHROPIC_API_KEY environment variable first, then falls back to
encrypted storage in %APPDATA%/CR2A/config.json. Encryption uses Fernet
with a machine-specific key derived from the Windows MachineGuid registry value.
"""

import base64
import hashlib
import logging
import os
import winreg
from typing import Optional

logger = logging.getLogger(__name__)


def _get_machine_guid() -> str:
    """Read the Windows MachineGuid from the registry.

    This GUID is unique per machine and does not change across reboots,
    making it suitable as a stable seed for deriving an encryption key.
    The encrypted API key is therefore not portable between machines.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        value, _ = winreg.QueryValueEx(key, "MachineGuid")
        winreg.CloseKey(key)
        return value
    except OSError:
        # Fallback: use hostname + username as a pseudo-unique identifier
        fallback = f"{os.environ.get('COMPUTERNAME', 'unknown')}-{os.environ.get('USERNAME', 'user')}"
        logger.warning("Could not read MachineGuid from registry, using fallback identifier")
        return fallback


def _derive_fernet_key() -> bytes:
    """Derive a 32-byte Fernet key from the machine GUID."""
    guid = _get_machine_guid()
    # SHA-256 produces exactly 32 bytes; Fernet needs url-safe base64 of 32 bytes
    raw = hashlib.sha256(guid.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(raw)


class ApiKeyManager:
    """Manages secure storage and retrieval of API keys."""

    ENV_VAR = "ANTHROPIC_API_KEY"

    def __init__(self, config_manager=None):
        """
        Args:
            config_manager: Optional ConfigManager instance for encrypted storage.
                           If None, only environment variable lookup is available.
        """
        self.config_manager = config_manager

    def get_key(self) -> Optional[str]:
        """Retrieve API key: env var first, then encrypted config.

        Returns:
            The API key string, or None if not found anywhere.
        """
        # Priority 1: Environment variable
        env_key = os.environ.get(self.ENV_VAR)
        if env_key:
            logger.debug("API key found in environment variable %s", self.ENV_VAR)
            return env_key

        # Priority 2: Encrypted config
        if self.config_manager:
            encrypted = self.config_manager.get_anthropic_api_key_encrypted()
            if encrypted:
                try:
                    return self._decrypt(encrypted)
                except Exception as e:
                    logger.warning("Failed to decrypt stored API key: %s", e)

        return None

    def set_key(self, key: str) -> bool:
        """Encrypt and store API key in config.

        Args:
            key: The plaintext API key to store.

        Returns:
            True if stored successfully, False otherwise.
        """
        if not self.config_manager:
            logger.error("Cannot store API key: no ConfigManager provided")
            return False

        try:
            encrypted = self._encrypt(key)
            self.config_manager.set_anthropic_api_key_encrypted(encrypted)
            self.config_manager.save_config()
            logger.info("API key encrypted and stored successfully")
            return True
        except Exception as e:
            logger.error("Failed to encrypt/store API key: %s", e)
            return False

    def delete_key(self) -> bool:
        """Remove stored API key from config.

        Returns:
            True if removed successfully, False otherwise.
        """
        if not self.config_manager:
            return False

        self.config_manager.set_anthropic_api_key_encrypted(None)
        self.config_manager.save_config()
        logger.info("Stored API key removed")
        return True

    def validate_key(self, key: str) -> bool:
        """Test if an API key is valid by making a minimal API call.

        Args:
            key: The plaintext API key to validate.

        Returns:
            True if the key is valid, False otherwise.
        """
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            # Minimal call: short message, low max_tokens
            client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}],
            )
            return True
        except ImportError:
            logger.error("anthropic package not installed")
            return False
        except Exception as e:
            logger.warning("API key validation failed: %s", e)
            return False

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt a string using Fernet with machine-bound key."""
        from cryptography.fernet import Fernet
        f = Fernet(_derive_fernet_key())
        return f.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def _decrypt(self, token: str) -> str:
        """Decrypt a Fernet token back to plaintext."""
        from cryptography.fernet import Fernet
        f = Fernet(_derive_fernet_key())
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
