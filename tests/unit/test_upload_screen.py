"""
Unit tests for UploadScreen component.

Tests cover:
- Initial state (analyze button disabled)
- File selection enables analyze button
- Invalid file shows error message
- File info display
- Analyze button handler
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import tkinter as tk
from tkinter import ttk
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.upload_screen import UploadScreen


class TestUploadScreen(unittest.TestCase):
    """Test cases for UploadScreen class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create Tkinter root for testing
        self.root = tk.Tk()
        self.parent = ttk.Frame(self.root)
        
        # Create mock controller
        self.mock_controller = Mock()
        self.mock_controller.contract_uploader = Mock()
        
        # Create upload screen
        self.upload_screen = UploadScreen(self.parent, self.mock_controller)
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass
    
    def test_initial_state_analyze_button_disabled(self):
        """Test that analyze button is initially disabled."""
        # Render the screen
        self.upload_screen.render()
        
        # Verify analyze button is disabled
        self.assertEqual(
            str(self.upload_screen.analyze_button['state']),
            'disabled',
            "Analyze button should be disabled initially"
        )
        
        # Verify no file is selected
        self.assertIsNone(
            self.upload_screen.selected_file_path,
            "No file should be selected initially"
        )
    
    def test_file_selection_enables_analyze_button(self):
        """Test that valid file selection enables analyze button."""
        # Render the screen
        self.upload_screen.render()
        
        # Mock contract uploader validation
        self.mock_controller.contract_uploader.validate_format.return_value = (True, "")
        self.mock_controller.contract_uploader.get_file_info.return_value = {
            'filename': 'test_contract.pdf',
            'file_size_mb': '1.5 MB',
            'page_count': 10
        }
        
        # Simulate file validation
        test_file_path = '/path/to/test_contract.pdf'
        self.upload_screen.validate_file(test_file_path)
        
        # Verify analyze button is enabled
        self.assertEqual(
            str(self.upload_screen.analyze_button['state']),
            'normal',
            "Analyze button should be enabled after valid file selection"
        )
        
        # Verify file path is stored
        self.assertEqual(
            self.upload_screen.selected_file_path,
            test_file_path,
            "Selected file path should be stored"
        )
    
    def test_invalid_file_shows_error_message(self):
        """Test that invalid file shows error message."""
        # Render the screen
        self.upload_screen.render()
        
        # Mock contract uploader validation to return error
        error_message = "Unsupported file format: .txt"
        self.mock_controller.contract_uploader.validate_format.return_value = (False, error_message)
        
        # Simulate file validation
        test_file_path = '/path/to/test_file.txt'
        self.upload_screen.validate_file(test_file_path)
        
        # Verify error is displayed in status label
        status_text = self.upload_screen.status_label['text']
        self.assertIn(
            "Error",
            status_text,
            "Status label should show error message"
        )
        self.assertIn(
            error_message,
            status_text,
            "Status label should contain the specific error message"
        )
        
        # Verify analyze button remains disabled
        self.assertEqual(
            str(self.upload_screen.analyze_button['state']),
            'disabled',
            "Analyze button should remain disabled for invalid file"
        )
        
        # Verify no file is selected
        self.assertIsNone(
            self.upload_screen.selected_file_path,
            "No file should be selected after validation failure"
        )
    
    def test_display_file_info(self):
        """Test that file info is displayed correctly."""
        # Render the screen
        self.upload_screen.render()
        
        # Create test file info
        file_info = {
            'filename': 'contract_2024.pdf',
            'file_size_mb': '2.3 MB',
            'page_count': 25
        }
        
        # Display file info
        self.upload_screen.display_file_info(file_info)
        
        # Verify filename is displayed
        self.assertEqual(
            self.upload_screen.file_name_label['text'],
            'contract_2024.pdf',
            "Filename should be displayed"
        )
        
        # Verify file size and page count are displayed
        size_text = self.upload_screen.file_size_label['text']
        self.assertIn('2.3 MB', size_text, "File size should be displayed")
        self.assertIn('25 pages', size_text, "Page count should be displayed")
    
    def test_display_file_info_without_page_count(self):
        """Test file info display when page count is not available."""
        # Render the screen
        self.upload_screen.render()
        
        # Create test file info without page count
        file_info = {
            'filename': 'contract.docx',
            'file_size_mb': '1.8 MB',
            'page_count': None
        }
        
        # Display file info
        self.upload_screen.display_file_info(file_info)
        
        # Verify filename is displayed
        self.assertEqual(
            self.upload_screen.file_name_label['text'],
            'contract.docx',
            "Filename should be displayed"
        )
        
        # Verify only file size is displayed (no page count)
        size_text = self.upload_screen.file_size_label['text']
        self.assertEqual(size_text, '1.8 MB', "Only file size should be displayed")
    
    def test_analyze_button_triggers_transition(self):
        """Test that analyze button triggers transition to analysis screen."""
        # Render the screen
        self.upload_screen.render()
        
        # Set up valid file selection
        test_file_path = '/path/to/test_contract.pdf'
        self.upload_screen.selected_file_path = test_file_path
        self.upload_screen.analyze_button.config(state=tk.NORMAL)
        
        # Click analyze button
        self.upload_screen.on_analyze_click()
        
        # Verify controller transition method was called
        self.mock_controller.transition_to_analysis.assert_called_once_with(test_file_path)
    
    def test_analyze_button_without_file_shows_error(self):
        """Test that clicking analyze without file selection shows error."""
        # Render the screen
        self.upload_screen.render()
        
        # Ensure no file is selected
        self.upload_screen.selected_file_path = None
        
        # Try to click analyze button
        self.upload_screen.on_analyze_click()
        
        # Verify error is displayed
        status_text = self.upload_screen.status_label['text']
        self.assertIn(
            "Error",
            status_text,
            "Status label should show error message"
        )
        
        # Verify controller transition was NOT called
        self.mock_controller.transition_to_analysis.assert_not_called()
    
    def test_clear_file_selection(self):
        """Test that clearing file selection resets UI."""
        # Render the screen
        self.upload_screen.render()
        
        # Set up file selection
        self.upload_screen.selected_file_path = '/path/to/file.pdf'
        self.upload_screen.file_info = {'filename': 'file.pdf'}
        self.upload_screen.analyze_button.config(state=tk.NORMAL)
        
        # Clear file selection
        self.upload_screen.clear_file_selection()
        
        # Verify state is reset
        self.assertIsNone(self.upload_screen.selected_file_path)
        self.assertIsNone(self.upload_screen.file_info)
        self.assertEqual(str(self.upload_screen.analyze_button['state']), 'disabled')
        self.assertEqual(self.upload_screen.file_name_label['text'], 'No file selected')
    
    def test_render_creates_all_widgets(self):
        """Test that render creates all required widgets."""
        # Render the screen
        self.upload_screen.render()
        
        # Verify all widgets are created
        self.assertIsNotNone(self.upload_screen.main_frame, "Main frame should be created")
        self.assertIsNotNone(self.upload_screen.title_label, "Title label should be created")
        self.assertIsNotNone(self.upload_screen.file_select_button, "File select button should be created")
        self.assertIsNotNone(self.upload_screen.file_info_frame, "File info frame should be created")
        self.assertIsNotNone(self.upload_screen.file_name_label, "File name label should be created")
        self.assertIsNotNone(self.upload_screen.file_size_label, "File size label should be created")
        self.assertIsNotNone(self.upload_screen.analyze_button, "Analyze button should be created")
        self.assertIsNotNone(self.upload_screen.status_label, "Status label should be created")
    
    @patch('src.upload_screen.filedialog.askopenfilename')
    def test_on_file_select_opens_dialog(self, mock_dialog):
        """Test that on_file_select opens file dialog."""
        # Render the screen
        self.upload_screen.render()
        
        # Mock file dialog to return a file path
        test_file_path = '/path/to/contract.pdf'
        mock_dialog.return_value = test_file_path
        
        # Mock validation
        self.mock_controller.contract_uploader.validate_format.return_value = (True, "")
        self.mock_controller.contract_uploader.get_file_info.return_value = {
            'filename': 'contract.pdf',
            'file_size_mb': '1.0 MB',
            'page_count': 5
        }
        
        # Call on_file_select
        self.upload_screen.on_file_select()
        
        # Verify file dialog was opened
        mock_dialog.assert_called_once()
        
        # Verify file was validated
        self.mock_controller.contract_uploader.validate_format.assert_called_once_with(test_file_path)
    
    @patch('src.upload_screen.filedialog.askopenfilename')
    def test_on_file_select_cancelled(self, mock_dialog):
        """Test that cancelling file dialog doesn't cause errors."""
        # Render the screen
        self.upload_screen.render()
        
        # Mock file dialog to return empty string (cancelled)
        mock_dialog.return_value = ""
        
        # Call on_file_select
        self.upload_screen.on_file_select()
        
        # Verify validation was not called
        self.mock_controller.contract_uploader.validate_format.assert_not_called()
        
        # Verify no file is selected
        self.assertIsNone(self.upload_screen.selected_file_path)


if __name__ == '__main__':
    unittest.main()
