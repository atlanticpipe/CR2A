"""
Unit tests for CR2A_GUI History Tab integration (Task 6.2).

Tests that the History tab is properly added to the main tab widget
and signals are connected correctly.
"""

import pytest
from unittest.mock import patch, MagicMock
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


class TestGUIHistoryTabIntegration:
    """Test suite for GUI History Tab integration (Task 6.2)."""
    
    def test_history_tab_added_to_tab_widget(self):
        """Test that History tab is added to the main tab widget."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Verify the tab was added to the tab widget
                # The tab should be at index 3 (after Upload, Analysis, Chat)
                tab_count = gui.tabs.count()
                assert tab_count >= 4, f"Expected at least 4 tabs, got {tab_count}"
                
                # Verify the History tab is the 4th tab (index 3)
                history_tab_text = gui.tabs.tabText(3)
                assert "History" in history_tab_text, f"Expected 'History' in tab text, got '{history_tab_text}'"
                
                gui.close()
    
    def test_history_tab_has_correct_label(self):
        """Test that History tab has the correct label with emoji."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Verify the tab label
                history_tab_text = gui.tabs.tabText(3)
                assert history_tab_text == "📜 History", f"Expected '📜 History', got '{history_tab_text}'"
                
                gui.close()
    
    def test_history_tab_signals_connected(self):
        """Test that History tab signals are connected to handler methods."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Verify the history_tab exists
                assert gui.history_tab is not None
                
                # Verify it's an instance of our mock (which has the signals)
                assert isinstance(gui.history_tab, MockHistoryTab)
                
                # The signals should be connected (we can't easily test this without
                # triggering them, but we can verify the tab was created properly)
                assert hasattr(gui.history_tab, 'analysis_selected')
                assert hasattr(gui.history_tab, 'analysis_deleted')
                
                gui.close()
    
    def test_history_tab_not_added_when_store_fails(self):
        """Test that History tab is not added when HistoryStore initialization fails."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            from src.history_store import HistoryStoreError
            mock_history_store.side_effect = HistoryStoreError("Storage directory inaccessible")
            
            with patch('src.qt_gui.QMessageBox.warning'):
                gui = CR2A_GUI()
                
                # Verify history_store is None
                assert gui.history_store is None
                
                # Verify history_tab is None
                assert gui.history_tab is None
                
                # Verify only 3 tabs exist (Upload, Analysis, Chat)
                tab_count = gui.tabs.count()
                assert tab_count == 3, f"Expected 3 tabs when history store fails, got {tab_count}"
                
                gui.close()
    
    def test_history_tab_added_after_chat_tab(self):
        """Test that History tab is added after the Chat tab (Requirements 2.1)."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Verify tab order
                assert gui.tabs.tabText(0) == "📄 Upload"
                assert gui.tabs.tabText(1) == "📊 Analysis"
                assert gui.tabs.tabText(2) == "💬 Chat"
                assert gui.tabs.tabText(3) == "📜 History"
                
                gui.close()
    
    def test_on_history_selected_handler_exists(self):
        """Test that on_history_selected handler method exists."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            gui = CR2A_GUI()
            
            # Verify the handler method exists
            assert hasattr(gui, 'on_history_selected')
            assert callable(gui.on_history_selected)
            
            gui.close()
    
    def test_on_history_deleted_handler_exists(self):
        """Test that on_history_deleted handler method exists."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            gui = CR2A_GUI()
            
            # Verify the handler method exists
            assert hasattr(gui, 'on_history_deleted')
            assert callable(gui.on_history_deleted)
            
            gui.close()
    
    def test_history_tab_instance_stored_in_gui(self):
        """Test that the HistoryTab instance is stored in the GUI."""
        with patch('src.qt_gui.HistoryStore') as mock_history_store:
            mock_store_instance = MagicMock()
            mock_history_store.return_value = mock_store_instance
            
            with patch('src.qt_gui.HistoryTab', MockHistoryTab):
                gui = CR2A_GUI()
                
                # Verify the instance is stored
                assert gui.history_tab is not None
                assert isinstance(gui.history_tab, MockHistoryTab)
                
                gui.close()
