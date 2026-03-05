"""
Unit tests for error handling and validation (Task 11.1).

Tests error scenarios for all components:
- File hash computation failure
- Storage transaction failure and rollback
- Invalid version number rejection
- Referential integrity violation handling
"""

import pytest
import sqlite3
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.contract_identity_detector import ContractIdentityDetector
from src.change_comparator import ChangeComparator
from src.version_manager import VersionManager, VersionManagerError
from src.differential_storage import (
    DifferentialStorage,
    DifferentialStorageError,
    Contract,
    Clause,
    VersionMetadata
)
from src.version_database import VersionDatabase, VersionDatabaseError
from src.analysis_models import (
    ComprehensiveAnalysisResult,
    AdministrativeAndCommercialTerms,
    TechnicalAndPerformanceTerms,
    LegalRiskAndEnforcement,
    RegulatoryAndComplianceTerms,
    DataTechnologyAndDeliverables
)


class TestContractIdentityDetectorErrors:
    """Test error handling in ContractIdentityDetector."""
    
    def test_compute_file_hash_file_not_found(self):
        """Test file hash computation with non-existent file."""
        db = VersionDatabase()
        detector = ContractIdentityDetector(db)
        
        with pytest.raises(FileNotFoundError):
            detector.compute_file_hash("nonexistent_file.pdf")
    
    def test_compute_file_hash_io_error(self):
        """Test file hash computation with unreadable file."""
        db = VersionDatabase()
        detector = ContractIdentityDetector(db)
        
        # Create a file and then make it unreadable
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            # Mock open to raise IOError
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with pytest.raises(IOError, match="Failed to compute file hash"):
                    detector.compute_file_hash(temp_path)
        finally:
            Path(temp_path).unlink(missing_ok=True)
    
    def test_find_potential_matches_invalid_hash(self):
        """Test finding matches with invalid file hash."""
        db = VersionDatabase()
        detector = ContractIdentityDetector(db)
        
        with pytest.raises(ValueError, match="file_hash must be a non-empty string"):
            detector.find_potential_matches("", "test.pdf")
        
        with pytest.raises(ValueError, match="file_hash must be a non-empty string"):
            detector.find_potential_matches(None, "test.pdf")
    
    def test_find_potential_matches_invalid_filename(self):
        """Test finding matches with invalid filename."""
        db = VersionDatabase()
        detector = ContractIdentityDetector(db)
        
        with pytest.raises(ValueError, match="filename must be a non-empty string"):
            detector.find_potential_matches("abc123", "")
        
        with pytest.raises(ValueError, match="filename must be a non-empty string"):
            detector.find_potential_matches("abc123", None)
    
    def test_find_potential_matches_database_error(self):
        """Test finding matches with database error (should return empty list)."""
        db = Mock()
        db.execute.side_effect = sqlite3.Error("Database error")
        
        detector = ContractIdentityDetector(db)
        
        # Should return empty list instead of raising
        matches = detector.find_potential_matches("abc123", "test.pdf")
        assert matches == []


class TestChangeComparatorErrors:
    """Test error handling in ChangeComparator."""
    
    def test_compare_contracts_none_old_analysis(self):
        """Test contract comparison with None old_analysis."""
        comparator = ChangeComparator()
        
        # Create a minimal valid new_analysis (just need it to not be None)
        new_analysis = Mock()
        
        with pytest.raises(ValueError, match="old_analysis cannot be None"):
            comparator.compare_contracts(None, new_analysis)
    
    def test_compare_contracts_none_new_analysis(self):
        """Test contract comparison with None new_analysis."""
        comparator = ChangeComparator()
        
        # Create a minimal valid old_analysis (just need it to not be None)
        old_analysis = Mock()
        
        with pytest.raises(ValueError, match="new_analysis cannot be None"):
            comparator.compare_contracts(old_analysis, None)


class TestVersionManagerErrors:
    """Test error handling in VersionManager."""
    
    def test_get_next_version_contract_not_found(self):
        """Test getting next version for non-existent contract."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        with pytest.raises(VersionManagerError, match="Contract not found"):
            manager.get_next_version("nonexistent_id")
    
    def test_assign_clause_versions_none_diff(self):
        """Test assigning versions with None contract_diff."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        with pytest.raises(ValueError, match="contract_diff cannot be None"):
            manager.assign_clause_versions(None, "contract_id", 2)
    
    def test_assign_clause_versions_invalid_contract_id(self):
        """Test assigning versions with invalid contract_id."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        from src.change_comparator import ContractDiff
        diff = ContractDiff([], [], [], [], {})
        
        with pytest.raises(ValueError, match="contract_id must be a non-empty string"):
            manager.assign_clause_versions(diff, "", 2)
        
        with pytest.raises(ValueError, match="contract_id must be a non-empty string"):
            manager.assign_clause_versions(diff, None, 2)
    
    def test_assign_clause_versions_invalid_version(self):
        """Test assigning versions with invalid version number."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        from src.change_comparator import ContractDiff
        diff = ContractDiff([], [], [], [], {})
        
        with pytest.raises(ValueError, match="new_version must be a positive integer"):
            manager.assign_clause_versions(diff, "contract_id", 0)
        
        with pytest.raises(ValueError, match="new_version must be a positive integer"):
            manager.assign_clause_versions(diff, "contract_id", -1)
    
    def test_assign_clause_versions_non_sequential(self):
        """Test assigning non-sequential version number (Requirement 8.1)."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        # Create a contract with version 1
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        storage.store_new_contract(contract, [])
        
        # Try to assign version 3 (should be 2)
        from src.change_comparator import ContractDiff
        diff = ContractDiff([], [], [], [], {})
        
        # Should raise ValueError (not VersionManagerError) for validation errors
        with pytest.raises((ValueError, VersionManagerError), match="Version number must be sequential"):
            manager.assign_clause_versions(diff, contract_id, 3)
    
    def test_reconstruct_version_invalid_version(self):
        """Test reconstructing with invalid version number."""
        storage = DifferentialStorage()
        manager = VersionManager(storage)
        
        # Create a contract with version 1
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        storage.store_new_contract(contract, [])
        
        # Try to reconstruct version 0 (invalid)
        with pytest.raises(VersionManagerError, match="Invalid version"):
            manager.reconstruct_version(contract_id, 0)
        
        # Try to reconstruct version 5 (doesn't exist)
        with pytest.raises(VersionManagerError, match="Invalid version"):
            manager.reconstruct_version(contract_id, 5)


class TestDifferentialStorageErrors:
    """Test error handling in DifferentialStorage."""
    
    def test_store_new_contract_none_contract(self):
        """Test storing with None contract."""
        storage = DifferentialStorage()
        
        with pytest.raises(ValueError, match="contract cannot be None"):
            storage.store_new_contract(None, [])
    
    def test_store_new_contract_invalid_contract_id(self):
        """Test storing with invalid contract_id."""
        storage = DifferentialStorage()
        
        contract = Contract(
            contract_id="",
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="contract_id must be a non-empty string"):
            storage.store_new_contract(contract, [])
    
    def test_store_new_contract_invalid_version(self):
        """Test storing new contract with version != 1."""
        storage = DifferentialStorage()
        
        contract = Contract(
            contract_id=str(uuid.uuid4()),
            filename="test.pdf",
            file_hash="abc123",
            current_version=2,  # Should be 1
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="New contract must have version 1"):
            storage.store_new_contract(contract, [])
    
    def test_store_new_contract_none_clauses(self):
        """Test storing with None clauses."""
        storage = DifferentialStorage()
        
        contract = Contract(
            contract_id=str(uuid.uuid4()),
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="clauses cannot be None"):
            storage.store_new_contract(contract, None)
    
    def test_store_new_contract_clause_missing_id(self):
        """Test storing with clause missing clause_id (Requirement 8.2)."""
        storage = DifferentialStorage()
        
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        clause = Clause(
            clause_id="",  # Invalid
            contract_id=contract_id,
            clause_version=1,
            clause_identifier="test",
            content="test content",
            metadata={},
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="All clauses must have a clause_id"):
            storage.store_new_contract(contract, [clause])
    
    def test_store_new_contract_clause_contract_id_mismatch(self):
        """Test storing with clause contract_id mismatch (Requirement 8.2)."""
        storage = DifferentialStorage()
        
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        clause = Clause(
            clause_id=str(uuid.uuid4()),
            contract_id="different_id",  # Mismatch
            clause_version=1,
            clause_identifier="test",
            content="test content",
            metadata={},
            created_at=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Clause contract_id must match contract"):
            storage.store_new_contract(contract, [clause])
    
    def test_store_new_contract_transaction_rollback(self):
        """Test transaction rollback on storage failure (Requirement 8.3)."""
        storage = DifferentialStorage()
        
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create a valid clause
        clause = Clause(
            clause_id=str(uuid.uuid4()),
            contract_id=contract_id,
            clause_version=1,
            clause_identifier="test",
            content="test content",
            metadata={},
            created_at=datetime.now()
        )
        
        # Mock the database to fail during clause insertion
        with patch.object(storage.db, 'connect') as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            
            # First execute succeeds (contract insert), second fails (clause insert)
            mock_cursor.execute.side_effect = [None, sqlite3.Error("Simulated error")]
            
            with pytest.raises(DifferentialStorageError):
                storage.store_new_contract(contract, [clause])
            
            # Verify rollback was called
            mock_conn.rollback.assert_called_once()
    
    def test_store_contract_version_invalid_inputs(self):
        """Test storing version with invalid inputs."""
        storage = DifferentialStorage()
        
        version_metadata = VersionMetadata(
            contract_id="test_id",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=[],
            change_summary={}
        )
        
        # Invalid contract_id
        with pytest.raises(ValueError, match="contract_id must be a non-empty string"):
            storage.store_contract_version("", 2, [], version_metadata)
        
        # Invalid version
        with pytest.raises(ValueError, match="version must be an integer >= 2"):
            storage.store_contract_version("test_id", 1, [], version_metadata)
        
        # None clauses
        with pytest.raises(ValueError, match="changed_clauses cannot be None"):
            storage.store_contract_version("test_id", 2, None, version_metadata)
        
        # None metadata
        with pytest.raises(ValueError, match="version_metadata cannot be None"):
            storage.store_contract_version("test_id", 2, [], None)
    
    def test_store_contract_version_metadata_mismatch(self):
        """Test storing version with metadata mismatch (Requirement 8.2)."""
        storage = DifferentialStorage()
        
        version_metadata = VersionMetadata(
            contract_id="different_id",  # Mismatch
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=[],
            change_summary={}
        )
        
        with pytest.raises(ValueError, match="version_metadata contract_id must match"):
            storage.store_contract_version("test_id", 2, [], version_metadata)
        
        version_metadata = VersionMetadata(
            contract_id="test_id",
            version=3,  # Mismatch
            timestamp=datetime.now(),
            changed_clause_ids=[],
            change_summary={}
        )
        
        with pytest.raises(ValueError, match="version_metadata version must match"):
            storage.store_contract_version("test_id", 2, [], version_metadata)
    
    def test_store_contract_version_non_sequential(self):
        """Test storing non-sequential version (Requirement 8.1)."""
        storage = DifferentialStorage()
        
        # Create a contract with version 1
        contract_id = str(uuid.uuid4())
        contract = Contract(
            contract_id=contract_id,
            filename="test.pdf",
            file_hash="abc123",
            current_version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        storage.store_new_contract(contract, [])
        
        # Try to store version 3 (should be 2)
        version_metadata = VersionMetadata(
            contract_id=contract_id,
            version=3,
            timestamp=datetime.now(),
            changed_clause_ids=[],
            change_summary={}
        )
        
        with pytest.raises(ValueError, match="Version must be sequential"):
            storage.store_contract_version(contract_id, 3, [], version_metadata)
    
    def test_store_contract_version_contract_not_found(self):
        """Test storing version for non-existent contract."""
        storage = DifferentialStorage()
        
        version_metadata = VersionMetadata(
            contract_id="nonexistent",
            version=2,
            timestamp=datetime.now(),
            changed_clause_ids=[],
            change_summary={}
        )
        
        with pytest.raises(DifferentialStorageError, match="Contract nonexistent not found"):
            storage.store_contract_version("nonexistent", 2, [], version_metadata)


class TestVersionDatabaseErrors:
    """Test error handling in VersionDatabase."""
    
    def test_referential_integrity_violation(self):
        """Test referential integrity violation handling (Requirement 8.4)."""
        db = VersionDatabase()
        
        # Try to insert a clause with non-existent contract_id
        with pytest.raises(VersionDatabaseError, match="Referential integrity violation"):
            db.execute("""
                INSERT INTO clauses (
                    clause_id, contract_id, clause_version, content, created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                "nonexistent_contract",
                1,
                "test content",
                datetime.now().isoformat()
            ))
    
    def test_unique_constraint_violation(self):
        """Test unique constraint violation handling."""
        # Use a fresh database instance for this test
        tmpdir = tempfile.mkdtemp()
        try:
            db_path = Path(tmpdir) / "test.db"
            db = VersionDatabase(db_path)
            
            # Insert a contract
            contract_id = str(uuid.uuid4())
            db.execute("""
                INSERT INTO contracts (
                    contract_id, filename, file_hash, current_version,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                contract_id,
                "test.pdf",
                "abc123",
                1,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            db.commit()
            
            # Try to insert the same contract again
            with pytest.raises(VersionDatabaseError, match="Unique constraint violation"):
                db.execute("""
                    INSERT INTO contracts (
                        contract_id, filename, file_hash, current_version,
                        created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    contract_id,
                    "test.pdf",
                    "abc123",
                    1,
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))
            
            db.close()
        finally:
            # Clean up
            import shutil
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except:
                pass
    
    def test_connection_failure(self):
        """Test database connection failure handling."""
        # Create database with invalid path
        with patch('sqlite3.connect', side_effect=sqlite3.Error("Connection failed")):
            with pytest.raises(VersionDatabaseError, match="Failed to connect to database"):
                db = VersionDatabase()
                db.connection = None  # Force reconnection
                db.connect()
    
    def test_commit_failure(self):
        """Test commit failure handling."""
        # Use a fresh database instance
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = VersionDatabase(db_path)
            
            # Close the connection to simulate a failure scenario
            db.close()
            
            # Try to commit without a connection
            with pytest.raises(VersionDatabaseError, match="Commit failed"):
                # Mock the connection to raise an error
                db.connection = Mock()
                db.connection.commit.side_effect = sqlite3.Error("Commit failed")
                db.commit()
    
    def test_rollback_failure(self):
        """Test rollback failure handling."""
        # Use a fresh database instance
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = VersionDatabase(db_path)
            
            # Close the connection to simulate a failure scenario
            db.close()
            
            # Try to rollback without a connection
            with pytest.raises(VersionDatabaseError, match="Rollback failed"):
                # Mock the connection to raise an error
                db.connection = Mock()
                db.connection.rollback.side_effect = sqlite3.Error("Rollback failed")
                db.rollback()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
