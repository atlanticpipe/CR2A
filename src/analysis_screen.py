"""
Analysis Screen Module

Provides UI for displaying progress during contract analysis in the Unified CR2A Application.
"""

import logging
import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import threading
import time
from src.ui_styles import UIStyles


logger = logging.getLogger(__name__)


class AnalysisScreen:
    """
    Analysis screen for displaying progress during contract analysis.
    
    This screen provides:
    - Progress bar widget
    - Status message label
    - Estimated time label
    - Cancel button (optional)
    """
    
    def __init__(self, parent: tk.Frame, controller):
        """
        Initialize analysis screen UI components.
        
        Args:
            parent: Parent Tkinter frame
            controller: ApplicationController instance
        """
        self.parent = parent
        self.controller = controller
        
        # State variables
        self.file_path: Optional[str] = None
        self.analysis_thread: Optional[threading.Thread] = None
        self.is_analyzing = False
        self.start_time: Optional[float] = None
        self.estimated_duration = 60  # Default estimate in seconds
        
        # UI components (will be created in render())
        self.main_frame = None
        self.title_label = None
        self.progress_bar = None
        self.status_label = None
        self.time_label = None
        self.cancel_button = None
        
        logger.debug("AnalysisScreen initialized")
    
    def render(self) -> None:
        """Display analysis screen widgets."""
        logger.info("Rendering analysis screen")
        
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
            text="Analyzing Contract...",
            font=UIStyles.get_title_font(),
            anchor=tk.CENTER
        )
        self.title_label.grid(row=0, column=0, pady=(0, UIStyles.PADDING_XLARGE))
        
        # Progress bar with consistent styling
        self.progress_bar = ttk.Progressbar(
            content_frame,
            mode='determinate',
            length=UIStyles.PROGRESS_BAR_LENGTH,
            maximum=100
        )
        self.progress_bar.grid(row=1, column=0, pady=(0, UIStyles.SPACING_LARGE), sticky=(tk.E, tk.W))
        
        # Status message label with consistent styling
        self.status_label = ttk.Label(
            content_frame,
            text="Initializing analysis...",
            font=UIStyles.get_large_font(),
            anchor=tk.CENTER,
            wraplength=UIStyles.TEXT_WRAP_LENGTH
        )
        self.status_label.grid(row=2, column=0, pady=(0, UIStyles.SPACING_MEDIUM))
        
        # Estimated time label with consistent styling (initially hidden)
        self.time_label = ttk.Label(
            content_frame,
            text="",
            font=UIStyles.get_small_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            anchor=tk.CENTER
        )
        self.time_label.grid(row=3, column=0, pady=(0, UIStyles.SPACING_XLARGE))
        
        # Cancel button with consistent styling (optional)
        button_config = UIStyles.get_button_config("medium")
        self.cancel_button = ttk.Button(
            content_frame,
            text="Cancel",
            command=self.on_cancel_click,
            state=tk.DISABLED,  # Disabled for now - can be enabled if cancel functionality is implemented
            **button_config
        )
        self.cancel_button.grid(row=4, column=0, pady=(0, UIStyles.SPACING_LARGE))
        
        # Bind keyboard shortcuts
        self._bind_keyboard_shortcuts()
        
        logger.info("Analysis screen rendered successfully")

    def start_analysis(self, file_path: str) -> None:
        """
        Begin contract analysis in background thread.
        
        Args:
            file_path: Path to contract file to analyze
        """
        logger.info("Starting analysis for file: %s", file_path)
        
        self.file_path = file_path
        self.is_analyzing = True
        self.start_time = time.time()
        
        # Reset progress
        self.progress_bar['value'] = 0
        self.status_label.config(text="Initializing analysis...")
        self.time_label.config(text="")
        
        # Start analysis in background thread
        self.analysis_thread = threading.Thread(
            target=self._run_analysis,
            daemon=True
        )
        self.analysis_thread.start()
        
        logger.info("Analysis thread started")
    
    def _run_analysis(self) -> None:
        """
        Run analysis in background thread.
        
        This method executes the actual analysis and handles completion/errors.
        """
        try:
            logger.debug("Analysis thread running")
            
            # Get analysis engine from controller
            if not self.controller.analysis_engine:
                error_msg = "Analysis engine not initialized"
                logger.error(error_msg)
                self.parent.after(0, lambda: self.on_analysis_error(Exception(error_msg)))
                return
            
            # Run analysis with progress callback
            analysis_result = self.controller.analysis_engine.analyze_contract(
                file_path=self.file_path,
                progress_callback=self._progress_callback_wrapper
            )
            
            # Convert to dictionary for storage
            result_dict = analysis_result.to_dict()
            
            # Call completion handler on main thread
            self.parent.after(0, lambda: self.on_analysis_complete(result_dict))
            
        except Exception as e:
            logger.error("Analysis failed: %s", e, exc_info=True)
            # Call error handler on main thread
            self.parent.after(0, lambda: self.on_analysis_error(e))
    
    def _progress_callback_wrapper(self, status: str, percent: int) -> None:
        """
        Wrapper for progress callback to update UI on main thread.
        
        Args:
            status: Status message
            percent: Progress percentage (0-100)
        """
        # Schedule UI update on main thread
        self.parent.after(0, lambda: self.update_progress(status, percent))
    
    def update_progress(self, status: str, percent: int) -> None:
        """
        Update progress indicator and status message.
        
        Args:
            status: Status message to display
            percent: Progress percentage (0-100)
        """
        logger.debug("Progress update: %s (%d%%)", status, percent)
        
        # Update progress bar
        self.progress_bar['value'] = percent
        
        # Update status message
        self.status_label.config(text=status)
        
        # Update estimated time if analysis has been running > 10 seconds
        if self.start_time:
            elapsed = time.time() - self.start_time
            
            if elapsed > 10:
                # Calculate estimated time remaining
                if percent > 0:
                    total_estimated = (elapsed / percent) * 100
                    remaining = total_estimated - elapsed
                    
                    # Format time remaining
                    if remaining > 60:
                        time_str = f"Estimated time remaining: {int(remaining / 60)} min {int(remaining % 60)} sec"
                    else:
                        time_str = f"Estimated time remaining: {int(remaining)} seconds"
                    
                    self.time_label.config(text=time_str)
                else:
                    self.time_label.config(text="Calculating estimated time...")
            else:
                # Clear time label if < 10 seconds
                self.time_label.config(text="")
        
        # Force UI update
        self.parent.update_idletasks()
    
    def on_analysis_complete(self, result: dict) -> None:
        """
        Handle successful analysis completion.
        
        Args:
            result: Analysis result dictionary
        """
        logger.info("Analysis completed successfully")
        
        self.is_analyzing = False
        
        # Update UI to show completion
        self.progress_bar['value'] = 100
        self.status_label.config(text="Analysis complete! Loading chat interface...")
        self.time_label.config(text="")
        
        # Log completion time
        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info("Analysis completed in %.2f seconds", elapsed)
        
        # Trigger transition to chat screen
        try:
            self.controller.transition_to_chat(result)
        except Exception as e:
            logger.error("Error transitioning to chat: %s", e)
            self.on_analysis_error(e)
    
    def on_analysis_error(self, error: Exception) -> None:
        """
        Handle analysis failure.
        
        Args:
            error: Exception that occurred during analysis
        """
        logger.error("Analysis error: %s", error)
        
        self.is_analyzing = False
        
        # Update UI to show error
        self.status_label.config(text=f"Error: {str(error)}")
        self.time_label.config(text="")
        
        # Show error dialog with retry option
        self._show_error_dialog(str(error))
    
    def _show_error_dialog(self, error_message: str) -> None:
        """
        Show error dialog with retry option.
        
        Args:
            error_message: Error message to display
        """
        from tkinter import messagebox
        
        # Show error message
        result = messagebox.askyesno(
            "Analysis Error",
            f"An error occurred during analysis:\n\n{error_message}\n\nWould you like to return to the upload screen and try again?",
            icon='error'
        )
        
        if result:
            # User wants to retry - return to upload screen
            logger.info("User chose to retry - returning to upload screen")
            self.controller.transition_to_upload()
        else:
            # User cancelled - stay on error screen
            logger.info("User cancelled retry")
            # Could add additional error handling here
    
    def on_cancel_click(self) -> None:
        """
        Handle cancel button click.
        
        Note: Cancel functionality is optional and currently disabled.
        If implemented, this would stop the analysis thread and return to upload.
        """
        logger.info("Cancel button clicked")
        
        if self.is_analyzing:
            # TODO: Implement cancellation logic
            # This would require making the analysis thread interruptible
            logger.warning("Cancel functionality not yet implemented")
            
            from tkinter import messagebox
            messagebox.showinfo(
                "Cancel",
                "Cancel functionality is not yet implemented. Please wait for analysis to complete."
            )
    
    def _bind_keyboard_shortcuts(self) -> None:
        """
        Bind keyboard shortcuts for the analysis screen.
        
        Binds:
        - Escape key to trigger cancel action (when cancel button is enabled)
        """
        logger.debug("Binding keyboard shortcuts for analysis screen")
        
        # Get the root window
        root = self.parent.winfo_toplevel()
        
        # Bind Escape key to cancel action
        # Only trigger if cancel button is enabled
        def on_escape_key(event):
            if self.cancel_button and self.cancel_button['state'] == tk.NORMAL:
                self.on_cancel_click()
                return "break"  # Prevent default behavior
        
        root.bind('<Escape>', on_escape_key)
        
        logger.debug("Keyboard shortcuts bound: Escape -> Cancel")
