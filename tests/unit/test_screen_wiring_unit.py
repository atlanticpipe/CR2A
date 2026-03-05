"""
Unit tests for screen wiring in ApplicationController.

Tests that screens are properly initialized and connected to the controller.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.application_controller import ApplicationController, AppState


class TestScreenWiringUnit:
    """Unit tests for screen wiring."""
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_initialize_screens_creates_all_screens(self, mock_chat, mock_analysis, 
                                                     mock_upload, mock_tk):
        """Test that initialize_screens creates all three screens."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        # Create controller
        controller = ApplicationController(mock_root)
        
        # Initialize screens
        controller.initialize_screens()
        
        # Verify all screens were created
        assert mock_upload.called
        assert mock_analysis.called
        assert mock_chat.called
        
        # Verify screens were passed correct arguments
        mock_upload.assert_called_once_with(mock_frame, controller)
        mock_analysis.assert_called_once_with(mock_frame, controller)
        mock_chat.assert_called_once_with(mock_frame, controller)
        
        # Verify main frame was created
        mock_tk.Frame.assert_called_once_with(mock_root)
        mock_frame.pack.assert_called_once()
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_initialize_screens_registers_callbacks(self, mock_chat, mock_analysis,
                                                     mock_upload, mock_tk):
        """Test that initialize_screens registers state callbacks."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        # Create controller
        controller = ApplicationController(mock_root)
        
        # Initialize screens
        controller.initialize_screens()
        
        # Verify callbacks are registered
        assert AppState.UPLOAD in controller._state_callbacks
        assert AppState.ANALYZING in controller._state_callbacks
        assert AppState.CHAT in controller._state_callbacks
        
        # Verify callbacks are callable
        assert callable(controller._state_callbacks[AppState.UPLOAD])
        assert callable(controller._state_callbacks[AppState.ANALYZING])
        assert callable(controller._state_callbacks[AppState.CHAT])
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_show_upload_screen_callback(self, mock_chat, mock_analysis,
                                         mock_upload, mock_tk):
        """Test that upload screen callback renders the screen."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        mock_upload_instance = Mock()
        mock_upload.return_value = mock_upload_instance
        
        # Create controller and initialize screens
        controller = ApplicationController(mock_root)
        controller.initialize_screens()
        
        # Call upload screen callback
        controller._show_upload_screen()
        
        # Verify render was called
        mock_upload_instance.render.assert_called_once()
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_show_analysis_screen_callback(self, mock_chat, mock_analysis,
                                           mock_upload, mock_tk):
        """Test that analysis screen callback renders and starts analysis."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        mock_analysis_instance = Mock()
        mock_analysis.return_value = mock_analysis_instance
        
        # Create controller and initialize screens
        controller = ApplicationController(mock_root)
        controller.initialize_screens()
        
        # Set current file
        controller.context.current_file = "/path/to/contract.pdf"
        
        # Call analysis screen callback
        controller._show_analysis_screen()
        
        # Verify render and start_analysis were called
        mock_analysis_instance.render.assert_called_once()
        mock_analysis_instance.start_analysis.assert_called_once_with("/path/to/contract.pdf")
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_show_chat_screen_callback(self, mock_chat, mock_analysis,
                                       mock_upload, mock_tk):
        """Test that chat screen callback renders and loads analysis."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        mock_chat_instance = Mock()
        mock_chat.return_value = mock_chat_instance
        
        # Create controller and initialize screens
        controller = ApplicationController(mock_root)
        controller.initialize_screens()
        
        # Set analysis result
        analysis_result = {
            "contract_metadata": {"filename": "test.pdf"},
            "clauses": [],
            "risks": [],
            "compliance_issues": [],
            "redlining_suggestions": []
        }
        controller.context.analysis_result = analysis_result
        
        # Call chat screen callback
        controller._show_chat_screen()
        
        # Verify render and load_analysis were called
        mock_chat_instance.render.assert_called_once()
        mock_chat_instance.load_analysis.assert_called_once_with(analysis_result)
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_state_transition_triggers_screen_callback(self, mock_chat, mock_analysis,
                                                       mock_upload, mock_tk):
        """Test that state transitions trigger the appropriate screen callbacks."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        mock_upload_instance = Mock()
        mock_analysis_instance = Mock()
        mock_chat_instance = Mock()
        
        mock_upload.return_value = mock_upload_instance
        mock_analysis.return_value = mock_analysis_instance
        mock_chat.return_value = mock_chat_instance
        
        # Create controller and initialize screens
        controller = ApplicationController(mock_root)
        controller.initialize_screens()
        
        # Test transition to upload
        controller.transition_to_upload()
        mock_upload_instance.render.assert_called()
        
        # Test transition to analysis
        controller.transition_to_analysis("/path/to/file.pdf")
        mock_analysis_instance.render.assert_called()
        mock_analysis_instance.start_analysis.assert_called_with("/path/to/file.pdf")
        
        # Test transition to chat
        analysis_result = {"clauses": []}
        controller.transition_to_chat(analysis_result)
        mock_chat_instance.render.assert_called()
        mock_chat_instance.load_analysis.assert_called_with(analysis_result)
    
    def test_initialize_screens_without_root_raises_error(self):
        """Test that initialize_screens raises error without root window."""
        # Create controller without root
        controller = ApplicationController(root=None)
        
        # Verify error is raised
        with pytest.raises(ValueError, match="Cannot initialize screens without Tkinter root window"):
            controller.initialize_screens()
    
    @patch('src.application_controller.tk')
    @patch('src.upload_screen.UploadScreen')
    @patch('src.analysis_screen.AnalysisScreen')
    @patch('src.chat_screen.ChatScreen')
    def test_screen_references_stored_correctly(self, mock_chat, mock_analysis,
                                                mock_upload, mock_tk):
        """Test that screen instances are stored in controller."""
        # Setup mocks
        mock_root = Mock()
        mock_frame = Mock()
        mock_tk.Frame.return_value = mock_frame
        
        mock_upload_instance = Mock()
        mock_analysis_instance = Mock()
        mock_chat_instance = Mock()
        
        mock_upload.return_value = mock_upload_instance
        mock_analysis.return_value = mock_analysis_instance
        mock_chat.return_value = mock_chat_instance
        
        # Create controller and initialize screens
        controller = ApplicationController(mock_root)
        controller.initialize_screens()
        
        # Verify screen references are stored
        assert controller.upload_screen == mock_upload_instance
        assert controller.analysis_screen == mock_analysis_instance
        assert controller.chat_screen == mock_chat_instance
        assert controller.main_frame == mock_frame


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
