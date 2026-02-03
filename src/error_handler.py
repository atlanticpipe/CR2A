"""
Error Handler Module

Provides centralized error handling with user-friendly messages and logging.
"""

import logging
import traceback
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json


logger = logging.getLogger(__name__)


@dataclass
class ErrorResponse:
    """Response object for handled errors."""
    
    message: str  # User-friendly error message
    severity: str  # "error", "warning", "info"
    recoverable: bool  # Whether the application can continue
    suggested_action: str  # What the user should do next
    technical_details: Optional[str] = None  # Technical error details for logging


class ErrorHandler:
    """
    Centralized error handling for the Contract Chat UI application.
    
    Responsibilities:
    - Map exception types to user-friendly messages
    - Log errors to file for debugging
    - Implement graceful degradation strategies
    - Preserve application state during errors
    """
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        Initialize error handler.
        
        Args:
            log_file_path: Path to error log file. If None, uses default location.
        """
        # Set up error log file
        if log_file_path is None:
            log_dir = Path.home() / ".contract_chat_ui" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file_path = str(log_dir / "errors.log")
        
        self.log_file_path = log_file_path
        
        # Configure file handler for error logging
        self._setup_file_logging()
        
        logger.info("ErrorHandler initialized with log file: %s", self.log_file_path)
    
    def _setup_file_logging(self):
        """Set up file handler for error logging."""
        try:
            # Create file handler
            file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
            file_handler.setLevel(logging.ERROR)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # Add handler to root logger
            logging.getLogger().addHandler(file_handler)
            
            # Store reference to handler for cleanup
            self.file_handler = file_handler
            
            logger.debug("File logging configured successfully")
            
        except Exception as e:
            logger.warning(f"Failed to set up file logging: {e}")
            self.file_handler = None
    
    def handle_error(self, error: Exception, context: str = "") -> ErrorResponse:
        """
        Handle error and generate user-friendly response.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred (e.g., "query_processing", "file_loading")
            
        Returns:
            ErrorResponse with user-friendly message and recovery guidance
        """
        logger.error(f"Handling error in context '{context}': {type(error).__name__}: {error}")
        
        # Log full traceback
        self._log_error_details(error, context)
        
        # Map exception to user-friendly response
        if isinstance(error, FileNotFoundError):
            return self._handle_file_not_found(error)
        
        elif isinstance(error, json.JSONDecodeError):
            return self._handle_json_decode_error(error)
        
        elif isinstance(error, PermissionError):
            return self._handle_permission_error(error)
        
        elif isinstance(error, MemoryError):
            return self._handle_memory_error(error)
        
        elif isinstance(error, TimeoutError):
            return self._handle_timeout_error(error)
        
        elif isinstance(error, ConnectionError):
            return self._handle_connection_error(error)
        
        elif isinstance(error, ValueError):
            return self._handle_value_error(error, context)
        
        elif isinstance(error, RuntimeError):
            return self._handle_runtime_error(error, context)
        
        elif isinstance(error, ImportError):
            return self._handle_import_error(error)
        
        else:
            return self._handle_unexpected_error(error, context)
    
    def _log_error_details(self, error: Exception, context: str):
        """
        Log detailed error information to file.
        
        Args:
            error: The exception
            context: Error context
        """
        try:
            # Create detailed error log entry
            error_details = {
                "timestamp": datetime.now().isoformat(),
                "context": context,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc()
            }
            
            # Log to file
            logger.error(
                f"Error Details:\n"
                f"Context: {error_details['context']}\n"
                f"Type: {error_details['error_type']}\n"
                f"Message: {error_details['error_message']}\n"
                f"Traceback:\n{error_details['traceback']}"
            )
            
            # Also write to JSON log for structured logging
            self._write_structured_log(error_details)
            
        except Exception as e:
            logger.warning(f"Failed to log error details: {e}")
    
    def _write_structured_log(self, error_details: Dict[str, Any]):
        """
        Write structured error log in JSON format.
        
        Args:
            error_details: Dictionary with error information
        """
        try:
            json_log_path = Path(self.log_file_path).parent / "errors.json"
            
            # Read existing logs
            existing_logs = []
            if json_log_path.exists():
                try:
                    with open(json_log_path, 'r', encoding='utf-8') as f:
                        existing_logs = json.load(f)
                except:
                    existing_logs = []
            
            # Append new error
            existing_logs.append(error_details)
            
            # Keep only last 100 errors
            if len(existing_logs) > 100:
                existing_logs = existing_logs[-100:]
            
            # Write back
            with open(json_log_path, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to write structured log: {e}")
    
    def _handle_file_not_found(self, error: FileNotFoundError) -> ErrorResponse:
        """Handle file not found errors."""
        return ErrorResponse(
            message="Could not find the specified file. Please check the path and try again.",
            severity="error",
            recoverable=True,
            suggested_action="Select a different file or verify the file path",
            technical_details=str(error)
        )
    
    def _handle_json_decode_error(self, error: json.JSONDecodeError) -> ErrorResponse:
        """Handle JSON parsing errors."""
        return ErrorResponse(
            message="The selected file is not valid JSON. Please ensure it was generated by ContractAnalysisCLI.exe.",
            severity="error",
            recoverable=True,
            suggested_action="Select a valid contract analysis JSON file",
            technical_details=f"JSON error at line {error.lineno}, column {error.colno}: {error.msg}"
        )
    
    def _handle_permission_error(self, error: PermissionError) -> ErrorResponse:
        """Handle permission errors."""
        return ErrorResponse(
            message="Permission denied. You may not have access to read or write this file.",
            severity="error",
            recoverable=True,
            suggested_action="Check file permissions or try a different location",
            technical_details=str(error)
        )
    
    def _handle_memory_error(self, error: MemoryError) -> ErrorResponse:
        """Handle memory errors."""
        return ErrorResponse(
            message="Insufficient memory to complete this operation. Try using Pythia-410M instead of Pythia-1B, or close other applications.",
            severity="error",
            recoverable=True,
            suggested_action="Change model in settings or free up system memory",
            technical_details=str(error)
        )
    
    def _handle_timeout_error(self, error: TimeoutError) -> ErrorResponse:
        """Handle timeout errors."""
        return ErrorResponse(
            message="The operation timed out. This may be due to a complex query or slow system performance.",
            severity="warning",
            recoverable=True,
            suggested_action="Try simplifying your question or wait a moment before trying again",
            technical_details=str(error)
        )
    
    def _handle_connection_error(self, error: ConnectionError) -> ErrorResponse:
        """Handle connection errors (e.g., OpenAI API)."""
        return ErrorResponse(
            message="Network connection failed. Check your internet connection if using OpenAI fallback.",
            severity="warning",
            recoverable=True,
            suggested_action="Check internet connection or disable OpenAI fallback in settings",
            technical_details=str(error)
        )
    
    def _handle_value_error(self, error: ValueError, context: str) -> ErrorResponse:
        """Handle value errors."""
        if "model" in context.lower():
            message = "Invalid model configuration. Please check your settings."
            action = "Verify model settings and try again"
        else:
            message = "Invalid input or data format encountered."
            action = "Check your input and try again"
        
        return ErrorResponse(
            message=message,
            severity="error",
            recoverable=True,
            suggested_action=action,
            technical_details=str(error)
        )
    
    def _handle_runtime_error(self, error: RuntimeError, context: str) -> ErrorResponse:
        """Handle runtime errors."""
        if "model not loaded" in str(error).lower():
            message = "The language model is not loaded. Please wait for initialization to complete."
            action = "Wait for model loading or restart the application"
        else:
            message = "A runtime error occurred during operation."
            action = "Try the operation again or restart the application"
        
        return ErrorResponse(
            message=message,
            severity="error",
            recoverable=True,
            suggested_action=action,
            technical_details=str(error)
        )
    
    def _handle_import_error(self, error: ImportError) -> ErrorResponse:
        """Handle import errors (missing dependencies)."""
        return ErrorResponse(
            message=f"Missing required dependency: {error.name if hasattr(error, 'name') else 'unknown'}. The application may not be properly installed.",
            severity="error",
            recoverable=False,
            suggested_action="Reinstall the application or contact support",
            technical_details=str(error)
        )
    
    def _handle_unexpected_error(self, error: Exception, context: str) -> ErrorResponse:
        """Handle unexpected errors."""
        return ErrorResponse(
            message="An unexpected error occurred. The application will continue running, but some features may not work correctly.",
            severity="error",
            recoverable=True,
            suggested_action="Try again or restart the application if problems persist",
            technical_details=f"{type(error).__name__}: {str(error)}"
        )
    
    def handle_data_corruption(self, details: str = "") -> ErrorResponse:
        """
        Handle data corruption detection.
        
        Args:
            details: Details about the corruption
            
        Returns:
            ErrorResponse for data corruption
        """
        logger.error(f"Data corruption detected: {details}")
        
        return ErrorResponse(
            message="The contract data appears to be corrupted or invalid. Please reload the file.",
            severity="error",
            recoverable=True,
            suggested_action="Reload the contract file or select a different file",
            technical_details=details
        )
    
    def get_graceful_degradation_strategy(self, error: Exception, context: str) -> Dict[str, Any]:
        """
        Get graceful degradation strategy for an error.
        
        This method determines how the application should continue operating
        after an error occurs.
        
        Args:
            error: The exception that occurred
            context: Context where the error occurred
            
        Returns:
            Dictionary with degradation strategy
        """
        strategy = {
            "continue_operation": True,
            "disable_features": [],
            "fallback_mode": None,
            "user_notification": None
        }
        
        # Model loading errors - disable AI features
        if isinstance(error, (MemoryError, RuntimeError)) and "model" in context.lower():
            strategy["continue_operation"] = True
            strategy["disable_features"] = ["pythia_queries"]
            strategy["fallback_mode"] = "basic_search"
            strategy["user_notification"] = "AI features disabled. Using basic search only."
        
        # OpenAI errors - disable fallback
        elif isinstance(error, ConnectionError) and "openai" in context.lower():
            strategy["continue_operation"] = True
            strategy["disable_features"] = ["openai_fallback"]
            strategy["fallback_mode"] = "pythia_only"
            strategy["user_notification"] = "OpenAI fallback disabled. Using local model only."
        
        # File loading errors - require new file
        elif isinstance(error, (FileNotFoundError, json.JSONDecodeError)):
            strategy["continue_operation"] = True
            strategy["disable_features"] = ["query_processing"]
            strategy["fallback_mode"] = "file_selection"
            strategy["user_notification"] = "Please load a valid contract file to continue."
        
        # Critical errors - cannot continue
        elif isinstance(error, ImportError):
            strategy["continue_operation"] = False
            strategy["user_notification"] = "Critical error. Application cannot continue."
        
        return strategy
    
    def get_log_file_path(self) -> str:
        """
        Get the path to the error log file.
        
        Returns:
            Path to error log file
        """
        return self.log_file_path
    
    def clear_old_logs(self, days: int = 30):
        """
        Clear error logs older than specified days.
        
        Args:
            days: Number of days to keep logs
        """
        try:
            json_log_path = Path(self.log_file_path).parent / "errors.json"
            
            if not json_log_path.exists():
                return
            
            # Read existing logs
            with open(json_log_path, 'r', encoding='utf-8') as f:
                logs = json.load(f)
            
            # Filter logs by age
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            filtered_logs = [
                log for log in logs
                if datetime.fromisoformat(log.get("timestamp", "")).timestamp() > cutoff_date
            ]
            
            # Write back filtered logs
            with open(json_log_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_logs, f, indent=2)
            
            logger.info(f"Cleared {len(logs) - len(filtered_logs)} old log entries")
            
        except Exception as e:
            logger.warning(f"Failed to clear old logs: {e}")
    
    def close(self):
        """Close file handlers and cleanup resources."""
        if hasattr(self, 'file_handler') and self.file_handler:
            try:
                self.file_handler.close()
                logging.getLogger().removeHandler(self.file_handler)
                logger.debug("File handler closed successfully")
            except Exception as e:
                logger.warning(f"Failed to close file handler: {e}")
