"""
Manual test for screen wiring.

This script verifies that the ApplicationController properly wires all screens
and handles state transitions correctly.

Run this script manually to visually verify the screen transitions work.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import logging
import tkinter as tk
from unittest.mock import Mock, patch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
)

logger = logging.getLogger(__name__)


def test_screen_wiring():
    """Test screen wiring with mocked components."""
    
    logger.info("=" * 80)
    logger.info("Manual Screen Wiring Test")
    logger.info("=" * 80)
    
    # Mock all the heavy components
    with patch('src.config_manager.ConfigManager') as mock_config, \
         patch('src.contract_uploader.ContractUploader') as mock_uploader, \
         patch('src.analysis_engine.AnalysisEngine') as mock_analysis, \
         patch('src.query_engine.QueryEngine') as mock_query:
        
        # Setup mocks
        mock_config_instance = Mock()
        mock_config_instance.get_openai_key.return_value = "sk-test-key"
        mock_config_instance.validate_config.return_value = (True, [])
        mock_config.return_value = mock_config_instance
        
        mock_uploader_instance = Mock()
        mock_uploader_instance.validate_format.return_value = (True, None)
        mock_uploader_instance.get_file_info.return_value = {
            'filename': 'test_contract.pdf',
            'file_size_mb': '2.5 MB',
            'page_count': 10
        }
        mock_uploader.return_value = mock_uploader_instance
        
        # Import after mocking
        from src.application_controller import ApplicationController, AppState
        
        # Create Tkinter root
        root = tk.Tk()
        root.title("Screen Wiring Test")
        root.geometry("1024x768")
        
        try:
            logger.info("Initializing ApplicationController...")
            controller = ApplicationController(root)
            
            logger.info("Initializing components...")
            controller.initialize_components()
            
            logger.info("Initializing screens...")
            controller.initialize_screens()
            
            logger.info("Starting application...")
            controller.start()
            
            # Verify initial state
            assert controller.get_current_state() == AppState.UPLOAD
            logger.info("✓ Application started in UPLOAD state")
            
            # Verify screens are created
            assert controller.upload_screen is not None
            assert controller.analysis_screen is not None
            assert controller.chat_screen is not None
            logger.info("✓ All screens created successfully")
            
            # Verify upload screen is rendered
            assert controller.upload_screen.main_frame is not None
            assert controller.upload_screen.title_label is not None
            logger.info("✓ Upload screen rendered successfully")
            
            # Test transition to analysis
            logger.info("\nTesting transition to ANALYZING state...")
            controller.transition_to_analysis("/path/to/test_contract.pdf")
            assert controller.get_current_state() == AppState.ANALYZING
            assert controller.get_current_file() == "/path/to/test_contract.pdf"
            logger.info("✓ Transitioned to ANALYZING state")
            
            # Test transition to chat
            logger.info("\nTesting transition to CHAT state...")
            analysis_result = {
                "contract_metadata": {
                    "filename": "test_contract.pdf",
                    "page_count": 10
                },
                "clauses": [
                    {"id": "1", "text": "Payment terms", "type": "payment"}
                ],
                "risks": [],
                "compliance_issues": [],
                "redlining_suggestions": []
            }
            controller.transition_to_chat(analysis_result)
            assert controller.get_current_state() == AppState.CHAT
            assert controller.get_analysis_result() == analysis_result
            logger.info("✓ Transitioned to CHAT state")
            
            # Test transition back to upload
            logger.info("\nTesting transition back to UPLOAD state...")
            controller.transition_to_upload()
            assert controller.get_current_state() == AppState.UPLOAD
            logger.info("✓ Transitioned back to UPLOAD state")
            
            logger.info("\n" + "=" * 80)
            logger.info("ALL TESTS PASSED!")
            logger.info("=" * 80)
            
            # Show success message
            success_label = tk.Label(
                root,
                text="✓ Screen Wiring Test Passed!\n\nAll screens are properly connected to the controller.\nState transitions work correctly.",
                font=("Segoe UI", 14),
                fg="green",
                pady=50
            )
            success_label.pack()
            
            # Add close button
            close_button = tk.Button(
                root,
                text="Close",
                command=root.destroy,
                font=("Segoe UI", 12),
                width=20
            )
            close_button.pack()
            
            # Run for a few seconds then close
            root.after(5000, root.destroy)
            root.mainloop()
            
        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise
        finally:
            try:
                root.destroy()
            except:
                pass


if __name__ == "__main__":
    test_screen_wiring()
