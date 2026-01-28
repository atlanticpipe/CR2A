#!/usr/bin/env python3
"""
Unit tests for extract.py module

Tests PDF and DOCX text extraction functionality.
"""

import unittest
import os
from pathlib import Path
import sys

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import extract


class TestExtractModule(unittest.TestCase):
    """Test cases for text extraction module"""
    
    def test_validate_file_exists(self):
        """Test file validation for existing files"""
        # This test file should exist
        test_file = __file__
        result = extract.validate_file(test_file)
        self.assertTrue(result, "Should validate existing file")
    
    def test_validate_file_not_exists(self):
        """Test file validation for non-existent files"""
        result = extract.validate_file("nonexistent_file.pdf")
        self.assertFalse(result, "Should reject non-existent file")
    
    def test_validate_file_empty_path(self):
        """Test file validation with empty path"""
        result = extract.validate_file("")
        self.assertFalse(result, "Should reject empty path")
    
    def test_validate_file_none(self):
        """Test file validation with None"""
        result = extract.validate_file(None)
        self.assertFalse(result, "Should reject None path")


if __name__ == '__main__':
    unittest.main()
