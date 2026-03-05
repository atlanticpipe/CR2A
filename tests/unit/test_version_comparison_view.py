"""
Unit tests for Version Comparison View.

Tests the UI component for comparing contract versions with
color-coded highlighting and change summaries.
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from PyQt5.QtWidgets import QApplication
import sys

from src.version_comparison_view import VersionComparisonView
from src.differential_storage import Contract, Clause


# Create QApplication instance for testing
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class TestVersionComparisonView(unittest.TestCase):
    """Test cases for VersionComparisonView."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.contract_id = "test-contract-123"
        
        # Mock storage
        self.mock_storage = Mock()
        
        # Mock contract
        self.mock_contract = Contract(
            contract_id=self.contract_id,
            filename="test_contract.pdf",
            file_hash="abc123",
            current_version=3,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.mock_storage.get_contract.return_value = self.mock_contract
    
    def test_init_creates_ui_components(self):
        """Test that initialization creates all UI components."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Verify UI components exist
        self.assertIsNotNone(view.version1_combo)
        self.assertIsNotNone(view.version2_combo)
        self.assertIsNotNone(view.modified_label)
        self.assertIsNotNone(view.added_label)
        self.assertIsNotNone(view.deleted_label)
        self.assertIsNotNone(view.comparison_layout)
    
    def test_load_versions_populates_dropdowns(self):
        """Test that load_versions populates version dropdowns correctly."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Verify dropdowns are populated
        self.assertEqual(view.version1_combo.count(), 3)
        self.assertEqual(view.version2_combo.count(), 3)
        
        # Verify version data
        self.assertEqual(view.version1_combo.itemData(0), 1)
        self.assertEqual(view.version1_combo.itemData(1), 2)
        self.assertEqual(view.version1_combo.itemData(2), 3)
    
    def test_load_versions_sets_default_selection(self):
        """Test that default selection is latest vs previous version."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Verify default selection (v2 vs v3)
        self.assertEqual(view.version1_combo.currentData(), 2)
        self.assertEqual(view.version2_combo.currentData(), 3)
    
    @patch('src.version_comparison_view.VersionManager')
    def test_compare_versions_reconstructs_both_versions(self, mock_vm_class):
        """Test that compare_versions reconstructs both versions."""
        mock_vm = Mock()
        mock_vm_class.return_value = mock_vm
        
        # Mock reconstruction results
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'clause1',
                    'content': 'Old content',
                    'clause_version': 1
                }
            ]
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'clause1',
                    'content': 'New content',
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
        
        # Compare versions
        view.compare_versions(1, 2)
        
        # Verify both versions were reconstructed
        self.assertEqual(mock_vm.reconstruct_version.call_count, 2)
        mock_vm.reconstruct_version.assert_any_call(self.contract_id, 1)
        mock_vm.reconstruct_version.assert_any_call(self.contract_id, 2)
    
    @patch('src.version_comparison_view.VersionManager')
    def test_compare_versions_detects_modified_clauses(self, mock_vm_class):
        """Test that modified clauses are detected and displayed."""
        mock_vm = Mock()
        mock_vm_class.return_value = mock_vm
        
        # Mock reconstruction with modified clause
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'clause1',
                    'content': 'This is the original content of the clause.',
                    'clause_version': 1
                }
            ]
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'clause1',
                    'content': 'This is the modified content of the clause.',
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
        
        # Compare versions
        view.compare_versions(1, 2)
        
        # Verify modified count is updated
        self.assertIn("1 modified", view.modified_label.text())
    
    @patch('src.version_comparison_view.VersionManager')
    def test_compare_versions_detects_added_clauses(self, mock_vm_class):
        """Test that added clauses are detected and displayed."""
        mock_vm = Mock()
        mock_vm_class.return_value = mock_vm
        
        # Mock reconstruction with added clause
        v1_data = {
            'clauses': []
        }
        v2_data = {
            'clauses': [
                {
                    'clause_identifier': 'new_clause',
                    'content': 'This is a new clause.',
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
        
        # Compare versions
        view.compare_versions(1, 2)
        
        # Verify added count is updated
        self.assertIn("1 added", view.added_label.text())
    
    @patch('src.version_comparison_view.VersionManager')
    def test_compare_versions_detects_deleted_clauses(self, mock_vm_class):
        """Test that deleted clauses are detected and displayed."""
        mock_vm = Mock()
        mock_vm_class.return_value = mock_vm
        
        # Mock reconstruction with deleted clause
        v1_data = {
            'clauses': [
                {
                    'clause_identifier': 'old_clause',
                    'content': 'This clause will be deleted.',
                    'clause_version': 1
                }
            ]
        }
        v2_data = {
            'clauses': []
        }
        
        mock_vm.reconstruct_version.side_effect = [v1_data, v2_data]
        
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        view.version_manager = mock_vm
        
        # Compare versions
        view.compare_versions(1, 2)
        
        # Verify deleted count is updated
        self.assertIn("1 deleted", view.deleted_label.text())
    
    def test_generate_html_diff_creates_valid_html(self):
        """Test that HTML diff generation creates valid HTML."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        old_text = "This is the old text"
        new_text = "This is the new text"
        
        html = view._generate_html_diff(old_text, new_text, is_old=True)
        
        # Verify HTML structure
        self.assertIn('<html>', html)
        self.assertIn('<style>', html)
        self.assertIn('</html>', html)
        self.assertIn('.deleted', html)
        self.assertIn('.added', html)
    
    def test_generate_html_diff_highlights_deletions_in_old(self):
        """Test that deletions are highlighted in old version."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        old_text = "This is old text"
        new_text = "This is new text"
        
        html = view._generate_html_diff(old_text, new_text, is_old=True)
        
        # Verify deleted word is highlighted
        self.assertIn('class="deleted"', html)
        self.assertIn('old', html)
    
    def test_generate_html_diff_highlights_additions_in_new(self):
        """Test that additions are highlighted in new version."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        old_text = "This is old text"
        new_text = "This is new text"
        
        html = view._generate_html_diff(old_text, new_text, is_old=False)
        
        # Verify added word is highlighted
        self.assertIn('class="added"', html)
        self.assertIn('new', html)
    
    def test_escape_html_escapes_special_characters(self):
        """Test that HTML special characters are escaped."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        text = '<script>alert("test")</script>'
        escaped = view._escape_html(text)
        
        # Verify special characters are escaped
        self.assertNotIn('<script>', escaped)
        self.assertIn('&lt;script&gt;', escaped)
        self.assertIn('&quot;', escaped)
    
    def test_update_summary_updates_all_labels(self):
        """Test that update_summary updates all change count labels."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Update summary
        view._update_summary(modified=5, added=3, deleted=2)
        
        # Verify labels are updated
        self.assertEqual(view.modified_label.text(), "5 modified")
        self.assertEqual(view.added_label.text(), "3 added")
        self.assertEqual(view.deleted_label.text(), "2 deleted")
    
    def test_clear_comparison_removes_widgets(self):
        """Test that clear_comparison removes all comparison widgets."""
        view = VersionComparisonView(
            contract_id=self.contract_id,
            differential_storage=self.mock_storage
        )
        
        # Add some widgets to comparison layout
        from PyQt5.QtWidgets import QLabel
        view.comparison_layout.addWidget(QLabel("Test 1"))
        view.comparison_layout.addWidget(QLabel("Test 2"))
        
        initial_count = view.comparison_layout.count()
        self.assertGreater(initial_count, 0)
        
        # Clear comparison
        view._clear_comparison()
        
        # Verify only empty label remains
        self.assertEqual(view.comparison_layout.count(), 1)


if __name__ == '__main__':
    unittest.main()
