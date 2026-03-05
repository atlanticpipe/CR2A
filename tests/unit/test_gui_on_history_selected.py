"""
Unit tests for CR2A_GUI on_history_selected handler (Task 6.3).

Tests that the on_history_selected handler properly:
- Loads full analysis from HistoryStore
- Sets as current_analysis
- Displays in Analysis tab
- Enables Chat tab for querying
- Switches to Analysis tab
- Handles load errors with user notification
"""

import pytest
from unittest.mock import patch, MagicMock, call
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import pyqtSignal
import sys
from datetime import datetime

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.qt_gui import CR2A_GUI
from src.analysis_models import AnalysisResult, ContractMetadata


class TestOnHistorySelected:
    """Test suite for on_history_selected handler (Task 6.3)."""
    
    def create_mock_analysis_result(self, filename="test_contract.pdf"):
        """Create a mock AnalysisResult for testing."""
        metadata = ContractMetadata(
            filename=filename,
            page_count=10,
            file_size_bytes=1024,
            analyzed_at=datetime.now()
        )
        
        result = AnalysisResult(
            metadata=metadata,
            clauses=[],
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        return result
    
    def test_loads_full_analysis_from_history_store(self):
        """Test that handler loads full analysis from HistoryStore (Requirement 4.1)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result()
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Call the handler
                record_id = "test-record-id-123"
                gui.on_history_selected(record_id)
                
                # Verify HistoryStore.get() was called with correct record_id
                mock_store.get.assert_called_once_with(record_id)
                
                gui.close()
    
    def test_sets_as_current_analysis(self):
        """Test that handler sets loaded analysis as current_analysis (Requirement 4.1)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result()
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Verify current_analysis is initially None
                assert gui.current_analysis is None
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify current_analysis is set
                assert gui.current_analysis is not None
                assert gui.current_analysis == mock_analysis
                
                gui.close()
    
    def test_displays_in_analysis_tab(self):
        """Test that handler displays analysis in Analysis tab (Requirement 4.2)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result()
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Mock the display_analysis method to verify it's called
                gui.display_analysis = MagicMock()
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify display_analysis was called with the loaded analysis
                gui.display_analysis.assert_called_once_with(mock_analysis)
                
                gui.close()
    
    def test_enables_chat_tab_for_querying(self):
        """Test that handler enables Chat tab for querying (Requirement 4.3)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result("loaded_contract.pdf")
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify chat history was updated to indicate analysis is loaded
                chat_text = gui.chat_history.toPlainText()
                assert "Historical Analysis Loaded" in chat_text
                assert "loaded_contract.pdf" in chat_text
                
                gui.close()
    
    def test_switches_to_analysis_tab(self):
        """Test that handler switches to Analysis tab (Requirement 4.2)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result()
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Set current tab to something else (e.g., Upload tab)
                gui.tabs.setCurrentIndex(0)
                assert gui.tabs.currentIndex() == 0
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify tab switched to Analysis tab (index 1)
                assert gui.tabs.currentIndex() == 1
                
                gui.close()
    
    def test_handles_load_error_when_analysis_not_found(self):
        """Test that handler handles load errors when analysis is not found (Requirement 4.4)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Simulate analysis not found (get returns None)
            mock_store.get.return_value = None
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Mock QMessageBox to verify error notification
                with patch.object(QMessageBox, 'critical') as mock_critical:
                    # Call the handler
                    gui.on_history_selected("non-existent-record")
                    
                    # Verify error message was shown
                    mock_critical.assert_called_once()
                    call_args = mock_critical.call_args
                    
                    # Verify the message contains relevant information
                    assert "Load Error" in str(call_args)
                    assert "Failed to load" in str(call_args)
                
                # Verify current_analysis was not set
                assert gui.current_analysis is None
                
                gui.close()
    
    def test_handles_load_error_with_exception(self):
        """Test that handler handles unexpected exceptions during load (Requirement 4.4)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Simulate an exception during get()
            mock_store.get.side_effect = Exception("Unexpected error")
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Mock QMessageBox to verify error notification
                with patch.object(QMessageBox, 'critical') as mock_critical:
                    # Call the handler
                    gui.on_history_selected("test-record-id")
                    
                    # Verify error message was shown
                    mock_critical.assert_called_once()
                    call_args = mock_critical.call_args
                    
                    # Verify the message contains error information
                    assert "Load Error" in str(call_args)
                    assert "unexpected error" in str(call_args).lower()
                
                gui.close()
    
    def test_handles_missing_history_store(self):
        """Test that handler handles case when history_store is None."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            from src.history_store import HistoryStoreError
            mock_history_store_class.side_effect = HistoryStoreError("Storage unavailable")
            
            with patch('src.qt_gui.QMessageBox.warning'):
                gui = CR2A_GUI()
                
                # Verify history_store is None
                assert gui.history_store is None
                
                # Mock QMessageBox to verify warning
                with patch.object(QMessageBox, 'warning') as mock_warning:
                    # Call the handler
                    gui.on_history_selected("test-record-id")
                    
                    # Verify warning was shown
                    mock_warning.assert_called_once()
                    call_args = mock_warning.call_args
                    
                    # Verify the message indicates history is unavailable
                    assert "History Unavailable" in str(call_args)
                
                gui.close()
    
    def test_sets_current_file_from_metadata(self):
        """Test that handler sets current_file from analysis metadata."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result with specific filename
            mock_analysis = self.create_mock_analysis_result("specific_contract.pdf")
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Verify current_file is initially None
                assert gui.current_file is None
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify current_file is set to the filename from metadata
                assert gui.current_file == "specific_contract.pdf"
                
                gui.close()
    
    def test_updates_status_bar(self):
        """Test that handler updates the status bar with loaded analysis info."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result("status_test.pdf")
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Call the handler
                gui.on_history_selected("test-record-id")
                
                # Verify status bar was updated
                status_text = gui.statusBar().currentMessage()
                assert "Loaded analysis" in status_text
                assert "status_test.pdf" in status_text
                
                gui.close()
    
    def test_logs_successful_load(self):
        """Test that handler logs successful load."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Create mock analysis result
            mock_analysis = self.create_mock_analysis_result()
            mock_store.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Mock logger to verify logging
                with patch('src.qt_gui.logger') as mock_logger:
                    # Call the handler
                    record_id = "test-record-id-123"
                    gui.on_history_selected(record_id)
                    
                    # Verify logging occurred
                    # Should log: "History record selected" and "Successfully loaded"
                    assert mock_logger.info.call_count >= 2
                    
                    # Check for specific log messages
                    log_calls = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("History record selected" in str(call) for call in log_calls)
                    assert any("Successfully loaded" in str(call) for call in log_calls)
                
                gui.close()
    
    def test_logs_load_error(self):
        """Test that handler logs load errors."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store_class:
            mock_store = MagicMock()
            mock_history_store_class.return_value = mock_store
            
            # Simulate analysis not found
            mock_store.get.return_value = None
            
            with patch('src.qt_gui.HistoryTab'):
                gui = CR2A_GUI()
                
                # Mock logger and QMessageBox
                with patch('src.qt_gui.logger') as mock_logger:
                    with patch.object(QMessageBox, 'critical'):
                        # Call the handler
                        record_id = "non-existent-record"
                        gui.on_history_selected(record_id)
                        
                        # Verify error was logged
                        mock_logger.error.assert_called_once()
                        error_call = str(mock_logger.error.call_args)
                        assert "Failed to load analysis" in error_call
                
                gui.close()
