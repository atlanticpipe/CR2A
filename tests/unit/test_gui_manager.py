"""
Unit tests for TkinterGUIManager.

Tests the GUI manager functionality including window initialization,
message display, settings management, and user interactions.
"""

import pytest
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock
from src.gui_manager import TkinterGUIManager


@pytest.fixture
def root():
    """Create a Tkinter root window for testing."""
    root = tk.Tk()
    yield root
    try:
        root.destroy()
    except:
        pass


@pytest.fixture
def mock_callback():
    """Create a mock callback function."""
    return Mock()


@pytest.fixture
def gui_manager(root, mock_callback):
    """Create a TkinterGUIManager instance for testing."""
    return TkinterGUIManager(root, mock_callback)


class TestTkinterGUIManagerInitialization:
    """Test GUI manager initialization."""
    
    def test_initialization_creates_window(self, root, mock_callback):
        """Test that initialization creates the main window."""
        gui = TkinterGUIManager(root, mock_callback)
        
        assert gui.root == root
        assert gui.query_callback == mock_callback
        assert gui.chat_enabled == False
        assert gui.current_file_path is None
    
    def test_window_title_set(self, root, mock_callback):
        """Test that window title is set correctly."""
        gui = TkinterGUIManager(root, mock_callback)
        
        assert root.title() == "Contract Chat UI"
    
    def test_default_settings(self, gui_manager):
        """Test that default settings are initialized."""
        settings = gui_manager.get_settings()
        
        assert settings["pythia_model"] == "410M"
        assert settings["openai_fallback"] == False


class TestFileSelection:
    """Test file selection dialog functionality."""
    
    @patch('tkinter.filedialog.askopenfilename')
    def test_show_file_dialog_returns_path(self, mock_dialog, gui_manager):
        """Test that file dialog returns selected path."""
        mock_dialog.return_value = "/path/to/contract.json"
        
        result = gui_manager.show_file_dialog()
        
        assert result == "/path/to/contract.json"
        mock_dialog.assert_called_once()
    
    @patch('tkinter.filedialog.askopenfilename')
    def test_show_file_dialog_cancelled(self, mock_dialog, gui_manager):
        """Test that file dialog returns None when cancelled."""
        mock_dialog.return_value = ""
        
        result = gui_manager.show_file_dialog()
        
        assert result is None
    
    @patch('tkinter.filedialog.askopenfilename')
    def test_load_contract_updates_file_path(self, mock_dialog, gui_manager):
        """Test that loading a contract updates the file path."""
        mock_dialog.return_value = "/path/to/contract.json"
        
        gui_manager._on_load_contract()
        
        assert gui_manager.get_current_file_path() == "/path/to/contract.json"


class TestMessageDisplay:
    """Test conversation message display."""
    
    def test_display_user_message(self, gui_manager):
        """Test displaying a user message."""
        gui_manager.display_message("Hello", "user")
        
        # Get text content
        content = gui_manager.conversation_text.get("1.0", tk.END)
        
        assert "You:" in content
        assert "Hello" in content
    
    def test_display_system_message_pythia(self, gui_manager):
        """Test displaying a system message from Pythia."""
        gui_manager.display_message("Response", "system", "pythia")
        
        content = gui_manager.conversation_text.get("1.0", tk.END)
        
        assert "💻" in content
        assert "Assistant:" in content
        assert "Response" in content
    
    def test_display_system_message_openai(self, gui_manager):
        """Test displaying a system message from OpenAI."""
        gui_manager.display_message("Response", "system", "openai")
        
        content = gui_manager.conversation_text.get("1.0", tk.END)
        
        assert "🌐" in content
        assert "Assistant:" in content
        assert "Response" in content
    
    def test_multiple_messages_displayed(self, gui_manager):
        """Test that multiple messages are displayed in order."""
        gui_manager.display_message("First", "user")
        gui_manager.display_message("Second", "system", "pythia")
        gui_manager.display_message("Third", "user")
        
        content = gui_manager.conversation_text.get("1.0", tk.END)
        
        assert "First" in content
        assert "Second" in content
        assert "Third" in content


class TestChatInput:
    """Test chat input functionality."""
    
    def test_chat_input_initially_disabled(self, gui_manager):
        """Test that chat input is initially disabled."""
        assert gui_manager.chat_enabled == False
        assert str(gui_manager.input_entry.cget("state")) == "disabled"
    
    def test_enable_chat_input(self, gui_manager):
        """Test enabling chat input."""
        gui_manager.enable_chat_input(True)
        
        assert gui_manager.chat_enabled == True
        assert str(gui_manager.input_entry.cget("state")) == "normal"
    
    def test_disable_chat_input(self, gui_manager):
        """Test disabling chat input."""
        gui_manager.enable_chat_input(True)
        gui_manager.enable_chat_input(False)
        
        assert gui_manager.chat_enabled == False
        assert str(gui_manager.input_entry.cget("state")) == "disabled"
    
    def test_send_message_calls_callback(self, gui_manager, mock_callback):
        """Test that sending a message calls the query callback."""
        gui_manager.enable_chat_input(True)
        gui_manager.input_entry.insert(0, "Test query")
        
        gui_manager._on_send()
        
        mock_callback.assert_called_once_with("Test query")
    
    def test_send_empty_message_ignored(self, gui_manager, mock_callback):
        """Test that empty messages are not sent."""
        gui_manager.enable_chat_input(True)
        gui_manager.input_entry.insert(0, "   ")
        
        gui_manager._on_send()
        
        mock_callback.assert_not_called()
    
    def test_send_clears_input(self, gui_manager, mock_callback):
        """Test that sending a message clears the input field."""
        gui_manager.enable_chat_input(True)
        gui_manager.input_entry.insert(0, "Test query")
        
        gui_manager._on_send()
        
        assert gui_manager.input_entry.get() == ""


class TestSettings:
    """Test settings management."""
    
    def test_get_default_settings(self, gui_manager):
        """Test getting default settings."""
        settings = gui_manager.get_settings()
        
        assert settings["pythia_model"] == "410M"
        assert settings["openai_fallback"] == False
    
    def test_settings_returns_copy(self, gui_manager):
        """Test that get_settings returns a copy."""
        settings1 = gui_manager.get_settings()
        settings1["pythia_model"] = "1B"
        
        settings2 = gui_manager.get_settings()
        
        assert settings2["pythia_model"] == "410M"


class TestLoadingIndicator:
    """Test loading indicator functionality."""
    
    def test_show_loading(self, gui_manager):
        """Test showing loading indicator."""
        gui_manager.show_loading("Processing...")
        
        # Check that loading frame is visible
        assert gui_manager.loading_label.cget("text") == "Processing..."
    
    def test_hide_loading(self, gui_manager):
        """Test hiding loading indicator."""
        gui_manager.show_loading("Loading...")
        gui_manager.hide_loading()
        
        # Loading frame should be hidden (place_forget called)
        # We can't easily test this without checking internal state


class TestErrorDisplay:
    """Test error display functionality."""
    
    @patch('tkinter.messagebox.showerror')
    def test_show_error_displays_message(self, mock_messagebox, gui_manager):
        """Test that show_error displays error message."""
        gui_manager.show_error("Test error")
        
        # Check conversation text
        content = gui_manager.conversation_text.get("1.0", tk.END)
        assert "Error:" in content
        assert "Test error" in content
        
        # Check messagebox was called
        mock_messagebox.assert_called_once_with("Error", "Test error")
    
    @patch('tkinter.messagebox.showerror')
    def test_multiple_errors_displayed(self, mock_messagebox, gui_manager):
        """Test that multiple errors are displayed."""
        gui_manager.show_error("Error 1")
        gui_manager.show_error("Error 2")
        
        content = gui_manager.conversation_text.get("1.0", tk.END)
        
        assert "Error 1" in content
        assert "Error 2" in content
        assert mock_messagebox.call_count == 2
