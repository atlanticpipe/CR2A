"""
Chat Screen Module

Provides interactive chat interface for querying analyzed contracts in the Unified CR2A Application.
"""

import logging
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Optional, Dict, Any
import threading
from datetime import datetime
from src.ui_styles import UIStyles


logger = logging.getLogger(__name__)


class ChatScreen:
    """
    Chat screen for interactive contract querying.
    
    This screen provides:
    - Scrollable conversation history text area
    - Multi-line query input field
    - Send button
    - "New Analysis" button
    - Contract filename display in title
    
    Memory optimizations:
    - Limits conversation history to MAX_HISTORY_MESSAGES
    - Clears old messages when limit is reached
    - Provides method to clear all data when transitioning away
    """
    
    # Maximum number of messages to keep in conversation history
    MAX_HISTORY_MESSAGES = 50  # 25 exchanges (user + assistant pairs)
    
    def __init__(self, parent: tk.Frame, controller):
        """
        Initialize chat screen UI components.
        
        Args:
            parent: Parent Tkinter frame
            controller: ApplicationController instance
        """
        self.parent = parent
        self.controller = controller
        
        # State variables
        self.analysis_result: Optional[Dict[str, Any]] = None
        self.contract_filename: str = "Unknown Contract"
        self.conversation_history: list = []
        self.is_processing = False
        
        # UI components (will be created in render())
        self.main_frame = None
        self.title_label = None
        self.conversation_text = None
        self.input_frame = None
        self.query_input = None
        self.send_button = None
        self.new_analysis_button = None
        self.thinking_label = None
        
        logger.debug("ChatScreen initialized")
    
    def render(self) -> None:
        """Display chat screen widgets."""
        logger.info("Rendering chat screen")
        
        # Clear parent frame
        for widget in self.parent.winfo_children():
            widget.destroy()
        
        # Create main frame with consistent padding
        self.main_frame = ttk.Frame(self.parent, padding=UIStyles.get_frame_padding())
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=0)  # Title
        self.main_frame.rowconfigure(1, weight=1)  # Conversation history
        self.main_frame.rowconfigure(2, weight=0)  # Thinking indicator
        self.main_frame.rowconfigure(3, weight=0)  # Input area
        self.main_frame.rowconfigure(4, weight=0)  # Buttons
        
        # Title with contract filename and consistent styling
        self.title_label = ttk.Label(
            self.main_frame,
            text=f"Contract Query - {self.contract_filename}",
            font=UIStyles.get_subtitle_font(),
            anchor=tk.W
        )
        self.title_label.grid(row=0, column=0, pady=(0, UIStyles.PADDING_MEDIUM), sticky=(tk.W, tk.E))
        
        # Conversation history with consistent styling (scrollable text area)
        history_frame = ttk.LabelFrame(
            self.main_frame,
            text="Conversation History",
            padding=UIStyles.get_labelframe_padding()
        )
        history_frame.grid(row=1, column=0, pady=(0, UIStyles.PADDING_MEDIUM), sticky=(tk.N, tk.S, tk.E, tk.W))
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        # Create scrolled text widget for conversation with consistent styling
        self.conversation_text = scrolledtext.ScrolledText(
            history_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=UIStyles.get_normal_font(),
            state=tk.DISABLED,  # Read-only
            bg=UIStyles.BACKGROUND_COLOR,
            relief=tk.FLAT,
            borderwidth=0
        )
        self.conversation_text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        
        # Configure text tags for styling with consistent colors
        self.conversation_text.tag_config(
            "user",
            foreground=UIStyles.PRIMARY_COLOR,
            font=(UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_NORMAL, UIStyles.FONT_WEIGHT_BOLD)
        )
        self.conversation_text.tag_config(
            "assistant",
            foreground=UIStyles.SECONDARY_COLOR,
            font=(UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_NORMAL, UIStyles.FONT_WEIGHT_BOLD)
        )
        self.conversation_text.tag_config(
            "timestamp",
            foreground=UIStyles.TEXT_SECONDARY,
            font=UIStyles.get_tiny_font()
        )
        self.conversation_text.tag_config(
            "message",
            foreground=UIStyles.TEXT_PRIMARY,
            font=UIStyles.get_normal_font()
        )
        
        # Thinking indicator with consistent styling (initially hidden)
        self.thinking_label = ttk.Label(
            self.main_frame,
            text="",
            font=(UIStyles.FONT_FAMILY, UIStyles.FONT_SIZE_SMALL, UIStyles.FONT_WEIGHT_ITALIC),
            foreground=UIStyles.TEXT_SECONDARY
        )
        self.thinking_label.grid(row=2, column=0, pady=(0, UIStyles.PADDING_SMALL), sticky=tk.W)
        
        # Query input area with consistent styling
        self.input_frame = ttk.LabelFrame(
            self.main_frame,
            text="Your Question",
            padding=UIStyles.get_labelframe_padding()
        )
        self.input_frame.grid(row=3, column=0, pady=(0, UIStyles.PADDING_MEDIUM), sticky=(tk.E, tk.W))
        self.input_frame.columnconfigure(0, weight=1)
        self.input_frame.rowconfigure(0, weight=1)
        
        # Multi-line query input field with consistent styling
        self.query_input = tk.Text(
            self.input_frame,
            wrap=tk.WORD,
            width=80,
            height=3,
            font=UIStyles.get_normal_font(),
            relief=tk.SOLID,
            borderwidth=1
        )
        self.query_input.grid(row=0, column=0, sticky=(tk.E, tk.W))
        
        # Bind events for input field
        self.query_input.bind('<KeyRelease>', self._on_input_change)
        self.query_input.bind('<Return>', self._on_enter_key)
        self.query_input.bind('<Escape>', self._on_escape_key)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.main_frame)
        buttons_frame.grid(row=4, column=0, sticky=(tk.E, tk.W))
        buttons_frame.columnconfigure(0, weight=0)
        buttons_frame.columnconfigure(1, weight=0)
        buttons_frame.columnconfigure(2, weight=1)
        buttons_frame.columnconfigure(3, weight=0)
        
        # Settings button with consistent styling (left side)
        button_config = UIStyles.get_button_config("medium")
        settings_button = ttk.Button(
            buttons_frame,
            text="⚙ Settings",
            command=self.on_settings_click,
            width=12
        )
        settings_button.grid(row=0, column=0, sticky=tk.W)
        
        # New Analysis button with consistent styling (left side)
        self.new_analysis_button = ttk.Button(
            buttons_frame,
            text="New Analysis",
            command=self.on_new_analysis_click,
            **button_config
        )
        self.new_analysis_button.grid(row=0, column=1, padx=(UIStyles.PADDING_MEDIUM, 0), sticky=tk.W)
        
        # Send button with consistent styling (right side, initially disabled)
        self.send_button = ttk.Button(
            buttons_frame,
            text="Send",
            command=self.on_query_submit,
            state=tk.DISABLED,
            **button_config
        )
        self.send_button.grid(row=0, column=3, padx=(UIStyles.PADDING_MEDIUM, 0), sticky=tk.E)
        
        logger.info("Chat screen rendered successfully")
    
    def _on_input_change(self, event=None) -> None:
        """
        Handle input field changes to enable/disable send button.
        
        Args:
            event: Tkinter event (optional)
        """
        # Only update if widgets exist
        if not self.query_input or not self.send_button:
            return
        
        # Get input text
        input_text = self.query_input.get("1.0", tk.END).strip()
        
        # Enable send button only if input is not empty
        if input_text and not self.is_processing:
            self.send_button.config(state=tk.NORMAL)
        else:
            self.send_button.config(state=tk.DISABLED)
    
    def _on_enter_key(self, event) -> str:
        """
        Handle Enter key press in input field.
        
        Args:
            event: Tkinter event
            
        Returns:
            "break" to prevent default behavior
        """
        # Check if Shift+Enter (allow newline)
        if event.state & 0x1:  # Shift key
            return None  # Allow default behavior (insert newline)
        
        # Enter without Shift - submit query
        if self.send_button['state'] == tk.NORMAL:
            self.on_query_submit()
        
        return "break"  # Prevent default behavior
    
    def _on_escape_key(self, event) -> str:
        """
        Handle Escape key press in input field.
        
        Clears the input field when Escape is pressed.
        
        Args:
            event: Tkinter event
            
        Returns:
            "break" to prevent default behavior
        """
        # Clear the input field
        if self.query_input:
            self.query_input.delete("1.0", tk.END)
            # Update send button state
            self._on_input_change()
        
        return "break"  # Prevent default behavior
    
    def load_analysis(self, analysis_result: Dict[str, Any]) -> None:
        """
        Load analysis result for querying.
        
        Args:
            analysis_result: Analysis result dictionary from OpenAI
        """
        logger.info("Loading analysis result into chat screen")
        
        self.analysis_result = analysis_result
        
        # Extract contract filename from metadata
        metadata = analysis_result.get('contract_metadata', {})
        self.contract_filename = metadata.get('filename', 'Unknown Contract')
        
        # Update title with filename
        if self.title_label:
            self.title_label.config(text=f"Contract Query - {self.contract_filename}")
        
        # Clear conversation history
        self.conversation_history = []
        
        # Display welcome message
        welcome_msg = f"Contract '{self.contract_filename}' has been analyzed and is ready for querying. Ask me anything about the contract!"
        self.display_message("assistant", welcome_msg)
        
        logger.info(f"Analysis loaded: {self.contract_filename}")
    
    def on_query_submit(self) -> None:
        """
        Handle query submission.
        
        Gets query text from input field, displays it in conversation history,
        clears the input field, and processes the query.
        """
        logger.info("Query submission initiated")
        
        # Get query text
        query_text = self.query_input.get("1.0", tk.END).strip()
        
        if not query_text:
            logger.warning("Empty query submitted")
            return
        
        # Display user query in conversation history
        self.display_message("user", query_text)
        
        # Clear input field
        self.query_input.delete("1.0", tk.END)
        
        # Disable send button during processing
        self.send_button.config(state=tk.DISABLED)
        
        # Process query (will be implemented in subtask 12.3)
        self._process_query(query_text)
        
        logger.info(f"Query submitted: {query_text[:50]}...")
    
    def display_message(self, sender: str, message: str) -> None:
        """
        Add message to conversation history with memory management.
        
        Implements memory optimization by:
        - Limiting history to MAX_HISTORY_MESSAGES
        - Removing oldest messages when limit is reached
        - Clearing old messages from UI display
        
        Args:
            sender: "user" or "assistant"
            message: Message text to display
        """
        logger.debug(f"Displaying message from {sender}")
        
        # Store in conversation history
        timestamp = datetime.now()
        self.conversation_history.append({
            'sender': sender,
            'message': message,
            'timestamp': timestamp
        })
        
        # Enforce history limit to manage memory
        if len(self.conversation_history) > self.MAX_HISTORY_MESSAGES:
            # Remove oldest messages
            messages_to_remove = len(self.conversation_history) - self.MAX_HISTORY_MESSAGES
            self.conversation_history = self.conversation_history[messages_to_remove:]
            
            logger.info(f"Conversation history limit reached, removed {messages_to_remove} old messages")
            
            # Rebuild conversation display from remaining history
            if self.conversation_text:
                self._rebuild_conversation_display()
                return
        
        # Only update UI if conversation_text widget exists
        if not self.conversation_text:
            return
        
        # Enable text widget for editing
        self.conversation_text.config(state=tk.NORMAL)
        
        # Add timestamp
        time_str = timestamp.strftime("%H:%M:%S")
        self.conversation_text.insert(tk.END, f"[{time_str}] ", "timestamp")
        
        # Add sender label
        if sender == "user":
            self.conversation_text.insert(tk.END, "You: ", "user")
        else:
            self.conversation_text.insert(tk.END, "Assistant: ", "assistant")
        
        # Add message text
        self.conversation_text.insert(tk.END, f"{message}\n\n", "message")
        
        # Disable text widget (read-only)
        self.conversation_text.config(state=tk.DISABLED)
        
        # Auto-scroll to bottom
        self.conversation_text.see(tk.END)
        
        logger.debug(f"Message displayed from {sender}")
    
    def _rebuild_conversation_display(self) -> None:
        """
        Rebuild conversation display from current history.
        
        Used when history is trimmed to remove old messages from UI.
        """
        if not self.conversation_text:
            return
        
        logger.debug("Rebuilding conversation display")
        
        # Enable text widget for editing
        self.conversation_text.config(state=tk.NORMAL)
        
        # Clear all text
        self.conversation_text.delete("1.0", tk.END)
        
        # Re-add all messages from history
        for msg_data in self.conversation_history:
            sender = msg_data['sender']
            message = msg_data['message']
            timestamp = msg_data['timestamp']
            
            # Add timestamp
            time_str = timestamp.strftime("%H:%M:%S")
            self.conversation_text.insert(tk.END, f"[{time_str}] ", "timestamp")
            
            # Add sender label
            if sender == "user":
                self.conversation_text.insert(tk.END, "You: ", "user")
            else:
                self.conversation_text.insert(tk.END, "Assistant: ", "assistant")
            
            # Add message text
            self.conversation_text.insert(tk.END, f"{message}\n\n", "message")
        
        # Disable text widget (read-only)
        self.conversation_text.config(state=tk.DISABLED)
        
        # Auto-scroll to bottom
        self.conversation_text.see(tk.END)
        
        logger.debug("Conversation display rebuilt")
    
    def _process_query(self, query_text: str) -> None:
        """
        Process query in background thread.
        
        Args:
            query_text: User's query text
        """
        logger.info("Starting query processing")
        
        # Set processing flag
        self.is_processing = True
        
        # Show thinking indicator
        self.show_thinking_indicator()
        
        # Process query in background thread
        query_thread = threading.Thread(
            target=self._run_query_processing,
            args=(query_text,),
            daemon=True
        )
        query_thread.start()
    
    def _run_query_processing(self, query_text: str) -> None:
        """
        Run query processing in background thread.
        
        Args:
            query_text: User's query text
        """
        try:
            logger.debug("Query processing thread running")
            
            # Check if query engine is available
            if not self.controller.query_engine:
                error_msg = "Query engine not initialized. Please check your OpenAI API settings."
                logger.error(error_msg)
                self.parent.after(0, lambda: self._on_query_error(error_msg))
                return
            
            # Check if analysis result is loaded
            if not self.analysis_result:
                error_msg = "No analysis result loaded. Please analyze a contract first."
                logger.error(error_msg)
                self.parent.after(0, lambda: self._on_query_error(error_msg))
                return
            
            # Process query using query engine
            response = self.controller.query_engine.process_query(
                query=query_text,
                analysis_result=self.analysis_result
            )
            
            # Call completion handler on main thread
            self.parent.after(0, lambda: self._on_query_complete(response))
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}", exc_info=True)
            # Call error handler on main thread
            self.parent.after(0, lambda: self._on_query_error(str(e)))
    
    def _on_query_complete(self, response: str) -> None:
        """
        Handle successful query completion.
        
        Args:
            response: Generated response text
        """
        logger.info("Query processing completed successfully")
        
        # Hide thinking indicator
        self.hide_thinking_indicator()
        
        # Display response in conversation history
        self.display_message("assistant", response)
        
        # Reset processing flag
        self.is_processing = False
        
        # Re-enable send button if input is not empty
        self._on_input_change()
    
    def _on_query_error(self, error_message: str) -> None:
        """
        Handle query processing error.
        
        Args:
            error_message: Error message to display
        """
        logger.error(f"Query error: {error_message}")
        
        # Hide thinking indicator
        self.hide_thinking_indicator()
        
        # Display error message in conversation history
        error_response = f"I encountered an error processing your question: {error_message}"
        self.display_message("assistant", error_response)
        
        # Reset processing flag
        self.is_processing = False
        
        # Re-enable send button if input is not empty
        self._on_input_change()
    
    def show_thinking_indicator(self) -> None:
        """Display 'thinking' indicator during query processing."""
        logger.debug("Showing thinking indicator")
        if self.thinking_label:
            self.thinking_label.config(text="Thinking...")
            self.parent.update_idletasks()
    
    def hide_thinking_indicator(self) -> None:
        """Hide 'thinking' indicator."""
        logger.debug("Hiding thinking indicator")
        if self.thinking_label:
            self.thinking_label.config(text="")
            self.parent.update_idletasks()
    
    def on_new_analysis_click(self) -> None:
        """
        Handle "New Analysis" button click.
        
        Triggers transition back to upload screen and clears conversation history.
        """
        logger.info("New Analysis button clicked")
        
        # Confirm with user if there's an active conversation
        if len(self.conversation_history) > 1:  # More than just welcome message
            from tkinter import messagebox
            
            result = messagebox.askyesno(
                "New Analysis",
                "Starting a new analysis will clear the current conversation. Continue?",
                icon='question'
            )
            
            if not result:
                logger.info("User cancelled new analysis")
                return
        
        # Clear all data to free memory
        self.clear_data()
        
        # Trigger transition back to upload screen
        logger.info("Transitioning back to upload screen")
        self.controller.transition_to_upload()
    
    def on_settings_click(self) -> None:
        """
        Handle settings button click.
        
        Opens the settings dialog for API key configuration.
        """
        logger.info("Settings button clicked from chat screen")
        
        try:
            # Open settings dialog through controller
            self.controller.open_settings_dialog()
            
        except Exception as e:
            logger.error(f"Error opening settings: {e}", exc_info=True)
            from tkinter import messagebox
            messagebox.showerror(
                "Error",
                f"Failed to open settings: {str(e)}",
                parent=self.parent
            )
        
        logger.info("Conversation history cleared, returned to upload screen")
    
    def clear_data(self) -> None:
        """
        Clear all data to free memory when transitioning away from chat screen.
        
        This method should be called when:
        - User clicks "New Analysis" button
        - Application transitions away from chat screen
        - Application needs to free memory
        
        Clears:
        - Conversation history
        - Analysis result
        - Conversation text widget content
        - Input field content
        """
        logger.info("Clearing chat screen data to free memory")
        
        # Clear conversation history
        self.conversation_history.clear()
        
        # Clear conversation text widget
        if self.conversation_text:
            self.conversation_text.config(state=tk.NORMAL)
            self.conversation_text.delete("1.0", tk.END)
            self.conversation_text.config(state=tk.DISABLED)
        
        # Clear input field
        if self.query_input:
            self.query_input.delete("1.0", tk.END)
        
        # Clear analysis result (can be large)
        self.analysis_result = None
        
        # Reset state
        self.is_processing = False
        self.contract_filename = "Unknown Contract"
        
        logger.info("Chat screen data cleared")
