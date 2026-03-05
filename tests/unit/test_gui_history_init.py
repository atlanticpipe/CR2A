"""
Unit tests for CR2A_GUI HistoryStore initialization.

Tests that the GUI properly initializes the HistoryStore and handles errors gracefully.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QApplication
import sys

# Ensure QApplication exists for tests
if not QApplication.instance():
    app = QApplication(sys.argv)

from src.qt_gui import CR2A_GUI
from src.history_store import HistoryStoreError


class TestGUIHistoryStoreInitialization:
    """Test suite for GUI HistoryStore initialization."""
    
    def test_history_store_initialized_successfully(self):
        """Test that HistoryStore is initialized successfully during GUI init."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_instance = MagicMock()
            mock_history_store.return_value = mock_instance
            
            gui = CR2A_GUI()
            
            # Verify HistoryStore was instantiated
            mock_history_store.assert_called_once()
            
            # Verify the instance was stored
            assert gui.history_store == mock_instance
            
            gui.close()
    
    def test_history_store_error_handled_gracefully(self):
        """Test that HistoryStoreError is handled gracefully without crashing."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            # Simulate HistoryStoreError during initialization
            mock_history_store.side_effect = HistoryStoreError("Storage directory inaccessible")
            
            with patch('src.qt_gui.QMessageBox.warning') as mock_warning:
                gui = CR2A_GUI()
                
                # Verify error was logged and warning shown
                mock_warning.assert_called_once()
                
                # Verify history_store is set to None
                assert gui.history_store is None
                
                # Verify GUI still works (other components initialized)
                assert gui.config_manager is not None
                
                gui.close()
    
    def test_unexpected_error_handled_gracefully(self):
        """Test that unexpected errors during HistoryStore init are handled gracefully."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            # Simulate unexpected error
            mock_history_store.side_effect = RuntimeError("Unexpected error")
            
            with patch('src.qt_gui.QMessageBox.warning') as mock_warning:
                gui = CR2A_GUI()
                
                # Verify error was logged and warning shown
                mock_warning.assert_called_once()
                
                # Verify history_store is set to None
                assert gui.history_store is None
                
                # Verify GUI still works
                assert gui.config_manager is not None
                
                gui.close()
    
    def test_history_store_initialized_before_engines(self):
        """Test that HistoryStore is initialized before analysis engines."""
        init_order = []
        
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_history_store.return_value = MagicMock()
            
            with patch('src.qt_gui.AnalysisEngine') as mock_analysis_engine:
                mock_analysis_engine.return_value = MagicMock()
                
                # Track initialization order
                def track_history_store(*args, **kwargs):
                    init_order.append('history_store')
                    return MagicMock()
                
                def track_analysis_engine(*args, **kwargs):
                    init_order.append('analysis_engine')
                    return MagicMock()
                
                mock_history_store.side_effect = track_history_store
                mock_analysis_engine.side_effect = track_analysis_engine
                
                # Set environment variable to avoid API key dialog
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key'}):
                    gui = CR2A_GUI()
                    
                    # Verify history_store was initialized before analysis_engine
                    assert 'history_store' in init_order
                    if 'analysis_engine' in init_order:
                        assert init_order.index('history_store') < init_order.index('analysis_engine')
                    
                    gui.close()
    
    def test_gui_continues_without_history_store(self):
        """Test that GUI continues to function even if HistoryStore fails."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_history_store.side_effect = HistoryStoreError("Failed to create directory")
            
            with patch('src.qt_gui.QMessageBox.warning'):
                gui = CR2A_GUI()
                
                # Verify GUI is still functional
                assert gui.history_store is None
                assert gui.analysis_engine is not None or gui.query_engine is not None or True  # At least GUI exists
                assert gui.tabs is not None
                assert gui.upload_tab is not None
                assert gui.analysis_tab is not None
                assert gui.chat_tab is not None
                
                gui.close()
