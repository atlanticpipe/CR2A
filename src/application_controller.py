"""
Application Controller Module

Central coordinator managing application lifecycle and state transitions
for the Unified CR2A Application.
"""

import logging
import tkinter as tk
from tkinter import messagebox
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass


logger = logging.getLogger(__name__)


class AppState(Enum):
    """Application state enumeration."""
    UPLOAD = "upload"
    ANALYZING = "analyzing"
    CHAT = "chat"
    ERROR = "error"


@dataclass
class ApplicationContext:
    """
    Application context holding current state and data.
    
    Attributes:
        current_state: Current application state
        current_file: Path to currently selected/analyzed file
        analysis_result: Stored analysis result from OpenAI
        error_message: Current error message if in ERROR state
        is_version_update: Whether the current upload is a version update
        matched_contract_id: ID of matched contract (if version update)
        matched_contract_version: Current version of matched contract
    """
    current_state: AppState
    current_file: Optional[str] = None
    analysis_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    is_version_update: bool = False
    matched_contract_id: Optional[str] = None
    matched_contract_version: Optional[int] = None


class ApplicationController:
    """
    Central coordinator managing application lifecycle and state transitions.
    
    This class manages the application state machine, coordinates component
    initialization, handles screen transitions, and provides global error handling.
    """
    
    def __init__(self, root=None):
        """
        Initialize application controller.
        
        Args:
            root: Tkinter root window (optional, for UI integration)
        """
        self.root = root
        self.context = ApplicationContext(current_state=AppState.UPLOAD)
        
        # Component references (initialized later)
        self.config_manager = None
        self.contract_uploader = None
        self.analysis_engine = None
        self.query_engine = None
        
        # Versioning component references (initialized later)
        self.version_db = None
        self.differential_storage = None
        self.contract_identity_detector = None
        self.change_comparator = None
        self.version_manager = None
        
        # Screen references (initialized later)
        self.upload_screen = None
        self.analysis_screen = None
        self.chat_screen = None
        
        # Main container frame for screens
        self.main_frame = None
        
        # State transition callbacks
        self._state_callbacks: Dict[AppState, Callable] = {}
        
        # Initialization status
        self._initialized = False
        self._initialization_errors = []
        
        logger.info("ApplicationController initialized")
    
    def register_state_callback(self, state: AppState, callback: Callable) -> None:
        """
        Register a callback to be called when transitioning to a state.
        
        Args:
            state: The state to register callback for
            callback: Function to call when entering this state
        """
        self._state_callbacks[state] = callback
        logger.debug("Registered callback for state: %s", state.value)
    
    def initialize_screens(self) -> None:
        """
        Initialize all UI screens and wire them to the controller.
        
        This method creates the main container frame and initializes:
        - UploadScreen
        - AnalysisScreen
        - ChatScreen
        
        It also registers state callbacks to show the appropriate screen.
        """
        logger.info("Initializing UI screens...")
        
        if not self.root:
            raise ValueError("Cannot initialize screens without Tkinter root window")
        
        # Create menu bar
        self._create_menu_bar()
        
        # Import screen classes
        from src.upload_screen import UploadScreen
        from src.analysis_screen import AnalysisScreen
        from src.chat_screen import ChatScreen
        
        # Create main container frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        logger.debug("Main container frame created")
        
        # Initialize screens
        logger.info("Creating UploadScreen...")
        self.upload_screen = UploadScreen(self.main_frame, self)
        
        logger.info("Creating AnalysisScreen...")
        self.analysis_screen = AnalysisScreen(self.main_frame, self)
        
        logger.info("Creating ChatScreen...")
        self.chat_screen = ChatScreen(self.main_frame, self)
        
        # Register state callbacks to show appropriate screens
        self.register_state_callback(AppState.UPLOAD, self._show_upload_screen)
        self.register_state_callback(AppState.ANALYZING, self._show_analysis_screen)
        self.register_state_callback(AppState.CHAT, self._show_chat_screen)
        
        logger.info("UI screens initialized successfully")
    
    def _create_menu_bar(self) -> None:
        """Create application menu bar with Settings option."""
        logger.debug("Creating menu bar")
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Settings...", command=self.open_settings_dialog)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        
        logger.debug("Menu bar created")
    
    def open_settings_dialog(self) -> None:
        """Open settings dialog for API key configuration."""
        logger.info("Opening settings dialog from menu")
        
        if not self.config_manager:
            logger.error("ConfigManager not initialized")
            tk.messagebox.showerror(
                "Error",
                "Configuration manager not initialized.",
                parent=self.root
            )
            return
        
        try:
            from src.settings_dialog import show_settings_dialog
            
            # Show dialog (not required, can be cancelled)
            result = show_settings_dialog(
                parent=self.root,
                config_manager=self.config_manager,
                required=False,
                on_save_callback=self._on_api_key_saved
            )
            
            if result:
                logger.info("Settings saved successfully")
            else:
                logger.info("Settings dialog cancelled")
        
        except Exception as e:
            logger.error(f"Error opening settings dialog: {e}", exc_info=True)
            tk.messagebox.showerror(
                "Error",
                f"Failed to open settings dialog:\n{str(e)}",
                parent=self.root
            )
    
    def _show_about_dialog(self) -> None:
        """Show about dialog."""
        about_text = (
            "CR2A - Contract Analysis Application\n\n"
            "Version 1.0\n\n"
            "Unified contract analysis tool combining:\n"
            "• Contract upload and validation\n"
            "• OpenAI-powered analysis\n"
            "• OpenAI-powered querying\n\n"
            "© 2024 CR2A Project"
        )
        tk.messagebox.showinfo("About CR2A", about_text, parent=self.root)
    
    def _show_upload_screen(self) -> None:
        """Show the upload screen."""
        logger.debug("Showing upload screen")
        if self.upload_screen:
            self.upload_screen.render()
    
    def _show_analysis_screen(self) -> None:
        """Show the analysis screen and start analysis."""
        logger.debug("Showing analysis screen")
        if self.analysis_screen:
            self.analysis_screen.render()
            # Start analysis with the current file
            if self.context.current_file:
                self.analysis_screen.start_analysis(self.context.current_file)
    
    def _show_chat_screen(self) -> None:
        """Show the chat screen and load analysis result."""
        logger.debug("Showing chat screen")
        if self.chat_screen:
            self.chat_screen.render()
            # Load analysis result if available
            if self.context.analysis_result:
                self.chat_screen.load_analysis(self.context.analysis_result)
    
    def _transition_state(self, new_state: AppState) -> None:
        """
        Transition to a new application state.
        
        Args:
            new_state: Target state to transition to
        """
        old_state = self.context.current_state
        logger.info("State transition: %s -> %s", old_state.value, new_state.value)
        
        self.context.current_state = new_state
        
        # Call registered callback if exists
        if new_state in self._state_callbacks:
            try:
                self._state_callbacks[new_state]()
            except Exception as e:
                logger.error("Error in state callback for %s: %s", new_state.value, e)
                self.handle_error(e, f"State transition to {new_state.value}")
    
    def start(self) -> None:
        """
        Start application and show upload screen.
        
        This method should be called after all components and screens are initialized.
        """
        logger.info("Starting application")
        
        if not self._initialized:
            logger.warning("Application started before initialization complete")
        
        # Transition to upload state
        self._transition_state(AppState.UPLOAD)
        
        logger.info("Application started successfully")
    
    def transition_to_analysis(self, file_path: str) -> None:
        """
        Transition from upload to analysis screen.
        
        This method now includes duplicate detection and version handling:
        1. Compute file hash
        2. Check for potential matches (hash or filename similarity)
        3. If matches found, prompt user to confirm if it's an update
        4. Store the decision for use during analysis
        
        Args:
            file_path: Path to contract file to analyze
        """
        logger.info("Transitioning to analysis for file: %s", file_path)
        
        # Validate current state
        if self.context.current_state != AppState.UPLOAD:
            logger.warning("Invalid state transition: %s -> ANALYZING", 
                          self.context.current_state.value)
        
        # Store file path
        self.context.current_file = file_path
        
        # Clear previous analysis result
        self.context.analysis_result = None
        
        # Initialize versioning context
        self.context.is_version_update = False
        self.context.matched_contract_id = None
        self.context.matched_contract_version = None
        
        # Check for duplicate contracts if versioning is enabled
        if self.contract_identity_detector:
            try:
                logger.info("Checking for duplicate contracts...")
                
                # Compute file hash
                file_hash = self.contract_identity_detector.compute_file_hash(file_path)
                logger.debug("File hash computed: %s", file_hash[:16] + "...")
                
                # Find potential matches
                from pathlib import Path
                filename = Path(file_path).name
                matches = self.contract_identity_detector.find_potential_matches(
                    file_hash=file_hash,
                    filename=filename
                )
                
                if matches:
                    logger.info("Found %d potential matches", len(matches))
                    
                    # Show user prompt to confirm if this is an update
                    match = matches[0]  # Use the best match
                    
                    if match.match_type == 'hash':
                        message = (
                            f"This file appears to be identical to a previously analyzed contract:\n\n"
                            f"Contract: {match.filename}\n"
                            f"Current Version: {match.current_version}\n\n"
                            f"Is this an updated version of the same contract?"
                        )
                    else:
                        message = (
                            f"This file has a similar name to a previously analyzed contract:\n\n"
                            f"Contract: {match.filename}\n"
                            f"Similarity: {match.similarity_score:.0%}\n"
                            f"Current Version: {match.current_version}\n\n"
                            f"Is this an updated version of the same contract?"
                        )
                    
                    # Show confirmation dialog
                    from tkinter import messagebox
                    result = messagebox.askyesno(
                        "Duplicate Contract Detected",
                        message,
                        parent=self.root
                    )
                    
                    if result:
                        # User confirmed it's an update
                        logger.info("User confirmed contract update for: %s", match.contract_id)
                        self.context.is_version_update = True
                        self.context.matched_contract_id = match.contract_id
                        self.context.matched_contract_version = match.current_version
                    else:
                        # User indicated it's a different contract
                        logger.info("User indicated this is a different contract")
                        self.context.is_version_update = False
                else:
                    logger.info("No duplicate contracts found")
                    
            except Exception as e:
                logger.error("Error during duplicate detection: %s", e, exc_info=True)
                # Continue with analysis even if duplicate detection fails
                logger.warning("Continuing with analysis despite duplicate detection error")
        
        # Transition to analyzing state
        self._transition_state(AppState.ANALYZING)
    
    def transition_to_chat(self, analysis_result: Dict[str, Any]) -> None:
        """
        Transition from analysis to chat screen.
        
        Args:
            analysis_result: Analysis result dictionary from OpenAI
        """
        logger.info("Transitioning to chat with analysis result")
        
        # Validate current state
        if self.context.current_state != AppState.ANALYZING:
            logger.warning("Invalid state transition: %s -> CHAT", 
                          self.context.current_state.value)
        
        # Store analysis result in memory
        self.context.analysis_result = analysis_result
        
        # Transition to chat state
        self._transition_state(AppState.CHAT)
        
        logger.info("Analysis result stored in memory for querying")
    
    def transition_to_upload(self) -> None:
        """
        Return to upload screen for new analysis.
        
        This clears the current file and analysis result to free memory.
        Also clears chat screen data if transitioning from chat.
        """
        logger.info("Transitioning back to upload screen")
        
        # Clear chat screen data if coming from chat state
        if self.context.current_state == AppState.CHAT and self.chat_screen:
            logger.info("Clearing chat screen data to free memory")
            self.chat_screen.clear_data()
        
        # Clear current file
        self.context.current_file = None
        
        # Clear analysis result to free memory
        if self.context.analysis_result:
            logger.info("Clearing analysis result to free memory")
            self.context.analysis_result = None
        
        # Transition to upload state
        self._transition_state(AppState.UPLOAD)
    
    def handle_error(self, error: Exception, context: str) -> None:
        """
        Display error message and determine recovery action.
        
        Args:
            error: Exception that occurred
            context: Context description where error occurred
        """
        error_msg = f"Error in {context}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        # Store error message
        self.context.error_message = error_msg
        
        # Transition to error state
        old_state = self.context.current_state
        self._transition_state(AppState.ERROR)
        
        # Determine recovery action based on where error occurred
        if old_state == AppState.UPLOAD:
            # Error during upload - stay on upload screen
            logger.info("Error during upload - returning to upload screen")
            self._transition_state(AppState.UPLOAD)
        
        elif old_state == AppState.ANALYZING:
            # Error during analysis - return to upload with option to retry
            logger.info("Error during analysis - returning to upload screen")
            self._transition_state(AppState.UPLOAD)
        
        elif old_state == AppState.CHAT:
            # Error during chat - stay on chat screen
            logger.info("Error during chat - staying on chat screen")
            self._transition_state(AppState.CHAT)
    
    def get_current_state(self) -> AppState:
        """
        Get current application state.
        
        Returns:
            Current AppState
        """
        return self.context.current_state
    
    def get_analysis_result(self) -> Optional[Dict[str, Any]]:
        """
        Get stored analysis result.
        
        Returns:
            Analysis result dictionary or None if not available
        """
        return self.context.analysis_result
    
    def get_current_file(self) -> Optional[str]:
        """
        Get current file path.
        
        Returns:
            File path or None if not set
        """
        return self.context.current_file
    
    def get_error_message(self) -> Optional[str]:
        """
        Get current error message.
        
        Returns:
            Error message or None if no error
        """
        return self.context.error_message
    
    def clear_error(self) -> None:
        """Clear current error message."""
        self.context.error_message = None
        logger.debug("Error message cleared")
    
    def is_initialized(self) -> bool:
        """
        Check if application is fully initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self._initialized
    
    def get_initialization_errors(self) -> list:
        """
        Get list of initialization errors.
        
        Returns:
            List of error messages from initialization
        """
        return self._initialization_errors.copy()
    
    def show_api_key_dialog_if_needed(self) -> bool:
        """
        Show API key configuration dialog if key is missing or invalid.
        
        This method checks for missing or invalid API keys and displays
        a setup dialog with clear instructions including the OpenAI platform URL.
        
        Returns:
            True if API key is configured (either already present or just saved),
            False if user cancelled or error occurred
        """
        logger.info("Checking if API key dialog is needed...")
        
        if not self.config_manager:
            logger.error("ConfigManager not initialized")
            return False
        
        # Check if API key exists and is valid
        api_key = self.config_manager.get_openai_key()
        
        if api_key:
            is_valid, errors = self.config_manager.validate_config()
            if is_valid or "OpenAI API key" not in str(errors):
                logger.info("API key already configured")
                return True
            else:
                logger.warning("API key exists but is invalid")
        
        # API key is missing or invalid - show dialog with clear setup instructions
        logger.info("API key missing or invalid - showing setup dialog")
        
        try:
            from src.settings_dialog import show_settings_dialog
            
            # Show dialog with clear setup instructions
            # The dialog includes:
            # - Clear message that API key is required
            # - Instructions on where to obtain an API key
            # - OpenAI platform URL: https://platform.openai.com/api-keys
            # - Field for entering the API key
            result = show_settings_dialog(
                parent=self.root,
                config_manager=self.config_manager,
                required=True,
                on_save_callback=self._on_api_key_saved
            )
            
            if result:
                logger.info("API key configured successfully")
                return True
            else:
                # Handle dialog cancellation gracefully
                logger.warning("User cancelled API key configuration")
                return False
        
        except Exception as e:
            logger.error(f"Error showing API key dialog: {e}", exc_info=True)
            return False
    
    def _on_api_key_saved(self) -> None:
        """
        Callback called after API key is saved in settings dialog.
        
        This method:
        1. Reloads configuration to get the new API key
        2. Attempts to initialize/reinitialize AnalysisEngine with the new key
        3. Logs success or failure of initialization
        4. Updates UI state if needed (shows success/error message)
        
        Requirements: 3.5
        """
        logger.info("API key saved callback triggered")
        
        # 1. Reload configuration after API key save
        if not self.config_manager:
            logger.error("ConfigManager not available for reloading configuration")
            return
        
        try:
            self.config_manager.load_config()
            logger.info("Configuration reloaded successfully after API key save")
        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}", exc_info=True)
            # Show error to user
            if self.root:
                messagebox.showerror(
                    "Configuration Error",
                    f"Failed to reload configuration after saving API key:\n{str(e)}",
                    parent=self.root
                )
            return
        
        # 2. Attempt to initialize AnalysisEngine with new key
        api_key = self.config_manager.get_openai_key()
        if not api_key:
            logger.warning("No API key found after reload")
            return
        
        logger.info("Attempting to initialize AnalysisEngine with new API key...")
        
        try:
            from src.analysis_engine import AnalysisEngine
            
            # Initialize or reinitialize AnalysisEngine
            self.analysis_engine = AnalysisEngine(openai_api_key=api_key)
            
            # 3. Log success of initialization
            logger.info("AnalysisEngine initialized successfully with new API key")
            
            # 4. Update UI state - show success message to user
            if self.root:
                messagebox.showinfo(
                    "Success",
                    "API key configured successfully!\n\n"
                    "The analysis engine is now ready to use.",
                    parent=self.root
                )
            
        except Exception as e:
            # 3. Log failure of initialization
            logger.error(f"Failed to initialize AnalysisEngine with new API key: {e}", exc_info=True)
            
            # 4. Update UI state - show error message to user with troubleshooting guidance
            error_message = (
                f"Failed to initialize the analysis engine:\n\n"
                f"{str(e)}\n\n"
                f"Troubleshooting:\n"
                f"• Verify your API key is correct\n"
                f"• Check your internet connection\n"
                f"• Ensure your API key has sufficient credits\n"
                f"• Visit https://platform.openai.com/account/api-keys to verify your key"
            )
            
            if self.root:
                messagebox.showerror(
                    "Initialization Failed",
                    error_message,
                    parent=self.root
                )
            
            # Set analysis_engine to None to indicate it's not available
            self.analysis_engine = None
    
    def initialize_components(self) -> bool:
        """
        Initialize all application components during startup.
        
        This method initializes:
        - ConfigManager (loads configuration and API key)
        - ContractUploader (file validation and text extraction)
        - AnalysisEngine (OpenAI client integration)
        - QueryEngine (query processing workflow with OpenAI)
        
        Returns:
            True if all components initialized successfully, False otherwise
        """
        logger.info("Initializing application components...")
        self._initialization_errors = []
        
        try:
            # Import components
            from src.config_manager import ConfigManager
            from src.contract_uploader import ContractUploader
            from src.analysis_engine import AnalysisEngine
            from src.query_engine import QueryEngine
            
            # 1. Initialize ConfigManager
            logger.info("Initializing ConfigManager...")
            try:
                self.config_manager = ConfigManager()
                self.config_manager.load_config()
                logger.info("ConfigManager initialized successfully")
            except ImportError as e:
                # Module import failure
                error_msg = (
                    f"Failed to initialize ConfigManager - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify your Python environment is properly configured\n"
                    f"• Check that all required modules are available\n"
                    f"• Reinstall the application if necessary"
                )
                logger.error(f"ConfigManager initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except PermissionError as e:
                # File permission issues
                error_msg = (
                    f"Failed to initialize ConfigManager - permission denied: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check file permissions for configuration directory\n"
                    f"• Ensure you have read/write access to the application directory\n"
                    f"• Try running the application with appropriate permissions\n"
                    f"• On Windows, try running as administrator"
                )
                logger.error(f"ConfigManager initialization failed - PermissionError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except OSError as e:
                # File system issues (disk full, path not found, etc.)
                error_msg = (
                    f"Failed to initialize ConfigManager - file system error: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check available disk space\n"
                    f"• Verify the configuration directory exists and is accessible\n"
                    f"• Check for file system errors\n"
                    f"• Ensure the application directory is not read-only"
                )
                logger.error(f"ConfigManager initialization failed - OSError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except ValueError as e:
                # Corrupted configuration file
                error_msg = (
                    f"Failed to initialize ConfigManager - corrupted configuration: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Configuration file may be corrupted\n"
                    f"• Try deleting the configuration file to reset to defaults\n"
                    f"• Check the configuration file for syntax errors\n"
                    f"• Restore from backup if available"
                )
                logger.error(f"ConfigManager initialization failed - ValueError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except Exception as e:
                # Generic error
                error_msg = (
                    f"Failed to initialize ConfigManager: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check the application logs for more details\n"
                    f"• Try deleting the configuration file to reset to defaults\n"
                    f"• Verify file permissions and disk space\n"
                    f"• Restart the application"
                )
                logger.error(f"ConfigManager initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            
            # 2. Validate API key dependency (don't show dialog automatically)
            logger.info("Validating OpenAI API key...")
            api_key = self.config_manager.get_openai_key()
            if not api_key:
                error_msg = "OpenAI API key is missing. Please configure API key in settings."
                logger.warning(error_msg)
                self._initialization_errors.append(error_msg)
                # Don't return False - allow user to configure key later
            else:
                # Validate API key format
                is_valid, errors = self.config_manager.validate_config()
                if not is_valid:
                    error_msg = f"Configuration validation failed: {', '.join(errors)}"
                    logger.warning(error_msg)
                    self._initialization_errors.append(error_msg)
                else:
                    logger.info("OpenAI API key validated successfully")
            
            # 3. Initialize ContractUploader
            logger.info("Initializing ContractUploader...")
            try:
                max_file_size = self.config_manager.get_max_file_size()
                self.contract_uploader = ContractUploader(max_file_size=max_file_size)
                logger.info("ContractUploader initialized with max file size: %.0f MB", 
                           max_file_size / (1024 * 1024))
            except ImportError as e:
                # Module import failure
                error_msg = (
                    f"Failed to initialize ContractUploader - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Install required packages for file processing\n"
                    f"• Verify your Python environment is properly configured\n"
                    f"• Check that all dependencies are installed"
                )
                logger.error(f"ContractUploader initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except ValueError as e:
                # Invalid configuration (e.g., invalid max_file_size)
                error_msg = (
                    f"Failed to initialize ContractUploader - invalid configuration: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check max_file_size setting in configuration (must be at least 1 MB)\n"
                    f"• Verify configuration file is not corrupted\n"
                    f"• Try resetting to default settings\n"
                    f"• Review the configuration file for errors"
                )
                logger.error(f"ContractUploader initialization failed - ValueError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            except Exception as e:
                # Generic error
                error_msg = (
                    f"Failed to initialize ContractUploader: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify configuration settings are correct\n"
                    f"• Check the application logs for more details\n"
                    f"• Try resetting to default settings\n"
                    f"• Restart the application"
                )
                logger.error(f"ContractUploader initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                return False
            
            # 4. Initialize AnalysisEngine (requires API key)
            logger.info("Initializing AnalysisEngine...")
            try:
                if api_key:
                    self.analysis_engine = AnalysisEngine(openai_api_key=api_key)
                    logger.info("AnalysisEngine initialized successfully")
                else:
                    logger.warning("AnalysisEngine not initialized - API key missing")
                    self.analysis_engine = None
            except ImportError as e:
                # Module import failure - likely missing dependency
                error_msg = (
                    f"Failed to initialize AnalysisEngine - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Install required packages: pip install openai\n"
                    f"• Verify your Python environment is properly configured\n"
                    f"• Check that all dependencies are installed"
                )
                logger.error(f"AnalysisEngine initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.analysis_engine = None
                # Don't return False - allow user to configure later
            except ConnectionError as e:
                # Network connection failure
                error_msg = (
                    f"Failed to initialize AnalysisEngine - network connection error: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check your internet connection\n"
                    f"• Verify firewall settings allow OpenAI API access\n"
                    f"• Try again in a few moments\n"
                    f"• Check OpenAI service status at https://status.openai.com"
                )
                logger.error(f"AnalysisEngine initialization failed - ConnectionError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.analysis_engine = None
                # Don't return False - allow retry later
            except ValueError as e:
                # Invalid configuration or API key format
                error_msg = (
                    f"Failed to initialize AnalysisEngine - invalid configuration: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify your API key format is correct (should start with 'sk-')\n"
                    f"• Check that your API key is at least 20 characters long\n"
                    f"• Visit https://platform.openai.com/account/api-keys to verify your key\n"
                    f"• Try re-entering your API key in Settings"
                )
                logger.error(f"AnalysisEngine initialization failed - ValueError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.analysis_engine = None
                # Don't return False - allow user to fix configuration
            except PermissionError as e:
                # File permission issues
                error_msg = (
                    f"Failed to initialize AnalysisEngine - permission denied: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check file permissions for configuration directory\n"
                    f"• Ensure you have write access to the application directory\n"
                    f"• Try running the application with appropriate permissions\n"
                    f"• On Windows, try running as administrator"
                )
                logger.error(f"AnalysisEngine initialization failed - PermissionError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.analysis_engine = None
                # Don't return False - allow user to fix permissions
            except Exception as e:
                # Generic error with troubleshooting guidance
                error_msg = (
                    f"Failed to initialize AnalysisEngine: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify your API key is correct and active\n"
                    f"• Check your internet connection\n"
                    f"• Ensure your API key has sufficient credits\n"
                    f"• Visit https://platform.openai.com/account/api-keys to verify your key\n"
                    f"• Check the application logs for more details"
                )
                logger.error(f"AnalysisEngine initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.analysis_engine = None
                # Don't return False - allow user to configure key later
            
            # 5. Initialize QueryEngine (requires OpenAI client)
            logger.info("Initializing QueryEngine...")
            try:
                if self.analysis_engine:
                    # Reuse OpenAI client from AnalysisEngine
                    openai_client = self.analysis_engine.openai_client
                    self.query_engine = QueryEngine(openai_client=openai_client)
                    logger.info("QueryEngine initialized successfully with OpenAI client")
                else:
                    logger.warning("QueryEngine not initialized - AnalysisEngine unavailable")
                    self.query_engine = None
            except ImportError as e:
                # Module import failure
                error_msg = (
                    f"Failed to initialize QueryEngine - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Install required packages for query processing\n"
                    f"• Verify your Python environment is properly configured\n"
                    f"• Check that all dependencies are installed"
                )
                logger.error(f"QueryEngine initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except ValueError as e:
                # Invalid configuration
                error_msg = (
                    f"Failed to initialize QueryEngine - invalid configuration: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify OpenAI client is properly configured\n"
                    f"• Check query engine settings in configuration\n"
                    f"• Try resetting to default settings\n"
                    f"• Review the configuration file for errors"
                )
                logger.error(f"QueryEngine initialization failed - ValueError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except AttributeError as e:
                # AnalysisEngine doesn't have openai_client attribute
                error_msg = (
                    f"Failed to initialize QueryEngine - AnalysisEngine missing OpenAI client: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify AnalysisEngine is properly initialized\n"
                    f"• Check that AnalysisEngine has openai_client attribute\n"
                    f"• Try restarting the application\n"
                    f"• Contact support if the issue persists"
                )
                logger.error(f"QueryEngine initialization failed - AttributeError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except Exception as e:
                # Generic error with troubleshooting guidance
                error_msg = (
                    f"Failed to initialize QueryEngine: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify OpenAI client is properly initialized\n"
                    f"• Check the application logs for more details\n"
                    f"• Try restarting the application\n"
                    f"• Contact support if the issue persists"
                )
                logger.error(f"QueryEngine initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            
            # 6. Initialize versioning components
            logger.info("Initializing versioning components...")
            try:
                from src.version_database import VersionDatabase
                from src.contract_identity_detector import ContractIdentityDetector
                from src.change_comparator import ChangeComparator
                from src.differential_storage import DifferentialStorage
                from src.version_manager import VersionManager
                
                # Initialize version database
                self.version_db = VersionDatabase()
                logger.info("VersionDatabase initialized successfully")
                
                # Initialize differential storage
                self.differential_storage = DifferentialStorage(database=self.version_db)
                logger.info("DifferentialStorage initialized successfully")
                
                # Initialize contract identity detector
                self.contract_identity_detector = ContractIdentityDetector(db=self.version_db)
                logger.info("ContractIdentityDetector initialized successfully")
                
                # Initialize change comparator
                self.change_comparator = ChangeComparator()
                logger.info("ChangeComparator initialized successfully")
                
                # Initialize version manager
                self.version_manager = VersionManager(storage=self.differential_storage)
                logger.info("VersionManager initialized successfully")
                
            except ImportError as e:
                error_msg = (
                    f"Failed to initialize versioning components - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify versioning modules are available\n"
                    f"• Check that all dependencies are installed\n"
                    f"• Restart the application"
                )
                logger.error(f"Versioning components initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                # Set components to None
                self.version_db = None
                self.differential_storage = None
                self.contract_identity_detector = None
                self.change_comparator = None
                self.version_manager = None
            except Exception as e:
                error_msg = (
                    f"Failed to initialize versioning components: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Check the application logs for more details\n"
                    f"• Verify database permissions\n"
                    f"• Restart the application"
                )
                logger.error(f"Versioning components initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                # Set components to None
                self.version_db = None
                self.differential_storage = None
                self.contract_identity_detector = None
                self.change_comparator = None
                self.version_manager = None
            except ImportError as e:
                # Module import failure
                error_msg = (
                    f"Failed to initialize QueryEngine - missing dependency: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Install required packages for query processing\n"
                    f"• Verify your Python environment is properly configured\n"
                    f"• Check that all dependencies are installed"
                )
                logger.error(f"QueryEngine initialization failed - ImportError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except ValueError as e:
                # Invalid configuration
                error_msg = (
                    f"Failed to initialize QueryEngine - invalid configuration: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify OpenAI client is properly configured\n"
                    f"• Check query engine settings in configuration\n"
                    f"• Try resetting to default settings\n"
                    f"• Review the configuration file for errors"
                )
                logger.error(f"QueryEngine initialization failed - ValueError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except AttributeError as e:
                # AnalysisEngine doesn't have openai_client attribute
                error_msg = (
                    f"Failed to initialize QueryEngine - AnalysisEngine missing OpenAI client: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify AnalysisEngine is properly initialized\n"
                    f"• Check that AnalysisEngine has openai_client attribute\n"
                    f"• Try restarting the application\n"
                    f"• Contact support if the issue persists"
                )
                logger.error(f"QueryEngine initialization failed - AttributeError: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            except Exception as e:
                # Generic error with troubleshooting guidance
                error_msg = (
                    f"Failed to initialize QueryEngine: {str(e)}\n\n"
                    f"Troubleshooting:\n"
                    f"• Verify OpenAI client is properly initialized\n"
                    f"• Check the application logs for more details\n"
                    f"• Try restarting the application\n"
                    f"• Contact support if the issue persists"
                )
                logger.error(f"QueryEngine initialization failed - Exception: {e}", exc_info=True)
                self._initialization_errors.append(error_msg)
                self.query_engine = None
                # Don't return False - allow analysis without query capability
            
            # Mark initialization as complete
            self._initialized = True
            
            # Log summary
            if self._initialization_errors:
                logger.warning("Component initialization completed with %d warnings", 
                             len(self._initialization_errors))
            else:
                logger.info("All components initialized successfully")
            
            return True
            
        except Exception as e:
            error_msg = f"Critical error during component initialization: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._initialization_errors.append(error_msg)
            return False
    
    def validate_dependencies(self) -> tuple[bool, list[str]]:
        """
        Validate that all required dependencies are available.
        
        Checks:
        - OpenAI API key is configured
        - All required components are initialized
        
        Returns:
            Tuple of (is_valid, list of missing dependencies)
        """
        logger.info("Validating dependencies...")
        missing = []
        
        # Check ConfigManager
        if not self.config_manager:
            missing.append("ConfigManager not initialized")
        
        # Check API key
        if self.config_manager:
            api_key = self.config_manager.get_openai_key()
            if not api_key:
                missing.append("OpenAI API key not configured")
        
        # Check ContractUploader
        if not self.contract_uploader:
            missing.append("ContractUploader not initialized")
        
        # Check AnalysisEngine
        if not self.analysis_engine:
            missing.append("AnalysisEngine not initialized (API key may be missing)")
        
        # Check QueryEngine
        if not self.query_engine:
            missing.append("QueryEngine not initialized")
        
        is_valid = len(missing) == 0
        
        if is_valid:
            logger.info("All dependencies validated successfully")
        else:
            logger.warning("Dependency validation failed: %s", ", ".join(missing))
        
        return is_valid, missing
    
    def handle_initialization_failure(self, component_name: str, error: Exception) -> None:
        """
        Handle initialization failure for a specific component.
        
        Args:
            component_name: Name of component that failed to initialize
            error: Exception that occurred during initialization
        """
        error_msg = f"Failed to initialize {component_name}: {str(error)}"
        logger.error(error_msg, exc_info=True)
        
        self._initialization_errors.append(error_msg)
        
        # Store error in context
        self.context.error_message = error_msg
        
        # Transition to error state
        self._transition_state(AppState.ERROR)
