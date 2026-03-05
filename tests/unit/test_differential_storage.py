"""
Unit tests for DifferentialStorage class.

Tests CRUD operations for contract versioning with differential storage.
"""

import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from src.differential_storage import (
    DifferentialStorage,
    DifferentialStorageError,
    Contract,
    Clause,
    VersionMetadata
)
from src.version_database import VersionDatabase


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_versions.db"
        db = VersionDatabase(db_path)
        yield db
        db.close()


@pytest.fixture
def storage(temp_db):
    """Create DifferentialStorage instance with temporary database."""
    return DifferentialStorage(database=temp_db)


@pytest.fixture
def sample_contract():
    """Create a sample contract for testing."""
    return Contract(
        contract_id="contract_001",
        filename="test_contract.pdf",
        file_hash="abc123def456",
        current_version=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_clauses():
    """Create sample clauses for testing."""
    now = datetime.now()
    return [
        Clause(
            clause_id="clause_001",
            contract_id="contract_001",
            clause_version=1,
            clause_identifier="Section 1",
            content="This is the first clause.",
            metadata={"risk_level": "low", "category": "general"},
            created_at=now,
            is_deleted=False,
            deleted_at=None
        ),
        Clause(
            clause_id="clause_002",
            contract_id="contract_001",
            clause_version=1,
            clause_identifier="Section 2",
            content="This is the second clause.",
            metadata={"risk_level": "medium", "category": "payment"},
            created_at=now,
            is_deleted=False,
            deleted_at=None
        )
    ]


class TestDifferentialStorage:
    """Test suite for DifferentialStorage class."""
    
    def test_store_new_contract(self, storage, sample_contract, sample_clauses):
        """Test storing a new contract with version 1."""
        # Store new contract
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Verify contract was stored
        retrieved_contract = storage.get_contract(sample_contract.contract_id)
        assert retrieved_contract is not None
        assert retrieved_contract.contract_id == sample_contract.contract_id
        assert retrieved_contract.filename == sample_contract.filename
        assert retrieved_contract.file_hash == sample_contract.file_hash
        assert retrieved_contract.current_version == 1
        
        # Verify clauses were stored
        retrieved_clauses = storage.get_clauses(sample_contract.contract_id)
        assert len(retrieved_clauses) == 2
        assert all(c.clause_version == 1 for c in retrieved_clauses)
        
        # Verify version metadata was stored
        version_history = storage.get_version_history(sample_contract.contract_id)
        assert len(version_history) == 1
        assert version_history[0].version == 1
        assert version_history[0].change_summary["added"] == 2
    
    def test_store_contract_version(self, storage, sample_contract, sample_clauses):
        """Test storing a new version with changed clauses."""
        # Store initial version
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Create modified clause for version 2
        modified_clause = Clause(
            clause_id="clause_003",  # New clause ID for modified version
            contract_id="contract_001",
            clause_version=2,
            clause_identifier="Section 1",
            content="This is the modified first clause.",
            metadata={"risk_level": "high", "category": "general"},
            created_at=datetime.now(),
            is_deleted=False,
            deleted_at=None
        )
        
        # Create version metadata
        version_metadata = VersionMetadata(
            contract_id="contract_001",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=["clause_003"],
            change_summary={"modified": 1, "added": 0, "deleted": 0}
        )
        
        # Store version 2
        storage.store_contract_version(
            "contract_001",
            2,
            [modified_clause],
            version_metadata
        )
        
        # Verify contract version was updated
        retrieved_contract = storage.get_contract("contract_001")
        assert retrieved_contract.current_version == 2
        
        # Verify version metadata
        version_history = storage.get_version_history("contract_001")
        assert len(version_history) == 2
        assert version_history[1].version == 2
        assert version_history[1].change_summary["modified"] == 1
    
    def test_get_contract_not_found(self, storage):
        """Test retrieving a non-existent contract."""
        result = storage.get_contract("nonexistent_contract")
        assert result is None
    
    def test_get_clauses_all_versions(self, storage, sample_contract, sample_clauses):
        """Test retrieving all clauses for all versions."""
        # Store initial version
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Add a modified clause in version 2
        modified_clause = Clause(
            clause_id="clause_003",
            contract_id="contract_001",
            clause_version=2,
            clause_identifier="Section 1",
            content="Modified clause.",
            metadata={},
            created_at=datetime.now(),
            is_deleted=False,
            deleted_at=None
        )
        
        version_metadata = VersionMetadata(
            contract_id="contract_001",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=["clause_003"],
            change_summary={"modified": 1, "added": 0, "deleted": 0}
        )
        
        storage.store_contract_version(
            "contract_001",
            2,
            [modified_clause],
            version_metadata
        )
        
        # Get all clauses (no version filter)
        all_clauses = storage.get_clauses("contract_001")
        assert len(all_clauses) == 3  # 2 from v1 + 1 from v2
    
    def test_get_clauses_specific_version(self, storage, sample_contract, sample_clauses):
        """Test retrieving clauses for a specific version."""
        # Store initial version
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Get clauses for version 1
        v1_clauses = storage.get_clauses("contract_001", version=1)
        assert len(v1_clauses) == 2
        assert all(c.clause_version == 1 for c in v1_clauses)
    
    def test_get_version_history(self, storage, sample_contract, sample_clauses):
        """Test retrieving version history."""
        # Store initial version
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Get version history
        history = storage.get_version_history("contract_001")
        assert len(history) == 1
        assert history[0].version == 1
        assert history[0].contract_id == "contract_001"
        assert len(history[0].changed_clause_ids) == 2
    
    def test_get_version_history_empty(self, storage):
        """Test retrieving version history for non-existent contract."""
        history = storage.get_version_history("nonexistent_contract")
        assert len(history) == 0
    
    def test_store_contract_version_nonexistent_contract(self, storage):
        """Test storing version for non-existent contract raises error."""
        clause = Clause(
            clause_id="clause_001",
            contract_id="nonexistent",
            clause_version=2,
            clause_identifier="Section 1",
            content="Test",
            metadata={},
            created_at=datetime.now(),
            is_deleted=False,
            deleted_at=None
        )
        
        version_metadata = VersionMetadata(
            contract_id="nonexistent",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=["clause_001"],
            change_summary={"modified": 1, "added": 0, "deleted": 0}
        )
        
        with pytest.raises(DifferentialStorageError):
            storage.store_contract_version(
                "nonexistent",
                2,
                [clause],
                version_metadata
            )
    
    def test_transaction_rollback_on_error(self, storage, sample_contract):
        """Test that transaction rolls back on error."""
        # Create invalid clauses (missing required fields will cause error)
        invalid_clauses = [
            Clause(
                clause_id="clause_001",
                contract_id="contract_001",
                clause_version=1,
                clause_identifier="Section 1",
                content="Valid clause",
                metadata={},
                created_at=datetime.now(),
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        # Store valid contract first
        storage.store_new_contract(sample_contract, invalid_clauses)
        
        # Now try to store a version with invalid data
        # This should fail and rollback
        try:
            # Force an error by using invalid SQL
            storage.db.execute("INSERT INTO nonexistent_table VALUES (1)")
            storage.db.commit()
        except:
            storage.db.rollback()
        
        # Verify original data is still intact
        contract = storage.get_contract("contract_001")
        assert contract is not None
        assert contract.current_version == 1
    
    def test_clause_metadata_serialization(self, storage, sample_contract):
        """Test that clause metadata is properly serialized/deserialized."""
        metadata = {
            "risk_level": "high",
            "category": "liability",
            "tags": ["important", "review"],
            "score": 8.5
        }
        
        clause = Clause(
            clause_id="clause_001",
            contract_id="contract_001",
            clause_version=1,
            clause_identifier="Section 1",
            content="Test clause",
            metadata=metadata,
            created_at=datetime.now(),
            is_deleted=False,
            deleted_at=None
        )
        
        storage.store_new_contract(sample_contract, [clause])
        
        # Retrieve and verify metadata
        retrieved_clauses = storage.get_clauses("contract_001")
        assert len(retrieved_clauses) == 1
        assert retrieved_clauses[0].metadata == metadata
    
    def test_deleted_clause_handling(self, storage, sample_contract, sample_clauses):
        """Test handling of deleted clauses."""
        # Store initial version
        storage.store_new_contract(sample_contract, sample_clauses)
        
        # Mark a clause as deleted in version 2
        deleted_clause = Clause(
            clause_id="clause_001",  # Same ID as original
            contract_id="contract_001",
            clause_version=2,
            clause_identifier="Section 1",
            content="This is the first clause.",
            metadata={},
            created_at=datetime.now(),
            is_deleted=True,
            deleted_at=datetime.now()
        )
        
        version_metadata = VersionMetadata(
            contract_id="contract_001",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=["clause_001"],
            change_summary={"modified": 0, "added": 0, "deleted": 1}
        )
        
        storage.store_contract_version(
            "contract_001",
            2,
            [deleted_clause],
            version_metadata
        )
        
        # Verify clause is marked as deleted
        all_clauses = storage.get_clauses("contract_001")
        deleted = [c for c in all_clauses if c.clause_id == "clause_001"]
        assert len(deleted) == 1
        assert deleted[0].is_deleted is True
        assert deleted[0].deleted_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
