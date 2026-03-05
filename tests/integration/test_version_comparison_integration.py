"""
Integration tests for Version Comparison View.

Tests the complete workflow of comparing contract versions
with mocked storage to avoid database initialization issues.
"""

import unittest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from PyQt5.QtWidgets import QApplication
import sys

from src.version_comparison_view import VersionComparisonView
from src.differential_storage import Contract


# Create QApplication instance for testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestVersionComparisonIntegration(unittest.TestCase):
    """Integration tests for version comparison workflow."""
    
    def setUp(self):
        """Set up test fixtures with mocked storage."""
        self.contract_id = "test-contract-integration"
        
        # Mock storage
        self.mock_storage = Mock()
        
        # Mock contract with multiple versions
        self.mock_contract = Contract(
            contract_id=self.contract_id,
            filename="test_contract.pdf",
            file_hash="hash123",
            current_version=2,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.mock_storage.get_contract.return_value = self.mock_contract
    
    def test_comparison_view_loads_versions(self):
        """Test that comparison view loads all available versions."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Verify versions are loaded
        self.assertEqual(view.version1_combo.count(), 2)
        self.assertEqual(view.version2_combo.count(), 2)
    
    def test_comparison_detects_modified_clause(self):
        """Test that comparison correctly detects modified clauses."""
        # Mock version manager
        mock_vm = Mock()
        
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'payment_terms',
                    'content': 'Payment shall be made within 30 days.',
                    'clause_version': 1
                }
            ]
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'payment_terms',
                    'content': 'Payment shall be made within 45 days.',
                    'clause_version': 2
                }
            ]
        }
        
        mock_vm.reconstruct_version.side_effect = [v1_data, v2_data]
        
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        view.version_manager = mock_vm
        
        # Compare v1 and v2
        view.compare_versions(1, 2)
        
        # Verify modified clause is detected
        self.assertIn("1 modified", view.modified_label.text())
    
    def test_comparison_detects_added_clause(self):
        """Test that comparison correctly detects added clauses."""
        # Mock version manager
        mock_vm = Mock()
        
        v1_data = {
            'clauses': []
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'warranty',
                    'content': 'Warranty period is 12 months.',
                    'clause_version': 2
                }
            ]
        }
        
        mock_vm.reconstruct_version.side_effect = [v1_data, v2_data]
        
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        view.version_manager = mock_vm
        
        # Compare v1 and v2
        view.compare_versions(1, 2)
        
        # Verify added clause is detected
        self.assertIn("1 added", view.added_label.text())
    
    def test_comparison_summary_is_accurate(self):
        """Test that change summary counts are accurate."""
        # Mock version manager
        mock_vm = Mock()
        
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'payment_terms',
                    'content': 'Payment shall be made within 30 days.',
                    'clause_version': 1
                }
            ]
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'payment_terms',
                    'content': 'Payment shall be made within 45 days.',
                    'clause_version': 2
                },
                {
                    'clause_identifier': 'warranty',
                    'content': 'Warranty period is 12 months.',
                    'clause_version': 2
                }
            ]
        }
        
        mock_vm.reconstruct_version.side_effect = [v1_data, v2_data]
        
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        view.version_manager = mock_vm
        
        # Compare v1 and v2
        view.compare_versions(1, 2)
        
        # Verify all counts
        self.assertIn("1 modified", view.modified_label.text())
        self.assertIn("1 added", view.added_label.text())
        self.assertIn("0 deleted", view.deleted_label.text())
    
    def test_html_diff_generation_works_with_real_data(self):
        """Test that HTML diff generation works with real clause data."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        old_text = "Payment shall be made within 30 days."
        new_text = "Payment shall be made within 45 days."
        
        html = view._generate_html_diff(old_text, new_text, is_old=True)
        
        # Verify HTML contains expected elements
        self.assertIn('<html>', html)
        self.assertIn('class="deleted"', html)
        self.assertIn('30', html)
    
    def test_comparison_handles_empty_versions(self):
        """Test that comparison handles versions with no changes gracefully."""
        # Mock version manager
        mock_vm = Mock()
        
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'payment_terms',
                    'content': 'Payment shall be made within 30 days.',
                    'clause_version': 1
                }
            ]
        }
        
        # Same data for both versions
        mock_vm.reconstruct_version.side_effect = [v1_data, v1_data]
        
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        view.version_manager = mock_vm
        
        # Compare v1 with itself (should show no changes)
        try:
            view.compare_versions(1, 1)
            # Verify no changes detected
            self.assertIn("0 modified", view.modified_label.text())
            self.assertIn("0 added", view.added_label.text())
            self.assertIn("0 deleted", view.deleted_label.text())
        except Exception as e:
            self.fail(f"Comparison raised unexpected exception: {e}")


if __name__ == '__main__':
    unittest.main()
