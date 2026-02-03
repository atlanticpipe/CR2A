"""
Tkinter GUI Manager for Contract Chat UI.

This module provides the TkinterGUIManager class which handles all GUI operations
including window management, conversation display, user input, and settings.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from typing import Callable, Optional, Dict, Any, List
import os

from src.error_handler import ErrorHandler


class TkinterGUIManager:
    """
    Manages the Tkinter GUI for the Contract Chat UI application.
    
    Responsibilities:
    - Window initialization and layout
    - File selection dialog
    - Conversation history display
    - Chat input handling
    - Settings panel
    - Loading indicators
    - Error display
    """
    
    def __init__(self, root: tk.Tk, query_callback: Callable[[str], None]):
        """
        Initialize GUI components.
        
        Args:
            root: Tkinter root window
            query_callback: Function to call when user submits query
        """
        self.root = root
        self.query_callback = query_callback
        self.error_handler = ErrorHandler()
        
        # Window configuration
        self.root.title("Contract Chat UI")
        self.root.geometry("900x700")
        self.root.minsize(600, 400)
        
        # Try to set window icon if available
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except:
                pass  # Icon loading is optional
        
        # Initialize variables
        self.chat_enabled = False
        self.current_file_path = None
        self.settings = {
            "pythia_model": "410M",
            "openai_fallback": False
        }
        
        # Create main layout
        self._create_layout()
        
        # Configure window close handler
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_layout(self):
        """Create the main window layout with frames."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Top frame - File selection and settings
        self._create_top_frame(main_frame)
        
        # Middle frame - Conversation history
        self._create_conversation_frame(main_frame)
        
        # Bottom frame - Chat input
        self._create_input_frame(main_frame)
        
        # Loading overlay (initially hidden)
        self._create_loading_overlay()
    
    def _create_top_frame(self, parent):
        """Create top frame with file selection and settings."""
        top_frame = ttk.Frame(parent)
        top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        top_frame.columnconfigure(1, weight=1)
        
        # Load Contract button
        self.load_button = ttk.Button(
            top_frame,
            text="Load Contract",
            command=self._on_load_contract
        )
        self.load_button.grid(row=0, column=0, padx=(0, 10))
        
        # File path label
        self.file_label = ttk.Label(top_frame, text="No contract loaded", foreground="gray")
        self.file_label.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        # Settings button
        self.settings_button = ttk.Button(
            top_frame,
            text="Settings",
            command=self._on_settings
        )
        self.settings_button.grid(row=0, column=2, padx=(5, 0))
        
        # About button
        self.about_button = ttk.Button(
            top_frame,
            text="About",
            command=self._on_about
        )
        self.about_button.grid(row=0, column=3, padx=(5, 0))
    
    def _create_conversation_frame(self, parent):
        """Create conversation history display frame."""
        conv_frame = ttk.LabelFrame(parent, text="Conversation", padding="5")
        conv_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        conv_frame.columnconfigure(0, weight=1)
        conv_frame.rowconfigure(0, weight=1)
        
        # Scrolled text widget for conversation history
        self.conversation_text = scrolledtext.ScrolledText(
            conv_frame,
            wrap=tk.WORD,
            width=80,
            height=25,
            state=tk.DISABLED,
            font=("Segoe UI", 10)
        )
        self.conversation_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text tags for styling
        self.conversation_text.tag_configure("user", foreground="#0066cc", font=("Segoe UI", 10, "bold"))
        self.conversation_text.tag_configure("system", foreground="#006600", font=("Segoe UI", 10))
        self.conversation_text.tag_configure("error", foreground="#cc0000", font=("Segoe UI", 10))
        self.conversation_text.tag_configure("timestamp", foreground="#666666", font=("Segoe UI", 8))
        self.conversation_text.tag_configure("example", foreground="#0066cc", font=("Segoe UI", 9, "italic"))
        
        # Display welcome message with example questions
        self._display_welcome_message()
    
    def _create_input_frame(self, parent):
        """Create chat input frame."""
        input_frame = ttk.Frame(parent)
        input_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        input_frame.columnconfigure(0, weight=1)
        
        # Input text field
        self.input_entry = ttk.Entry(input_frame, font=("Segoe UI", 10))
        self.input_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.input_entry.bind("<Return>", self._on_send)
        
        # Send button
        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            command=self._on_send
        )
        self.send_button.grid(row=0, column=1)
        
        # Initially disable chat input
        self.enable_chat_input(False)
    
    def _create_loading_overlay(self):
        """Create loading indicator overlay."""
        self.loading_frame = tk.Frame(self.root, bg="white", bd=2, relief=tk.RAISED)
        self.loading_label = ttk.Label(
            self.loading_frame,
            text="Loading...",
            font=("Segoe UI", 12)
        )
        self.loading_label.pack(padx=20, pady=20)
        # Initially hidden
        self.loading_frame.place_forget()
    
    def _on_load_contract(self):
        """Handle Load Contract button click."""
        file_path = self.show_file_dialog()
        if file_path:
            self.current_file_path = file_path
            # Display shortened path
            display_path = os.path.basename(file_path)
            self.file_label.config(text=f"Loaded: {display_path}", foreground="black")
    
    def _on_settings(self):
        """Handle Settings button click."""
        # Create settings dialog
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x250")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (settings_window.winfo_width() // 2)
        y = (settings_window.winfo_screenheight() // 2) - (settings_window.winfo_height() // 2)
        settings_window.geometry(f"+{x}+{y}")
        
        # Settings content
        content_frame = ttk.Frame(settings_window, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Pythia model selection
        ttk.Label(content_frame, text="Pythia Model:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        model_var = tk.StringVar(value=self.settings["pythia_model"])
        model_frame = ttk.Frame(content_frame)
        model_frame.pack(anchor=tk.W, pady=(0, 15))
        
        ttk.Radiobutton(
            model_frame,
            text="Pythia-410M (Faster, smaller)",
            variable=model_var,
            value="410M"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            model_frame,
            text="Pythia-1B (More capable)",
            variable=model_var,
            value="1B"
        ).pack(anchor=tk.W)
        
        # OpenAI fallback toggle
        ttk.Label(content_frame, text="OpenAI Fallback:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))
        
        openai_var = tk.BooleanVar(value=self.settings["openai_fallback"])
        ttk.Checkbutton(
            content_frame,
            text="Enable OpenAI fallback for complex queries",
            variable=openai_var
        ).pack(anchor=tk.W, pady=(0, 15))
        
        # Current configuration display
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        ttk.Label(
            content_frame,
            text=f"Current: Pythia-{self.settings['pythia_model']}, OpenAI: {'Enabled' if self.settings['openai_fallback'] else 'Disabled'}",
            foreground="gray"
        ).pack(anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(content_frame)
        button_frame.pack(side=tk.BOTTOM, pady=(10, 0))
        
        def save_settings():
            self.settings["pythia_model"] = model_var.get()
            self.settings["openai_fallback"] = openai_var.get()
            settings_window.destroy()
        
        ttk.Button(button_frame, text="Save", command=save_settings).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.LEFT)
    
    def _on_about(self):
        """Handle About button click."""
        # Create about dialog
        about_window = tk.Toplevel(self.root)
        about_window.title("About Contract Chat UI")
        about_window.geometry("450x350")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        
        # Center the window
        about_window.update_idletasks()
        x = (about_window.winfo_screenwidth() // 2) - (about_window.winfo_width() // 2)
        y = (about_window.winfo_screenheight() // 2) - (about_window.winfo_height() // 2)
        about_window.geometry(f"+{x}+{y}")
        
        # About content
        content_frame = ttk.Frame(about_window, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Application icon/logo (text-based)
        ttk.Label(
            content_frame,
            text="📄💬",
            font=("Segoe UI", 48)
        ).pack(pady=(10, 5))
        
        # Application name
        ttk.Label(
            content_frame,
            text="Contract Chat UI",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 5))
        
        # Version info
        ttk.Label(
            content_frame,
            text="Version 1.0.0",
            font=("Segoe UI", 10)
        ).pack(pady=(0, 15))
        
        # Description
        description = (
            "A conversational interface for exploring contract analysis results.\n\n"
            "Built with Python and Tkinter, powered by Pythia LLM for local\n"
            "natural language processing. Load contract analysis JSON files\n"
            "and ask questions in plain English."
        )
        ttk.Label(
            content_frame,
            text=description,
            font=("Segoe UI", 9),
            justify=tk.CENTER,
            foreground="#555555"
        ).pack(pady=(0, 15))
        
        # Separator
        ttk.Separator(content_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Technology info
        tech_info = (
            "Technologies:\n"
            "• Python with Tkinter GUI\n"
            "• Pythia LLM (EleutherAI)\n"
            "• Optional OpenAI fallback\n"
            "• CPU-only inference (no GPU required)"
        )
        ttk.Label(
            content_frame,
            text=tech_info,
            font=("Segoe UI", 9),
            justify=tk.LEFT,
            foreground="#666666"
        ).pack(pady=(0, 15))
        
        # Close button
        ttk.Button(
            content_frame,
            text="Close",
            command=about_window.destroy
        ).pack(pady=(10, 0))
    
    def _on_send(self, event=None):
        """Handle send button click or Enter key press."""
        query = self.input_entry.get().strip()
        if query and self.chat_enabled:
            try:
                # Check if user is asking for help
                if self._is_help_query(query):
                    self._show_example_questions()
                    self.input_entry.delete(0, tk.END)
                    return
                
                # Display user message
                self.display_message(query, "user")
                
                # Clear input
                self.input_entry.delete(0, tk.END)
                
                # Call query callback
                if self.query_callback:
                    self.query_callback(query)
                    
            except Exception as e:
                # Handle errors during query submission
                error_response = self.error_handler.handle_error(e, "query_submission")
                self.show_error(error_response.message)
    
    def _on_closing(self):
        """Handle window close event."""
        try:
            # Cleanup error handler
            if hasattr(self, 'error_handler'):
                self.error_handler.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.root.destroy()
    
    def show_file_dialog(self) -> Optional[str]:
        """
        Display file selection dialog for JSON files.
        
        Returns:
            Selected file path or None if cancelled
        """
        file_path = filedialog.askopenfilename(
            title="Select Contract Analysis JSON",
            filetypes=[
                ("JSON files", "*.json"),
                ("All files", "*.*")
            ],
            initialdir=os.getcwd()
        )
        return file_path if file_path else None
    
    def display_message(self, message: str, sender: str, source: str = "pythia"):
        """
        Add message to conversation history.
        
        Args:
            message: Message text to display
            sender: "user" or "system"
            source: "pythia" or "openai" for system messages
        """
        try:
            self.conversation_text.config(state=tk.NORMAL)
            
            # Add timestamp and sender
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if sender == "user":
                prefix = f"[{timestamp}] You: "
                self.conversation_text.insert(tk.END, prefix, "user")
                self.conversation_text.insert(tk.END, f"{message}\n\n")
            else:
                # Add source icon
                icon = "💻" if source == "pythia" else "🌐"
                prefix = f"[{timestamp}] {icon} Assistant: "
                self.conversation_text.insert(tk.END, prefix, "system")
                self.conversation_text.insert(tk.END, f"{message}\n\n")
            
            self.conversation_text.config(state=tk.DISABLED)
            self.conversation_text.see(tk.END)
            
        except Exception as e:
            # Handle errors during message display
            error_response = self.error_handler.handle_error(e, "message_display")
            print(f"Error displaying message: {error_response.message}")
    
    def show_error(self, error_message: str):
        """
        Display error message to user.
        
        Args:
            error_message: Error message to display
        """
        try:
            # Show in conversation history
            self.conversation_text.config(state=tk.NORMAL)
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            prefix = f"[{timestamp}] ⚠️ Error: "
            self.conversation_text.insert(tk.END, prefix, "error")
            self.conversation_text.insert(tk.END, f"{error_message}\n\n", "error")
            self.conversation_text.config(state=tk.DISABLED)
            self.conversation_text.see(tk.END)
            
        except Exception as e:
            # If we can't display in conversation, show popup
            print(f"Error displaying error message: {e}")
            
        # Also show as popup for critical errors
        try:
            messagebox.showerror("Error", error_message)
        except Exception as e:
            print(f"Error showing error popup: {e}")
    
    def show_loading(self, message: str = "Loading..."):
        """
        Display loading indicator with message.
        
        Args:
            message: Loading message to display
        """
        self.loading_label.config(text=message)
        
        # Center the loading frame
        self.root.update_idletasks()
        x = (self.root.winfo_width() // 2) - (self.loading_frame.winfo_reqwidth() // 2)
        y = (self.root.winfo_height() // 2) - (self.loading_frame.winfo_reqheight() // 2)
        self.loading_frame.place(x=x, y=y)
    
    def hide_loading(self):
        """Hide loading indicator."""
        self.loading_frame.place_forget()
    
    def enable_chat_input(self, enabled: bool):
        """
        Enable or disable chat input field.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.chat_enabled = enabled
        state = tk.NORMAL if enabled else tk.DISABLED
        self.input_entry.config(state=state)
        self.send_button.config(state=state)
        
        if enabled:
            self.input_entry.focus()
    
    def get_settings(self) -> Dict[str, Any]:
        """
        Get current user settings.
        
        Returns:
            Dictionary with current settings
        """
        return self.settings.copy()
    
    def get_current_file_path(self) -> Optional[str]:
        """
        Get the currently loaded file path.
        
        Returns:
            File path or None if no file loaded
        """
        return self.current_file_path
    
    def set_file_loaded(self, file_path: str):
        """
        Update UI to show file is loaded.
        
        Args:
            file_path: Path to loaded file
        """
        self.current_file_path = file_path
        display_path = os.path.basename(file_path)
        self.file_label.config(text=f"Loaded: {display_path}", foreground="black")

    def show_download_consent_dialog(self, model_size: str, model_info: dict) -> bool:
        """
        Display download consent dialog on first run.
        
        Args:
            model_size: "410M" or "1B"
            model_info: Dictionary with model information (disk_space, ram_required, etc.)
            
        Returns:
            True if user approves download, False otherwise
        """
        message = f"""Pythia-{model_size} model needs to be downloaded.

Model Information:
• Disk Space: {model_info.get('disk_space', 'Unknown')}
• RAM Required: {model_info.get('ram_required', 'Unknown')}
• Load Time: {model_info.get('load_time', 'Unknown')}
• Query Time: {model_info.get('query_time', 'Unknown')}

{model_info.get('description', '')}

The model will be cached in your home directory (~/.contract_chat_ui/models) 
and only needs to be downloaded once.

Do you want to download the model now?"""
        
        result = messagebox.askyesno(
            "Model Download Required",
            message,
            icon='question'
        )
        
        return result
    
    def show_download_progress_dialog(self, model_size: str) -> tk.Toplevel:
        """
        Show download progress dialog.
        
        Args:
            model_size: "410M" or "1B"
            
        Returns:
            Toplevel window with progress bar
        """
        # Create progress dialog
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Downloading Model")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)
        
        # Center the window
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Create widgets
        frame = ttk.Frame(progress_window, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(
            frame,
            text=f"Downloading Pythia-{model_size}",
            font=("Arial", 12, "bold")
        )
        title_label.pack(pady=(0, 10))
        
        # Status label
        status_label = ttk.Label(frame, text="Initializing download...")
        status_label.pack(pady=(0, 10))
        
        # Progress bar
        progress_bar = ttk.Progressbar(
            frame,
            mode='determinate',
            length=350
        )
        progress_bar.pack(pady=(0, 10))
        
        # Store references for updating
        progress_window.status_label = status_label
        progress_window.progress_bar = progress_bar
        
        # Center on parent
        progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (progress_window.winfo_width() // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (progress_window.winfo_height() // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        return progress_window
    
    def update_download_progress(self, progress_window: tk.Toplevel, progress: float, status: str):
        """
        Update download progress dialog.
        
        Args:
            progress_window: Progress dialog window
            progress: Progress value (0.0 to 1.0)
            status: Status message
        """
        if progress_window and progress_window.winfo_exists():
            progress_window.status_label.config(text=status)
            progress_window.progress_bar['value'] = progress * 100
            progress_window.update()
    
    def close_download_progress_dialog(self, progress_window: tk.Toplevel):
        """
        Close download progress dialog.
        
        Args:
            progress_window: Progress dialog window to close
        """
        if progress_window and progress_window.winfo_exists():
            progress_window.destroy()
    
    def show_download_error(self, error_message: str):
        """
        Display download error message.
        
        Args:
            error_message: Error message to display
        """
        message = f"""Failed to download Pythia model.

Error: {error_message}

Please check your internet connection and try again.
You can also try:
• Selecting a different model size in settings
• Restarting the application
• Checking available disk space"""
        
        messagebox.showerror("Download Failed", message)
    
    def _display_welcome_message(self):
        """Display welcome message with example questions on startup."""
        welcome_text = """Welcome to Contract Chat UI!

Load a contract analysis JSON file to get started. Once loaded, you can ask questions about the contract in natural language.

"""
        
        self.conversation_text.config(state=tk.NORMAL)
        self.conversation_text.insert(tk.END, welcome_text, "system")
        self._insert_example_questions()
        self.conversation_text.config(state=tk.DISABLED)
    
    def _show_example_questions(self):
        """Show example questions when user asks for help."""
        self.display_message("Here are some example questions you can ask:", "system", "pythia")
        
        self.conversation_text.config(state=tk.NORMAL)
        self._insert_example_questions()
        self.conversation_text.config(state=tk.DISABLED)
        self.conversation_text.see(tk.END)
    
    def _insert_example_questions(self):
        """Insert example questions into conversation text."""
        examples = self._get_example_questions()
        
        self.conversation_text.insert(tk.END, "Example Questions:\n\n", "system")
        
        for category, questions in examples.items():
            self.conversation_text.insert(tk.END, f"{category}:\n", "system")
            for question in questions:
                self.conversation_text.insert(tk.END, f"  • {question}\n", "example")
            self.conversation_text.insert(tk.END, "\n")
        
        self.conversation_text.insert(tk.END, "Type 'help' or 'examples' anytime to see these questions again.\n\n", "system")
    
    def _get_example_questions(self) -> Dict[str, List[str]]:
        """
        Get example questions organized by category.
        
        Returns:
            Dictionary mapping category names to lists of example questions
        """
        return {
            "Contract Parties": [
                "Who are the parties in this contract?",
                "What is the buyer's name?",
                "Who is the seller?",
            ],
            "Contract Terms": [
                "What are the main terms of this contract?",
                "What are the payment terms?",
                "What is the contract duration?",
                "Are there any termination clauses?",
            ],
            "Risks": [
                "What risks are identified in this contract?",
                "Are there any high-priority risks?",
                "What are the liability risks?",
            ],
            "Dates and Deadlines": [
                "When does this contract start?",
                "What is the contract end date?",
                "Are there any important deadlines?",
            ],
            "Financial Information": [
                "What is the total contract value?",
                "What are the payment amounts?",
                "Are there any penalties or fees?",
            ],
        }
    
    def _is_help_query(self, query: str) -> bool:
        """
        Check if query is asking for help or examples.
        
        Args:
            query: User's query text
            
        Returns:
            True if query is asking for help, False otherwise
        """
        help_keywords = ["help", "example", "examples", "sample", "samples", "what can i ask", "how do i"]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in help_keywords)
