"""
Unit tests for ChatScreen module.

Tests the chat screen UI components, query submission, message display,
and navigation functionality.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import tkinter as tk
from datetime import datetime
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.chat_screen import ChatScreen


class TestChatScreen(unittest.TestCase):
    """Test cases for ChatScreen class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create Tkinter root
        self.root = tk.Tk()
        self.parent = tk.Frame(self.root)
        
        # Create mock controller
        self.mock_controller = Mock()
        self.mock_controller.query_engine = Mock()
        
        # Create ChatScreen instance
        self.chat_screen = ChatScreen(self.parent, self.mock_controller)
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass
    
    def test_initialization(self):
        """Test ChatScreen initialization."""
        self.assertIsNotNone(self.chat_screen)
        self.assertEqual(self.chat_screen.parent, self.parent)
        self.assertEqual(self.chat_screen.controller, self.mock_controller)
        self.assertIsNone(self.chat_screen.analysis_result)
        self.assertEqual(self.chat_screen.contract_filename, "Unknown Contract")
        self.assertEqual(self.chat_screen.conversation_history, [])
        self.assertFalse(self.chat_screen.is_processing)
    
    def test_render_creates_ui_components(self):
        """Test that render() creates all required UI components."""
        self.chat_screen.render()
        
        # Check that UI components are created
        self.assertIsNotNone(self.chat_screen.main_frame)
        self.assertIsNotNone(self.chat_screen.title_label)
        self.assertIsNotNone(self.chat_screen.conversation_text)
        self.assertIsNotNone(self.chat_screen.query_input)
        self.assertIsNotNone(self.chat_screen.send_button)
        self.assertIsNotNone(self.chat_screen.new_analysis_button)
        self.assertIsNotNone(self.chat_screen.thinking_label)
    
    def test_send_button_initially_disabled(self):
        """Test that send button is initially disabled."""
        self.chat_screen.render()
        
        # Send button should be disabled when input is empty
        self.assertEqual(str(self.chat_screen.send_button['state']), 'disabled')
    
    def test_send_button_enabled_with_input(self):
        """Test that send button is enabled when input is not empty."""
        self.chat_screen.render()
        
        # Add text to input field
        self.chat_screen.query_input.insert("1.0", "Test query")
        
        # Trigger input change event
        self.chat_screen._on_input_change()
        
        # Send button should be enabled
        self.assertEqual(str(self.chat_screen.send_button['state']), 'normal')
    
    def test_send_button_disabled_when_empty(self):
        """Test that send button is disabled when input is cleared."""
        self.chat_screen.render()
        
        # Add text then clear it
        self.chat_screen.query_input.insert("1.0", "Test query")
        self.chat_screen._on_input_change()
        self.chat_screen.query_input.delete("1.0", tk.END)
        self.chat_screen._on_input_change()
        
        # Send button should be disabled
        self.assertEqual(str(self.chat_screen.send_button['state']), 'disabled')
    
    def test_load_analysis_updates_title(self):
        """Test that load_analysis() updates the title with contract filename."""
        self.chat_screen.render()
        
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {
                'filename': 'test_contract.pdf',
                'analyzed_at': '2024-01-15T10:30:00Z',
                'page_count': 10
            },
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        # Load analysis
        self.chat_screen.load_analysis(analysis_result)
        
        # Check that title is updated
        self.assertIn('test_contract.pdf', self.chat_screen.title_label['text'])
        self.assertEqual(self.chat_screen.contract_filename, 'test_contract.pdf')
    
    def test_load_analysis_displays_welcome_message(self):
        """Test that load_analysis() displays a welcome message."""
        self.chat_screen.render()
        
        # Create mock analysis result
        analysis_result = {
            'contract_metadata': {
                'filename': 'test_contract.pdf'
            },
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        # Load analysis
        self.chat_screen.load_analysis(analysis_result)
        
        # Check that conversation history has welcome message
        self.assertEqual(len(self.chat_screen.conversation_history), 1)
        self.assertEqual(self.chat_screen.conversation_history[0]['sender'], 'assistant')
        self.assertIn('ready for querying', self.chat_screen.conversation_history[0]['message'])
    
    def test_display_message_adds_to_history(self):
        """Test that display_message() adds message to conversation history."""
        self.chat_screen.render()
        
        # Display a message
        self.chat_screen.display_message("user", "Test question")
        
        # Check that message is in history
        self.assertEqual(len(self.chat_screen.conversation_history), 1)
        self.assertEqual(self.chat_screen.conversation_history[0]['sender'], 'user')
        self.assertEqual(self.chat_screen.conversation_history[0]['message'], 'Test question')
        self.assertIsInstance(self.chat_screen.conversation_history[0]['timestamp'], datetime)
    
    def test_display_message_updates_text_widget(self):
        """Test that display_message() updates the conversation text widget."""
        self.chat_screen.render()
        
        # Display a message
        self.chat_screen.display_message("user", "Test question")
        
        # Get text from widget
        text_content = self.chat_screen.conversation_text.get("1.0", tk.END)
        
        # Check that message appears in text widget
        self.assertIn("You:", text_content)
        self.assertIn("Test question", text_content)
    
    def test_on_query_submit_clears_input(self):
        """Test that on_query_submit() clears the input field."""
        self.chat_screen.render()
        
        # Add text to input
        self.chat_screen.query_input.insert("1.0", "Test query")
        
        # Submit query
        with patch.object(self.chat_screen, '_process_query'):
            self.chat_screen.on_query_submit()
        
        # Check that input is cleared
        input_text = self.chat_screen.query_input.get("1.0", tk.END).strip()
        self.assertEqual(input_text, "")
    
    def test_on_query_submit_displays_query(self):
        """Test that on_query_submit() displays the query in conversation history."""
        self.chat_screen.render()
        
        # Add text to input
        self.chat_screen.query_input.insert("1.0", "Test query")
        
        # Submit query
        with patch.object(self.chat_screen, '_process_query'):
            self.chat_screen.on_query_submit()
        
        # Check that query is in history
        self.assertEqual(len(self.chat_screen.conversation_history), 1)
        self.assertEqual(self.chat_screen.conversation_history[0]['sender'], 'user')
        self.assertEqual(self.chat_screen.conversation_history[0]['message'], 'Test query')
    
    def test_on_query_submit_disables_send_button(self):
        """Test that on_query_submit() disables send button during processing."""
        self.chat_screen.render()
        
        # Add text to input and enable button
        self.chat_screen.query_input.insert("1.0", "Test query")
        self.chat_screen._on_input_change()
        
        # Submit query
        with patch.object(self.chat_screen, '_process_query'):
            self.chat_screen.on_query_submit()
        
        # Check that send button is disabled
        self.assertEqual(str(self.chat_screen.send_button['state']), 'disabled')
    
    def test_on_query_submit_ignores_empty_query(self):
        """Test that on_query_submit() ignores empty queries."""
        self.chat_screen.render()
        
        # Submit empty query
        with patch.object(self.chat_screen, '_process_query') as mock_process:
            self.chat_screen.on_query_submit()
        
        # Check that _process_query was not called
        mock_process.assert_not_called()
        
        # Check that no message was added to history
        self.assertEqual(len(self.chat_screen.conversation_history), 0)
    
    def test_show_thinking_indicator(self):
        """Test that show_thinking_indicator() displays thinking message."""
        self.chat_screen.render()
        
        # Show thinking indicator
        self.chat_screen.show_thinking_indicator()
        
        # Check that thinking label has text
        self.assertIn("Thinking", self.chat_screen.thinking_label['text'])
    
    def test_hide_thinking_indicator(self):
        """Test that hide_thinking_indicator() clears thinking message."""
        self.chat_screen.render()
        
        # Show then hide thinking indicator
        self.chat_screen.show_thinking_indicator()
        self.chat_screen.hide_thinking_indicator()
        
        # Check that thinking label is empty
        self.assertEqual(self.chat_screen.thinking_label['text'], "")
    
    @patch('tkinter.messagebox')
    def test_on_new_analysis_click_confirms_with_user(self, mock_messagebox):
        """Test that on_new_analysis_click() confirms with user if conversation exists."""
        self.chat_screen.render()
        
        # Add messages to conversation history
        self.chat_screen.conversation_history = [
            {'sender': 'assistant', 'message': 'Welcome'},
            {'sender': 'user', 'message': 'Test query'}
        ]
        
        # Mock user clicking "No"
        mock_messagebox.askyesno.return_value = False
        
        # Click new analysis button
        self.chat_screen.on_new_analysis_click()
        
        # Check that confirmation dialog was shown
        mock_messagebox.askyesno.assert_called_once()
        
        # Check that transition was not called
        self.mock_controller.transition_to_upload.assert_not_called()
    
    @patch('tkinter.messagebox')
    def test_on_new_analysis_click_clears_history(self, mock_messagebox):
        """Test that on_new_analysis_click() clears conversation history."""
        self.chat_screen.render()
        
        # Add messages to conversation history
        self.chat_screen.conversation_history = [
            {'sender': 'assistant', 'message': 'Welcome'},
            {'sender': 'user', 'message': 'Test query'}
        ]
        
        # Mock user clicking "Yes"
        mock_messagebox.askyesno.return_value = True
        
        # Click new analysis button
        self.chat_screen.on_new_analysis_click()
        
        # Check that conversation history is cleared
        self.assertEqual(len(self.chat_screen.conversation_history), 0)
    
    @patch('tkinter.messagebox')
    def test_on_new_analysis_click_transitions_to_upload(self, mock_messagebox):
        """Test that on_new_analysis_click() triggers transition to upload screen."""
        self.chat_screen.render()
        
        # Add messages to conversation history
        self.chat_screen.conversation_history = [
            {'sender': 'assistant', 'message': 'Welcome'},
            {'sender': 'user', 'message': 'Test query'}
        ]
        
        # Mock user clicking "Yes"
        mock_messagebox.askyesno.return_value = True
        
        # Click new analysis button
        self.chat_screen.on_new_analysis_click()
        
        # Check that transition was called
        self.mock_controller.transition_to_upload.assert_called_once()
    
    def test_conversation_history_completeness(self):
        """Test that all messages are displayed in chronological order."""
        self.chat_screen.render()
        
        # Display multiple messages
        self.chat_screen.display_message("user", "First question")
        self.chat_screen.display_message("assistant", "First answer")
        self.chat_screen.display_message("user", "Second question")
        self.chat_screen.display_message("assistant", "Second answer")
        
        # Check that all messages are in history
        self.assertEqual(len(self.chat_screen.conversation_history), 4)
        
        # Check chronological order
        self.assertEqual(self.chat_screen.conversation_history[0]['message'], "First question")
        self.assertEqual(self.chat_screen.conversation_history[1]['message'], "First answer")
        self.assertEqual(self.chat_screen.conversation_history[2]['message'], "Second question")
        self.assertEqual(self.chat_screen.conversation_history[3]['message'], "Second answer")


if __name__ == '__main__':
    unittest.main()
