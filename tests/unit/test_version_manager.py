"""
Unit tests for VersionManager.

Tests version management functionality including version assignment,
metadata retrieval, and version reconstruction.
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.version_manager import VersionManager, VersionManagerError, VersionedContract
from src.differential_storage import (
    DifferentialStorage,
    Contract,
    Clause,
    VersionMetadata
)
from src.change_comparator import (
    ContractDiff,
    ClauseComparison,
    ClauseChangeType
)


@pytest.fixture
def mock_storage():
    """Create a mock DifferentialStorage instance."""
    return Mock(spec=DifferentialStorage)


@pytest.fixture
def version_manager(mock_storage):
    """Create a VersionManager instance with mock storage."""
    return VersionManager(mock_storage)


@pytest.fixture
def sample_contract():
    """Create a sample contract for testing."""
    return Contract(
        contract_id="contract-123",
        filename="test_contract.pdf",
        file_hash="abc123",
        current_version=1,
        created_at=datetime(2024, 1, 1, 10, 0, 0),
        updated_at=datetime(2024, 1, 1, 10, 0, 0)
    )


@pytest.fixture
def sample_clauses():
    """Create sample clauses for testing."""
    return [
        Clause(
            clause_id="clause-1",
            contract_id="contract-123",
            clause_version=1,
            clause_identifier="scope_of_work",
            content="Original scope of work content",
            metadata={"change_type": "added"},
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            is_deleted=False,
            deleted_at=None
        ),
        Clause(
            clause_id="clause-2",
            contract_id="contract-123",
            clause_version=1,
            clause_identifier="payment_terms",
            content="Original payment terms content",
            metadata={"change_type": "added"},
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            is_deleted=False,
            deleted_at=None
        )
    ]


class TestGetNextVersion:
    """Tests for get_next_version method."""
    
    def test_get_next_version_success(self, version_manager, mock_storage, sample_contract):
        """Test getting next version number successfully."""
        mock_storage.get_contract.return_value = sample_contract
        
        next_version = version_manager.get_next_version("contract-123")
        
        assert next_version == 2
        mock_storage.get_contract.assert_called_once_with("contract-123")
    
    def test_get_next_version_contract_not_found(self, version_manager, mock_storage):
        """Test error when contract not found."""
        mock_storage.get_contract.return_value = None
        
        with pytest.raises(VersionManagerError, match="Contract not found"):
            version_manager.get_next_version("nonexistent")
    
    def test_get_next_version_multiple_versions(self, version_manager, mock_storage):
        """Test getting next version for contract with multiple versions."""
        contract = Contract(
            contract_id="contract-456",
            filename="test.pdf",
            file_hash="def456",
            current_version=5,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_storage.get_contract.return_value = contract
        
        next_version = version_manager.get_next_version("contract-456")
        
        assert next_version == 6


class TestAssignClauseVersions:
    """Tests for assign_clause_versions method."""
    
    def test_assign_versions_with_unchanged_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test version assignment preserves version for unchanged clauses."""
        # Setup mock storage to return existing contract and clauses
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        # Create diff with unchanged clauses
        contract_diff = ContractDiff(
            unchanged_clauses=[
                ClauseComparison(
                    clause_identifier="scope_of_work",
                    change_type=ClauseChangeType.UNCHANGED,
                    old_content="Original scope of work content",
                    new_content="Original scope of work content",
                    similarity_score=1.0
                )
            ],
            modified_clauses=[],
            added_clauses=[],
            deleted_clauses=[],
            change_summary={"unchanged": 1, "modified": 0, "added": 0, "deleted": 0}
        )
        
        result = version_manager.assign_clause_versions(
            contract_diff,
            "contract-123",
            2
        )
        
        assert isinstance(result, VersionedContract)
        assert result.version == 2
        assert len(result.clauses) == 1
        
        # Unchanged clause should preserve version 1
        unchanged_clause = result.clauses[0]
        assert unchanged_clause.clause_version == 1
        assert unchanged_clause.clause_identifier == "scope_of_work"
    
    def test_assign_versions_with_modified_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test version assignment assigns new version to modified clauses."""
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        contract_diff = ContractDiff(
            unchanged_clauses=[],
            modified_clauses=[
                ClauseComparison(
                    clause_identifier="payment_terms",
                    change_type=ClauseChangeType.MODIFIED,
                    old_content="Original payment terms content",
                    new_content="Modified payment terms content",
                    similarity_score=0.85
                )
            ],
            added_clauses=[],
            deleted_clauses=[],
            change_summary={"unchanged": 0, "modified": 1, "added": 0, "deleted": 0}
        )
        
        result = version_manager.assign_clause_versions(
            contract_diff,
            "contract-123",
            2
        )
        
        assert len(result.clauses) == 1
        
        # Modified clause should get new version
        modified_clause = result.clauses[0]
        assert modified_clause.clause_version == 2
        assert modified_clause.clause_identifier == "payment_terms"
        assert modified_clause.content == "Modified payment terms content"
        assert "old_content" in modified_clause.metadata
    
    def test_assign_versions_with_added_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test version assignment assigns new version to added clauses."""
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        contract_diff = ContractDiff(
            unchanged_clauses=[],
            modified_clauses=[],
            added_clauses=[
                ClauseComparison(
                    clause_identifier="warranty",
                    change_type=ClauseChangeType.ADDED,
                    old_content=None,
                    new_content="New warranty clause content",
                    similarity_score=0.0
                )
            ],
            deleted_clauses=[],
            change_summary={"unchanged": 0, "modified": 0, "added": 1, "deleted": 0}
        )
        
        result = version_manager.assign_clause_versions(
            contract_diff,
            "contract-123",
            2
        )
        
        assert len(result.clauses) == 1
        
        # Added clause should get new version
        added_clause = result.clauses[0]
        assert added_clause.clause_version == 2
        assert added_clause.clause_identifier == "warranty"
        assert added_clause.content == "New warranty clause content"
        assert not added_clause.is_deleted
    
    def test_assign_versions_with_deleted_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test version assignment marks deleted clauses."""
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        contract_diff = ContractDiff(
            unchanged_clauses=[],
            modified_clauses=[],
            added_clauses=[],
            deleted_clauses=[
                ClauseComparison(
                    clause_identifier="scope_of_work",
                    change_type=ClauseChangeType.DELETED,
                    old_content="Original scope of work content",
                    new_content=None,
                    similarity_score=0.0
                )
            ],
            change_summary={"unchanged": 0, "modified": 0, "added": 0, "deleted": 1}
        )
        
        result = version_manager.assign_clause_versions(
            contract_diff,
            "contract-123",
            2
        )
        
        assert len(result.clauses) == 1
        
        # Deleted clause should be marked as deleted
        deleted_clause = result.clauses[0]
        assert deleted_clause.is_deleted
        assert deleted_clause.deleted_at is not None
        assert deleted_clause.clause_identifier == "scope_of_work"
    
    def test_assign_versions_creates_metadata(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test that version metadata is created correctly."""
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        contract_diff = ContractDiff(
            unchanged_clauses=[],
            modified_clauses=[
                ClauseComparison(
                    clause_identifier="payment_terms",
                    change_type=ClauseChangeType.MODIFIED,
                    old_content="Old",
                    new_content="New",
                    similarity_score=0.8
                )
            ],
            added_clauses=[],
            deleted_clauses=[],
            change_summary={"unchanged": 0, "modified": 1, "added": 0, "deleted": 0}
        )
        
        result = version_manager.assign_clause_versions(
            contract_diff,
            "contract-123",
            2
        )
        
        # Check version metadata
        assert result.version_metadata.contract_id == "contract-123"
        assert result.version_metadata.version == 2
        assert isinstance(result.version_metadata.timestamp, datetime)
        assert len(result.version_metadata.changed_clause_ids) == 1
        assert result.version_metadata.change_summary == contract_diff.change_summary


class TestGetVersionMetadata:
    """Tests for get_version_metadata method."""
    
    def test_get_version_metadata_success(self, version_manager, mock_storage):
        """Test retrieving version metadata successfully."""
        metadata = VersionMetadata(
            contract_id="contract-123",
            version=2,
            timestamp=datetime(2024, 1, 2, 10, 0, 0),
            changed_clause_ids=["clause-1", "clause-2"],
            change_summary={"modified": 2, "added": 0, "deleted": 0}
        )
        
        mock_storage.get_version_history.return_value = [metadata]
        
        result = version_manager.get_version_metadata("contract-123", 2)
        
        assert result == metadata
        mock_storage.get_version_history.assert_called_once_with("contract-123")
    
    def test_get_version_metadata_not_found(self, version_manager, mock_storage):
        """Test when version metadata is not found."""
        mock_storage.get_version_history.return_value = []
        
        result = version_manager.get_version_metadata("contract-123", 5)
        
        assert result is None


class TestReconstructVersion:
    """Tests for reconstruct_version method."""
    
    def test_reconstruct_version_1(
        self,
        version_manager,
        mock_storage,
        sample_contract,
        sample_clauses
    ):
        """Test reconstructing version 1 of a contract."""
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = sample_clauses
        
        metadata = VersionMetadata(
            contract_id="contract-123",
            version=1,
            timestamp=datetime(2024, 1, 1, 10, 0, 0),
            changed_clause_ids=["clause-1", "clause-2"],
            change_summary={"added": 2, "modified": 0, "deleted": 0}
        )
        mock_storage.get_version_history.return_value = [metadata]
        
        result = version_manager.reconstruct_version("contract-123", 1)
        
        assert result["contract_id"] == "contract-123"
        assert result["version"] == 1
        assert len(result["clauses"]) == 2
        assert result["version_metadata"] is not None
    
    def test_reconstruct_version_excludes_future_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract
    ):
        """Test that reconstruction excludes clauses added after the version."""
        # Create clauses with different versions
        clauses = [
            Clause(
                clause_id="clause-1",
                contract_id="contract-123",
                clause_version=1,
                clause_identifier="scope_of_work",
                content="Version 1 content",
                metadata={},
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                is_deleted=False,
                deleted_at=None
            ),
            Clause(
                clause_id="clause-2",
                contract_id="contract-123",
                clause_version=2,
                clause_identifier="warranty",
                content="Added in version 2",
                metadata={},
                created_at=datetime(2024, 1, 2, 10, 0, 0),
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        sample_contract.current_version = 2
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = clauses
        mock_storage.get_version_history.return_value = []
        
        result = version_manager.reconstruct_version("contract-123", 1)
        
        # Should only include clause from version 1
        assert len(result["clauses"]) == 1
        assert result["clauses"][0]["clause_identifier"] == "scope_of_work"
    
    def test_reconstruct_version_excludes_deleted_clauses(
        self,
        version_manager,
        mock_storage,
        sample_contract
    ):
        """Test that reconstruction excludes deleted clauses."""
        clauses = [
            Clause(
                clause_id="clause-1",
                contract_id="contract-123",
                clause_version=1,
                clause_identifier="scope_of_work",
                content="Content",
                metadata={},
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                is_deleted=True,
                deleted_at=datetime(2024, 1, 2, 10, 0, 0)
            )
        ]
        
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = clauses
        mock_storage.get_version_history.return_value = []
        
        result = version_manager.reconstruct_version("contract-123", 1)
        
        # Should exclude deleted clause
        assert len(result["clauses"]) == 0
    
    def test_reconstruct_version_invalid_version(
        self,
        version_manager,
        mock_storage,
        sample_contract
    ):
        """Test error when requesting invalid version number."""
        mock_storage.get_contract.return_value = sample_contract
        
        with pytest.raises(VersionManagerError, match="Invalid version"):
            version_manager.reconstruct_version("contract-123", 5)
    
    def test_reconstruct_version_contract_not_found(
        self,
        version_manager,
        mock_storage
    ):
        """Test error when contract not found."""
        mock_storage.get_contract.return_value = None
        
        with pytest.raises(VersionManagerError, match="Contract not found"):
            version_manager.reconstruct_version("nonexistent", 1)
    
    def test_reconstruct_version_takes_latest_clause_version(
        self,
        version_manager,
        mock_storage,
        sample_contract
    ):
        """Test that reconstruction takes the latest version of each clause."""
        # Create multiple versions of the same clause
        clauses = [
            Clause(
                clause_id="clause-1",
                contract_id="contract-123",
                clause_version=1,
                clause_identifier="scope_of_work",
                content="Version 1 content",
                metadata={},
                created_at=datetime(2024, 1, 1, 10, 0, 0),
                is_deleted=False,
                deleted_at=None
            ),
            Clause(
                clause_id="clause-1-v2",
                contract_id="contract-123",
                clause_version=2,
                clause_identifier="scope_of_work",
                content="Version 2 content",
                metadata={},
                created_at=datetime(2024, 1, 2, 10, 0, 0),
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        sample_contract.current_version = 2
        mock_storage.get_contract.return_value = sample_contract
        mock_storage.get_clauses.return_value = clauses
        mock_storage.get_version_history.return_value = []
        
        result = version_manager.reconstruct_version("contract-123", 2)
        
        # Should only include the latest version (version 2)
        assert len(result["clauses"]) == 1
        assert result["clauses"][0]["clause_version"] == 2
        assert result["clauses"][0]["content"] == "Version 2 content"
