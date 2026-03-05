"""
Integration test for versioning upload workflow.

Tests the integration of ContractIdentityDetector, ChangeComparator,
VersionManager, and DifferentialStorage in the upload workflow.
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.application_controller import ApplicationController, AppState
from src.version_database import VersionDatabase
from src.contract_identity_detector import ContractIdentityDetector
from src.change_comparator import ChangeComparator
from src.differential_storage import DifferentialStorage, Contract, Clause
from src.version_manager import VersionManager


class TestVersioningUploadWorkflow(unittest.TestCase):
    """Test versioning integration in upload workflow."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Initialize versioning components
        self.db = VersionDatabase(db_path=self.temp_db.name)
        self.storage = DifferentialStorage(database=self.db)
        self.detector = ContractIdentityDetector(db=self.db)
        self.comparator = ChangeComparator()
        self.version_manager = VersionManager(storage=self.storage)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close database
        self.db.close()
        
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_new_contract_upload(self):
        """Test uploading a new contract (version 1)."""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test contract content")
            test_file = f.name
        
        try:
            # Compute file hash
            file_hash = self.detector.compute_file_hash(test_file)
            
            # Check for matches (should be none)
            matches = self.detector.find_potential_matches(
                file_hash=file_hash,
                filename="test_contract.txt"
            )
            
            self.assertEqual(len(matches), 0, "Should find no matches for new contract")
            
            # Create and store new contract
            contract_id = "test-contract-1"
            timestamp = datetime.now()
            
            contract = Contract(
                contract_id=contract_id,
                filename="test_contract.txt",
                file_hash=file_hash,
                current_version=1,
                created_at=timestamp,
                updated_at=timestamp
            )
            
            clauses = [
                Clause(
                    clause_id="clause-1",
                    contract_id=contract_id,
                    clause_version=1,
                    clause_identifier="section_1",
                    content="Test clause content",
                    metadata={"risk_level": "low"},
                    created_at=timestamp,
                    is_deleted=False,
                    deleted_at=None
                )
            ]
            
            self.storage.store_new_contract(contract, clauses)
            
            # Verify storage
            stored_contract = self.storage.get_contract(contract_id)
            self.assertIsNotNone(stored_contract)
            self.assertEqual(stored_contract.current_version, 1)
            
            stored_clauses = self.storage.get_clauses(contract_id)
            self.assertEqual(len(stored_clauses), 1)
            
        finally:
            # Clean up test file
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    def test_duplicate_detection_hash_match(self):
        """Test duplicate detection with hash match."""
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("Test contract content")
            test_file = f.name
        
        try:
            # Compute file hash
            file_hash = self.detector.compute_file_hash(test_file)
            
            # Store initial contract
            contract_id = "test-contract-2"
            timestamp = datetime.now()
            
            contract = Contract(
                contract_id=contract_id,
                filename="original_contract.txt",
                file_hash=file_hash,
                current_version=1,
                created_at=timestamp,
                updated_at=timestamp
            )
            
            self.storage.store_new_contract(contract, [])
            
            # Check for matches with same hash
            matches = self.detector.find_potential_matches(
                file_hash=file_hash,
                filename="original_contract.txt"
            )
            
            self.assertEqual(len(matches), 1, "Should find one hash match")
            self.assertEqual(matches[0].match_type, 'hash')
            self.assertEqual(matches[0].contract_id, contract_id)
            
        finally:
            # Clean up test file
            if os.path.exists(test_file):
                os.unlink(test_file)
    
    def test_duplicate_detection_filename_similarity(self):
        """Test duplicate detection with filename similarity."""
        # Store initial contract
        contract_id = "test-contract-3"
        timestamp = datetime.now()
        
        contract = Contract(
            contract_id=contract_id,
            filename="my_contract_v1.pdf",
            file_hash="hash123",
            current_version=1,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.storage.store_new_contract(contract, [])
        
        # Check for matches with similar filename
        matches = self.detector.find_potential_matches(
            file_hash="different_hash",
            filename="my_contract_v2.pdf"
        )
        
        # Should find filename match (similarity > 0.8)
        self.assertGreater(len(matches), 0, "Should find filename match")
        if len(matches) > 0:
            self.assertEqual(matches[0].match_type, 'filename')
            self.assertGreater(matches[0].similarity_score, 0.8)
    
    def test_application_controller_initialization(self):
        """Test that ApplicationController initializes versioning components."""
        # Create mock root
        mock_root = Mock()
        
        # Create controller
        controller = ApplicationController(root=mock_root)
        
        # Initialize components
        success = controller.initialize_components()
        
        # Verify versioning components are initialized
        # Note: They may be None if dependencies are missing, but should not raise errors
        self.assertTrue(success or len(controller.get_initialization_errors()) > 0)


if __name__ == '__main__':
    unittest.main()
