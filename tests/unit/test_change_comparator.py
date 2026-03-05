"""
Unit tests for ChangeComparator module.

Tests the change comparison functionality including text normalization,
similarity calculation, clause comparison, and contract diff generation.
"""

import pytest
from datetime import datetime

from src.change_comparator import (
    ChangeComparator,
    ClauseChangeType,
    ClauseComparison,
    ContractDiff
)
from src.analysis_models import (
    ClauseBlock,
    RedlineRecommendation,
    ComprehensiveAnalysisResult,
    ContractOverview,
    ContractMetadata,
    AdministrativeAndCommercialTerms,
    TechnicalAndPerformanceTerms,
    LegalRiskAndEnforcement,
    RegulatoryAndComplianceTerms,
    DataTechnologyAndDeliverables
)


class TestTextNormalization:
    """Test text normalization functionality."""
    
    def test_normalize_text_lowercase(self):
        """Test that text is converted to lowercase."""
        comparator = ChangeComparator()
        result = comparator.normalize_text("HELLO WORLD")
        assert result == "hello world"
    
    def test_normalize_text_whitespace_collapse(self):
        """Test that multiple whitespace is collapsed to single space."""
        comparator = ChangeComparator()
        result = comparator.normalize_text("hello    world\n\ntest")
        assert result == "hello world test"
    
    def test_normalize_text_strip(self):
        """Test that leading/trailing whitespace is stripped."""
        comparator = ChangeComparator()
        result = comparator.normalize_text("  hello world  ")
        assert result == "hello world"
    
    def test_normalize_text_combined(self):
        """Test normalization with all transformations."""
        comparator = ChangeComparator()
        result = comparator.normalize_text("  HELLO   World\n\tTest  ")
        assert result == "hello world test"
    
    def test_normalize_text_empty(self):
        """Test normalization of empty string."""
        comparator = ChangeComparator()
        result = comparator.normalize_text("")
        assert result == ""
    
    def test_normalize_text_none(self):
        """Test normalization of None."""
        comparator = ChangeComparator()
        result = comparator.normalize_text(None)
        assert result == ""


class TestTextSimilarity:
    """Test text similarity calculation."""
    
    def test_calculate_similarity_identical(self):
        """Test similarity of identical texts."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity(
            "hello world",
            "hello world"
        )
        assert similarity == 1.0
    
    def test_calculate_similarity_case_insensitive(self):
        """Test that similarity is case-insensitive."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity(
            "Hello World",
            "hello world"
        )
        assert similarity == 1.0
    
    def test_calculate_similarity_whitespace_insensitive(self):
        """Test that similarity is whitespace-insensitive."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity(
            "hello    world",
            "hello world"
        )
        assert similarity == 1.0
    
    def test_calculate_similarity_completely_different(self):
        """Test similarity of completely different texts."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity(
            "hello world",
            "goodbye universe"
        )
        assert similarity < 0.5
    
    def test_calculate_similarity_partial_match(self):
        """Test similarity of partially matching texts."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity(
            "The contractor shall complete the work",
            "The contractor shall complete all work"
        )
        assert 0.8 < similarity < 1.0
    
    def test_calculate_similarity_empty_strings(self):
        """Test similarity of empty strings."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity("", "")
        assert similarity == 1.0
    
    def test_calculate_similarity_one_empty(self):
        """Test similarity when one string is empty."""
        comparator = ChangeComparator()
        similarity = comparator.calculate_text_similarity("hello", "")
        assert similarity == 0.0


class TestClauseComparison:
    """Test clause comparison functionality."""
    
    def create_clause(self, text: str) -> ClauseBlock:
        """Helper to create a ClauseBlock for testing."""
        return ClauseBlock(
            clause_language=text,
            clause_summary="Test summary",
            risk_triggers_identified=[],
            flow_down_obligations=[],
            redline_recommendations=[],
            harmful_language_policy_conflicts=[]
        )
    
    def test_compare_clauses_added(self):
        """Test detection of added clause."""
        comparator = ChangeComparator()
        new_clause = self.create_clause("New clause text")
        
        result = comparator.compare_clauses(None, new_clause, "test_clause")
        
        assert result.change_type == ClauseChangeType.ADDED
        assert result.old_content is None
        assert result.new_content == "New clause text"
        assert result.similarity_score == 0.0
    
    def test_compare_clauses_deleted(self):
        """Test detection of deleted clause."""
        comparator = ChangeComparator()
        old_clause = self.create_clause("Old clause text")
        
        result = comparator.compare_clauses(old_clause, None, "test_clause")
        
        assert result.change_type == ClauseChangeType.DELETED
        assert result.old_content == "Old clause text"
        assert result.new_content is None
        assert result.similarity_score == 0.0
    
    def test_compare_clauses_unchanged(self):
        """Test detection of unchanged clause (similarity >= 0.95)."""
        comparator = ChangeComparator()
        old_clause = self.create_clause("The contractor shall complete the work")
        new_clause = self.create_clause("The contractor shall complete the work")
        
        result = comparator.compare_clauses(old_clause, new_clause, "test_clause")
        
        assert result.change_type == ClauseChangeType.UNCHANGED
        assert result.similarity_score >= 0.95
    
    def test_compare_clauses_modified(self):
        """Test detection of modified clause (similarity < 0.95)."""
        comparator = ChangeComparator()
        old_clause = self.create_clause("The contractor shall complete the work")
        new_clause = self.create_clause("The subcontractor must finish all tasks")
        
        result = comparator.compare_clauses(old_clause, new_clause, "test_clause")
        
        assert result.change_type == ClauseChangeType.MODIFIED
        assert result.similarity_score < 0.95
    
    def test_compare_clauses_minor_change_unchanged(self):
        """Test that minor changes (< 5% difference) are classified as unchanged."""
        comparator = ChangeComparator()
        # Very similar text with minor punctuation difference
        old_clause = self.create_clause("The contractor shall complete the work.")
        new_clause = self.create_clause("The contractor shall complete the work")
        
        result = comparator.compare_clauses(old_clause, new_clause, "test_clause")
        
        # Should be classified as unchanged due to high similarity
        assert result.change_type == ClauseChangeType.UNCHANGED
        assert result.similarity_score >= 0.95


class TestContractComparison:
    """Test full contract comparison functionality."""
    
    def create_minimal_analysis(self) -> ComprehensiveAnalysisResult:
        """Helper to create a minimal ComprehensiveAnalysisResult for testing."""
        return ComprehensiveAnalysisResult(
            schema_version="1.0",
            contract_overview=ContractOverview(
                project_title="Test Project",
                solicitation_no="TEST-001",
                owner="Test Owner",
                contractor="Test Contractor",
                scope="Test scope",
                general_risk_level="Low",
                bid_model="Lump Sum",
                notes="Test notes"
            ),
            administrative_and_commercial_terms=AdministrativeAndCommercialTerms(),
            technical_and_performance_terms=TechnicalAndPerformanceTerms(),
            legal_risk_and_enforcement=LegalRiskAndEnforcement(),
            regulatory_and_compliance_terms=RegulatoryAndComplianceTerms(),
            data_technology_and_deliverables=DataTechnologyAndDeliverables(),
            supplemental_operational_risks=[],
            metadata=ContractMetadata(
                filename="test.pdf",
                analyzed_at=datetime.now(),
                page_count=10,
                file_size_bytes=1000
            )
        )
    
    def create_clause(self, text: str) -> ClauseBlock:
        """Helper to create a ClauseBlock for testing."""
        return ClauseBlock(
            clause_language=text,
            clause_summary="Test summary",
            risk_triggers_identified=[],
            flow_down_obligations=[],
            redline_recommendations=[],
            harmful_language_policy_conflicts=[]
        )
    
    def test_compare_contracts_no_changes(self):
        """Test comparison of identical contracts."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.unchanged_clauses) == 0
        assert len(diff.modified_clauses) == 0
        assert len(diff.added_clauses) == 0
        assert len(diff.deleted_clauses) == 0
        assert diff.change_summary['total'] == 0
    
    def test_compare_contracts_with_added_clause(self):
        """Test comparison with added clause."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Add a clause to the second analysis
        analysis2.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("New contract term clause")
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.added_clauses) == 1
        assert diff.added_clauses[0].clause_identifier == 'contract_term_renewal_extensions'
        assert diff.change_summary['added'] == 1
    
    def test_compare_contracts_with_deleted_clause(self):
        """Test comparison with deleted clause."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Add a clause to the first analysis only
        analysis1.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("Old contract term clause")
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.deleted_clauses) == 1
        assert diff.deleted_clauses[0].clause_identifier == 'contract_term_renewal_extensions'
        assert diff.change_summary['deleted'] == 1
    
    def test_compare_contracts_with_modified_clause(self):
        """Test comparison with modified clause."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Add different versions of the same clause
        analysis1.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("The contract term is one year")
        analysis2.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("The contract term is two years")
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.modified_clauses) == 1
        assert diff.modified_clauses[0].clause_identifier == 'contract_term_renewal_extensions'
        assert diff.change_summary['modified'] == 1
    
    def test_compare_contracts_with_unchanged_clause(self):
        """Test comparison with unchanged clause."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Add identical clauses
        clause_text = "The contract term is one year with renewal options"
        analysis1.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause(clause_text)
        analysis2.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause(clause_text)
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.unchanged_clauses) == 1
        assert diff.unchanged_clauses[0].clause_identifier == 'contract_term_renewal_extensions'
        assert diff.change_summary['unchanged'] == 1
    
    def test_compare_contracts_multiple_changes(self):
        """Test comparison with multiple types of changes."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Unchanged clause
        analysis1.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("Contract term clause")
        analysis2.administrative_and_commercial_terms.contract_term_renewal_extensions = \
            self.create_clause("Contract term clause")
        
        # Modified clause
        analysis1.technical_and_performance_terms.scope_of_work = \
            self.create_clause("Original scope of work")
        analysis2.technical_and_performance_terms.scope_of_work = \
            self.create_clause("Updated scope of work with changes")
        
        # Added clause
        analysis2.legal_risk_and_enforcement.indemnification = \
            self.create_clause("New indemnification clause")
        
        # Deleted clause
        analysis1.regulatory_and_compliance_terms.certified_payroll = \
            self.create_clause("Old payroll clause")
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        assert len(diff.unchanged_clauses) == 1
        assert len(diff.modified_clauses) == 1
        assert len(diff.added_clauses) == 1
        assert len(diff.deleted_clauses) == 1
        assert diff.change_summary['total'] == 4
    
    def test_compare_contracts_supplemental_risks(self):
        """Test comparison of supplemental operational risks."""
        comparator = ChangeComparator()
        
        analysis1 = self.create_minimal_analysis()
        analysis2 = self.create_minimal_analysis()
        
        # Add supplemental risks
        analysis1.supplemental_operational_risks = [
            self.create_clause("Risk 1"),
            self.create_clause("Risk 2")
        ]
        analysis2.supplemental_operational_risks = [
            self.create_clause("Risk 1"),
            self.create_clause("Risk 3")
        ]
        
        diff = comparator.compare_contracts(analysis1, analysis2)
        
        # Should detect changes in supplemental risks
        assert diff.change_summary['total'] >= 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
