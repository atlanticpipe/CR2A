"""
Settings Dialog Module

Provides a dialog window for API key configuration in the Unified CR2A Application.
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable
from src.ui_styles import UIStyles


logger = logging.getLogger(__name__)


class SettingsDialog:
    """
    Settings dialog for API key configuration.
    
    This dialog provides:
    - API key input field (with password masking)
    - Show/hide password toggle
    - Validation before saving
    - Save and Cancel buttons
    
    The dialog can be shown on startup if the API key is missing,
    or opened from the settings menu.
    """
    
    def __init__(self, parent: tk.Tk, config_manager, on_save_callback: Optional[Callable] = None,
                 title: Optional[str] = None, message: Optional[str] = None):
        """
        Initialize settings dialog.
        
        Args:
            parent: Parent Tkinter window
            config_manager: ConfigManager instance for saving/loading settings
            on_save_callback: Optional callback to call after successful save
            title: Optional custom dialog title
            message: Optional custom message to display at top of dialog
        """
        self.parent = parent
        self.config_manager = config_manager
        self.on_save_callback = on_save_callback
        self.custom_title = title
        self.custom_message = message
        
        # Dialog window
        self.dialog = None
        
        # UI components
        self.api_key_var = None
        self.api_key_entry = None
        self.show_key_var = None
        self.show_key_checkbox = None
        self.save_button = None
        self.cancel_button = None
        self.validation_label = None
        
        # Result
        self.result = None  # Will be set to True if saved, False if cancelled
        
        logger.debug("SettingsDialog initialized")
    
    def show(self, required: bool = False) -> bool:
        """
        Show the settings dialog.
        
        Args:
            required: If True, the dialog cannot be cancelled (for first-time setup)
        
        Returns:
            True if settings were saved, False if cancelled
        """
        logger.info(f"Showing settings dialog (required={required})")
        
        # Create dialog window
        self.dialog = tk.Toplevel(self.parent)
        # Use custom title if provided, otherwise use default
        dialog_title = self.custom_title if self.custom_title else "Settings - OpenAI API Key"
        self.dialog.title(dialog_title)
        self.dialog.geometry("550x450")  # Increased height to accommodate custom message
        self.dialog.resizable(False, False)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog on parent window
        self._center_dialog()
        
        # Create UI
        self._create_widgets(required)
        
        # Load current API key if exists
        self._load_current_key()
        
        # If required, disable close button
        if required:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_required_close_attempt)
        else:
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Wait for dialog to close
        self.dialog.wait_window()
        
        logger.info(f"Settings dialog closed with result: {self.result}")
        return self.result if self.result is not None else False
    
    def _center_dialog(self) -> None:
        """Center dialog on parent window."""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self, required: bool) -> None:
        """
        Create dialog widgets.
        
        Args:
            required: If True, show message that API key is required
        """
        # Main frame with consistent padding
        main_frame = ttk.Frame(self.dialog, padding=UIStyles.get_frame_padding())
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Display custom message prominently if provided
        if self.custom_message:
            message_frame = ttk.Frame(main_frame, relief=tk.RIDGE, borderwidth=2)
            message_frame.pack(fill=tk.X, pady=(0, UIStyles.SPACING_LARGE))
            
            message_label = ttk.Label(
                message_frame,
                text=self.custom_message,
                font=UIStyles.get_small_font(),
                foreground=UIStyles.TEXT_PRIMARY,
                justify=tk.LEFT,
                wraplength=500,
                padding=UIStyles.get_frame_padding()
            )
            message_label.pack(fill=tk.X)
        
        # Title with consistent styling
        title_label = ttk.Label(
            main_frame,
            text="OpenAI API Key Configuration",
            font=UIStyles.get_subtitle_font()
        )
        title_label.pack(pady=(0, UIStyles.PADDING_MEDIUM))
        
        # Description or required message with consistent styling
        if required:
            desc_text = ("An OpenAI API key is required to analyze contracts.\n"
                        "Please enter your API key to continue.")
            desc_color = UIStyles.ERROR_COLOR
        else:
            desc_text = ("Enter your OpenAI API key to enable contract analysis.\n"
                        "Your API key will be stored securely with encryption.")
            desc_color = UIStyles.TEXT_SECONDARY
        
        desc_label = ttk.Label(
            main_frame,
            text=desc_text,
            font=UIStyles.get_small_font(),
            foreground=desc_color,
            justify=tk.CENTER,
            wraplength=450
        )
        desc_label.pack(pady=(0, UIStyles.SPACING_LARGE))
        
        # API Key input frame with consistent padding
        input_frame = ttk.LabelFrame(main_frame, text="API Key", padding=UIStyles.get_labelframe_padding())
        input_frame.pack(fill=tk.X, pady=(0, UIStyles.PADDING_MEDIUM))
        
        # API Key entry with consistent styling
        self.api_key_var = tk.StringVar()
        self.api_key_var.trace_add("write", self._on_key_changed)
        
        self.api_key_entry = ttk.Entry(
            input_frame,
            textvariable=self.api_key_var,
            show="*",  # Mask the key by default
            font=("Consolas", UIStyles.FONT_SIZE_NORMAL),
            width=50
        )
        self.api_key_entry.pack(fill=tk.X, pady=(0, UIStyles.PADDING_MEDIUM))
        self.api_key_entry.focus()
        
        # Show/hide key checkbox
        self.show_key_var = tk.BooleanVar(value=False)
        self.show_key_checkbox = ttk.Checkbutton(
            input_frame,
            text="Show API key",
            variable=self.show_key_var,
            command=self._toggle_key_visibility
        )
        self.show_key_checkbox.pack(anchor=tk.W)
        
        # Validation message label with consistent styling
        self.validation_label = ttk.Label(
            main_frame,
            text="",
            font=UIStyles.get_small_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            wraplength=450
        )
        self.validation_label.pack(pady=(0, UIStyles.PADDING_MEDIUM))
        
        # Help text with consistent styling
        help_text = ("API keys start with 'sk-' and are at least 20 characters long.\n"
                    "Get your API key from: https://platform.openai.com/api-keys")
        help_label = ttk.Label(
            main_frame,
            text=help_text,
            font=UIStyles.get_tiny_font(),
            foreground=UIStyles.TEXT_SECONDARY,
            justify=tk.CENTER,
            wraplength=450
        )
        help_label.pack(pady=(0, UIStyles.SPACING_LARGE))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # Save button
        self.save_button = ttk.Button(
            button_frame,
            text="Save",
            command=self._on_save,
            state=tk.DISABLED  # Initially disabled until valid key entered
        )
        self.save_button.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Cancel button (only if not required)
        if not required:
            self.cancel_button = ttk.Button(
                button_frame,
                text="Cancel",
                command=self._on_cancel
            )
            self.cancel_button.pack(side=tk.RIGHT)
        
        # Bind Enter key to save
        self.dialog.bind("<Return>", lambda e: self._on_save() if self.save_button['state'] == tk.NORMAL else None)
        
        # Bind Escape key to cancel (only if not required)
        if not required:
            self.dialog.bind("<Escape>", lambda e: self._on_cancel())
    
    def _load_current_key(self) -> None:
        """Load current API key from config if exists."""
        try:
            current_key = self.config_manager.get_openai_key()
            if current_key:
                self.api_key_var.set(current_key)
                logger.debug("Loaded existing API key into dialog")
        except Exception as e:
            logger.warning(f"Could not load current API key: {e}")
    
    def _toggle_key_visibility(self) -> None:
        """Toggle API key visibility (show/hide)."""
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
            logger.debug("API key visibility: shown")
        else:
            self.api_key_entry.config(show="*")
            logger.debug("API key visibility: hidden")
    
    def _on_key_changed(self, *args) -> None:
        """
        Handle API key text change.
        
        Validates the key and enables/disables save button.
        """
        api_key = self.api_key_var.get().strip()
        
        # Clear validation message with consistent styling
        self.validation_label.config(text="", foreground=UIStyles.TEXT_SECONDARY)
        
        # If empty, disable save button
        if not api_key:
            self.save_button.config(state=tk.DISABLED)
            return
        
        # Validate format
        is_valid, message = self._validate_api_key(api_key)
        
        if is_valid:
            self.validation_label.config(text="✓ Valid API key format", foreground=UIStyles.SUCCESS_COLOR)
            self.save_button.config(state=tk.NORMAL)
        else:
            self.validation_label.config(text=f"✗ {message}", foreground=UIStyles.ERROR_COLOR)
            self.save_button.config(state=tk.DISABLED)
    
    def _validate_api_key(self, api_key: str) -> tuple[bool, str]:
        """
        Validate API key format.
        
        Args:
            api_key: API key to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if starts with "sk-"
        if not api_key.startswith("sk-"):
            return False, "API key must start with 'sk-'"
        
        # Check minimum length
        if len(api_key) < 20:
            return False, "API key must be at least 20 characters long"
        
        # Check for invalid characters (basic check)
        # OpenAI keys are alphanumeric with hyphens
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
        if not all(c in valid_chars for c in api_key):
            return False, "API key contains invalid characters"
        
        return True, ""
    
    def _on_save(self) -> None:
        """Handle save button click."""
        api_key = self.api_key_var.get().strip()
        
        logger.info("Attempting to save API key")
        
        # Validate one more time
        is_valid, message = self._validate_api_key(api_key)
        if not is_valid:
            logger.warning(f"API key validation failed: {message}")
            messagebox.showerror(
                "Invalid API Key",
                message,
                parent=self.dialog
            )
            return
        
        try:
            # Save API key to config
            self.config_manager.set_openai_key(api_key)
            success = self.config_manager.save_config()
            
            if success:
                logger.info("API key saved successfully")
                
                # Show success message
                messagebox.showinfo(
                    "Settings Saved",
                    "Your API key has been saved securely.",
                    parent=self.dialog
                )
                
                # Set result and close
                self.result = True
                
                # Call callback if provided
                if self.on_save_callback:
                    try:
                        self.on_save_callback()
                    except Exception as e:
                        logger.error(f"Error in save callback: {e}")
                
                self.dialog.destroy()
            else:
                logger.error("Failed to save configuration")
                messagebox.showerror(
                    "Save Failed",
                    "Failed to save configuration. Please check file permissions.",
                    parent=self.dialog
                )
        
        except Exception as e:
            logger.error(f"Error saving API key: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"An error occurred while saving: {str(e)}",
                parent=self.dialog
            )
    
    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        logger.info("Settings dialog cancelled")
        self.result = False
        self.dialog.destroy()
    
    def _on_required_close_attempt(self) -> None:
        """Handle close attempt when API key is required."""
        logger.warning("User attempted to close required settings dialog")
        messagebox.showwarning(
            "API Key Required",
            "An OpenAI API key is required to use this application.\n"
            "Please enter your API key or close the application.",
            parent=self.dialog
        )


def show_settings_dialog(parent: tk.Tk, config_manager, required: bool = False, 
                        title: Optional[str] = None, message: Optional[str] = None,
                        on_save_callback: Optional[Callable] = None) -> bool:
    """
    Show settings dialog (convenience function).
    
    Args:
        parent: Parent Tkinter window
        config_manager: ConfigManager instance
        required: If True, dialog cannot be cancelled
        title: Optional custom dialog title
        message: Optional custom message to display at top of dialog
        on_save_callback: Optional callback after successful save
    
    Returns:
        True if settings were saved, False if cancelled
    """
    dialog = SettingsDialog(parent, config_manager, on_save_callback, title, message)
    return dialog.show(required=required)
