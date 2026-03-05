"""
Unit tests for ContractIdentityDetector.

Tests file hashing, filename similarity, and duplicate detection functionality.
"""

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

from src.contract_identity_detector import ContractIdentityDetector, ContractMatch
from src.version_database import VersionDatabase


class TestContractIdentityDetector(unittest.TestCase):
    """Test cases for ContractIdentityDetector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create temporary database for testing
        self.temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db_file.close()
        
        self.db = VersionDatabase(Path(self.temp_db_file.name))
        self.detector = ContractIdentityDetector(self.db)
        
        # Create temporary test files
        self.temp_files = []
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Close database connection
        self.db.close()
        
        # Remove temporary database file
        if os.path.exists(self.temp_db_file.name):
            os.unlink(self.temp_db_file.name)
        
        # Remove temporary test files
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def _create_temp_file(self, content: bytes, suffix: str = '.txt') -> str:
        """Create a temporary file with given content."""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(content)
        temp_file.close()
        self.temp_files.append(temp_file.name)
        return temp_file.name
    
    def test_compute_file_hash_consistency(self):
        """Test that computing hash multiple times produces same result."""
        content = b"Test contract content"
        file_path = self._create_temp_file(content)
        
        hash1 = self.detector.compute_file_hash(file_path)
        hash2 = self.detector.compute_file_hash(file_path)
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA-256 produces 64 hex characters
    
    def test_compute_file_hash_known_value(self):
        """Test hash computation against known SHA-256 value."""
        content = b"Hello, World!"
        expected_hash = hashlib.sha256(content).hexdigest()
        
        file_path = self._create_temp_file(content)
        computed_hash = self.detector.compute_file_hash(file_path)
        
        self.assertEqual(computed_hash, expected_hash)
    
    def test_compute_file_hash_empty_file(self):
        """Test hash computation for empty file."""
        file_path = self._create_temp_file(b"")
        
        hash_value = self.detector.compute_file_hash(file_path)
        
        # SHA-256 of empty string
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(hash_value, expected)
    
    def test_compute_file_hash_large_file(self):
        """Test hash computation for large file (tests chunked reading)."""
        # Create 1MB file
        content = b"x" * (1024 * 1024)
        file_path = self._create_temp_file(content)
        
        hash_value = self.detector.compute_file_hash(file_path)
        expected = hashlib.sha256(content).hexdigest()
        
        self.assertEqual(hash_value, expected)
    
    def test_compute_file_hash_nonexistent_file(self):
        """Test that computing hash of nonexistent file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.detector.compute_file_hash("/nonexistent/file.txt")
    
    def test_calculate_filename_similarity_identical(self):
        """Test filename similarity for identical names."""
        similarity = self.detector.calculate_filename_similarity(
            "contract.pdf",
            "contract.pdf"
        )
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_filename_similarity_different_extensions(self):
        """Test filename similarity ignores extensions."""
        similarity = self.detector.calculate_filename_similarity(
            "contract.pdf",
            "contract.docx"
        )
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_filename_similarity_case_insensitive(self):
        """Test filename similarity is case-insensitive."""
        similarity = self.detector.calculate_filename_similarity(
            "Contract.pdf",
            "contract.pdf"
        )
        self.assertEqual(similarity, 1.0)
    
    def test_calculate_filename_similarity_high_similarity(self):
        """Test filename similarity for similar names."""
        similarity = self.detector.calculate_filename_similarity(
            "contract_v1.pdf",
            "contract_v2.pdf"
        )
        # Should be high similarity (only 1 character different)
        self.assertGreater(similarity, 0.8)
    
    def test_calculate_filename_similarity_low_similarity(self):
        """Test filename similarity for different names."""
        similarity = self.detector.calculate_filename_similarity(
            "contract.pdf",
            "agreement.pdf"
        )
        # Should be low similarity
        self.assertLess(similarity, 0.8)
    
    def test_calculate_filename_similarity_empty_strings(self):
        """Test filename similarity with empty strings."""
        similarity = self.detector.calculate_filename_similarity("", "contract.pdf")
        self.assertEqual(similarity, 0.0)
        
        similarity = self.detector.calculate_filename_similarity("contract.pdf", "")
        self.assertEqual(similarity, 0.0)
    
    def test_calculate_filename_similarity_special_characters(self):
        """Test filename similarity with special characters."""
        similarity = self.detector.calculate_filename_similarity(
            "contract-2024.pdf",
            "contract_2024.pdf"
        )
        # Should be high similarity (only punctuation different)
        self.assertGreater(similarity, 0.8)
    
    def test_find_potential_matches_hash_match(self):
        """Test finding matches by file hash."""
        # Insert a contract into database
        content = b"Test contract content"
        file_path = self._create_temp_file(content)
        file_hash = self.detector.compute_file_hash(file_path)
        
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_1', 'original.pdf', file_hash, 1))
        self.db.commit()
        
        # Find matches for same hash
        matches = self.detector.find_potential_matches(file_hash, 'duplicate.pdf')
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].contract_id, 'contract_1')
        self.assertEqual(matches[0].match_type, 'hash')
        self.assertEqual(matches[0].similarity_score, 1.0)
    
    def test_find_potential_matches_filename_match(self):
        """Test finding matches by filename similarity."""
        # Insert a contract with different hash
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_1', 'contract_v1.pdf', 'hash123', 1))
        self.db.commit()
        
        # Find matches for similar filename but different hash
        matches = self.detector.find_potential_matches('hash456', 'contract_v2.pdf')
        
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].contract_id, 'contract_1')
        self.assertEqual(matches[0].match_type, 'filename')
        self.assertGreater(matches[0].similarity_score, 0.8)
    
    def test_find_potential_matches_no_matches(self):
        """Test finding matches when none exist."""
        # Insert a contract with different hash and filename
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_1', 'agreement.pdf', 'hash123', 1))
        self.db.commit()
        
        # Find matches for completely different file
        matches = self.detector.find_potential_matches('hash456', 'invoice.pdf')
        
        self.assertEqual(len(matches), 0)
    
    def test_find_potential_matches_multiple_filename_matches(self):
        """Test finding multiple filename matches sorted by similarity."""
        # Insert multiple contracts
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_1', 'contract_v1.pdf', 'hash1', 1))
        
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_2', 'contract_v2.pdf', 'hash2', 1))
        
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_3', 'contract.pdf', 'hash3', 1))
        
        self.db.commit()
        
        # Find matches for similar filename
        matches = self.detector.find_potential_matches('hash4', 'contract_v3.pdf')
        
        # Should find multiple matches, sorted by similarity
        self.assertGreater(len(matches), 0)
        
        # Verify sorting (higher similarity first)
        for i in range(len(matches) - 1):
            self.assertGreaterEqual(
                matches[i].similarity_score,
                matches[i + 1].similarity_score
            )
    
    def test_find_potential_matches_hash_priority_over_filename(self):
        """Test that hash matches take priority over filename matches."""
        content = b"Test content"
        file_path = self._create_temp_file(content)
        file_hash = self.detector.compute_file_hash(file_path)
        
        # Insert contract with matching hash but different filename
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_1', 'different.pdf', file_hash, 1))
        
        # Insert contract with similar filename but different hash
        self.db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash, current_version)
            VALUES (?, ?, ?, ?)
        """, ('contract_2', 'contract_v1.pdf', 'hash123', 1))
        
        self.db.commit()
        
        # Find matches - should prioritize hash match
        matches = self.detector.find_potential_matches(file_hash, 'contract_v2.pdf')
        
        # Hash match should be first
        self.assertGreater(len(matches), 0)
        self.assertEqual(matches[0].match_type, 'hash')
        self.assertEqual(matches[0].contract_id, 'contract_1')


if __name__ == '__main__':
    unittest.main()
