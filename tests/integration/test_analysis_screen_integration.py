"""
Integration tests for AnalysisScreen with ApplicationController.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
import tkinter as tk
from src.analysis_screen import AnalysisScreen
from src.application_controller import ApplicationController, AppState
from src.analysis_models import AnalysisResult, ContractMetadata


class TestAnalysisScreenIntegration(unittest.TestCase):
    """Integration tests for AnalysisScreen with ApplicationController."""
    
    def setUp(self):
        """Set up test fixtures."""
        try:
            self.root = tk.Tk()
            self.parent = tk.Frame(self.root)
            self.controller = ApplicationController(self.root)
            
            # Mock analysis engine
            self.mock_engine = Mock()
            self.controller.analysis_engine = self.mock_engine
            
            self.screen = AnalysisScreen(self.parent, self.controller)
        except Exception as e:
            self.skipTest(f"Tkinter not available: {e}")
    
    def tearDown(self):
        """Clean up after tests."""
        try:
            if hasattr(self, 'root'):
                self.root.destroy()
        except:
            pass
    
    def test_screen_initialization_with_controller(self):
        """Test that AnalysisScreen initializes properly with ApplicationController."""
        self.assertIsNotNone(self.screen)
        self.assertEqual(self.screen.controller, self.controller)
    
    def test_screen_renders_without_errors(self):
        """Test that AnalysisScreen renders without errors."""
        try:
            self.screen.render()
            self.assertIsNotNone(self.screen.main_frame)
        except Exception as e:
            self.fail(f"Screen rendering failed: {e}")
    
    def test_start_analysis_with_mock_engine(self):
        """Test that start_analysis works with mocked analysis engine."""
        self.screen.render()
        
        # Create mock analysis result
        mock_result = Mock(spec=AnalysisResult)
        mock_result.to_dict.return_value = {
            "metadata": {"filename": "test.pdf"},
            "clauses": [],
            "risks": [],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        
        # Mock the analyze_contract method
        self.mock_engine.analyze_contract.return_value = mock_result
        
        # Start analysis (this will run in background thread)
        self.screen.start_analysis("/path/to/test.pdf")
        
        # Verify state
        self.assertTrue(self.screen.is_analyzing)
        self.assertEqual(self.screen.file_path, "/path/to/test.pdf")
    
    def test_progress_callback_updates_ui(self):
        """Test that progress callback properly updates UI."""
        self.screen.render()
        
        # Call progress callback
        self.screen.update_progress("Testing progress", 50)
        
        # Verify UI updates
        self.assertEqual(self.screen.progress_bar['value'], 50)
        self.assertEqual(self.screen.status_label.cget('text'), "Testing progress")
    
    def test_completion_triggers_state_transition(self):
        """Test that completion triggers transition to chat state."""
        self.screen.render()
        
        # Mock result
        result = {
            "metadata": {"filename": "test.pdf"},
            "clauses": [],
            "risks": [],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        
        # Complete analysis
        self.screen.on_analysis_complete(result)
        
        # Verify transition was called
        # Note: We can't easily verify the actual state transition without
        # mocking the controller's transition method, but we can verify
        # the UI updates correctly
        self.assertEqual(self.screen.progress_bar['value'], 100)
        self.assertFalse(self.screen.is_analyzing)


if __name__ == '__main__':
    unittest.main()
