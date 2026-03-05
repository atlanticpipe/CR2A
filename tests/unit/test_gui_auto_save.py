"""
Unit tests for CR2A_GUI auto-save functionality (Task 6.4).

Tests that analysis results are automatically saved to the history store
when analysis completes, and that the History tab is updated accordingly.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import pyqtSignal
import sys
from datetime import datetime

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.qt_gui import CR2A_GUI
from src.analysis_models import AnalysisResult, ContractMetadata
from src.history_models import AnalysisRecord


class MockHistoryTab(QWidget):
    """Mock HistoryTab that inherits from QWidget for proper Qt integration."""
    analysis_selected = pyqtSignal(str)
    analysis_deleted = pyqtSignal(str)
    
    def __init__(self, history_store, parent=None):
        super().__init__(parent)
        self.history_store = history_store
        self.add_record = MagicMock()


class TestGUIAutoSave:
    """Test suite for GUI auto-save functionality (Task 6.4)."""
    
    def create_mock_analysis_result(self):
        """Create a mock AnalysisResult for testing."""
        metadata = ContractMetadata(
            filename="test_contract.pdf",
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
    
    def test_auto_save_called_on_analysis_complete(self):
        """Test that auto-save is called when analysis completes."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    gui = CR2A_GUI()
                    
                    # Create a mock analysis result
                    result = self.create_mock_analysis_result()
                    
                    # Mock the save method to return a record ID
                    mock_store_instance.save.return_value = "test-record-id"
                    
                    # Mock get_summary to return a record
                    mock_record = AnalysisRecord(
                        id="test-record-id",
                        filename="test_contract.pdf",
                        analyzed_at=datetime.now(),
                        clause_count=0,
                        risk_count=0,
                        file_path="test-record-id.json"
                    )
                    mock_store_instance.get_summary.return_value = mock_record
                    
                    # Call on_analysis_complete
                    gui.on_analysis_complete(result)
                    
                    # Verify save was called
                    mock_store_instance.save.assert_called_once_with(result)
                    
                    gui.close()
    
    def test_auto_save_updates_history_tab(self):
        """Test that auto-save updates the History tab with the new record."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    gui = CR2A_GUI()
                    
                    # Create a mock analysis result
                    result = self.create_mock_analysis_result()
                    
                    # Mock the save method to return a record ID
                    mock_store_instance.save.return_value = "test-record-id"
                    
                    # Mock get_summary to return a record
                    mock_record = AnalysisRecord(
                        id="test-record-id",
                        filename="test_contract.pdf",
                        analyzed_at=datetime.now(),
                        clause_count=0,
                        risk_count=0,
                        file_path="test-record-id.json"
                    )
                    mock_store_instance.get_summary.return_value = mock_record
                    
                    # Call on_analysis_complete
                    gui.on_analysis_complete(result)
                    
                    # Verify get_summary was called
                    mock_store_instance.get_summary.assert_called_once_with("test-record-id")
                    
                    # Verify add_record was called on the history tab
                    gui.history_tab.add_record.assert_called_once_with(mock_record)
                    
                    gui.close()
    
    def test_auto_save_handles_save_error_gracefully(self):
        """Test that auto-save handles save errors without blocking workflow."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    with patch('src.qt_gui.QMessageBox.warning') as mock_warning:
                        gui = CR2A_GUI()
                        
                        # Create a mock analysis result
                        result = self.create_mock_analysis_result()
                        
                        # Mock the save method to raise an exception
                        from src.history_store import HistoryStoreError
                        mock_store_instance.save.side_effect = HistoryStoreError("Disk full")
                        
                        # Call on_analysis_complete - should not raise exception
                        gui.on_analysis_complete(result)
                        
                        # Verify warning was shown to user
                        mock_warning.assert_called_once()
                        
                        # Verify the analysis is still set as current
                        assert gui.current_analysis == result
                        
                        gui.close()
    
    def test_auto_save_skipped_when_history_store_unavailable(self):
        """Test that auto-save is skipped when history store is unavailable."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            from src.history_store import HistoryStoreError
            mock_history_store.side_effect = HistoryStoreError("Storage directory inaccessible")
            
            with patch('src.qt_gui.QMessageBox.warning'):
                with patch('src.qt_gui.QMessageBox.information'):
                    gui = CR2A_GUI()
                    
                    # Verify history_store is None
                    assert gui.history_store is None
                    
                    # Create a mock analysis result
                    result = self.create_mock_analysis_result()
                    
                    # Call on_analysis_complete - should not raise exception
                    gui.on_analysis_complete(result)
                    
                    # Verify the analysis is still set as current
                    assert gui.current_analysis == result
                    
                    gui.close()
    
    def test_auto_save_skipped_when_history_tab_unavailable(self):
        """Test that auto-save is skipped when history tab is unavailable."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab') as mock_history_tab:
                # Make HistoryTab initialization fail
                mock_history_tab.side_effect = Exception("Tab initialization failed")
                
                with patch('src.qt_gui.QMessageBox.warning'):
                    with patch('src.qt_gui.QMessageBox.information'):
                        gui = CR2A_GUI()
                        
                        # Verify history_tab is None
                        assert gui.history_tab is None
                        
                        # Create a mock analysis result
                        result = self.create_mock_analysis_result()
                        
                        # Call on_analysis_complete - should not raise exception
                        gui.on_analysis_complete(result)
                        
                        # Verify the analysis is still set as current
                        assert gui.current_analysis == result
                        
                        # Verify save was not called (since history_tab is None)
                        mock_store_instance.save.assert_not_called()
                        
                        gui.close()
    
    def test_auto_save_handles_get_summary_failure(self):
        """Test that auto-save handles get_summary failure gracefully."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    gui = CR2A_GUI()
                    
                    # Create a mock analysis result
                    result = self.create_mock_analysis_result()
                    
                    # Mock the save method to return a record ID
                    mock_store_instance.save.return_value = "test-record-id"
                    
                    # Mock get_summary to return None (failure)
                    mock_store_instance.get_summary.return_value = None
                    
                    # Call on_analysis_complete - should not raise exception
                    gui.on_analysis_complete(result)
                    
                    # Verify save was called
                    mock_store_instance.save.assert_called_once_with(result)
                    
                    # Verify get_summary was called
                    mock_store_instance.get_summary.assert_called_once_with("test-record-id")
                    
                    # Verify add_record was NOT called (since get_summary returned None)
                    gui.history_tab.add_record.assert_not_called()
                    
                    # Verify the analysis is still set as current
                    assert gui.current_analysis == result
                    
                    gui.close()
    
    def test_auto_save_method_exists(self):
        """Test that _auto_save_analysis method exists."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            gui = CR2A_GUI()
            
            # Verify the method exists
            assert hasattr(gui, '_auto_save_analysis')
            assert callable(gui._auto_save_analysis)
            
            gui.close()
    
    def test_auto_save_logs_success(self):
        """Test that auto-save logs success messages."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                with patch('src.qt_gui.QMessageBox.information'):
                    with patch('src.qt_gui.logger') as mock_logger:
                        gui = CR2A_GUI()
                        
                        # Create a mock analysis result
                        result = self.create_mock_analysis_result()
                        
                        # Mock the save method to return a record ID
                        mock_store_instance.save.return_value = "test-record-id"
                        
                        # Mock get_summary to return a record
                        mock_record = AnalysisRecord(
                            id="test-record-id",
                            filename="test_contract.pdf",
                            analyzed_at=datetime.now(),
                            clause_count=0,
                            risk_count=0,
                            file_path="test-record-id.json"
                        )
                        mock_store_instance.get_summary.return_value = mock_record
                        
                        # Call on_analysis_complete
                        gui.on_analysis_complete(result)
                        
                        # Verify success was logged
                        # Check that info was called with messages about auto-save
                        info_calls = [str(call) for call in mock_logger.info.call_args_list]
                        assert any("Auto-saved" in str(call) for call in info_calls)
                        
                        gui.close()
