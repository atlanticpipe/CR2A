"""
Unit tests for HistoryTab versioning features (Task 9).
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock
from PyQt5.QtWidgets import QApplication

from src.history_tab import HistoryTab
from src.history_store import HistoryStore
from src.differential_storage import DifferentialStorage, Contract, Clause
from src.version_manager import VersionManager


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
        yield Path(tmpdir)


@pytest.fixture
def history_store(temp_storage):
    """Create HistoryStore instance for tests."""
    return HistoryStore(temp_storage / "history")


@pytest.fixture
def differential_storage(temp_storage):
    """Create DifferentialStorage instance for tests."""
    from src.version_database import VersionDatabase
    db = VersionDatabase(temp_storage / "versions.db")
    return DifferentialStorage(db)


class TestHistoryTabVersioning:
    """Test suite for HistoryTab versioning features."""
    
    def test_initialization_with_differential_storage(self, qapp, history_store, differential_storage):
        """Test that HistoryTab initializes with differential storage."""
        tab = HistoryTab(history_store, differential_storage)
        
        assert tab is not None
        assert tab.differential_storage == differential_storage
        assert tab.version_manager is not None
        assert isinstance(tab.version_manager, VersionManager)
    
    def test_initialization_without_differential_storage(self, qapp, history_store):
        """Test that HistoryTab works without differential storage."""
        tab = HistoryTab(history_store, None)
        
        assert tab is not None
        assert tab.differential_storage is None
        assert tab.version_manager is None
    
    def test_get_all_contracts_method_exists(self, differential_storage):
        """Test that get_all_contracts method exists in DifferentialStorage."""
        assert hasattr(differential_storage, 'get_all_contracts')
        
        # Test it returns empty list initially
        contracts = differential_storage.get_all_contracts()
        assert isinstance(contracts, list)
        assert len(contracts) == 0
    
    def test_get_all_contracts_returns_stored_contracts(self, differential_storage):
        """Test that get_all_contracts returns stored contracts."""
        # Create and store a contract
        contract = Contract(
            contract_id="test_contract_1",
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        clause = Clause(
            clause_id="clause_1",
            contract_id="test_contract_1",
            clause_version=1,
            clause_identifier="Section 1",
            content="Test clause content",
            metadata={},
            created_at=datetime.now(),
            is_deleted=False,
            deleted_at=None
        )
        
        differential_storage.store_new_contract(contract, [clause])
        
        # Get all contracts
        contracts = differential_storage.get_all_contracts()
        
        assert len(contracts) == 1
        assert contracts[0].contract_id == "test_contract_1"
        assert contracts[0].filename == "test.pdf"
        assert contracts[0].current_version == 1
    
    def test_retrieve_version_method_exists(self, qapp, history_store, differential_storage):
        """Test that retrieve_version method exists in HistoryTab."""
        tab = HistoryTab(history_store, differential_storage)
        
        assert hasattr(tab, 'retrieve_version')
    
    def test_retrieve_version_returns_none_without_version_manager(self, qapp, history_store):
        """Test that retrieve_version returns None when version manager is not available."""
        tab = HistoryTab(history_store, None)
        
        result = tab.retrieve_version("test_contract", 1)
        
        assert result is None
    
    def test_display_version_method_exists(self, qapp, history_store, differential_storage):
        """Test that display_version method exists in HistoryTab."""
        tab = HistoryTab(history_store, differential_storage)
        
        assert hasattr(tab, 'display_version')
    
    def test_version_selected_signal_exists(self, qapp, history_store, differential_storage):
        """Test that version_selected signal exists."""
        tab = HistoryTab(history_store, differential_storage)
        
        assert hasattr(tab, 'version_selected')
    
    def test_version_selected_signal_emits_correctly(self, qapp, history_store, differential_storage):
        """Test that version_selected signal emits with correct parameters."""
        tab = HistoryTab(history_store, differential_storage)
        
        # Connect signal to a mock
        signal_received = []
        tab.version_selected.connect(lambda cid, ver: signal_received.append((cid, ver)))
        
        # Emit the signal
        tab.version_selected.emit("test_contract", 2)
        
        # Verify signal was received
        assert len(signal_received) == 1
        assert signal_received[0] == ("test_contract", 2)
    
    def test_count_versioned_clauses_returns_zero_without_storage(self, qapp, history_store):
        """Test that _count_versioned_clauses returns 0 without differential storage."""
        tab = HistoryTab(history_store, None)
        
        count = tab._count_versioned_clauses("test_contract")
        
        assert count == 0
    
    def test_count_versioned_clauses_with_single_version(self, qapp, history_store, differential_storage):
        """Test that _count_versioned_clauses returns 0 when all clauses have single version."""
        tab = HistoryTab(history_store, differential_storage)
        
        # Create contract with clauses all at version 1
        contract = Contract(
            contract_id="test_contract_2",
            filename="test2.pdf",
            file_hash="def456",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        clauses = [
            Clause(
                clause_id=f"clause_{i}",
                contract_id="test_contract_2",
                clause_version=1,
                clause_identifier=f"Section {i}",
                content=f"Clause {i} content",
                metadata={},
                created_at=datetime.now(),
                is_deleted=False,
                deleted_at=None
            )
            for i in range(3)
        ]
        
        differential_storage.store_new_contract(contract, clauses)
        
        # Count versioned clauses
        count = tab._count_versioned_clauses("test_contract_2")
        
        # Should be 0 since all clauses have only one version
        assert count == 0
    
    def test_get_contract_for_record_returns_none_without_storage(self, qapp, history_store):
        """Test that _get_contract_for_record returns None without differential storage."""
        from src.history_models import AnalysisRecord
        
        tab = HistoryTab(history_store, None)
        
        record = AnalysisRecord(
            id="test_record",
            filename="test.pdf",
            analyzed_at=datetime.now(),
            clause_count=3,
            risk_count=1,
            file_path=Path("/tmp/test.json")
        )
        
        contract = tab._get_contract_for_record(record)
        
        assert contract is None
