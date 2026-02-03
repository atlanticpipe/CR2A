"""
Contract Chat UI Main Application Class

Orchestrates all components and manages application lifecycle.
"""

import tkinter as tk
import logging
from typing import Optional
from pathlib import Path

from src.config_manager import ConfigManager
from src.gui_manager import TkinterGUIManager
from src.json_loader import ContractJSONLoader, ValidationError
from src.data_store import ContractDataStore
from src.query_engine import QueryEngine
from src.error_handler import ErrorHandler


logger = logging.getLogger(__name__)


class ContractChatUI:
    """
    Main application class for Contract Chat UI.
    
    Orchestrates all components including GUI, query engine, configuration,
    and manages the application lifecycle.
    """
    
    def __init__(self):
        """Initialize the main application and all components."""
        logger.info("Initializing ContractChatUI application")
        
        # Initialize error handler
        self.error_handler = ErrorHandler()
        
        # Initialize configuration manager
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        logger.info("Configuration loaded")
        
        # Initialize Tkinter root window
        self.root = tk.Tk()
        
        # Apply window settings from config
        window_settings = self.config_manager.get_window_settings()
        self.root.geometry(
            f"{window_settings['window_width']}x{window_settings['window_height']}"
            f"+{window_settings['window_x']}+{window_settings['window_y']}"
        )
        
        # Initialize data components
        self.json_loader = ContractJSONLoader()
        self.data_store = ContractDataStore()
        
        # Initialize Pythia engine (lazy loading - model loaded on first query)
        pythia_model_size = self.config_manager.get_pythia_model_size()
        self.pythia_engine = PythiaEngine(model_size=pythia_model_size)
        logger.info(f"Pythia engine initialized with model size: {pythia_model_size}")
        
        # Initialize model download manager
        self.download_manager = ModelDownloadManager(cache_dir=self.pythia_engine.cache_dir)
        logger.info("Model download manager initialized")
        
        # Initialize query engine
        self.query_engine = QueryEngine(self.data_store, self.pythia_engine)
        
        # Configure OpenAI fallback if enabled
        if self.config_manager.is_openai_fallback_enabled():
            api_key = self.config_manager.get_openai_key()
            if api_key:
                self.query_engine.enable_openai_fallback(api_key)
                logger.info("OpenAI fallback enabled")
        
        # Initialize GUI manager with query callback
        self.gui_manager = TkinterGUIManager(self.root, self._handle_query)
        logger.info("GUI manager initialized")
        
        # Wire file loading callback
        self._wire_file_loading()
        
        # Configure window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        logger.info("ContractChatUI initialization complete")
    
    def _wire_file_loading(self):
        """Wire file loading callback to GUI manager."""
        # Override the GUI manager's file loading handler
        original_load_handler = self.gui_manager._on_load_contract
        
        def load_contract_handler():
            file_path = self.gui_manager.show_file_dialog()
            if file_path:
                self.load_file(file_path)
        
        self.gui_manager._on_load_contract = load_contract_handler
        logger.debug("File loading callback wired")
    
    def _ensure_model_downloaded(self) -> bool:
        """
        Ensure Pythia model is downloaded and cached.
        
        Checks if model exists in cache, and if not, prompts user for download consent
        and downloads the model with progress tracking.
        
        Returns:
            True if model is available (cached or downloaded), False if download failed or cancelled
        """
        model_size = self.pythia_engine.model_size
        
        # Check if model is already cached
        if self.download_manager.is_model_cached(model_size):
            logger.info(f"Model Pythia-{model_size} found in cache")
            return True
        
        logger.info(f"Model Pythia-{model_size} not found in cache, prompting for download")
        
        # Get model information
        model_info = self.download_manager.get_model_size_info(model_size)
        
        # Show download consent dialog
        user_approved = self.gui_manager.show_download_consent_dialog(model_size, model_info)
        
        if not user_approved:
            logger.info("User declined model download")
            return False
        
        logger.info("User approved model download, starting download...")
        
        # Show progress dialog
        progress_window = self.gui_manager.show_download_progress_dialog(model_size)
        
        # Track download success
        download_success = [False]  # Use list to allow modification in nested function
        
        def progress_callback(progress: float, status: str):
            """Update progress dialog."""
            self.gui_manager.update_download_progress(progress_window, progress, status)
        
        def completion_callback(success: bool, error: Optional[str]):
            """Handle download completion."""
            download_success[0] = success
            
            # Close progress dialog
            self.gui_manager.close_download_progress_dialog(progress_window)
            
            if not success:
                logger.error(f"Model download failed: {error}")
                self.gui_manager.show_download_error(error or "Unknown error")
            else:
                logger.info("Model download completed successfully")
        
        # Start download in background thread
        download_thread = self.download_manager.download_model_async(
            model_size,
            progress_callback=progress_callback,
            completion_callback=completion_callback
        )
        
        # Wait for download to complete
        download_thread.join()
        
        return download_success[0]
    
    def _handle_query(self, query: str):
        """
        Handle user query submission.
        
        This is the callback function passed to GUI manager that processes
        user queries through the query engine.
        
        Args:
            query: User's natural language question
        """
        logger.info(f"Handling user query: {query}")
        
        try:
            # Show loading indicator
            self.gui_manager.show_loading("Processing query...")
            self.root.update()
            
            # Ensure Pythia model is loaded
            if not self.pythia_engine.is_model_loaded():
                logger.info("Loading Pythia model for first query...")
                
                # First, ensure model is downloaded
                if not self._ensure_model_downloaded():
                    raise RuntimeError("Model download cancelled or failed. Cannot process queries without Pythia model.")
                
                self.gui_manager.show_loading(f"Loading Pythia-{self.pythia_engine.model_size} model...")
                self.root.update()
                
                if not self.pythia_engine.load_model():
                    raise RuntimeError("Failed to load Pythia model")
                
                logger.info("Pythia model loaded successfully")
            
            # Get current settings for OpenAI fallback
            settings = self.gui_manager.get_settings()
            use_openai = settings.get("openai_fallback", False)
            
            # Check if OpenAI fallback should be used
            if use_openai and not self.query_engine.is_openai_fallback_enabled():
                # Enable OpenAI fallback if user has enabled it in settings
                api_key = self.config_manager.get_openai_key()
                if api_key:
                    self.query_engine.enable_openai_fallback(api_key)
            elif not use_openai and self.query_engine.is_openai_fallback_enabled():
                # Disable if user has disabled it
                self.query_engine.disable_openai_fallback()
            
            # Process query
            response = self.query_engine.process_query(query, use_openai_fallback=False)
            
            # Check if we should ask user about OpenAI fallback
            if (use_openai and 
                response.confidence < self.query_engine.get_fallback_threshold() and
                response.source == "pythia"):
                
                # Ask user for consent to use OpenAI
                from tkinter import messagebox
                use_openai_confirmed = messagebox.askyesno(
                    "Use OpenAI Fallback?",
                    f"Pythia has low confidence ({response.confidence:.0%}) in this answer.\n\n"
                    "Would you like to use OpenAI for a potentially better response?\n"
                    "(This will make an external API call and may incur costs)"
                )
                
                if use_openai_confirmed:
                    logger.info("User approved OpenAI fallback")
                    # Re-process with OpenAI fallback
                    response = self.query_engine.process_query(query, use_openai_fallback=True)
            
            # Hide loading indicator
            self.gui_manager.hide_loading()
            
            # Display response in conversation history
            self.gui_manager.display_message(
                response.answer,
                sender="system",
                source=response.source
            )
            
            logger.info(f"Query processed successfully (source: {response.source}, confidence: {response.confidence:.2f})")
            
        except Exception as e:
            # Hide loading indicator
            self.gui_manager.hide_loading()
            
            # Handle error
            logger.error(f"Error processing query: {e}", exc_info=True)
            error_response = self.error_handler.handle_error(e, "query_processing")
            
            # Display error to user
            self.gui_manager.show_error(error_response.message)
    
    def load_file(self, file_path: str) -> bool:
        """
        Load contract analysis JSON file.
        
        Args:
            file_path: Path to JSON file
            
        Returns:
            True if loaded successfully, False otherwise
        """
        logger.info(f"Loading file: {file_path}")
        
        try:
            # Show loading indicator
            self.gui_manager.show_loading("Loading contract data...")
            self.root.update()
            
            # Load JSON file
            contract_data = self.json_loader.load_file(file_path)
            
            # Check schema compatibility and show warnings if any
            is_compatible, warnings = self.json_loader.check_schema_compatibility(contract_data)
            
            if warnings:
                warning_message = "Contract loaded with warnings:\n\n" + "\n".join(f"• {w}" for w in warnings)
                warning_message += "\n\nThe contract was loaded successfully, but some fields may be empty or incomplete."
                logger.warning(f"Schema compatibility warnings: {warnings}")
                
                # Show warning dialog
                from tkinter import messagebox
                messagebox.showwarning("Schema Compatibility Warning", warning_message)
            
            # Load data into store
            self.data_store.load_data(contract_data)
            
            # Hide loading indicator
            self.gui_manager.hide_loading()
            
            # Update GUI to show file is loaded
            self.gui_manager.set_file_loaded(file_path)
            
            # Enable chat interface
            self.gui_manager.enable_chat_input(True)
            
            # Display success message
            success_msg = f"Contract loaded successfully from {Path(file_path).name}."
            if warnings:
                success_msg += " Note: Some fields may be empty (see warning dialog)."
            success_msg += " You can now ask questions about the contract."
            
            self.gui_manager.display_message(
                success_msg,
                sender="system",
                source="pythia"
            )
            
            logger.info("File loaded successfully")
            return True
            
        except (FileNotFoundError, ValidationError) as e:
            # Hide loading indicator
            self.gui_manager.hide_loading()
            
            # Handle expected errors
            logger.error(f"Error loading file: {e}")
            error_response = self.error_handler.handle_error(e, "file_loading")
            self.gui_manager.show_error(error_response.message)
            return False
            
        except Exception as e:
            # Hide loading indicator
            self.gui_manager.hide_loading()
            
            # Handle unexpected errors
            logger.error(f"Unexpected error loading file: {e}", exc_info=True)
            error_response = self.error_handler.handle_error(e, "file_loading")
            self.gui_manager.show_error(error_response.message)
            return False
    
    def _on_closing(self):
        """Handle application closing."""
        logger.info("Application closing")
        
        try:
            # Save window settings
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            window_x = self.root.winfo_x()
            window_y = self.root.winfo_y()
            
            self.config_manager.set_window_settings(window_width, window_height, window_x, window_y)
            
            # Save current settings
            settings = self.gui_manager.get_settings()
            self.config_manager.set_pythia_model_size(settings.get("pythia_model", "410M"))
            self.config_manager.set_openai_fallback_enabled(settings.get("openai_fallback", False))
            
            # Save configuration
            self.config_manager.save_config(self.config_manager.get_all_settings())
            logger.info("Configuration saved")
            
            # Cleanup components
            if hasattr(self, 'pythia_engine') and self.pythia_engine.is_model_loaded():
                self.pythia_engine.unload_model()
            
            if hasattr(self, 'error_handler'):
                self.error_handler.close()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        finally:
            # Destroy window
            self.root.destroy()
            logger.info("Application closed")
    
    def run(self):
        """Start the Tkinter main event loop."""
        logger.info("Starting application main loop")
        self.root.mainloop()
