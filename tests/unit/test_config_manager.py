"""
Unit tests for ConfigManager class.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from src.config_manager import ConfigManager


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    def test_initialization_with_defaults(self):
        """Test that ConfigManager initializes with default values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "nonexistent_config.json")
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            assert config["window_width"] == 1024
            assert config["window_height"] == 768
            assert config["theme"] == "light"
    
    def test_load_missing_config_file(self):
        """Test loading when config file doesn't exist returns defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "missing_config.json")
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            # Should return defaults without error
            assert config["window_width"] == 1024
            assert config["theme"] == "light"
    
    def test_load_valid_config_file(self):
        """Test loading a valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "test_config.json")
            
            # Create a test config file (JSON format)
            test_config = {
                "window_width": 1280,
                "window_height": 720,
                "theme": "dark",
                "openai_api_key_encrypted": "test_encrypted_key"
            }
            with open(config_path, 'w') as f:
                json.dump(test_config, f)
            
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            assert config["window_width"] == 1280
            assert config["window_height"] == 720
            assert config["theme"] == "dark"
    
    def test_load_corrupted_config_file(self):
        """Test that corrupted config file falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "corrupted_config.json")
            
            # Create a corrupted config file (invalid JSON)
            with open(config_path, 'w') as f:
                f.write("{ invalid json content }")
            
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            # Should return defaults without crashing
            assert config["window_width"] == 1024
            assert config["theme"] == "light"
    
    def test_save_config(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "save_test_config.json")
            config_manager = ConfigManager(config_path)
            
            # Modify config
            new_config = {
                "window_width": 1920,
                "window_height": 1080,
                "theme": "dark",
            }
            
            # Save config
            result = config_manager.save_config(new_config)
            assert result is True
            
            # Verify file was created
            assert os.path.exists(config_path)
            
            # Verify it's valid JSON
            with open(config_path, 'r') as f:
                saved_data = json.load(f)
                assert saved_data["window_width"] == 1920
                assert saved_data["window_height"] == 1080
    
    def test_get_openai_key_encrypted(self):
        """Test retrieving and decrypting OpenAI API key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "api_key_config.json")
            config_manager = ConfigManager(config_path)
            
            # Set API key (will be encrypted)
            test_key = "sk-test123456789abcdef"
            config_manager.set_openai_key(test_key)
            
            # Retrieve and verify decryption
            retrieved_key = config_manager.get_openai_key()
            assert retrieved_key == test_key
    
    def test_get_openai_key_not_present(self):
        """Test retrieving OpenAI API key when not configured."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "no_key_config.json")
            config_manager = ConfigManager(config_path)
            config_manager.load_config()
            
            api_key = config_manager.get_openai_key()
            assert api_key is None
    
    def test_set_openai_key_encryption(self):
        """Test that API key is encrypted when stored."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "encrypt_test.json")
            config_manager = ConfigManager(config_path)
            
            test_key = "sk-new-key-abc123"
            config_manager.set_openai_key(test_key)
            
            # Verify key is encrypted in config
            encrypted_key = config_manager.config.get("openai_api_key_encrypted")
            assert encrypted_key is not None
            assert encrypted_key != test_key  # Should be encrypted, not plaintext
            
            # Verify decryption works
            retrieved_key = config_manager.get_openai_key()
            assert retrieved_key == test_key
    
    def test_validate_config_missing_api_key(self):
        """Test configuration validation with missing API key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "validate_test.json")
            config_manager = ConfigManager(config_path)
            
            is_valid, errors = config_manager.validate_config()
            assert not is_valid
            assert any("API key is missing" in error for error in errors)
    
    def test_validate_config_invalid_api_key_format(self):
        """Test configuration validation with invalid API key format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "validate_test.json")
            config_manager = ConfigManager(config_path)
            
            # Set invalid API key (doesn't start with sk-)
            config_manager.set_openai_key("invalid-key-format")
            
            is_valid, errors = config_manager.validate_config()
            assert not is_valid
            assert any("invalid" in error.lower() for error in errors)
    
    def test_validate_config_valid(self):
        """Test configuration validation with valid settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "validate_test.json")
            config_manager = ConfigManager(config_path)
            
            # Set valid API key
            config_manager.set_openai_key("sk-validkey123456789abcdef")
            
            is_valid, errors = config_manager.validate_config()
            assert is_valid
            assert len(errors) == 0
    
    def test_validate_config_invalid_window_dimensions(self):
        """Test configuration validation with invalid window dimensions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "validate_test.json")
            config_manager = ConfigManager(config_path)
            
            # Set valid API key but invalid window size
            config_manager.set_openai_key("sk-validkey123456789abcdef")
            config_manager.set_window_settings(400, 300)  # Too small
            
            is_valid, errors = config_manager.validate_config()
            assert not is_valid
            assert any("window dimensions" in error.lower() for error in errors)
    
    def test_get_window_settings(self):
        """Test retrieving window settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "window_config.json")
            config_manager = ConfigManager(config_path)
            
            config_manager.set_window_settings(1280, 720)
            
            window_settings = config_manager.get_window_settings()
            assert window_settings["window_width"] == 1280
            assert window_settings["window_height"] == 720
    
    def test_set_window_settings(self):
        """Test setting window settings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "window_test.json")
            config_manager = ConfigManager(config_path)
            
            config_manager.set_window_settings(1600, 900)
            
            window_settings = config_manager.get_window_settings()
            assert window_settings["window_width"] == 1600
            assert window_settings["window_height"] == 900
    
    def test_get_theme(self):
        """Test retrieving theme setting."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "theme_test.json")
            config_manager = ConfigManager(config_path)
            
            theme = config_manager.get_theme()
            assert theme == "light"  # Default
    
    def test_set_theme(self):
        """Test setting theme."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "theme_test.json")
            config_manager = ConfigManager(config_path)
            
            config_manager.set_theme("dark")
            
            theme = config_manager.get_theme()
            assert theme == "dark"
    
    def test_set_invalid_theme(self):
        """Test setting invalid theme falls back to default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "theme_test.json")
            config_manager = ConfigManager(config_path)
            
            config_manager.set_theme("invalid")
            
            theme = config_manager.get_theme()
            assert theme == "light"  # Should fall back to default
    
    def test_get_all_settings(self):
        """Test retrieving all settings (without encrypted key)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "all_settings_test.json")
            config_manager = ConfigManager(config_path)
            
            config_manager.set_window_settings(1024, 768)
            config_manager.set_openai_key("sk-test123")
            
            all_settings = config_manager.get_all_settings()
            assert all_settings["window_width"] == 1024
            assert all_settings["window_height"] == 768
            # Encrypted key should not be in returned settings
            assert "openai_api_key_encrypted" not in all_settings
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "reset_test.json")
            config_manager = ConfigManager(config_path)
            
            # Modify settings
            config_manager.set_window_settings(1920, 1080)
            config_manager.set_theme("dark")
            
            # Reset to defaults
            config_manager.reset_to_defaults()
            
            # Verify defaults are restored
            assert config_manager.get_window_settings()["window_width"] == 1024
            assert config_manager.get_theme() == "light"
    
    def test_persistence_across_instances(self):
        """Test that saved config persists across ConfigManager instances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "persist_config.json")
            
            # First instance - save config
            config_manager1 = ConfigManager(config_path)
            config_manager1.set_window_settings(1440, 900)
            config_manager1.set_openai_key("sk-persist-test-key123")
            config_manager1.save_config()
            
            # Second instance - load config
            config_manager2 = ConfigManager(config_path)
            config_manager2.load_config()
            
            window_settings = config_manager2.get_window_settings()
            assert window_settings["window_width"] == 1440
            assert window_settings["window_height"] == 900
            assert config_manager2.get_openai_key() == "sk-persist-test-key123"
    
    def test_config_file_creation_in_appdata(self):
        """Test that config file is created in %APPDATA%/CR2A/ when no path specified."""
        # Create ConfigManager without specifying path
        config_manager = ConfigManager()
        
        # Verify path is in APPDATA/CR2A
        expected_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'CR2A'
        assert config_manager.config_path.parent == expected_dir
        assert config_manager.config_path.name == 'config.json'

    def test_get_max_file_size_default(self):
        """Test retrieving default max file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "file_size_test.json")
            config_manager = ConfigManager(config_path)
            
            max_size = config_manager.get_max_file_size()
            assert max_size == 200 * 1024 * 1024  # 200 MB default
    
    def test_set_max_file_size(self):
        """Test setting max file size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "file_size_test.json")
            config_manager = ConfigManager(config_path)
            
            # Set to 150 MB
            config_manager.set_max_file_size(150 * 1024 * 1024)
            
            max_size = config_manager.get_max_file_size()
            assert max_size == 150 * 1024 * 1024
    
    def test_set_max_file_size_minimum_validation(self):
        """Test that max file size has minimum of 1 MB."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "file_size_test.json")
            config_manager = ConfigManager(config_path)
            
            # Try to set below minimum (500 KB)
            config_manager.set_max_file_size(500 * 1024)
            
            # Should be set to minimum 1 MB
            max_size = config_manager.get_max_file_size()
            assert max_size == 1024 * 1024
    
    def test_load_config_backward_compatibility_max_file_size(self):
        """Test that loading config without max_file_size adds default value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "old_config.json")
            
            # Create old config file without max_file_size
            old_config = {
                "window_width": 1280,
                "window_height": 720,
                "theme": "dark"
            }
            with open(config_path, 'w') as f:
                json.dump(old_config, f)
            
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            # Should have default max_file_size
            assert "max_file_size" in config
            assert config["max_file_size"] == 200 * 1024 * 1024
            
            # Other settings should be preserved
            assert config["window_width"] == 1280
            assert config["window_height"] == 720
            assert config["theme"] == "dark"
    
    def test_load_config_backward_compatibility_pythia_model_size(self):
        """Test that loading config with obsolete pythia_model_size doesn't cause errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "legacy_config.json")
            
            # Create legacy config file with pythia_model_size
            legacy_config = {
                "window_width": 1280,
                "window_height": 720,
                "pythia_model_size": "1B",
                "theme": "dark"
            }
            with open(config_path, 'w') as f:
                json.dump(legacy_config, f)
            
            config_manager = ConfigManager(config_path)
            config = config_manager.load_config()
            
            # Should load successfully without errors
            assert config["window_width"] == 1280
            assert config["window_height"] == 720
            assert config["theme"] == "dark"
            # pythia_model_size may be present but should be ignored
            # Validation should pass even with obsolete setting
            config_manager.set_openai_key("sk-validkey123456789abcdef")
            is_valid, errors = config_manager.validate_config()
            assert is_valid
            assert len(errors) == 0
    
    def test_max_file_size_persistence(self):
        """Test that max_file_size persists across save/load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "persist_file_size.json")
            
            # First instance - set and save
            config_manager1 = ConfigManager(config_path)
            config_manager1.set_max_file_size(300 * 1024 * 1024)  # 300 MB
            config_manager1.save_config()
            
            # Second instance - load
            config_manager2 = ConfigManager(config_path)
            config_manager2.load_config()
            
            max_size = config_manager2.get_max_file_size()
            assert max_size == 300 * 1024 * 1024
