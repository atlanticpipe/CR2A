"""
Unit tests for ErrorHandler class.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.error_handler import ErrorHandler, ErrorResponse


class TestErrorHandler:
    """Test suite for ErrorHandler class."""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary directory for log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def error_handler(self, temp_log_dir):
        """Create ErrorHandler instance with temporary log file."""
        log_file = os.path.join(temp_log_dir, "test_errors.log")
        handler = ErrorHandler(log_file_path=log_file)
        yield handler
        # Cleanup
        handler.close()
    
    def test_initialization(self, error_handler, temp_log_dir):
        """Test ErrorHandler initialization."""
        assert error_handler is not None
        assert error_handler.log_file_path.endswith("test_errors.log")
    
    def test_initialization_default_path(self):
        """Test ErrorHandler initialization with default log path."""
        handler = ErrorHandler()
        assert handler.log_file_path is not None
        assert ".contract_chat_ui" in handler.log_file_path
        assert "logs" in handler.log_file_path
    
    def test_handle_file_not_found_error(self, error_handler):
        """Test handling of FileNotFoundError."""
        error = FileNotFoundError("test_file.json not found")
        response = error_handler.handle_error(error, "file_loading")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "file" in response.message.lower()
        assert "select" in response.suggested_action.lower()
    
    def test_handle_json_decode_error(self, error_handler):
        """Test handling of JSONDecodeError."""
        error = json.JSONDecodeError("Invalid JSON", "doc", 10)
        response = error_handler.handle_error(error, "file_loading")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "json" in response.message.lower()
        assert "valid" in response.suggested_action.lower()
    
    def test_handle_permission_error(self, error_handler):
        """Test handling of PermissionError."""
        error = PermissionError("Access denied")
        response = error_handler.handle_error(error, "file_access")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "permission" in response.message.lower()
    
    def test_handle_memory_error(self, error_handler):
        """Test handling of MemoryError."""
        error = MemoryError("Out of memory")
        response = error_handler.handle_error(error, "model_loading")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "memory" in response.message.lower()
        assert "model" in response.suggested_action.lower()
    
    def test_handle_timeout_error(self, error_handler):
        """Test handling of TimeoutError."""
        error = TimeoutError("Operation timed out")
        response = error_handler.handle_error(error, "query_processing")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "warning"
        assert response.recoverable is True
        assert "timed out" in response.message.lower()
    
    def test_handle_connection_error(self, error_handler):
        """Test handling of ConnectionError."""
        error = ConnectionError("Network error")
        response = error_handler.handle_error(error, "openai_query")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "warning"
        assert response.recoverable is True
        assert "connection" in response.message.lower() or "network" in response.message.lower()
    
    def test_handle_value_error(self, error_handler):
        """Test handling of ValueError."""
        error = ValueError("Invalid value")
        response = error_handler.handle_error(error, "input_validation")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "invalid" in response.message.lower()
    
    def test_handle_runtime_error_model_not_loaded(self, error_handler):
        """Test handling of RuntimeError for model not loaded."""
        error = RuntimeError("Model not loaded")
        response = error_handler.handle_error(error, "model_query")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "model" in response.message.lower()
    
    def test_handle_import_error(self, error_handler):
        """Test handling of ImportError."""
        error = ImportError("Module not found")
        response = error_handler.handle_error(error, "initialization")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is False
        assert "dependency" in response.message.lower()
    
    def test_handle_unexpected_error(self, error_handler):
        """Test handling of unexpected error types."""
        error = Exception("Unknown error")
        response = error_handler.handle_error(error, "unknown_context")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "unexpected" in response.message.lower()
    
    def test_handle_data_corruption(self, error_handler):
        """Test handling of data corruption."""
        response = error_handler.handle_data_corruption("Invalid schema")
        
        assert isinstance(response, ErrorResponse)
        assert response.severity == "error"
        assert response.recoverable is True
        assert "corrupt" in response.message.lower()
        assert "reload" in response.suggested_action.lower()
    
    def test_error_logging_to_file(self, error_handler, temp_log_dir):
        """Test that errors are logged to file."""
        error = ValueError("Test error")
        error_handler.handle_error(error, "test_context")
        
        # Check that log file was created
        log_file = Path(error_handler.log_file_path)
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
            assert "ValueError" in log_content
            assert "Test error" in log_content
            assert "test_context" in log_content
    
    def test_structured_logging(self, error_handler, temp_log_dir):
        """Test structured JSON logging."""
        error = ValueError("Test error")
        error_handler.handle_error(error, "test_context")
        
        # Check that JSON log file was created
        json_log_path = Path(error_handler.log_file_path).parent / "errors.json"
        assert json_log_path.exists()
        
        # Check JSON content
        with open(json_log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            assert isinstance(logs, list)
            assert len(logs) > 0
            
            last_log = logs[-1]
            assert last_log["error_type"] == "ValueError"
            assert last_log["error_message"] == "Test error"
            assert last_log["context"] == "test_context"
            assert "timestamp" in last_log
            assert "traceback" in last_log
    
    def test_graceful_degradation_model_error(self, error_handler):
        """Test graceful degradation strategy for model errors."""
        error = MemoryError("Out of memory")
        strategy = error_handler.get_graceful_degradation_strategy(error, "model_loading")
        
        assert strategy["continue_operation"] is True
        assert "pythia_queries" in strategy["disable_features"]
        assert strategy["fallback_mode"] == "basic_search"
        assert strategy["user_notification"] is not None
    
    def test_graceful_degradation_openai_error(self, error_handler):
        """Test graceful degradation strategy for OpenAI errors."""
        error = ConnectionError("Network error")
        strategy = error_handler.get_graceful_degradation_strategy(error, "openai_query")
        
        assert strategy["continue_operation"] is True
        assert "openai_fallback" in strategy["disable_features"]
        assert strategy["fallback_mode"] == "pythia_only"
    
    def test_graceful_degradation_file_error(self, error_handler):
        """Test graceful degradation strategy for file errors."""
        error = FileNotFoundError("File not found")
        strategy = error_handler.get_graceful_degradation_strategy(error, "file_loading")
        
        assert strategy["continue_operation"] is True
        assert "query_processing" in strategy["disable_features"]
        assert strategy["fallback_mode"] == "file_selection"
    
    def test_graceful_degradation_critical_error(self, error_handler):
        """Test graceful degradation strategy for critical errors."""
        error = ImportError("Missing dependency")
        strategy = error_handler.get_graceful_degradation_strategy(error, "initialization")
        
        assert strategy["continue_operation"] is False
    
    def test_get_log_file_path(self, error_handler):
        """Test getting log file path."""
        path = error_handler.get_log_file_path()
        assert path is not None
        assert path.endswith("test_errors.log")
    
    def test_clear_old_logs(self, error_handler, temp_log_dir):
        """Test clearing old logs."""
        # Create some test logs
        json_log_path = Path(error_handler.log_file_path).parent / "errors.json"
        
        from datetime import datetime, timedelta
        
        old_log = {
            "timestamp": (datetime.now() - timedelta(days=40)).isoformat(),
            "error_type": "OldError",
            "error_message": "Old error"
        }
        
        recent_log = {
            "timestamp": datetime.now().isoformat(),
            "error_type": "RecentError",
            "error_message": "Recent error"
        }
        
        with open(json_log_path, 'w', encoding='utf-8') as f:
            json.dump([old_log, recent_log], f)
        
        # Clear logs older than 30 days
        error_handler.clear_old_logs(days=30)
        
        # Check that only recent log remains
        with open(json_log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            assert len(logs) == 1
            assert logs[0]["error_type"] == "RecentError"
    
    def test_multiple_errors_logged(self, error_handler, temp_log_dir):
        """Test that multiple errors are logged correctly."""
        errors = [
            ValueError("Error 1"),
            FileNotFoundError("Error 2"),
            RuntimeError("Error 3")
        ]
        
        for error in errors:
            error_handler.handle_error(error, "test")
        
        # Check JSON log
        json_log_path = Path(error_handler.log_file_path).parent / "errors.json"
        with open(json_log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            assert len(logs) == 3
    
    def test_log_limit_enforcement(self, error_handler, temp_log_dir):
        """Test that log limit (100 entries) is enforced."""
        # Create 105 error logs
        for i in range(105):
            error = ValueError(f"Error {i}")
            error_handler.handle_error(error, "test")
        
        # Check that only last 100 are kept
        json_log_path = Path(error_handler.log_file_path).parent / "errors.json"
        with open(json_log_path, 'r', encoding='utf-8') as f:
            logs = json.load(f)
            assert len(logs) == 100
            # Check that oldest logs were removed
            assert logs[0]["error_message"] == "Error 5"
            assert logs[-1]["error_message"] == "Error 104"


class TestErrorResponse:
    """Test suite for ErrorResponse dataclass."""
    
    def test_error_response_creation(self):
        """Test creating ErrorResponse."""
        response = ErrorResponse(
            message="Test error",
            severity="error",
            recoverable=True,
            suggested_action="Try again"
        )
        
        assert response.message == "Test error"
        assert response.severity == "error"
        assert response.recoverable is True
        assert response.suggested_action == "Try again"
        assert response.technical_details is None
    
    def test_error_response_with_technical_details(self):
        """Test ErrorResponse with technical details."""
        response = ErrorResponse(
            message="Test error",
            severity="error",
            recoverable=True,
            suggested_action="Try again",
            technical_details="ValueError: invalid input"
        )
        
        assert response.technical_details == "ValueError: invalid input"
