"""
Unit tests for CR2A_GUI on_history_deleted handler (Task 6.5).

Tests that the on_history_deleted handler properly cleans up when
a deleted analysis was currently loaded.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import pyqtSignal
import sys

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.qt_gui import CR2A_GUI


class MockHistoryTab(QWidget):
    """Mock HistoryTab that inherits from QWidget for proper Qt integration."""
    analysis_selected = pyqtSignal(str)
    analysis_deleted = pyqtSignal(str)
    
    def __init__(self, history_store, parent=None):
        super().__init__(parent)
        self.history_store = history_store


class TestGUIOnHistoryDeleted:
    """Test suite for GUI on_history_deleted handler (Task 6.5)."""
    
    def test_on_history_deleted_clears_current_analysis_when_match(self):
        """Test that on_history_deleted clears current analysis when deleted record matches."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Set up a current analysis with a record_id
                mock_analysis = MagicMock()
                mock_analysis.metadata.filename = "test_contract.pdf"
                gui.current_analysis = mock_analysis
                gui.current_file = "test_contract.pdf"
                gui.current_history_record_id = "test-record-123"
                
                # Call on_history_deleted with matching record_id
                gui.on_history_deleted("test-record-123")
                
                # Verify cleanup
                assert gui.current_analysis is None
                assert gui.current_file is None
                assert gui.current_history_record_id is None
                
                gui.close()
    
    def test_on_history_deleted_does_not_clear_when_no_match(self):
        """Test that on_history_deleted does not clear current analysis when record_id doesn't match."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Set up a current analysis with a different record_id
                mock_analysis = MagicMock()
                mock_analysis.metadata.filename = "test_contract.pdf"
                gui.current_analysis = mock_analysis
                gui.current_file = "test_contract.pdf"
                gui.current_history_record_id = "test-record-123"
                
                # Call on_history_deleted with different record_id
                gui.on_history_deleted("different-record-456")
                
                # Verify no cleanup
                assert gui.current_analysis is not None
                assert gui.current_file is not None
                assert gui.current_history_record_id == "test-record-123"
                
                gui.close()
    
    def test_on_history_deleted_does_not_clear_when_no_current_analysis(self):
        """Test that on_history_deleted handles case when no analysis is loaded."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # No current analysis
                gui.current_analysis = None
                gui.current_file = None
                gui.current_history_record_id = None
                
                # Call on_history_deleted - should not raise error
                gui.on_history_deleted("test-record-123")
                
                # Verify still None
                assert gui.current_analysis is None
                assert gui.current_file is None
                assert gui.current_history_record_id is None
                
                gui.close()
    
    def test_on_history_deleted_updates_chat_history(self):
        """Test that on_history_deleted updates chat history when clearing current analysis."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Set up a current analysis with a record_id
                mock_analysis = MagicMock()
                mock_analysis.metadata.filename = "test_contract.pdf"
                gui.current_analysis = mock_analysis
                gui.current_file = "test_contract.pdf"
                gui.current_history_record_id = "test-record-123"
                
                # Get initial chat history length
                initial_chat_text = gui.chat_history.toPlainText()
                
                # Call on_history_deleted with matching record_id
                gui.on_history_deleted("test-record-123")
                
                # Verify chat history was updated
                updated_chat_text = gui.chat_history.toPlainText()
                assert len(updated_chat_text) > len(initial_chat_text)
                assert "deleted from history" in updated_chat_text.lower()
                
                gui.close()
    
    def test_on_history_deleted_clears_analysis_display(self):
        """Test that on_history_deleted clears the analysis display."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Set up a current analysis with a record_id
                mock_analysis = MagicMock()
                mock_analysis.metadata.filename = "test_contract.pdf"
                gui.current_analysis = mock_analysis
                gui.current_file = "test_contract.pdf"
                gui.current_history_record_id = "test-record-123"
                
                # Call on_history_deleted with matching record_id
                gui.on_history_deleted("test-record-123")
                
                # Verify the analysis layout has the "no analysis" label
                # The layout should have at least one widget (the no_analysis_label)
                assert gui.analysis_layout.count() > 0
                
                gui.close()
    
    def test_on_history_selected_sets_record_id(self):
        """Test that on_history_selected sets the current_history_record_id."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            # Mock the get method to return a valid analysis
            mock_analysis = MagicMock()
            mock_analysis.metadata.filename = "test_contract.pdf"
            mock_analysis.clauses = []
            mock_analysis.risks = []
            mock_analysis.compliance_issues = []
            mock_analysis.redlining_suggestions = []
            mock_store_instance.get.return_value = mock_analysis
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Call on_history_selected
                gui.on_history_selected("test-record-123")
                
                # Verify the record_id was stored
                assert gui.current_history_record_id == "test-record-123"
                assert gui.current_analysis is not None
                
                gui.close()
    
    def test_on_analysis_complete_clears_record_id(self):
        """Test that on_analysis_complete clears the current_history_record_id."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    gui = CR2A_GUI()
                    
                    # Set a history record_id
                    gui.current_history_record_id = "test-record-123"
                    
                    # Mock analysis result
                    mock_result = MagicMock()
                    mock_result.metadata.filename = "new_contract.pdf"
                    mock_result.clauses = []
                    mock_result.risks = []
                    mock_result.compliance_issues = []
                    mock_result.redlining_suggestions = []
                    
                    # Mock the display_analysis method to avoid display issues
                    with patch.object(gui, 'display_analysis'):
                        # Call on_analysis_complete
                        gui.on_analysis_complete(mock_result)
                        
                        # Verify the record_id was cleared
                        assert gui.current_history_record_id is None
                        assert gui.current_analysis is not None
                    
                    gui.close()
