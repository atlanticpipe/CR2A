"""
Final integration test for Contract Change Tracking & Differential Versioning.

This test verifies that all components (ContractIdentityDetector, ChangeComparator,
VersionManager, and DifferentialStorage) work together seamlessly with the existing
CR2A application components.

Tests the complete workflow:
1. Upload new contract (version 1)
2. Upload updated contract (version 2) with duplicate detection
3. View version history
4. Compare versions
5. Retrieve historical versions
"""

import unittest
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from src.application_controller import ApplicationController, AppState, ApplicationContext
from src.version_database import VersionDatabase
from src.contract_identity_detector import ContractIdentityDetector
from src.change_comparator import ChangeComparator, ContractDiff, ClauseChangeType
from src.differential_storage import DifferentialStorage, Contract, Clause
from src.version_manager import VersionManager


class TestFinalIntegration(unittest.TestCase):
    """Test complete integration of all versioning components."""
    
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
        
        # Create test files
        self.test_file_v1 = self._create_test_file("Contract v1 content\nClause 1: Original text")
        self.test_file_v2 = self._create_test_file("Contract v2 content\nClause 1: Modified text\nClause 2: New clause")
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close database
        self.db.close()
        
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        
        # Remove test files
        for f in [self.test_file_v1, self.test_file_v2]:
            if os.path.exists(f):
                os.unlink(f)
    
    def _create_test_file(self, content: str) -> str:
        """Create a temporary test file with given content."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write(content)
            return f.name
    
    def test_complete_workflow_new_contract(self):
        """Test complete workflow for uploading a new contract."""
        # Step 1: Compute file hash
        file_hash = self.detector.compute_file_hash(self.test_file_v1)
        self.assertIsNotNone(file_hash)
        self.assertGreater(len(file_hash), 0)
        
        # Step 2: Check for duplicates (should be none)
        matches = self.detector.find_potential_matches(
            file_hash=file_hash,
            filename="test_contract.txt"
        )
        self.assertEqual(len(matches), 0, "Should find no matches for new contract")
        
        # Step 3: Create and store new contract (version 1)
        contract_id = "contract-001"
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
                clause_identifier="clause_1",
                content="Original text",
                metadata={"risk_level": "low"},
                created_at=timestamp,
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        self.storage.store_new_contract(contract, clauses)
        
        # Step 4: Verify storage
        stored_contract = self.storage.get_contract(contract_id)
        self.assertIsNotNone(stored_contract)
        self.assertEqual(stored_contract.current_version, 1)
        self.assertEqual(stored_contract.filename, "test_contract.txt")
        
        stored_clauses = self.storage.get_clauses(contract_id)
        self.assertEqual(len(stored_clauses), 1)
        self.assertEqual(stored_clauses[0].clause_version, 1)
    
    def test_complete_workflow_updated_contract(self):
        """Test complete workflow for uploading an updated contract."""
        # Setup: Store initial contract (version 1)
        contract_id = "contract-002"
        timestamp_v1 = datetime.now()
        file_hash_v1 = self.detector.compute_file_hash(self.test_file_v1)
        
        contract_v1 = Contract(
            contract_id=contract_id,
            filename="test_contract.txt",
            file_hash=file_hash_v1,
            current_version=1,
            created_at=timestamp_v1,
            updated_at=timestamp_v1
        )
        
        clauses_v1 = [
            Clause(
                clause_id="clause-1",
                contract_id=contract_id,
                clause_version=1,
                clause_identifier="clause_1",
                content="Original text",
                metadata={"risk_level": "low"},
                created_at=timestamp_v1,
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        self.storage.store_new_contract(contract_v1, clauses_v1)
        
        # Step 1: Upload updated contract - compute hash
        file_hash_v2 = self.detector.compute_file_hash(self.test_file_v2)
        
        # Step 2: Check for duplicates (should find filename match)
        matches = self.detector.find_potential_matches(
            file_hash=file_hash_v2,
            filename="test_contract.txt"
        )
        self.assertGreater(len(matches), 0, "Should find filename match")
        self.assertEqual(matches[0].contract_id, contract_id)
        
        # Step 3: Get next version number
        next_version = self.version_manager.get_next_version(contract_id)
        self.assertEqual(next_version, 2)
        
        # Step 4: Store version 2 with changed clauses
        timestamp_v2 = datetime.now()
        
        changed_clauses = [
            Clause(
                clause_id="clause-1-v2",
                contract_id=contract_id,
                clause_version=2,
                clause_identifier="clause_1",
                content="Modified text",
                metadata={"risk_level": "low"},
                created_at=timestamp_v2,
                is_deleted=False,
                deleted_at=None
            ),
            Clause(
                clause_id="clause-2",
                contract_id=contract_id,
                clause_version=2,
                clause_identifier="clause_2",
                content="New clause",
                metadata={"risk_level": "medium"},
                created_at=timestamp_v2,
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        from src.version_manager import VersionMetadata
        version_metadata = VersionMetadata(
            contract_id=contract_id,
            version=2,
            timestamp=timestamp_v2,
            changed_clause_ids=["clause-1-v2", "clause-2"],
            change_summary={"modified": 1, "added": 1, "deleted": 0}
        )
        
        self.storage.store_contract_version(
            contract_id=contract_id,
            version=2,
            changed_clauses=changed_clauses,
            version_metadata=version_metadata
        )
        
        # Step 5: Verify version 2 storage
        stored_contract = self.storage.get_contract(contract_id)
        self.assertEqual(stored_contract.current_version, 2)
        
        all_clauses = self.storage.get_clauses(contract_id)
        self.assertEqual(len(all_clauses), 3, "Should have 3 clause records (1 original + 2 new)")
        
        # Step 6: Retrieve version history
        version_history = self.storage.get_version_history(contract_id)
        self.assertEqual(len(version_history), 2, "Should have 2 version metadata records")
        self.assertEqual(version_history[1].version, 2)
        self.assertEqual(version_history[1].change_summary['modified'], 1)
        self.assertEqual(version_history[1].change_summary['added'], 1)
    
    def test_version_reconstruction(self):
        """Test reconstructing historical versions."""
        # Setup: Create contract with multiple versions
        contract_id = "contract-003"
        timestamp_v1 = datetime.now()
        
        # Version 1
        contract_v1 = Contract(
            contract_id=contract_id,
            filename="test_contract.txt",
            file_hash="hash1",
            current_version=1,
            created_at=timestamp_v1,
            updated_at=timestamp_v1
        )
        
        clauses_v1 = [
            Clause(
                clause_id="clause-1",
                contract_id=contract_id,
                clause_version=1,
                clause_identifier="clause_1",
                content="Version 1 text",
                metadata={},
                created_at=timestamp_v1,
                is_deleted=False,
                deleted_at=None
            ),
            Clause(
                clause_id="clause-2",
                contract_id=contract_id,
                clause_version=1,
                clause_identifier="clause_2",
                content="Clause 2 original",
                metadata={},
                created_at=timestamp_v1,
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        self.storage.store_new_contract(contract_v1, clauses_v1)
        
        # Version 2: Modify clause 1, add clause 3
        timestamp_v2 = datetime.now()
        
        changed_clauses_v2 = [
            Clause(
                clause_id="clause-1-v2",
                contract_id=contract_id,
                clause_version=2,
                clause_identifier="clause_1",
                content="Version 2 text",
                metadata={},
                created_at=timestamp_v2,
                is_deleted=False,
                deleted_at=None
            ),
            Clause(
                clause_id="clause-3",
                contract_id=contract_id,
                clause_version=2,
                clause_identifier="clause_3",
                content="New clause in v2",
                metadata={},
                created_at=timestamp_v2,
                is_deleted=False,
                deleted_at=None
            )
        ]
        
        from src.version_manager import VersionMetadata
        version_metadata_v2 = VersionMetadata(
            contract_id=contract_id,
            version=2,
            timestamp=timestamp_v2,
            changed_clause_ids=["clause-1-v2", "clause-3"],
            change_summary={"modified": 1, "added": 1, "deleted": 0}
        )
        
        self.storage.store_contract_version(
            contract_id=contract_id,
            version=2,
            changed_clauses=changed_clauses_v2,
            version_metadata=version_metadata_v2
        )
        
        # Reconstruct version 1
        reconstructed_v1 = self.version_manager.reconstruct_version(contract_id, 1)
        
        self.assertEqual(len(reconstructed_v1['clauses']), 2, "Version 1 should have 2 clauses")
        
        # Verify clause content for v1
        clause_contents = {c['clause_identifier']: c['content'] for c in reconstructed_v1['clauses']}
        self.assertEqual(clause_contents['clause_1'], "Version 1 text")
        self.assertEqual(clause_contents['clause_2'], "Clause 2 original")
        self.assertNotIn('clause_3', clause_contents, "Clause 3 should not exist in v1")
        
        # Reconstruct version 2
        reconstructed_v2 = self.version_manager.reconstruct_version(contract_id, 2)
        
        self.assertEqual(len(reconstructed_v2['clauses']), 3, "Version 2 should have 3 clauses")
        
        # Verify clause content for v2
        clause_contents_v2 = {c['clause_identifier']: c['content'] for c in reconstructed_v2['clauses']}
        self.assertEqual(clause_contents_v2['clause_1'], "Version 2 text")
        self.assertEqual(clause_contents_v2['clause_2'], "Clause 2 original")
        self.assertEqual(clause_contents_v2['clause_3'], "New clause in v2")
    
    def test_application_controller_versioning_integration(self):
        """Test that ApplicationController properly integrates versioning components."""
        # Create mock root
        mock_root = Mock()
        
        # Create controller
        controller = ApplicationController(root=mock_root)
        
        # Initialize components
        success = controller.initialize_components()
        
        # Verify versioning components are initialized
        self.assertIsNotNone(controller.version_db, "VersionDatabase should be initialized")
        self.assertIsNotNone(controller.differential_storage, "DifferentialStorage should be initialized")
        self.assertIsNotNone(controller.contract_identity_detector, "ContractIdentityDetector should be initialized")
        self.assertIsNotNone(controller.change_comparator, "ChangeComparator should be initialized")
        self.assertIsNotNone(controller.version_manager, "VersionManager should be initialized")
    
    def test_application_controller_duplicate_detection_flow(self):
        """Test duplicate detection flow in ApplicationController."""
        # Create mock root
        mock_root = Mock()
        
        # Create controller with isolated database
        controller = ApplicationController(root=mock_root)
        
        # Initialize with a temporary database for this test
        temp_db_test = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db_test.close()
        
        try:
            # Override versioning components with test database
            from src.version_database import VersionDatabase
            from src.contract_identity_detector import ContractIdentityDetector
            from src.differential_storage import DifferentialStorage
            from src.version_manager import VersionManager
            from src.change_comparator import ChangeComparator
            
            test_db = VersionDatabase(db_path=temp_db_test.name)
            controller.version_db = test_db
            controller.differential_storage = DifferentialStorage(database=test_db)
            controller.contract_identity_detector = ContractIdentityDetector(db=test_db)
            controller.change_comparator = ChangeComparator()
            controller.version_manager = VersionManager(storage=controller.differential_storage)
            
            # Store a contract in the database
            contract_id = "contract-004"
            timestamp = datetime.now()
            file_hash = controller.contract_identity_detector.compute_file_hash(self.test_file_v1)
            
            contract = Contract(
                contract_id=contract_id,
                filename="existing_contract.txt",
                file_hash=file_hash,
                current_version=1,
                created_at=timestamp,
                updated_at=timestamp
            )
            
            controller.differential_storage.store_new_contract(contract, [])
            
            # Mock the messagebox to simulate user confirmation
            with patch('tkinter.messagebox.askyesno', return_value=True):
                # Simulate transition_to_analysis with the same file
                controller.context = ApplicationContext(current_state=AppState.UPLOAD)
                controller.transition_to_analysis(self.test_file_v1)
                
                # Verify context is updated with version info
                self.assertTrue(controller.context.is_version_update, "Should be marked as version update")
                self.assertEqual(controller.context.matched_contract_id, contract_id)
                self.assertEqual(controller.context.matched_contract_version, 1)
            
            # Clean up
            test_db.close()
        finally:
            if os.path.exists(temp_db_test.name):
                os.unlink(temp_db_test.name)
    
    def test_error_handling_missing_contract(self):
        """Test error handling when trying to access non-existent contract."""
        # DifferentialStorage returns None for missing contracts, not ValueError
        result = self.storage.get_contract("non-existent-contract")
        self.assertIsNone(result, "Should return None for non-existent contract")
    
    def test_error_handling_invalid_version(self):
        """Test error handling when trying to reconstruct invalid version."""
        # Store a contract with version 1
        contract_id = "contract-005"
        timestamp = datetime.now()
        
        contract = Contract(
            contract_id=contract_id,
            filename="test.txt",
            file_hash="hash",
            current_version=1,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        self.storage.store_new_contract(contract, [])
        
        # Try to reconstruct version 5 (doesn't exist)
        # VersionManager raises VersionManagerError, not ValueError
        from src.version_manager import VersionManagerError
        with self.assertRaises(VersionManagerError):
            self.version_manager.reconstruct_version(contract_id, 5)


if __name__ == '__main__':
    unittest.main()
