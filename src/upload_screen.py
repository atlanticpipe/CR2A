"""
Upload Screen Module

Provides UI for contract file selection and validation in the Unified CR2A Application.
"""

import logging
import tkinter as tk
from tkinter import ttk, filedialog
from typing import Optional, Callable
from pathlib import Path
from src.ui_styles import UIStyles


logger = logging.getLogger(__name__)


class UploadScreen:
    """
    Upload screen for contract file selection and validation.
    
    This screen provides:
    - File selection button
    - Analyze button (initially disabled)
    - File info display area
    - Status message area
    """
    
    def __init__(self, parent: tk.Frame, controller):
        """
        Initialize upload screen UI components.
        
        Args:
            parent: Parent Tkinter frame
            controller: ApplicationController instance
        """
        self.parent = parent
        self.controller = controller
        
        # State variables
        self.selected_file_path: Optional[str] = None
        self.file_info: Optional[dict] = None
        
        # UI components (will be created in render())
        self.main_frame = None
        self.title_label = None
        self.file_select_button = None
        self.file_info_frame = None
        self.file_name_label = None
        self.file_size_label = None
        self.analyze_button = None
        self.status_label = None
        
        logger.debug("UploadScreen initialized")
    
    def render(self) -> None:
        """Display upload screen widgets."""
        logger.info("Rendering upload screen")
        
        # Clear parent frame
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # Create main frame with consistent padding
        self.main_frame = ttk.Frame(self.parent, padding=UIStyles.get_frame_padding())
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for centering
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=0)
        self.main_frame.rowconfigure(2, weight=0)
        self.main_frame.rowconfigure(3, weight=0)
        self.main_frame.rowconfigure(4, weight=0)
        self.main_frame.rowconfigure(5, weight=1)
        
        # Create content frame (centered)
        content_frame = ttk.Frame(self.main_frame)
        content_frame.grid(row=1, column=0, rowspan=4, sticky=(tk.N, tk.S, tk.E, tk.W))
        content_frame.columnconfigure(0, weight=1)
        
        # Title with consistent styling
        self.title_label = ttk.Label(
            content_frame,
            text="CR2A Contract Analysis",
            font=UIStyles.get_title_font(),
            anchor=tk.CENTER
        )
        self.title_label.grid(row=0, column=0, pady=(0, UIStyles.SPACING_XLARGE))
        
        # Subtitle with consistent styling
        subtitle_label = ttk.Label(
            content_frame,
            text="Upload a contract document to begin analysis",
            font=UIStyles.get_large_font(),
            anchor=tk.CENTER,
            foreground=UIStyles.TEXT_SECONDARY
        )
        subtitle_label.grid(row=1, column=0, pady=(0, UIStyles.PADDING_XLARGE))
        
        # File selection button with consistent styling
        button_config = UIStyles.get_button_config("large")
        self.file_select_button = ttk.Button(
            content_frame,
            text="Select Contract File",
            command=self.on_file_select,
            **button_config
        )
        self.file_select_button.grid(row=2, column=0, pady=(0, UIStyles.SPACING_LARGE))
        
        # File info display area with consistent padding
        self.file_info_frame = ttk.LabelFrame(
            content_frame,
            text="Selected File",
            padding=UIStyles.get_labelframe_padding()
        )
        self.file_info_frame.grid(row=3, column=0, pady=(0, UIStyles.SPACING_LARGE), sticky=(tk.E, tk.W))
        self.file_info_frame.columnconfigure(0, weight=1)
        
        # File name label with consistent styling
        self.file_name_label = ttk.Label(
            self.file_info_frame,
            text="No file selected",
            font=UIStyles.get_normal_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            anchor=tk.CENTER
        )
        self.file_name_label.grid(row=0, column=0, pady=(0, UIStyles.PADDING_SMALL))
        
        # File size label with consistent styling
        self.file_size_label = ttk.Label(
            self.file_info_frame,
            text="",
            font=UIStyles.get_small_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            anchor=tk.CENTER
        )
        self.file_size_label.grid(row=1, column=0)
        
        # Analyze button with consistent styling (initially disabled)
        self.analyze_button = ttk.Button(
            content_frame,
            text="Analyze Contract",
            command=self.on_analyze_click,
            state=tk.DISABLED,
            **button_config
        )
        self.analyze_button.grid(row=4, column=0, pady=(0, UIStyles.SPACING_LARGE))
        
        # Status message area with consistent styling
        self.status_label = ttk.Label(
            content_frame,
            text="",
            font=UIStyles.get_small_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            anchor=tk.CENTER,
            wraplength=UIStyles.TEXT_WRAP_LENGTH
        )
        self.status_label.grid(row=5, column=0, pady=(UIStyles.PADDING_MEDIUM, 0))
        
        # Settings button in bottom left corner
        settings_frame = ttk.Frame(self.main_frame)
        settings_frame.grid(row=5, column=0, sticky=(tk.S, tk.W), pady=UIStyles.PADDING_MEDIUM, padx=UIStyles.PADDING_MEDIUM)
        
        settings_button = ttk.Button(
            settings_frame,
            text="⚙ Settings",
            command=self.on_settings_click,
            width=12
        )
        settings_button.pack()
        
        # Bind keyboard shortcuts
        self._bind_keyboard_shortcuts()
        
        logger.info("Upload screen rendered successfully")
    
    def on_file_select(self) -> None:
        """
        Handle file selection button click.
        
        Opens file dialog and validates selected file.
        """
        logger.info("File selection initiated")
        
        # Clear previous status
        self.show_status("", "gray")
        
        # Open file dialog
        file_path = filedialog.askopenfilename(
            title="Select Contract Document",
            filetypes=[
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx"),
                ("All supported files", "*.pdf *.docx"),
                ("All files", "*.*")
            ],
            initialdir=Path.home()
        )
        
        # Check if user cancelled
        if not file_path:
            logger.debug("File selection cancelled by user")
            return
        
        logger.info(f"File selected: {file_path}")
        
        # Validate file
        self.validate_file(file_path)
    
    def validate_file(self, file_path: str) -> None:
        """
        Validate file format and readability.
        
        Args:
            file_path: Path to file to validate
        """
        logger.info(f"Validating file: {file_path}")
        
        try:
            # Get contract uploader from controller
            if not self.controller.contract_uploader:
                error_msg = "Contract uploader not initialized"
                logger.error(error_msg)
                self.show_error(error_msg)
                return
            
            # Validate file format
            is_valid, error_msg = self.controller.contract_uploader.validate_format(file_path)
            
            if not is_valid:
                logger.warning(f"File validation failed: {error_msg}")
                self.show_error(error_msg)
                self.clear_file_selection()
                return
            
            # Get file info
            file_info = self.controller.contract_uploader.get_file_info(file_path)
            
            # Store file path and info
            self.selected_file_path = file_path
            self.file_info = file_info
            
            # Update UI
            self.display_file_info(file_info)
            
            # Enable analyze button
            self.analyze_button.config(state=tk.NORMAL)
            
            # Show success status
            self.show_status("File validated successfully. Ready to analyze.", "green")
            
            logger.info(f"File validated successfully: {file_info['filename']}")
            
        except Exception as e:
            logger.error(f"Error during file validation: {e}", exc_info=True)
            self.show_error(f"Error validating file: {str(e)}")
            self.clear_file_selection()
    
    def display_file_info(self, file_info: dict) -> None:
        """
        Display filename and file size.
        
        Args:
            file_info: Dictionary containing file metadata
        """
        logger.debug(f"Displaying file info: {file_info}")
        
        # Update file name label with consistent styling
        filename = file_info.get('filename', 'Unknown')
        self.file_name_label.config(
            text=filename,
            foreground=UIStyles.TEXT_PRIMARY
        )
        
        # Update file size label with consistent styling
        file_size = file_info.get('file_size_mb', 'Unknown')
        page_count = file_info.get('page_count')
        
        if page_count:
            size_text = f"{file_size} • {page_count} pages"
        else:
            size_text = file_size
        
        self.file_size_label.config(
            text=size_text,
            foreground=UIStyles.TEXT_PRIMARY
        )
    
    def clear_file_selection(self) -> None:
        """Clear file selection and reset UI."""
        logger.debug("Clearing file selection")
        
        self.selected_file_path = None
        self.file_info = None
        
        # Reset file info display with consistent styling
        self.file_name_label.config(
            text="No file selected",
            foreground=UIStyles.TEXT_SECONDARY
        )
        self.file_size_label.config(text="")
        
        # Disable analyze button
        self.analyze_button.config(state=tk.DISABLED)
    
    def on_analyze_click(self) -> None:
        """
        Handle analyze button click.
        
        Triggers transition to analysis screen.
        """
        logger.info("Analyze button clicked")
        
        if not self.selected_file_path:
            logger.warning("Analyze clicked but no file selected")
            self.show_error("Please select a file first")
            return
        
        try:
            # Show processing status
            self.show_status("Starting analysis...", "blue")
            
            # Disable buttons during transition
            self.file_select_button.config(state=tk.DISABLED)
            self.analyze_button.config(state=tk.DISABLED)
            
            # Trigger transition to analysis screen
            logger.info(f"Transitioning to analysis for file: {self.selected_file_path}")
            self.controller.transition_to_analysis(self.selected_file_path)
            
        except Exception as e:
            logger.error(f"Error starting analysis: {e}", exc_info=True)
            self.show_error(f"Failed to start analysis: {str(e)}")
            
            # Re-enable buttons
            self.file_select_button.config(state=tk.NORMAL)
            self.analyze_button.config(state=tk.NORMAL)
    
    def on_settings_click(self) -> None:
        """
        Handle settings button click.
        
        Opens the settings dialog for API key configuration.
        """
        logger.info("Settings button clicked")
        
        try:
            # Open settings dialog through controller
            self.controller.open_settings_dialog()
            
        except Exception as e:
            logger.error(f"Error opening settings: {e}", exc_info=True)
            self.show_error(f"Failed to open settings: {str(e)}")
    
    def show_error(self, message: str) -> None:
        """
        Display error message to user.
        
        Args:
            message: Error message to display
        """
        logger.debug(f"Showing error: {message}")
        self.show_status(f"Error: {message}", "red")
    
    def show_status(self, message: str, color: str = "gray") -> None:
        """
        Display status message with consistent styling.
        
        Args:
            message: Status message to display
            color: Status type - "success", "error", "warning", "info", or "default"
        """
        if self.status_label:
            # Map old color names to status types
            status_type_map = {
                "gray": "default",
                "green": "success",
                "red": "error",
                "blue": "info"
            }
            status_type = status_type_map.get(color, "default")
            actual_color = UIStyles.get_status_color(status_type)
            
            self.status_label.config(text=message, foreground=actual_color)
    
    def _bind_keyboard_shortcuts(self) -> None:
        """
        Bind keyboard shortcuts for the upload screen.
        
        Binds:
        - Enter key to trigger analyze action (when analyze button is enabled)
        """
        logger.debug("Binding keyboard shortcuts for upload screen")
        
        # Get the root window
        root = self.parent.winfo_toplevel()
        
        # Bind Enter key to analyze action
        # Only trigger if analyze button is enabled
        def on_enter_key(event):
            if self.analyze_button and self.analyze_button['state'] == tk.NORMAL:
                self.on_analyze_click()
                return "break"  # Prevent default behavior
        
        root.bind('<Return>', on_enter_key)
        
        logger.debug("Keyboard shortcuts bound: Enter -> Analyze")
