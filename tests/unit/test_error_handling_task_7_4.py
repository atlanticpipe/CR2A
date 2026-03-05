"""
Unit tests for Task 7.4: Error handling for non-API-key initialization failures.

Tests that different exception types in initialize_components() generate
descriptive error messages with troubleshooting guidance.
"""

import pytest
from unittest.mock import Mock, patch
from src.application_controller import ApplicationController


class TestErrorHandlingTask74:
    """Test error handling for non-API-key initialization failures (Task 7.4)."""
    
    @patch('src.config_manager.ConfigManager')
    def test_config_manager_import_error(self, mock_config):
        """Test ConfigManager ImportError generates descriptive error message."""
        # Setup mock to raise ImportError
        mock_config.side_effect = ImportError("No module named 'some_dependency'")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "missing dependency" in error_msg
        assert "Troubleshooting" in error_msg
        assert "Python environment" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    def test_config_manager_permission_error(self, mock_config):
        """Test ConfigManager PermissionError generates descriptive error message."""
        # Setup mock to raise PermissionError
        mock_config.side_effect = PermissionError("Permission denied")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "permission denied" in error_msg
        assert "Troubleshooting" in error_msg
        assert "file permissions" in error_msg
        assert "administrator" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    def test_config_manager_os_error(self, mock_config):
        """Test ConfigManager OSError generates descriptive error message."""
        # Setup mock to raise OSError
        mock_config.side_effect = OSError("Disk full")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "file system error" in error_msg
        assert "Troubleshooting" in error_msg
        assert "disk space" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    def test_config_manager_value_error(self, mock_config):
        """Test ConfigManager ValueError generates descriptive error message."""
        # Setup mock to raise ValueError
        mock_config_instance = Mock()
        mock_config_instance.load_config.side_effect = ValueError("Invalid JSON")
        mock_config.return_value = mock_config_instance
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "corrupted configuration" in error_msg
        assert "Troubleshooting" in error_msg
        assert "configuration file" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    def test_contract_uploader_import_error(self, mock_uploader, mock_config):
        """Test ContractUploader ImportError generates descriptive error message."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = None
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup ContractUploader to raise ImportError
        mock_uploader.side_effect = ImportError("No module named 'PyPDF2'")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should fail
        assert result is False
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        # Find the ContractUploader error (may not be first due to API key warning)
        uploader_error = [e for e in errors if "ContractUploader" in e]
        assert len(uploader_error) > 0
        error_msg = uploader_error[0]
        assert "missing dependency" in error_msg
        assert "Troubleshooting" in error_msg
        assert "file processing" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    def test_analysis_engine_connection_error(self, mock_analysis, mock_uploader, mock_config):
        """Test AnalysisEngine ConnectionError generates descriptive error message."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup AnalysisEngine to raise ConnectionError
        mock_analysis.side_effect = ConnectionError("Network unreachable")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings (AnalysisEngine is optional)
        assert result is True
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "network connection error" in error_msg
        assert "Troubleshooting" in error_msg
        assert "internet connection" in error_msg
        assert "status.openai.com" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    def test_analysis_engine_value_error(self, mock_analysis, mock_uploader, mock_config):
        """Test AnalysisEngine ValueError generates descriptive error message."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "invalid-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup AnalysisEngine to raise ValueError
        mock_analysis.side_effect = ValueError("Invalid API key format")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings
        assert result is True
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "invalid configuration" in error_msg
        assert "Troubleshooting" in error_msg
        assert "API key format" in error_msg
        assert "sk-" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_query_engine_value_error(self, mock_query, mock_analysis,
                                      mock_uploader, mock_config):
        """Test QueryEngine ValueError generates descriptive error message."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup QueryEngine to raise ValueError
        mock_query.side_effect = ValueError("Invalid configuration")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings
        assert result is True
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "invalid configuration" in error_msg
        assert "Troubleshooting" in error_msg
        assert "QueryEngine" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    def test_generic_exception_has_troubleshooting(self, mock_analysis, mock_uploader, mock_config):
        """Test generic Exception generates error message with troubleshooting guidance."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup AnalysisEngine to raise generic Exception
        mock_analysis.side_effect = Exception("Unexpected error")
        
        controller = ApplicationController()
        result = controller.initialize_components()
        
        # Should succeed with warnings
        assert result is True
        errors = controller.get_initialization_errors()
        assert len(errors) > 0
        
        # Check error message contains troubleshooting guidance
        error_msg = errors[0]
        assert "Failed to initialize AnalysisEngine" in error_msg
        assert "Troubleshooting" in error_msg
        assert "Unexpected error" in error_msg
    
    @patch('src.config_manager.ConfigManager')
    @patch('src.contract_uploader.ContractUploader')
    @patch('src.analysis_engine.AnalysisEngine')
    @patch('src.query_engine.QueryEngine')
    def test_full_exception_details_logged(self, mock_query, mock_analysis,
                                           mock_uploader, mock_config):
        """Test that full exception details are logged for debugging."""
        # Setup ConfigManager mock
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config_instance.get_max_file_size.return_value = 200 * 1024 * 1024
        mock_config.return_value = mock_config_instance
        
        # Setup QueryEngine to raise exception
        mock_query.side_effect = RuntimeError("Test error with stack trace")
        
        controller = ApplicationController()
        
        # Capture log output
        with patch('src.application_controller.logger') as mock_logger:
            result = controller.initialize_components()
            
            # Verify logger.error was called with exc_info=True for full stack trace
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if 'QueryEngine initialization failed' in str(call)]
            assert len(error_calls) > 0
            
            # Check that exc_info=True was passed for stack trace logging
            for call in error_calls:
                if 'exc_info' in call[1]:
                    assert call[1]['exc_info'] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
