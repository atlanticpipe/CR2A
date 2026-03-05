"""
Unit tests for HistoryTab class.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from src.history_tab import HistoryTab
from src.history_store import HistoryStore
from src.history_models import AnalysisRecord
from src.analysis_models import AnalysisResult, ContractMetadata, Clause, Risk


# Ensure QApplication exists for widget tests
@pytest.fixture(scope="module")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def temp_storage():
    """Create temporary storage directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_history"


@pytest.fixture
def history_store(temp_storage):
    """Create HistoryStore instance for tests."""
    return HistoryStore(temp_storage)


@pytest.fixture
def sample_analysis_result():
    """Create a sample AnalysisResult for testing."""
    metadata = ContractMetadata(
        filename="test_contract.pdf",
        analyzed_at=datetime(2024, 1, 15, 10, 30, 0),
        page_count=10,
        file_size_bytes=1024000
    )
    
    clauses = [
        Clause(
            id="clause_1",
            type="payment_terms",
            text="Payment shall be made within 30 days",
            page=1,
            risk_level="low"
        ),
        Clause(
            id="clause_2",
            type="liability",
            text="Liability is limited to contract value",
            page=2,
            risk_level="medium"
        ),
        Clause(
            id="clause_3",
            type="termination",
            text="Either party may terminate with 30 days notice",
            page=3,
            risk_level="low"
        )
    ]
    
    risks = [
        Risk(
            id="risk_1",
            clause_id="clause_2",
            severity="medium",
            description="Limited liability may not cover all damages",
            recommendation="Consider increasing liability coverage"
        ),
        Risk(
            id="risk_2",
            clause_id="clause_3",
            severity="low",
            description="Short termination notice period",
            recommendation="Consider extending notice period"
        )
    ]
    
    return AnalysisResult(
        metadata=metadata,
        clauses=clauses,
        risks=risks,
        compliance_issues=[],
        redlining_suggestions=[]
    )


class TestHistoryTab:
    """Test suite for HistoryTab class."""
    
    def test_initialization(self, qapp, history_store):
        """Test that HistoryTab initializes correctly."""
        tab = HistoryTab(history_store)
        
        assert tab is not None
        assert tab.history_store == history_store
        assert hasattr(tab, 'analysis_selected')
        assert hasattr(tab, 'analysis_deleted')
    
    def test_empty_state_displayed_initially(self, qapp, history_store):
        """Test that empty state message is displayed when no records exist."""
        tab = HistoryTab(history_store)
        
        # Find the empty label in the layout
        found_empty_label = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'text') and "No analysis history yet" in widget.text():
                    found_empty_label = True
                    break
        
        assert found_empty_label, "Empty state message should be displayed"
    
    def test_refresh_displays_records(self, qapp, history_store, sample_analysis_result):
        """Test that refresh() displays saved records."""
        # Save a record
        record_id = history_store.save(sample_analysis_result)
        
        # Create tab and refresh
        tab = HistoryTab(history_store)
        
        # Check that record is displayed
        found_record = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    found_record = True
                    break
        
        assert found_record, "Saved record should be displayed after refresh"
    
    def test_record_widget_shows_filename(self, qapp, history_store, sample_analysis_result):
        """Test that record widget displays filename."""
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Find the record widget
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        # Check that filename is displayed somewhere in the widget
        # We need to search through child widgets for labels
        found_filename = False
        for child in record_widget.findChildren(type(record_widget)):
            if hasattr(child, 'text') and "test_contract.pdf" in str(child.text()):
                found_filename = True
                break
        
        # Alternative: check the widget's string representation or layout
        # Since we know the implementation uses labels, we can be more specific
        from PyQt5.QtWidgets import QLabel
        for label in record_widget.findChildren(QLabel):
            if "test_contract.pdf" in label.text():
                found_filename = True
                break
        
        assert found_filename, "Filename should be displayed in record widget"
    
    def test_record_widget_shows_date_time(self, qapp, history_store, sample_analysis_result):
        """Test that record widget displays date and time."""
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Find the record widget
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        # Check that date/time is displayed
        from PyQt5.QtWidgets import QLabel
        found_datetime = False
        for label in record_widget.findChildren(QLabel):
            # The date format is "2024-01-15 10:30:00"
            if "2024-01-15" in label.text() and "10:30:00" in label.text():
                found_datetime = True
                break
        
        assert found_datetime, "Date and time should be displayed in record widget"
    
    def test_record_widget_shows_clause_count(self, qapp, history_store, sample_analysis_result):
        """Test that record widget displays clause count."""
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Find the record widget
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        # Check that clause count is displayed (should be 3 clauses)
        from PyQt5.QtWidgets import QLabel
        found_clause_count = False
        for label in record_widget.findChildren(QLabel):
            if "3 clauses" in label.text():
                found_clause_count = True
                break
        
        assert found_clause_count, "Clause count should be displayed in record widget"
    
    def test_record_widget_has_delete_button(self, qapp, history_store, sample_analysis_result):
        """Test that record widget has a delete button."""
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Find the record widget
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        # Check that delete button exists
        from PyQt5.QtWidgets import QPushButton
        found_delete_button = False
        for button in record_widget.findChildren(QPushButton):
            if "Delete" in button.text():
                found_delete_button = True
                break
        
        assert found_delete_button, "Delete button should be present in record widget"
    
    def test_add_record_adds_to_list(self, qapp, history_store, sample_analysis_result):
        """Test that add_record() adds a new record to the list."""
        tab = HistoryTab(history_store)
        
        # Save and add record
        record_id = history_store.save(sample_analysis_result)
        record = history_store.get_summary(record_id)
        tab.add_record(record)
        
        # Check that the record is present
        found_record = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    found_record = True
                    break
        
        assert found_record, "Added record should be present in the list"
    
    def test_add_record_removes_empty_state(self, qapp, history_store, sample_analysis_result):
        """Test that add_record() removes the empty state message."""
        tab = HistoryTab(history_store)
        
        # Save and add record
        record_id = history_store.save(sample_analysis_result)
        record = history_store.get_summary(record_id)
        tab.add_record(record)
        
        # Empty state should be gone
        found_empty_label = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'text') and "No analysis history yet" in widget.text():
                    found_empty_label = True
                    break
        
        assert not found_empty_label, "Empty state message should be removed after adding record"
    
    def test_add_record_maintains_sort_order(self, qapp, history_store):
        """Test that add_record() maintains sort order (newest first)."""
        tab = HistoryTab(history_store)
        
        # Create three analysis results with different timestamps
        from datetime import timedelta
        
        # First analysis (oldest)
        metadata1 = ContractMetadata(
            filename="contract1.pdf",
            analyzed_at=datetime(2024, 1, 15, 10, 0, 0),
            page_count=10,
            file_size_bytes=1024000
        )
        result1 = AnalysisResult(
            metadata=metadata1,
            clauses=[],
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Second analysis (middle)
        metadata2 = ContractMetadata(
            filename="contract2.pdf",
            analyzed_at=datetime(2024, 1, 15, 11, 0, 0),
            page_count=10,
            file_size_bytes=1024000
        )
        result2 = AnalysisResult(
            metadata=metadata2,
            clauses=[],
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Third analysis (newest)
        metadata3 = ContractMetadata(
            filename="contract3.pdf",
            analyzed_at=datetime(2024, 1, 15, 12, 0, 0),
            page_count=10,
            file_size_bytes=1024000
        )
        result3 = AnalysisResult(
            metadata=metadata3,
            clauses=[],
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Add records in order (simulating sequential analyses)
        id1 = history_store.save(result1)
        record1 = history_store.get_summary(id1)
        tab.add_record(record1)
        
        id2 = history_store.save(result2)
        record2 = history_store.get_summary(id2)
        tab.add_record(record2)
        
        id3 = history_store.save(result3)
        record3 = history_store.get_summary(id3)
        tab.add_record(record3)
        
        # Collect record IDs in display order
        displayed_ids = []
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id'):
                    displayed_ids.append(widget.record_id)
        
        # Verify order: newest first (id3, id2, id1)
        assert len(displayed_ids) == 3, "Should have 3 records displayed"
        assert displayed_ids[0] == id3, "Newest record should be first"
        assert displayed_ids[1] == id2, "Middle record should be second"
        assert displayed_ids[2] == id1, "Oldest record should be last"
    
    def test_remove_record_removes_from_list(self, qapp, history_store, sample_analysis_result):
        """Test that remove_record() removes a record from the list."""
        # Save a record
        record_id = history_store.save(sample_analysis_result)
        
        # Create tab (will load the record)
        tab = HistoryTab(history_store)
        
        # Verify record is present
        found_before = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    found_before = True
                    break
        
        assert found_before, "Record should be present before removal"
        
        # Remove the record
        tab.remove_record(record_id)
        
        # Verify record is gone
        found_after = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    found_after = True
                    break
        
        assert not found_after, "Record should be removed from the list"
    
    def test_remove_record_shows_empty_state_when_last_removed(self, qapp, history_store, sample_analysis_result):
        """Test that remove_record() shows empty state when last record is removed."""
        # Save a record
        record_id = history_store.save(sample_analysis_result)
        
        # Create tab
        tab = HistoryTab(history_store)
        
        # Remove the record
        tab.remove_record(record_id)
        
        # Empty state should be shown
        found_empty_label = False
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'text') and "No analysis history yet" in widget.text():
                    found_empty_label = True
                    break
        
        assert found_empty_label, "Empty state message should be shown when last record is removed"
    
    def test_view_button_emits_signal(self, qapp, history_store, sample_analysis_result):
        """Test that clicking view button emits analysis_selected signal."""
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Connect signal to a mock
        signal_received = []
        tab.analysis_selected.connect(lambda rid: signal_received.append(rid))
        
        # Find and click the view button
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        from PyQt5.QtWidgets import QPushButton
        for button in record_widget.findChildren(QPushButton):
            if "View" in button.text():
                button.click()
                break
        
        # Signal should have been emitted with the record_id
        assert len(signal_received) == 1
        assert signal_received[0] == record_id
    
    @patch('src.history_tab.QMessageBox.question')
    @patch('src.history_tab.QMessageBox.information')
    def test_delete_button_shows_confirmation(self, mock_info, mock_question, qapp, history_store, sample_analysis_result):
        """Test that clicking delete button shows confirmation dialog."""
        mock_question.return_value = QMessageBox.No  # User cancels
        
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Find and click the delete button
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        from PyQt5.QtWidgets import QPushButton
        for button in record_widget.findChildren(QPushButton):
            if "Delete" in button.text():
                button.click()
                break
        
        # Confirmation dialog should have been shown
        assert mock_question.called
    
    @patch('src.history_tab.QMessageBox.question')
    @patch('src.history_tab.QMessageBox.information')
    def test_delete_confirmed_removes_record(self, mock_info, mock_question, qapp, history_store, sample_analysis_result):
        """Test that confirming deletion removes the record."""
        mock_question.return_value = QMessageBox.Yes  # User confirms
        
        record_id = history_store.save(sample_analysis_result)
        tab = HistoryTab(history_store)
        
        # Connect signal to a mock
        signal_received = []
        tab.analysis_deleted.connect(lambda rid: signal_received.append(rid))
        
        # Find and click the delete button
        record_widget = None
        for i in range(tab.history_layout.count()):
            item = tab.history_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'record_id') and widget.record_id == record_id:
                    record_widget = widget
                    break
        
        assert record_widget is not None
        
        from PyQt5.QtWidgets import QPushButton
        for button in record_widget.findChildren(QPushButton):
            if "Delete" in button.text():
                button.click()
                break
        
        # Signal should have been emitted
        assert len(signal_received) == 1
        assert signal_received[0] == record_id
        
        # Record should be removed from storage
        assert history_store.get(record_id) is None
