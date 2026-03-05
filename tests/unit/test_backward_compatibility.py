"""
Unit tests for backward compatibility features.

Tests schema format detection and legacy conversion functionality.
"""

import unittest
from datetime import datetime
from src.result_parser import ComprehensiveResultParser
from src.analysis_models import (
    AnalysisResult,
    ContractMetadata,
    Clause,
    Risk,
    ComplianceIssue,
    RedliningSuggestion,
    ComprehensiveAnalysisResult
)
from src.schema_validator import SchemaValidator
from src.schema_loader import SchemaLoader


class TestSchemaFormatDetection(unittest.TestCase):
    """Test schema format detection functionality."""
    
    def test_detect_comprehensive_format_with_schema_version(self):
        """Test detection of comprehensive format with schema_version field."""
        data = {
            'schema_version': '1.0.0',
            'contract_overview': {},
            'metadata': {}
        }
        
        format_type = ComprehensiveResultParser.detect_schema_format(data)
        self.assertEqual(format_type, 'comprehensive')
    
    def test_detect_comprehensive_format_with_sections(self):
        """Test detection of comprehensive format with multiple sections."""
        data = {
            'contract_overview': {},
            'administrative_and_commercial_terms': {},
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'metadata': {}
        }
        
        format_type = ComprehensiveResultParser.detect_schema_format(data)
        self.assertEqual(format_type, 'comprehensive')
    
    def test_detect_legacy_format_with_clauses_and_risks(self):
        """Test detection of legacy format with clauses and risks."""
        data = {
            'contract_metadata': {},
            'clauses': [],
            'risks': [],
            'compliance_issues': []
        }
        
        format_type = ComprehensiveResultParser.detect_schema_format(data)
        self.assertEqual(format_type, 'legacy')
    
    def test_detect_legacy_format_with_contract_metadata(self):
        """Test detection of legacy format with contract_metadata field."""
        data = {
            'contract_metadata': {'filename': 'test.pdf'},
            'clauses': []
        }
        
        format_type = ComprehensiveResultParser.detect_schema_format(data)
        self.assertEqual(format_type, 'legacy')
    
    def test_detect_unknown_format(self):
        """Test detection returns unknown for ambiguous data."""
        data = {
            'some_field': 'value',
            'other_field': 123
        }
        
        format_type = ComprehensiveResultParser.detect_schema_format(data)
        self.assertEqual(format_type, 'unknown')


class TestLegacyConversion(unittest.TestCase):
    """Test legacy to comprehensive format conversion."""
    
    def setUp(self):
        """Set up test fixtures."""
        schema_loader = SchemaLoader()
        schema_validator = SchemaValidator(schema_loader)
        self.parser = ComprehensiveResultParser(schema_validator)
    
    def test_convert_simple_legacy_result(self):
        """Test conversion of simple legacy result."""
        # Create a simple legacy result
        metadata = ContractMetadata(
            filename='test_contract.pdf',
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=50000
        )
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=[],
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Convert to comprehensive format
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Verify conversion
        self.assertIsInstance(comprehensive, ComprehensiveAnalysisResult)
        self.assertEqual(comprehensive.metadata.filename, 'test_contract.pdf')
        self.assertIn('legacy-converted', comprehensive.schema_version)
        self.assertIsNotNone(comprehensive.contract_overview)
        self.assertEqual(comprehensive.contract_overview.general_risk_level, 'Low')
    
    def test_convert_legacy_with_clauses(self):
        """Test conversion preserves clause data."""
        metadata = ContractMetadata(
            filename='test.pdf',
            analyzed_at=datetime.now(),
            page_count=5,
            file_size_bytes=25000
        )
        
        clauses = [
            Clause(
                id='clause_1',
                type='payment_terms',
                text='Payment shall be made within 30 days',
                page=1,
                risk_level='medium'
            ),
            Clause(
                id='clause_2',
                type='liability',
                text='Contractor shall indemnify owner',
                page=2,
                risk_level='high'
            )
        ]
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=clauses,
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Convert
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Verify clauses were mapped to sections
        # Payment terms should go to administrative section
        self.assertIsNotNone(comprehensive.administrative_and_commercial_terms.retainage_progress_payments)
        
        # Liability should go to legal section
        self.assertIsNotNone(comprehensive.legal_risk_and_enforcement.limitations_of_liability)
    
    def test_convert_legacy_with_risks(self):
        """Test conversion maps risks to risk_triggers_identified."""
        metadata = ContractMetadata(
            filename='test.pdf',
            analyzed_at=datetime.now(),
            page_count=5,
            file_size_bytes=25000
        )
        
        clauses = [
            Clause(
                id='clause_1',
                type='payment_terms',
                text='Payment terms',
                page=1,
                risk_level='medium'
            )
        ]
        
        risks = [
            Risk(
                id='risk_1',
                clause_id='clause_1',
                severity='high',
                description='Late payment penalties are excessive',
                recommendation='Negotiate lower penalties'
            )
        ]
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=clauses,
            risks=risks,
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Convert
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Verify risk was mapped
        payment_clause = comprehensive.administrative_and_commercial_terms.retainage_progress_payments
        self.assertIsNotNone(payment_clause)
        self.assertIn('Late payment penalties are excessive', payment_clause.risk_triggers_identified)
    
    def test_convert_legacy_with_redlining_suggestions(self):
        """Test conversion maps redlining suggestions to redline_recommendations."""
        metadata = ContractMetadata(
            filename='test.pdf',
            analyzed_at=datetime.now(),
            page_count=5,
            file_size_bytes=25000
        )
        
        clauses = [
            Clause(
                id='clause_1',
                type='warranty',
                text='Warranty period is 1 year',
                page=1,
                risk_level='low'
            )
        ]
        
        redlining = [
            RedliningSuggestion(
                clause_id='clause_1',
                original_text='Warranty period is 1 year',
                suggested_text='Warranty period is 2 years',
                rationale='Industry standard is 2 years'
            )
        ]
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=clauses,
            risks=[],
            compliance_issues=[],
            redlining_suggestions=redlining
        )
        
        # Convert
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Verify redlining was mapped
        warranty_clause = comprehensive.technical_and_performance_terms.warranty
        self.assertIsNotNone(warranty_clause)
        self.assertEqual(len(warranty_clause.redline_recommendations), 1)
        self.assertEqual(warranty_clause.redline_recommendations[0].action, 'replace')
        self.assertEqual(warranty_clause.redline_recommendations[0].text, 'Warranty period is 2 years')
    
    def test_convert_legacy_with_unmapped_clauses(self):
        """Test unmapped clauses go to supplemental operational risks."""
        metadata = ContractMetadata(
            filename='test.pdf',
            analyzed_at=datetime.now(),
            page_count=5,
            file_size_bytes=25000
        )
        
        clauses = [
            Clause(
                id='clause_1',
                type='unknown_type',
                text='Some unusual clause',
                page=1,
                risk_level='medium'
            )
        ]
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=clauses,
            risks=[],
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Convert
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Verify unmapped clause went to supplemental risks
        self.assertEqual(len(comprehensive.supplemental_operational_risks), 1)
        self.assertIn('Some unusual clause', comprehensive.supplemental_operational_risks[0].clause_language)
    
    def test_convert_legacy_determines_risk_level(self):
        """Test overall risk level is determined from risks."""
        metadata = ContractMetadata(
            filename='test.pdf',
            analyzed_at=datetime.now(),
            page_count=5,
            file_size_bytes=25000
        )
        
        risks = [
            Risk(id='r1', clause_id='c1', severity='critical', description='Critical risk', recommendation='Fix'),
            Risk(id='r2', clause_id='c2', severity='high', description='High risk', recommendation='Fix')
        ]
        
        legacy = AnalysisResult(
            metadata=metadata,
            clauses=[],
            risks=risks,
            compliance_issues=[],
            redlining_suggestions=[]
        )
        
        # Convert
        comprehensive = self.parser.convert_legacy_result(legacy)
        
        # Should be Critical due to critical risk
        self.assertEqual(comprehensive.contract_overview.general_risk_level, 'Critical')


if __name__ == '__main__':
    unittest.main()
