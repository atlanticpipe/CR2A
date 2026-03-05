"""
Unit tests for Settings Dialog

Tests the settings dialog for API key configuration.
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, MagicMock, patch
from src.settings_dialog import SettingsDialog, show_settings_dialog
from src.config_manager import ConfigManager
import tempfile
from pathlib import Path


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_manager(temp_config_dir):
    """Create a ConfigManager instance with temporary config path."""
    config_path = temp_config_dir / "config.json"
    return ConfigManager(config_path=str(config_path))


@pytest.fixture
def root_window():
    """Create a Tkinter root window for testing."""
    root = tk.Tk()
    root.withdraw()  # Hide the window
    yield root
    try:
        root.destroy()
    except:
        pass


class TestSettingsDialog:
    """Test suite for SettingsDialog class."""
    
    def test_initialization(self, root_window, config_manager):
        """Test that SettingsDialog initializes correctly."""
        dialog = SettingsDialog(root_window, config_manager)
        
        assert dialog.parent == root_window
        assert dialog.config_manager == config_manager
        assert dialog.dialog is None
        assert dialog.result is None
        assert dialog.custom_title is None
        assert dialog.custom_message is None
    
    def test_initialization_with_custom_title_and_message(self, root_window, config_manager):
        """Test that SettingsDialog initializes correctly with custom title and message."""
        custom_title = "API Key Setup Required"
        custom_message = "Please configure your API key."
        callback = Mock()
        
        dialog = SettingsDialog(root_window, config_manager, callback, custom_title, custom_message)
        
        assert dialog.parent == root_window
        assert dialog.config_manager == config_manager
        assert dialog.on_save_callback == callback
        assert dialog.custom_title == custom_title
        assert dialog.custom_message == custom_message
        assert dialog.dialog is None
        assert dialog.result is None
    
    def test_validate_api_key_valid(self, root_window, config_manager):
        """Test API key validation with valid keys."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # Valid API key
        is_valid, message = dialog._validate_api_key("sk-1234567890abcdefghij")
        assert is_valid is True
        assert message == ""
        
        # Valid API key with longer length
        is_valid, message = dialog._validate_api_key("sk-" + "a" * 50)
        assert is_valid is True
        assert message == ""
    
    def test_validate_api_key_invalid_prefix(self, root_window, config_manager):
        """Test API key validation rejects keys without 'sk-' prefix."""
        dialog = SettingsDialog(root_window, config_manager)
        
        is_valid, message = dialog._validate_api_key("abc-1234567890abcdefghij")
        assert is_valid is False
        assert "must start with 'sk-'" in message
    
    def test_validate_api_key_too_short(self, root_window, config_manager):
        """Test API key validation rejects keys that are too short."""
        dialog = SettingsDialog(root_window, config_manager)
        
        is_valid, message = dialog._validate_api_key("sk-12345")
        assert is_valid is False
        assert "at least 20 characters" in message
    
    def test_validate_api_key_invalid_characters(self, root_window, config_manager):
        """Test API key validation rejects keys with invalid characters."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # API key with spaces
        is_valid, message = dialog._validate_api_key("sk-1234567890 abcdefghij")
        assert is_valid is False
        assert "invalid characters" in message
        
        # API key with special characters
        is_valid, message = dialog._validate_api_key("sk-1234567890@bcdefghij")
        assert is_valid is False
        assert "invalid characters" in message
    
    def test_validate_api_key_empty(self, root_window, config_manager):
        """Test API key validation rejects empty keys."""
        dialog = SettingsDialog(root_window, config_manager)
        
        is_valid, message = dialog._validate_api_key("")
        assert is_valid is False
        assert "must start with 'sk-'" in message
    
    @patch('tkinter.messagebox.showinfo')
    def test_save_valid_api_key(self, mock_showinfo, root_window, config_manager):
        """Test saving a valid API key."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # Set up dialog components
        dialog.api_key_var = tk.StringVar(value="sk-1234567890abcdefghij")
        dialog.dialog = Mock()
        dialog.dialog.destroy = Mock()
        
        # Mock the save callback
        callback_called = []
        dialog.on_save_callback = lambda: callback_called.append(True)
        
        # Call save
        dialog._on_save()
        
        # Verify API key was saved
        saved_key = config_manager.get_openai_key()
        assert saved_key == "sk-1234567890abcdefghij"
        
        # Verify result was set to True
        assert dialog.result is True
        
        # Verify callback was called
        assert len(callback_called) == 1
        
        # Verify dialog was destroyed
        dialog.dialog.destroy.assert_called_once()
        
        # Verify success message was shown
        mock_showinfo.assert_called_once()
    
    @patch('tkinter.messagebox.showerror')
    def test_save_invalid_api_key(self, mock_showerror, root_window, config_manager):
        """Test that saving an invalid API key shows error."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # Set up dialog components
        dialog.api_key_var = tk.StringVar(value="invalid-key")
        dialog.dialog = Mock()
        
        # Call save
        dialog._on_save()
        
        # Verify error was shown
        mock_showerror.assert_called_once()
        
        # Verify API key was not saved
        saved_key = config_manager.get_openai_key()
        assert saved_key is None
        
        # Verify result was not set
        assert dialog.result is None
    
    def test_cancel_dialog(self, root_window, config_manager):
        """Test cancelling the dialog."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # Set up dialog components
        dialog.dialog = Mock()
        dialog.dialog.destroy = Mock()
        
        # Call cancel
        dialog._on_cancel()
        
        # Verify result was set to False
        assert dialog.result is False
        
        # Verify dialog was destroyed
        dialog.dialog.destroy.assert_called_once()
    
    def test_load_current_key(self, root_window, config_manager):
        """Test loading existing API key into dialog."""
        # Save an API key first
        config_manager.set_openai_key("sk-existing1234567890abc")
        config_manager.save_config()
        
        # Create dialog
        dialog = SettingsDialog(root_window, config_manager)
        dialog.api_key_var = tk.StringVar()
        
        # Load current key
        dialog._load_current_key()
        
        # Verify key was loaded
        assert dialog.api_key_var.get() == "sk-existing1234567890abc"
    
    def test_toggle_key_visibility(self, root_window, config_manager):
        """Test toggling API key visibility."""
        dialog = SettingsDialog(root_window, config_manager)
        
        # Create mock entry widget
        dialog.api_key_entry = Mock()
        dialog.show_key_var = tk.BooleanVar(value=False)
        
        # Initially hidden
        dialog._toggle_key_visibility()
        dialog.api_key_entry.config.assert_called_with(show="*")
        
        # Show key
        dialog.show_key_var.set(True)
        dialog._toggle_key_visibility()
        dialog.api_key_entry.config.assert_called_with(show="")
        
        # Hide key again
        dialog.show_key_var.set(False)
        dialog._toggle_key_visibility()
        dialog.api_key_entry.config.assert_called_with(show="*")
    
    @patch('tkinter.messagebox.showwarning')
    def test_required_close_attempt(self, mock_showwarning, root_window, config_manager):
        """Test that closing a required dialog shows warning."""
        dialog = SettingsDialog(root_window, config_manager)
        dialog.dialog = Mock()
        
        # Attempt to close required dialog
        dialog._on_required_close_attempt()
        
        # Verify warning was shown
        mock_showwarning.assert_called_once()
        
        # Verify dialog was not destroyed
        assert dialog.result is None


class TestShowSettingsDialogFunction:
    """Test suite for show_settings_dialog convenience function."""
    
    @patch('src.settings_dialog.SettingsDialog')
    def test_show_settings_dialog_not_required(self, mock_dialog_class, root_window, config_manager):
        """Test show_settings_dialog function with required=False."""
        # Set up mock
        mock_dialog_instance = Mock()
        mock_dialog_instance.show.return_value = True
        mock_dialog_class.return_value = mock_dialog_instance
        
        # Call function
        callback = Mock()
        result = show_settings_dialog(
            root_window,
            config_manager,
            required=False,
            on_save_callback=callback
        )
        
        # Verify dialog was created with correct parameters (including None for title and message)
        mock_dialog_class.assert_called_once_with(root_window, config_manager, callback, None, None)
        
        # Verify show was called with required=False
        mock_dialog_instance.show.assert_called_once_with(required=False)
        
        # Verify result
        assert result is True
    
    @patch('src.settings_dialog.SettingsDialog')
    def test_show_settings_dialog_required(self, mock_dialog_class, root_window, config_manager):
        """Test show_settings_dialog function with required=True."""
        # Set up mock
        mock_dialog_instance = Mock()
        mock_dialog_instance.show.return_value = False
        mock_dialog_class.return_value = mock_dialog_instance
        
        # Call function
        result = show_settings_dialog(
            root_window,
            config_manager,
            required=True
        )
        
        # Verify show was called with required=True
        mock_dialog_instance.show.assert_called_once_with(required=True)
        
        # Verify result
        assert result is False
    
    @patch('src.settings_dialog.SettingsDialog')
    def test_show_settings_dialog_with_custom_title(self, mock_dialog_class, root_window, config_manager):
        """Test show_settings_dialog function with custom title."""
        # Set up mock
        mock_dialog_instance = Mock()
        mock_dialog_instance.show.return_value = True
        mock_dialog_class.return_value = mock_dialog_instance
        
        # Call function with custom title
        custom_title = "API Key Setup Required"
        result = show_settings_dialog(
            root_window,
            config_manager,
            required=True,
            title=custom_title
        )
        
        # Verify dialog was created with custom title
        mock_dialog_class.assert_called_once_with(root_window, config_manager, None, custom_title, None)
        
        # Verify result
        assert result is True
    
    @patch('src.settings_dialog.SettingsDialog')
    def test_show_settings_dialog_with_custom_message(self, mock_dialog_class, root_window, config_manager):
        """Test show_settings_dialog function with custom message."""
        # Set up mock
        mock_dialog_instance = Mock()
        mock_dialog_instance.show.return_value = True
        mock_dialog_class.return_value = mock_dialog_instance
        
        # Call function with custom message
        custom_message = "Please configure your API key to continue."
        result = show_settings_dialog(
            root_window,
            config_manager,
            required=True,
            message=custom_message
        )
        
        # Verify dialog was created with custom message
        mock_dialog_class.assert_called_once_with(root_window, config_manager, None, None, custom_message)
        
        # Verify result
        assert result is True
    
    @patch('src.settings_dialog.SettingsDialog')
    def test_show_settings_dialog_with_custom_title_and_message(self, mock_dialog_class, root_window, config_manager):
        """Test show_settings_dialog function with both custom title and message."""
        # Set up mock
        mock_dialog_instance = Mock()
        mock_dialog_instance.show.return_value = True
        mock_dialog_class.return_value = mock_dialog_instance
        
        # Call function with custom title and message
        custom_title = "API Key Setup Required"
        custom_message = "The analysis engine requires an OpenAI API key to function."
        callback = Mock()
        result = show_settings_dialog(
            root_window,
            config_manager,
            required=True,
            title=custom_title,
            message=custom_message,
            on_save_callback=callback
        )
        
        # Verify dialog was created with custom title and message
        mock_dialog_class.assert_called_once_with(root_window, config_manager, callback, custom_title, custom_message)
        
        # Verify result
        assert result is True


class TestSettingsDialogIntegration:
    """Integration tests for settings dialog with ConfigManager."""
    
    def test_full_workflow_save_and_load(self, root_window, config_manager):
        """Test complete workflow: open dialog, save key, verify saved."""
        # Create dialog
        dialog = SettingsDialog(root_window, config_manager)
        
        # Simulate user input
        dialog.api_key_var = tk.StringVar(value="sk-test1234567890abcdef")
        dialog.dialog = Mock()
        dialog.dialog.destroy = Mock()
        
        # Mock messagebox
        with patch('tkinter.messagebox.showinfo'):
            # Save
            dialog._on_save()
        
        # Verify key was saved and encrypted
        saved_key = config_manager.get_openai_key()
        assert saved_key == "sk-test1234567890abcdef"
        
        # Verify config file was created
        assert config_manager.config_path.exists()
        
        # Create new config manager to verify persistence
        new_config_manager = ConfigManager(config_path=str(config_manager.config_path))
        new_config_manager.load_config()
        
        # Verify key can be loaded
        loaded_key = new_config_manager.get_openai_key()
        assert loaded_key == "sk-test1234567890abcdef"
    
    def test_validation_with_config_manager(self, root_window, config_manager):
        """Test that validation works correctly with ConfigManager."""
        # Save a valid API key
        config_manager.set_openai_key("sk-valid1234567890abcdef")
        config_manager.save_config()
        
        # Validate config
        is_valid, errors = config_manager.validate_config()
        
        # Should be valid
        assert is_valid is True
        assert len(errors) == 0
        
        # Save an invalid API key (too short)
        config_manager.set_openai_key("sk-short")
        
        # Validate config
        is_valid, errors = config_manager.validate_config()
        
        # Should be invalid
        assert is_valid is False
        assert any("invalid" in err.lower() for err in errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
