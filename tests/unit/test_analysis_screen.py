"""
Unit tests for AnalysisScreen module.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import tkinter as tk
from src.analysis_screen import AnalysisScreen
from src.application_controller import ApplicationController, AppState


class TestAnalysisScreen(unittest.TestCase):
    """Test cases for AnalysisScreen class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.parent = tk.Frame(self.root)
        self.controller = Mock(spec=ApplicationController)
        self.screen = AnalysisScreen(self.parent, self.controller)
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass
    
    def test_initialization(self):
        """Test AnalysisScreen initialization."""
        self.assertEqual(self.screen.parent, self.parent)
        self.assertEqual(self.screen.controller, self.controller)
        self.assertIsNone(self.screen.file_path)
        self.assertIsNone(self.screen.analysis_thread)
        self.assertFalse(self.screen.is_analyzing)
        self.assertIsNone(self.screen.start_time)
    
    def test_render_creates_ui_components(self):
        """Test that render() creates all required UI components."""
        self.screen.render()
        
        # Verify main components exist
        self.assertIsNotNone(self.screen.main_frame)
        self.assertIsNotNone(self.screen.title_label)
        self.assertIsNotNone(self.screen.progress_bar)
        self.assertIsNotNone(self.screen.status_label)
        self.assertIsNotNone(self.screen.time_label)
        self.assertIsNotNone(self.screen.cancel_button)
    
    def test_render_sets_initial_text(self):
        """Test that render() sets initial text values."""
        self.screen.render()
        
        # Check title
        self.assertEqual(self.screen.title_label.cget('text'), "Analyzing Contract...")
        
        # Check initial status
        self.assertEqual(self.screen.status_label.cget('text'), "Initializing analysis...")
        
        # Check time label is empty
        self.assertEqual(self.screen.time_label.cget('text'), "")
        
        # Check cancel button is disabled
        self.assertEqual(str(self.screen.cancel_button.cget('state')), 'disabled')
    
    def test_render_clears_previous_widgets(self):
        """Test that render() clears previous widgets."""
        # Create a widget in parent
        old_widget = tk.Label(self.parent, text="Old widget")
        old_widget.pack()
        
        # Get initial widget count
        initial_count = len(self.parent.winfo_children())
        self.assertGreater(initial_count, 0)
        
        # Render screen
        self.screen.render()
        
        # After render, there should be only the main_frame
        final_count = len(self.parent.winfo_children())
        self.assertEqual(final_count, 1)  # Only main_frame should exist
    
    def test_update_progress_updates_ui(self):
        """Test that update_progress() updates progress bar and status."""
        self.screen.render()
        
        # Update progress
        self.screen.update_progress("Extracting text...", 25)
        
        # Verify updates
        self.assertEqual(self.screen.progress_bar['value'], 25)
        self.assertEqual(self.screen.status_label.cget('text'), "Extracting text...")
    
    def test_update_progress_shows_time_after_10_seconds(self):
        """Test that update_progress() shows estimated time after 10 seconds."""
        self.screen.render()
        
        # Mock start time to 15 seconds ago
        import time
        self.screen.start_time = time.time() - 15
        
        # Update progress to 50%
        self.screen.update_progress("Analyzing...", 50)
        
        # Time label should have content
        time_text = self.screen.time_label.cget('text')
        self.assertIn("Estimated time remaining", time_text)
    
    def test_update_progress_hides_time_before_10_seconds(self):
        """Test that update_progress() hides time before 10 seconds."""
        self.screen.render()
        
        # Mock start time to 5 seconds ago
        import time
        self.screen.start_time = time.time() - 5
        
        # Update progress
        self.screen.update_progress("Starting...", 10)
        
        # Time label should be empty
        self.assertEqual(self.screen.time_label.cget('text'), "")
    
    @patch('src.analysis_screen.threading.Thread')
    def test_start_analysis_creates_thread(self, mock_thread):
        """Test that start_analysis() creates and starts a background thread."""
        self.screen.render()
        
        # Start analysis
        self.screen.start_analysis("/path/to/contract.pdf")
        
        # Verify thread was created and started
        mock_thread.assert_called_once()
        mock_thread.return_value.start.assert_called_once()
        
        # Verify state
        self.assertEqual(self.screen.file_path, "/path/to/contract.pdf")
        self.assertTrue(self.screen.is_analyzing)
        self.assertIsNotNone(self.screen.start_time)
    
    @patch('src.analysis_screen.threading.Thread')
    def test_start_analysis_resets_progress(self, mock_thread):
        """Test that start_analysis() resets progress indicators."""
        self.screen.render()
        
        # Set some progress
        self.screen.progress_bar['value'] = 50
        self.screen.status_label.config(text="Old status")
        
        # Start analysis
        self.screen.start_analysis("/path/to/contract.pdf")
        
        # Verify reset
        self.assertEqual(self.screen.progress_bar['value'], 0)
        self.assertEqual(self.screen.status_label.cget('text'), "Initializing analysis...")
    
    def test_on_analysis_complete_updates_ui(self):
        """Test that on_analysis_complete() updates UI."""
        self.screen.render()
        self.screen.is_analyzing = True
        
        # Mock result
        result = {"clauses": [], "risks": []}
        
        # Complete analysis
        self.screen.on_analysis_complete(result)
        
        # Verify UI updates
        self.assertEqual(self.screen.progress_bar['value'], 100)
        self.assertIn("complete", self.screen.status_label.cget('text').lower())
        self.assertFalse(self.screen.is_analyzing)
    
    def test_on_analysis_complete_transitions_to_chat(self):
        """Test that on_analysis_complete() triggers transition to chat."""
        self.screen.render()
        
        # Mock result
        result = {"clauses": [], "risks": []}
        
        # Complete analysis
        self.screen.on_analysis_complete(result)
        
        # Verify transition was called
        self.controller.transition_to_chat.assert_called_once_with(result)
    
    @patch('tkinter.messagebox.askyesno')
    def test_on_analysis_error_shows_dialog(self, mock_messagebox):
        """Test that on_analysis_error() shows error dialog."""
        self.screen.render()
        self.screen.is_analyzing = True
        
        # Mock user response
        mock_messagebox.return_value = False
        
        # Trigger error
        error = Exception("Test error")
        self.screen.on_analysis_error(error)
        
        # Verify dialog was shown
        mock_messagebox.assert_called_once()
        
        # Verify state
        self.assertFalse(self.screen.is_analyzing)
        self.assertIn("Error", self.screen.status_label.cget('text'))
    
    @patch('tkinter.messagebox.askyesno')
    def test_on_analysis_error_returns_to_upload_on_retry(self, mock_messagebox):
        """Test that on_analysis_error() returns to upload when user chooses retry."""
        self.screen.render()
        
        # Mock user choosing to retry
        mock_messagebox.return_value = True
        
        # Trigger error
        error = Exception("Test error")
        self.screen.on_analysis_error(error)
        
        # Verify transition to upload
        self.controller.transition_to_upload.assert_called_once()
    
    @patch('tkinter.messagebox.showinfo')
    def test_on_cancel_click_shows_not_implemented(self, mock_messagebox):
        """Test that on_cancel_click() shows not implemented message."""
        self.screen.render()
        self.screen.is_analyzing = True
        
        # Click cancel
        self.screen.on_cancel_click()
        
        # Verify message shown
        mock_messagebox.assert_called_once()


class TestAnalysisScreenIntegration(unittest.TestCase):
    """Integration tests for AnalysisScreen with real components."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.root = tk.Tk()
        self.parent = tk.Frame(self.root)
        self.controller = Mock(spec=ApplicationController)
        
        # Mock analysis engine
        self.mock_engine = Mock()
        self.controller.analysis_engine = self.mock_engine
        
        self.screen = AnalysisScreen(self.parent, self.controller)
        self.screen.render()
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            self.root.destroy()
        except:
            pass
    
    def test_progress_callback_wrapper_updates_ui(self):
        """Test that progress callback wrapper updates UI on main thread."""
        # Call progress callback
        self.screen._progress_callback_wrapper("Test status", 50)
        
        # Process pending events
        self.root.update()
        
        # Verify UI was updated
        self.assertEqual(self.screen.progress_bar['value'], 50)
        self.assertEqual(self.screen.status_label.cget('text'), "Test status")


if __name__ == '__main__':
    unittest.main()
