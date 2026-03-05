"""
Unit tests for ApplicationController module.

Tests state management, component initialization, and error handling.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from src.application_controller import (
    ApplicationController,
    AppState,
    ApplicationContext
)


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestApplicationContext:
    """Test ApplicationContext dataclass."""
    
    def test_context_initialization(self):
        """Test context initializes with correct defaults."""
        context = ApplicationContext(current_state=AppState.UPLOAD)
        
        assert context.current_state == AppState.UPLOAD
        assert context.current_file is None
        assert context.analysis_result is None
        assert context.error_message is None
    
    def test_context_with_data(self):
        """Test context with all fields populated."""
        analysis_result = {"clauses": [], "risks": []}
        context = ApplicationContext(
            current_state=AppState.CHAT,
            current_file="/path/to/contract.pdf",
            analysis_result=analysis_result,
            error_message="Test error"
        )
        
        assert context.current_state == AppState.CHAT
        assert context.current_file == "/path/to/contract.pdf"
        assert context.analysis_result == analysis_result
        assert context.error_message == "Test error"


class TestAppState:
    """Test AppState enum."""
    
    def test_app_state_values(self):
        """Test all AppState enum values exist."""
        assert AppState.UPLOAD.value == "upload"
        assert AppState.ANALYZING.value == "analyzing"
        assert AppState.CHAT.value == "chat"
        assert AppState.ERROR.value == "error"
    
    def test_app_state_comparison(self):
        """Test AppState enum comparison."""
        assert AppState.UPLOAD == AppState.UPLOAD
        assert AppState.UPLOAD != AppState.CHAT


class TestApplicationController:
    """Test ApplicationController class."""
    
    def test_controller_initialization(self):
        """Test controller initializes with correct defaults."""
        controller = ApplicationController()
        
        assert controller.context.current_state == AppState.UPLOAD
        assert controller.context.current_file is None
        assert controller.context.analysis_result is None
        assert controller.context.error_message is None
        assert not controller.is_initialized()
        assert controller.get_initialization_errors() == []
    
    def test_controller_with_root(self):
        """Test controller initialization with Tkinter root."""
        mock_root = Mock()
        controller = ApplicationController(root=mock_root)
        
        assert controller.root == mock_root
        assert controller.context.current_state == AppState.UPLOAD
    
    def test_start_application(self):
        """Test starting application transitions to UPLOAD state."""
        controller = ApplicationController()
        controller.start()
        
        assert controller.get_current_state() == AppState.UPLOAD
    
    def test_transition_to_analysis(self):
        """Test transition from UPLOAD to ANALYZING state."""
        controller = ApplicationController()
        controller.start()
        
        file_path = "/path/to/contract.pdf"
        controller.transition_to_analysis(file_path)
        
        assert controller.get_current_state() == AppState.ANALYZING
        assert controller.get_current_file() == file_path
        assert controller.get_analysis_result() is None
    
    def test_transition_to_chat(self):
        """Test transition from ANALYZING to CHAT state."""
        controller = ApplicationController()
        controller.context.current_state = AppState.ANALYZING
        
        analysis_result = {
            "clauses": [{"id": "1", "text": "Test clause"}],
            "risks": []
        }
        controller.transition_to_chat(analysis_result)
        
        assert controller.get_current_state() == AppState.CHAT
        assert controller.get_analysis_result() == analysis_result
    
    def test_transition_to_upload(self):
        """Test transition back to UPLOAD state."""
        controller = ApplicationController()
        controller.context.current_state = AppState.CHAT
        controller.context.current_file = "/path/to/contract.pdf"
        controller.context.analysis_result = {"clauses": []}
        
        controller.transition_to_upload()
        
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_current_file() is None
        # Analysis result is cleared to free memory
        assert controller.get_analysis_result() is None
    
    def test_state_transition_callback(self):
        """Test state transition callbacks are called."""
        controller = ApplicationController()
        callback_called = []
        
        def test_callback():
            callback_called.append(True)
        
        controller.register_state_callback(AppState.ANALYZING, test_callback)
        controller.transition_to_analysis("/path/to/file.pdf")
        
        assert len(callback_called) == 1
        assert controller.get_current_state() == AppState.ANALYZING
    
    def test_handle_error_from_upload(self):
        """Test error handling from UPLOAD state."""
        controller = ApplicationController()
        controller.start()
        
        error = ValueError("Test error")
        controller.handle_error(error, "file upload")
        
        # Should return to UPLOAD state after error
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_error_message() is not None
        assert "Test error" in controller.get_error_message()
    
    def test_handle_error_from_analyzing(self):
        """Test error handling from ANALYZING state."""
        controller = ApplicationController()
        controller.context.current_state = AppState.ANALYZING
        
        error = RuntimeError("Analysis failed")
        controller.handle_error(error, "contract analysis")
        
        # Should return to UPLOAD state after analysis error
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_error_message() is not None
        assert "Analysis failed" in controller.get_error_message()
    
    def test_handle_error_from_chat(self):
        """Test error handling from CHAT state."""
        controller = ApplicationController()
        controller.context.current_state = AppState.CHAT
        
        error = Exception("Query processing error")
        controller.handle_error(error, "query processing")
        
        # Should stay on CHAT state after query error
        assert controller.get_current_state() == AppState.CHAT
        assert controller.get_error_message() is not None
    
    def test_clear_error(self):
        """Test clearing error message."""
        controller = ApplicationController()
        controller.context.error_message = "Test error"
        
        controller.clear_error()
        
        assert controller.get_error_message() is None
    
    def test_get_current_state(self):
        """Test getting current state."""
        controller = ApplicationController()
        
        assert controller.get_current_state() == AppState.UPLOAD
        
        controller.context.current_state = AppState.CHAT
        assert controller.get_current_state() == AppState.CHAT
    
    def test_analysis_result_storage(self):
        """Test analysis result is stored in memory."""
        controller = ApplicationController()
        controller.context.current_state = AppState.ANALYZING
        
        analysis_result = {
            "metadata": {"filename": "test.pdf"},
            "clauses": [{"id": "1", "text": "Clause 1"}],
            "risks": [{"id": "r1", "severity": "high"}],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        
        controller.transition_to_chat(analysis_result)
        
        stored_result = controller.get_analysis_result()
        assert stored_result == analysis_result
        assert stored_result["metadata"]["filename"] == "test.pdf"
        assert len(stored_result["clauses"]) == 1
        assert len(stored_result["risks"]) == 1


class TestComponentInitialization:
    """Test component initialization functionality."""
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_initialize_components_success(self, mock_query, 
                                          mock_analysis, mock_uploader, mock_config):
        """Test successful component initialization with OpenAI."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key-123"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024  # 200 MB
        mock_config.return_value = mock_config_instance
        
        # Initialize controller
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Verify initialization succeeded
        assert result is True
        assert controller.is_initialized()
        assert len(controller.get_initialization_errors()) == 0
        
        # Verify components were created
        assert controller.config_manager is not None
        assert controller.contract_uploader is not None
        assert controller.analysis_engine is not None
        assert controller.query_engine is not None
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    def test_initialize_components_missing_api_key(self, mock_analysis, 
                                                   mock_uploader, mock_config):
        """Test initialization with missing API key."""
        # Setup mock with no API key
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = None
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024  # 200 MB
        mock_config.return_value = mock_config_instance
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should still succeed but with warnings
        assert result is True
        assert controller.is_initialized()
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        assert any("API key" in error for error in errors)
    
    @patch('src.config_manager.ConfigManager')
    def test_initialize_components_config_failure(self, mock_config):
        """Test initialization failure in ConfigManager."""
        # Setup mock to raise exception
        mock_config.side_effect = Exception("Config initialization failed")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        assert not controller.is_initialized()
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        assert any("ConfigManager" in error for error in errors)
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_initialize_components_query_engine_failure(self, mock_query, mock_analysis,
                                                  mock_uploader, mock_config):
        """Test initialization with QueryEngine initialization failure."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024  # 200 MB
        mock_config.return_value = mock_config_instance
        
        # QueryEngine initialization raises exception
        mock_query.side_effect = Exception("Failed to initialize QueryEngine")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings (QueryEngine is optional)
        assert result is True
        assert controller.is_initialized()
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        assert any("Query" in error for error in errors)
    
    def test_validate_dependencies_all_present(self):
        """Test dependency validation with all components present."""
        controller = ApplicationController()
        
        # Mock all components
        controller.config_manager = Mock()
        controller.config_manager.get_openai_key.return_value = "sk-test-key"
        controller.contract_uploader = Mock()
        controller.analysis_engine = Mock()
        controller.query_engine = Mock()
        
        is_valid, missing = controller.validate_dependencies()
        
        assert is_valid is True
        assert len(missing) == 0
    
    def test_validate_dependencies_missing_api_key(self):
        """Test dependency validation with missing API key."""
        controller = ApplicationController()
        
        # Mock components but no API key
        controller.config_manager = Mock()
        controller.config_manager.get_openai_key.return_value = None
        controller.contract_uploader = Mock()
        controller.analysis_engine = None
        controller.query_engine = Mock()
        
        is_valid, missing = controller.validate_dependencies()
        
        assert is_valid is False
        assert len(missing) > 0
        assert any("API key" in dep for dep in missing)
    
    def test_validate_dependencies_query_engine_missing(self):
        """Test dependency validation with QueryEngine missing."""
        controller = ApplicationController()
        
        # Mock components but QueryEngine missing
        controller.config_manager = Mock()
        controller.config_manager.get_openai_key.return_value = "sk-test-key"
        controller.contract_uploader = Mock()
        controller.analysis_engine = Mock()
        controller.query_engine = None
        
        is_valid, missing = controller.validate_dependencies()
        
        # QueryEngine is required, so validation should fail
        assert is_valid is False
        assert len(missing) > 0
        assert any("QueryEngine" in dep for dep in missing)
    
    def test_handle_initialization_failure(self):
        """Test handling initialization failure for a component."""
        controller = ApplicationController()
        
        error = RuntimeError("Component failed to initialize")
        controller.handle_initialization_failure("TestComponent", error)
        
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        assert "TestComponent" in errors[0]
        assert controller.get_current_state() == AppState.ERROR
        assert controller.get_error_message() is not None


class TestStateTransitions:
    """Test state transition logic."""
    
    def test_upload_to_analyzing_transition(self):
        """Test valid transition from UPLOAD to ANALYZING."""
        controller = ApplicationController()
        controller.start()
        
        assert controller.get_current_state() == AppState.UPLOAD
        
        controller.transition_to_analysis("/path/to/file.pdf")
        
        assert controller.get_current_state() == AppState.ANALYZING
        assert controller.get_current_file() == "/path/to/file.pdf"
    
    def test_analyzing_to_chat_transition(self):
        """Test valid transition from ANALYZING to CHAT."""
        controller = ApplicationController()
        controller.context.current_state = AppState.ANALYZING
        
        analysis_result = {"clauses": [], "risks": []}
        controller.transition_to_chat(analysis_result)
        
        assert controller.get_current_state() == AppState.CHAT
        assert controller.get_analysis_result() == analysis_result
    
    def test_chat_to_upload_transition(self):
        """Test valid transition from CHAT to UPLOAD."""
        controller = ApplicationController()
        controller.context.current_state = AppState.CHAT
        controller.context.current_file = "/path/to/file.pdf"
        
        controller.transition_to_upload()
        
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_current_file() is None
    
    def test_invalid_state_transition_logged(self):
        """Test that invalid state transitions are logged but allowed."""
        controller = ApplicationController()
        controller.context.current_state = AppState.CHAT
        
        # Try to transition to ANALYZING from CHAT (unusual but allowed)
        controller.transition_to_analysis("/path/to/file.pdf")
        
        # Transition should succeed (controller is permissive)
        assert controller.get_current_state() == AppState.ANALYZING
    
    def test_data_preservation_on_error(self):
        """Test that analysis result is preserved when error occurs."""
        controller = ApplicationController()
        controller.context.current_state = AppState.CHAT
        
        analysis_result = {"clauses": [{"id": "1"}], "risks": []}
        controller.context.analysis_result = analysis_result
        
        # Trigger error
        error = Exception("Test error")
        controller.handle_error(error, "query processing")
        
        # Analysis result should be preserved
        assert controller.get_analysis_result() == analysis_result
        assert controller.get_analysis_result()["clauses"][0]["id"] == "1"


class TestAPIKeyDialog:
    """Test API key dialog functionality."""
    
    @patch('src.settings_dialog.show_settings_dialog')
    def test_show_api_key_dialog_when_key_missing(self, mock_dialog):
        """Test that API key dialog is shown when key is missing."""
        mock_config = Mock()
        mock_config.get_openai_key.return_value = None
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Mock the settings dialog to return True (user saved key)
        mock_dialog.return_value = True
        result = controller.show_api_key_dialog_if_needed()
        
        # Dialog should be shown
        mock_dialog.assert_called_once()
        assert result is True
    
    @patch('src.settings_dialog.show_settings_dialog')
    def test_show_api_key_dialog_when_key_invalid(self, mock_dialog):
        """Test that API key dialog is shown when key is invalid."""
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "invalid-key"
        mock_config.validate_config.return_value = (False, ["OpenAI API key is invalid"])
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Mock the settings dialog to return True (user saved key)
        mock_dialog.return_value = True
        result = controller.show_api_key_dialog_if_needed()
        
        # Dialog should be shown
        mock_dialog.assert_called_once()
        assert result is True
    
    def test_no_dialog_when_key_valid(self):
        """Test that no dialog is shown when API key is valid."""
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "sk-valid-key-12345678901234567890"
        mock_config.validate_config.return_value = (True, [])
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        result = controller.show_api_key_dialog_if_needed()
        
        # No dialog should be shown, method should return True
        assert result is True
    
    @patch('src.settings_dialog.show_settings_dialog')
    def test_dialog_cancellation_handled_gracefully(self, mock_dialog):
        """Test that dialog cancellation is handled gracefully."""
        mock_config = Mock()
        mock_config.get_openai_key.return_value = None
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Mock the settings dialog to return False (user cancelled)
        mock_dialog.return_value = False
        result = controller.show_api_key_dialog_if_needed()
        
        # Dialog should be shown
        mock_dialog.assert_called_once()
        # Method should return False when user cancels
        assert result is False
    
    def test_dialog_not_shown_when_config_manager_missing(self):
        """Test that dialog is not shown when ConfigManager is not initialized."""
        controller = ApplicationController()
        controller.config_manager = None
        
        result = controller.show_api_key_dialog_if_needed()
        
        # Method should return False when ConfigManager is missing
        assert result is False
    
    @patch('src.settings_dialog.show_settings_dialog')
    def test_dialog_includes_required_parameter(self, mock_dialog):
        """Test that dialog is shown with required=True parameter."""
        mock_config = Mock()
        mock_config.get_openai_key.return_value = None
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Mock the settings dialog
        mock_dialog.return_value = True
        controller.show_api_key_dialog_if_needed()
        
        # Verify dialog was called with required=True
        call_args = mock_dialog.call_args
        assert call_args[1]['required'] is True


class TestAPIKeySavedCallback:
    """Test _on_api_key_saved() callback functionality."""
    
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('tkinter.messagebox.showinfo')
    def test_callback_success_with_valid_key(self, mock_showinfo, mock_analysis_engine):
        """Test callback successfully initializes AnalysisEngine with valid API key."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "sk-test-key-12345678901234567890"
        mock_analysis_instance = Mock()
        mock_analysis_engine.return_value = mock_analysis_instance
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        controller.analysis_engine = None
        
        # Call the callback
        controller._on_api_key_saved()
        
        # Verify configuration was reloaded
        mock_config.load_config.assert_called_once()
        
        # Verify AnalysisEngine was initialized with the API key
        mock_analysis_engine.assert_called_once_with(openai_api_key="sk-test-key-12345678901234567890")
        assert controller.analysis_engine == mock_analysis_instance
        
        # Verify success message was shown
        mock_showinfo.assert_called_once()
        call_args = mock_showinfo.call_args
        assert "Success" in call_args[0][0]
        assert "configured successfully" in call_args[0][1]
    
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('tkinter.messagebox.showerror')
    def test_callback_handles_initialization_failure(self, mock_showerror, mock_analysis_engine):
        """Test callback handles AnalysisEngine initialization failure gracefully."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "sk-test-key-12345678901234567890"
        mock_analysis_engine.side_effect = Exception("Invalid API key")
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        controller.analysis_engine = None
        
        # Call the callback
        controller._on_api_key_saved()
        
        # Verify configuration was reloaded
        mock_config.load_config.assert_called_once()
        
        # Verify AnalysisEngine initialization was attempted
        mock_analysis_engine.assert_called_once()
        
        # Verify analysis_engine is set to None after failure
        assert controller.analysis_engine is None
        
        # Verify error message was shown with troubleshooting guidance
        mock_showerror.assert_called_once()
        call_args = mock_showerror.call_args
        assert "Initialization Failed" in call_args[0][0]
        error_message = call_args[0][1]
        assert "Invalid API key" in error_message
        assert "Troubleshooting" in error_message
        assert "platform.openai.com" in error_message
    
    @patch('tkinter.messagebox.showerror')
    def test_callback_handles_config_reload_failure(self, mock_showerror):
        """Test callback handles configuration reload failure."""
        # Setup mocks
        mock_config = Mock()
        mock_config.load_config.side_effect = Exception("Failed to load config")
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Call the callback
        controller._on_api_key_saved()
        
        # Verify error message was shown
        mock_showerror.assert_called_once()
        call_args = mock_showerror.call_args
        assert "Configuration Error" in call_args[0][0]
        assert "Failed to reload configuration" in call_args[0][1]
    
    def test_callback_returns_early_when_no_config_manager(self):
        """Test callback returns early when ConfigManager is not available."""
        controller = ApplicationController()
        controller.config_manager = None
        controller.root = Mock()
        
        # Call the callback - should not raise exception
        controller._on_api_key_saved()
        
        # No assertions needed - just verify it doesn't crash
    
    def test_callback_returns_early_when_no_api_key_after_reload(self):
        """Test callback returns early when no API key found after reload."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_openai_key.return_value = None
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        
        # Call the callback
        controller._on_api_key_saved()
        
        # Verify configuration was reloaded
        mock_config.load_config.assert_called_once()
        
        # Verify no further action was taken (no AnalysisEngine initialization)
        # No assertions needed - just verify it doesn't crash
    
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('tkinter.messagebox.showinfo')
    def test_callback_reinitializes_existing_analysis_engine(self, mock_showinfo, mock_analysis_engine):
        """Test callback reinitializes AnalysisEngine even if one already exists."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "sk-new-key-12345678901234567890"
        mock_old_engine = Mock()
        mock_new_engine = Mock()
        mock_analysis_engine.return_value = mock_new_engine
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = Mock()
        controller.analysis_engine = mock_old_engine  # Existing engine
        
        # Call the callback
        controller._on_api_key_saved()
        
        # Verify AnalysisEngine was reinitialized with new key
        mock_analysis_engine.assert_called_once_with(openai_api_key="sk-new-key-12345678901234567890")
        assert controller.analysis_engine == mock_new_engine
        assert controller.analysis_engine != mock_old_engine
        
        # Verify success message was shown
        mock_showinfo.assert_called_once()
    
    @patch('src.analysis_engine.AnalysisEngine')
    def test_callback_works_without_root_window(self, mock_analysis_engine):
        """Test callback works even without root window (no UI messages)."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_openai_key.return_value = "sk-test-key-12345678901234567890"
        mock_analysis_instance = Mock()
        mock_analysis_engine.return_value = mock_analysis_instance
        
        controller = ApplicationController()
        controller.config_manager = mock_config
        controller.root = None  # No root window
        controller.analysis_engine = None
        
        # Call the callback - should not crash
        controller._on_api_key_saved()
        
        # Verify configuration was reloaded
        mock_config.load_config.assert_called_once()
        
        # Verify AnalysisEngine was initialized
        mock_analysis_engine.assert_called_once()
        assert controller.analysis_engine == mock_analysis_instance


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

