"""
Integration tests for ApplicationController.

Tests the complete workflow of state transitions and component coordination.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from src.application_controller import ApplicationController, AppState


# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


class TestApplicationControllerIntegration:
    """Integration tests for ApplicationController workflow."""
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_complete_workflow_upload_to_chat(self, mock_query,
                                              mock_analysis, mock_uploader, mock_config):
        """Test complete workflow from upload through analysis to chat."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024  # 200 MB
        mock_config.return_value = mock_config_instance
        
        # Initialize controller
        controller = ApplicationController()
        init_result = controller.initialize_components()
        
        assert init_result is True
        assert controller.is_initialized()
        
        # Start application (UPLOAD state)
        controller.start()
        assert controller.get_current_state() == AppState.UPLOAD
        
        # Transition to analysis
        file_path = "/path/to/contract.pdf"
        controller.transition_to_analysis(file_path)
        assert controller.get_current_state() == AppState.ANALYZING
        assert controller.get_current_file() == file_path
        
        # Simulate analysis completion
        analysis_result = {
            "metadata": {"filename": "contract.pdf"},
            "clauses": [{"id": "1", "text": "Payment terms"}],
            "risks": [{"id": "r1", "severity": "medium"}],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        controller.transition_to_chat(analysis_result)
        
        # Verify chat state
        assert controller.get_current_state() == AppState.CHAT
        assert controller.get_analysis_result() == analysis_result
        
        # Return to upload for new analysis
        controller.transition_to_upload()
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_current_file() is None
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    def test_error_recovery_during_analysis(self, mock_analysis,
                                           mock_uploader, mock_config):
        """Test error recovery during analysis phase."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config.return_value = mock_config_instance
        
        # Initialize controller
        controller = ApplicationController()
        controller.initialize_components()
        controller.start()
        
        # Transition to analysis
        controller.transition_to_analysis("/path/to/contract.pdf")
        assert controller.get_current_state() == AppState.ANALYZING
        
        # Simulate error during analysis
        error = RuntimeError("OpenAI API error: Rate limit exceeded")
        controller.handle_error(error, "contract analysis")
        
        # Should return to UPLOAD state
        assert controller.get_current_state() == AppState.UPLOAD
        assert controller.get_error_message() is not None
        assert "Rate limit" in controller.get_error_message()
        
        # Clear error and retry
        controller.clear_error()
        assert controller.get_error_message() is None
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_data_preservation_across_states(self, mock_query,
                                             mock_analysis, mock_uploader, mock_config):
        """Test that analysis result is preserved across state transitions."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config.return_value = mock_config_instance
        
        # Initialize and start
        controller = ApplicationController()
        controller.initialize_components()
        controller.start()
        
        # Complete analysis workflow
        controller.transition_to_analysis("/path/to/contract.pdf")
        
        analysis_result = {
            "metadata": {"filename": "contract.pdf", "page_count": 25},
            "clauses": [
                {"id": "1", "text": "Clause 1"},
                {"id": "2", "text": "Clause 2"}
            ],
            "risks": [{"id": "r1", "severity": "high"}],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        controller.transition_to_chat(analysis_result)
        
        # Verify data is stored
        stored_result = controller.get_analysis_result()
        assert stored_result == analysis_result
        assert len(stored_result["clauses"]) == 2
        assert stored_result["metadata"]["page_count"] == 25
        
        # Simulate error in chat
        error = Exception("Query processing error")
        controller.handle_error(error, "query processing")
        
        # Data should still be preserved
        assert controller.get_analysis_result() == analysis_result
        assert len(controller.get_analysis_result()["clauses"]) == 2
    
    @patch('src.config_manager.ConfigManager')
    def test_initialization_with_missing_dependencies(self, mock_config):
        """Test initialization behavior with missing dependencies."""
        # Setup mock with no API key
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = None
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024  # 200 MB
        mock_config.return_value = mock_config_instance
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings
        assert result is True
        assert controller.is_initialized()
        
        # Check for warnings
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Validate dependencies should fail
        is_valid, missing = controller.validate_dependencies()
        assert is_valid is False
        assert len(missing) > 0
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_state_callbacks_execution(self, mock_query,
                                       mock_analysis, mock_uploader, mock_config):
        """Test that state callbacks are executed during transitions."""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config.return_value = mock_config_instance
        
        # Initialize controller
        controller = ApplicationController()
        controller.initialize_components()
        
        # Register callbacks
        callback_log = []
        
        def upload_callback():
            callback_log.append("UPLOAD")
        
        def analyzing_callback():
            callback_log.append("ANALYZING")
        
        def chat_callback():
            callback_log.append("CHAT")
        
        controller.register_state_callback(AppState.UPLOAD, upload_callback)
        controller.register_state_callback(AppState.ANALYZING, analyzing_callback)
        controller.register_state_callback(AppState.CHAT, chat_callback)
        
        # Execute workflow
        controller.start()
        assert "UPLOAD" in callback_log
        
        controller.transition_to_analysis("/path/to/file.pdf")
        assert "ANALYZING" in callback_log
        
        controller.transition_to_chat({"clauses": []})
        assert "CHAT" in callback_log
        
        # Verify all callbacks were called
        assert len(callback_log) == 3
        assert callback_log == ["UPLOAD", "ANALYZING", "CHAT"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
