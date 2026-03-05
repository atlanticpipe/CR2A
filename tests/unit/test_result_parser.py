"""
Unit tests for Result Parser.

Tests parsing and validation of OpenAI API responses.
"""

import pytest
from datetime import datetime
from src.result_parser import ResultParser
from src.analysis_models import AnalysisResult


class TestResultParser:
    """Tests for ResultParser class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = ResultParser()
    
    def test_parse_complete_response(self):
        """Test parsing a complete API response."""
        api_response = {
            'contract_metadata': {
                'page_count': 10
            },
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment shall be made within 30 days',
                    'page': 3,
                    'risk_level': 'low'
                }
            ],
            'risks': [
                {
                    'id': 'risk_1',
                    'clause_id': 'clause_1',
                    'severity': 'high',
                    'description': 'Unlimited liability',
                    'recommendation': 'Negotiate cap'
                }
            ],
            'compliance_issues': [
                {
                    'id': 'compliance_1',
                    'regulation': 'GDPR',
                    'issue': 'Missing data terms',
                    'severity': 'medium'
                }
            ],
            'redlining_suggestions': [
                {
                    'clause_id': 'clause_1',
                    'original_text': 'Original',
                    'suggested_text': 'Suggested',
                    'rationale': 'Clarify'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024,
            page_count=10
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.metadata.filename == 'test.pdf'
        assert len(result.clauses) == 1
        assert len(result.risks) == 1
        assert len(result.compliance_issues) == 1
        assert len(result.redlining_suggestions) == 1
    
    def test_parse_empty_response(self):
        """Test parsing an empty API response."""
        api_response = {}
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024,
            page_count=1
        )
        
        assert isinstance(result, AnalysisResult)
        assert result.metadata.filename == 'test.pdf'
        assert len(result.clauses) == 0
        assert len(result.risks) == 0
    
    def test_parse_partial_response(self):
        """Test parsing a partial API response with missing fields."""
        api_response = {
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment terms',
                    'page': 1,
                    'risk_level': 'low'
                }
            ]
            # Missing risks, compliance_issues, redlining_suggestions
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert isinstance(result, AnalysisResult)
        assert len(result.clauses) == 1
        assert len(result.risks) == 0
        assert len(result.compliance_issues) == 0
        assert len(result.redlining_suggestions) == 0
    
    def test_parse_clause_with_defaults(self):
        """Test parsing clause with missing optional fields."""
        api_response = {
            'clauses': [
                {
                    'text': 'Some clause text'
                    # Missing id, type, page, risk_level
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert len(result.clauses) == 1
        assert result.clauses[0].id == 'clause_1'  # Default ID
        assert result.clauses[0].type == 'unknown'  # Default type
        assert result.clauses[0].risk_level == 'low'  # Default risk level
    
    def test_parse_clause_with_invalid_risk_level(self):
        """Test parsing clause with invalid risk level defaults to 'low'."""
        api_response = {
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment terms',
                    'page': 1,
                    'risk_level': 'invalid_level'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert len(result.clauses) == 1
        assert result.clauses[0].risk_level == 'low'
    
    def test_parse_risk_with_invalid_severity(self):
        """Test parsing risk with invalid severity defaults to 'low'."""
        api_response = {
            'risks': [
                {
                    'id': 'risk_1',
                    'clause_id': 'clause_1',
                    'severity': 'invalid_severity',
                    'description': 'Some risk',
                    'recommendation': 'Fix it'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert len(result.risks) == 1
        assert result.risks[0].severity == 'low'
    
    def test_skip_clause_with_empty_text(self):
        """Test that clauses with empty text are skipped."""
        api_response = {
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': '',  # Empty text
                    'page': 1,
                    'risk_level': 'low'
                },
                {
                    'id': 'clause_2',
                    'type': 'liability',
                    'text': 'Valid clause',
                    'page': 2,
                    'risk_level': 'high'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Only the valid clause should be included
        assert len(result.clauses) == 1
        assert result.clauses[0].id == 'clause_2'
    
    def test_skip_risk_with_empty_description(self):
        """Test that risks with empty description are skipped."""
        api_response = {
            'risks': [
                {
                    'id': 'risk_1',
                    'clause_id': 'clause_1',
                    'severity': 'high',
                    'description': '',  # Empty description
                    'recommendation': 'Fix it'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert len(result.risks) == 0
    
    def test_skip_redlining_with_missing_fields(self):
        """Test that redlining suggestions with missing required fields are skipped."""
        api_response = {
            'redlining_suggestions': [
                {
                    'clause_id': 'clause_1',
                    'original_text': 'Original',
                    # Missing suggested_text
                    'rationale': 'Clarify'
                }
            ]
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        assert len(result.redlining_suggestions) == 0
    
    def test_parse_with_non_list_fields(self):
        """Test parsing handles non-list fields gracefully."""
        api_response = {
            'clauses': 'not a list',  # Invalid type
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        
        result = self.parser.parse_api_response(
            api_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Should handle gracefully and return empty lists
        assert len(result.clauses) == 0


from src.result_parser import ComprehensiveResultParser
from src.schema_loader import SchemaLoader
from src.schema_validator import SchemaValidator
from src.analysis_models import (
    ComprehensiveAnalysisResult,
    ContractOverview,
    ClauseBlock,
    AdministrativeAndCommercialTerms,
    TechnicalAndPerformanceTerms,
    LegalRiskAndEnforcement,
    RegulatoryAndComplianceTerms,
    DataTechnologyAndDeliverables,
)


class TestComprehensiveResultParser:
    """Tests for ComprehensiveResultParser class.
    
    Validates: Requirements 4.1, 4.2
    """
    
    @pytest.fixture
    def schema_loader(self):
        """Create a SchemaLoader instance."""
        return SchemaLoader()
    
    @pytest.fixture
    def schema_validator(self, schema_loader):
        """Create a SchemaValidator instance."""
        return SchemaValidator(schema_loader)
    
    @pytest.fixture
    def parser(self, schema_validator):
        """Create a ComprehensiveResultParser instance."""
        return ComprehensiveResultParser(schema_validator)
    
    @pytest.fixture
    def sample_clause_block(self):
        """Create a sample clause block dictionary in schema format."""
        return {
            'Clause Language': 'The contractor shall maintain insurance coverage.',
            'Clause Summary': 'Insurance requirements for the contractor.',
            'Risk Triggers Identified': ['Insufficient coverage', 'Lapse in policy'],
            'Flow-Down Obligations': ['Subcontractors must also maintain insurance'],
            'Redline Recommendations': [
                {
                    'action': 'insert',
                    'text': 'Minimum coverage of $1M required',
                    'reference': 'Industry standard'
                }
            ],
            'Harmful Language / Policy Conflicts': ['Unlimited liability exposure']
        }
    
    @pytest.fixture
    def sample_contract_overview(self):
        """Create a sample contract overview dictionary in schema format."""
        return {
            'Project Title': 'Highway Construction Project',
            'Solicitation No.': 'SOL-2024-001',
            'Owner': 'State Department of Transportation',
            'Contractor': 'ABC Construction Inc.',
            'Scope': 'Construction of 10-mile highway segment',
            'General Risk Level': 'Medium',
            'Bid Model': 'Lump Sum',
            'Notes': 'Project includes environmental considerations'
        }
    
    @pytest.fixture
    def sample_comprehensive_response(self, sample_contract_overview, sample_clause_block):
        """Create a sample comprehensive API response."""
        return {
            'schema_version': 'v1.0.0',
            'contract_overview': sample_contract_overview,
            'administrative_and_commercial_terms': {
                'Bonding, Surety, & Insurance Obligations': sample_clause_block
            },
            'technical_and_performance_terms': {
                'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)': sample_clause_block
            },
            'legal_risk_and_enforcement': {
                'Indemnification, Defense & Hold Harmless Provisions': sample_clause_block
            },
            'regulatory_and_compliance_terms': {
                'Certified Payroll, Recordkeeping & Reporting Obligations': sample_clause_block
            },
            'data_technology_and_deliverables': {
                'Data Ownership, Access & Rights to Digital Deliverables': sample_clause_block
            },
            'supplemental_operational_risks': [sample_clause_block]
        }
    
    def test_init_with_schema_validator(self, parser, schema_validator):
        """Test that ComprehensiveResultParser initializes with SchemaValidator."""
        assert parser._validator is schema_validator
    
    def test_parse_contract_overview_all_8_fields(self, parser, sample_contract_overview):
        """
        Test parsing contract_overview section with all 8 fields.
        
        Validates: Requirement 4.1
        """
        result = parser._parse_contract_overview(sample_contract_overview)
        
        assert isinstance(result, ContractOverview)
        assert result.project_title == 'Highway Construction Project'
        assert result.solicitation_no == 'SOL-2024-001'
        assert result.owner == 'State Department of Transportation'
        assert result.contractor == 'ABC Construction Inc.'
        assert result.scope == 'Construction of 10-mile highway segment'
        assert result.general_risk_level == 'Medium'
        assert result.bid_model == 'Lump Sum'
        assert result.notes == 'Project includes environmental considerations'
    
    def test_parse_clause_block(self, parser, sample_clause_block):
        """
        Test parsing a single ClauseBlock.
        
        Validates: Requirement 4.2
        """
        result = parser._parse_clause_block(sample_clause_block)
        
        assert isinstance(result, ClauseBlock)
        assert result.clause_language == 'The contractor shall maintain insurance coverage.'
        assert result.clause_summary == 'Insurance requirements for the contractor.'
        assert len(result.risk_triggers_identified) == 2
        assert 'Insufficient coverage' in result.risk_triggers_identified
        assert len(result.flow_down_obligations) == 1
        assert len(result.redline_recommendations) == 1
        assert result.redline_recommendations[0].action == 'insert'
        assert len(result.harmful_language_policy_conflicts) == 1
    
    def test_parse_clause_block_returns_none_for_empty_data(self, parser):
        """Test that _parse_clause_block returns None for empty data."""
        assert parser._parse_clause_block({}) is None
        assert parser._parse_clause_block(None) is None
        assert parser._parse_clause_block({'Clause Language': ''}) is None
    
    def test_parse_section_administrative(self, parser, sample_clause_block):
        """
        Test parsing administrative_and_commercial_terms section.
        
        Validates: Requirement 4.2
        """
        section_data = {
            'Bonding, Surety, & Insurance Obligations': sample_clause_block,
            'Change Orders, Scope Adjustments & Modifications': sample_clause_block
        }
        
        result = parser._parse_section(section_data, AdministrativeAndCommercialTerms)
        
        assert isinstance(result, AdministrativeAndCommercialTerms)
        assert result.bonding_surety_insurance is not None
        assert result.change_orders is not None
        assert result.contract_term_renewal_extensions is None  # Not provided
    
    def test_parse_section_technical(self, parser, sample_clause_block):
        """
        Test parsing technical_and_performance_terms section.
        
        Validates: Requirement 4.2
        """
        section_data = {
            'Scope of Work (Work Inclusions, Exclusions & Defined Deliverables)': sample_clause_block
        }
        
        result = parser._parse_section(section_data, TechnicalAndPerformanceTerms)
        
        assert isinstance(result, TechnicalAndPerformanceTerms)
        assert result.scope_of_work is not None
    
    def test_parse_section_legal(self, parser, sample_clause_block):
        """
        Test parsing legal_risk_and_enforcement section.
        
        Validates: Requirement 4.2
        """
        section_data = {
            'Indemnification, Defense & Hold Harmless Provisions': sample_clause_block
        }
        
        result = parser._parse_section(section_data, LegalRiskAndEnforcement)
        
        assert isinstance(result, LegalRiskAndEnforcement)
        assert result.indemnification is not None
    
    def test_parse_section_regulatory(self, parser, sample_clause_block):
        """
        Test parsing regulatory_and_compliance_terms section.
        
        Validates: Requirement 4.2
        """
        section_data = {
            'Certified Payroll, Recordkeeping & Reporting Obligations': sample_clause_block
        }
        
        result = parser._parse_section(section_data, RegulatoryAndComplianceTerms)
        
        assert isinstance(result, RegulatoryAndComplianceTerms)
        assert result.certified_payroll is not None
    
    def test_parse_section_data_technology(self, parser, sample_clause_block):
        """
        Test parsing data_technology_and_deliverables section.
        
        Validates: Requirement 4.2
        """
        section_data = {
            'Data Ownership, Access & Rights to Digital Deliverables': sample_clause_block
        }
        
        result = parser._parse_section(section_data, DataTechnologyAndDeliverables)
        
        assert isinstance(result, DataTechnologyAndDeliverables)
        assert result.data_ownership is not None
    
    def test_parse_section_returns_empty_for_invalid_data(self, parser):
        """Test that _parse_section returns empty instance for invalid data."""
        result = parser._parse_section({}, AdministrativeAndCommercialTerms)
        assert isinstance(result, AdministrativeAndCommercialTerms)
        
        result = parser._parse_section(None, AdministrativeAndCommercialTerms)
        assert isinstance(result, AdministrativeAndCommercialTerms)
    
    def test_parse_supplemental_risks(self, parser, sample_clause_block):
        """Test parsing supplemental_operational_risks list."""
        data = [sample_clause_block, sample_clause_block]
        
        result = parser._parse_supplemental_risks(data)
        
        assert len(result) == 2
        assert all(isinstance(block, ClauseBlock) for block in result)
    
    def test_parse_supplemental_risks_skips_invalid(self, parser, sample_clause_block):
        """Test that invalid items in supplemental_operational_risks are skipped."""
        data = [
            sample_clause_block,
            {},  # Empty - should be skipped
            {'Clause Language': ''},  # Empty language - should be skipped
            sample_clause_block
        ]
        
        result = parser._parse_supplemental_risks(data)
        
        assert len(result) == 2
    
    def test_parse_api_response_complete(self, parser, sample_comprehensive_response):
        """
        Test parsing a complete comprehensive API response.
        
        Validates: Requirements 4.1, 4.2
        """
        result = parser.parse_api_response(
            sample_comprehensive_response,
            filename='contract.pdf',
            file_size_bytes=2048,
            page_count=50
        )
        
        assert isinstance(result, ComprehensiveAnalysisResult)
        assert result.schema_version == 'v1.0.0'
        
        # Verify contract overview (Requirement 4.1)
        assert result.contract_overview.project_title == 'Highway Construction Project'
        assert result.contract_overview.general_risk_level == 'Medium'
        
        # Verify sections (Requirement 4.2)
        assert result.administrative_and_commercial_terms.bonding_surety_insurance is not None
        assert result.technical_and_performance_terms.scope_of_work is not None
        assert result.legal_risk_and_enforcement.indemnification is not None
        assert result.regulatory_and_compliance_terms.certified_payroll is not None
        assert result.data_technology_and_deliverables.data_ownership is not None
        
        # Verify supplemental risks
        assert len(result.supplemental_operational_risks) == 1
        
        # Verify metadata
        assert result.metadata.filename == 'contract.pdf'
        assert result.metadata.file_size_bytes == 2048
        assert result.metadata.page_count == 50
    
    def test_parse_api_response_empty_sections(self, parser, sample_contract_overview):
        """Test parsing API response with empty sections."""
        api_response = {
            'schema_version': 'v1.0.0',
            'contract_overview': sample_contract_overview,
            'administrative_and_commercial_terms': {},
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'regulatory_and_compliance_terms': {},
            'data_technology_and_deliverables': {},
            'supplemental_operational_risks': []
        }
        
        result = parser.parse_api_response(
            api_response,
            filename='contract.pdf',
            file_size_bytes=1024
        )
        
        assert isinstance(result, ComprehensiveAnalysisResult)
        assert result.administrative_and_commercial_terms is not None
        assert result.supplemental_operational_risks == []
    
    def test_parse_api_response_missing_sections(self, parser, sample_contract_overview):
        """Test parsing API response with missing sections (graceful handling)."""
        api_response = {
            'schema_version': 'v1.0.0',
            'contract_overview': sample_contract_overview
            # All other sections missing
        }
        
        result = parser.parse_api_response(
            api_response,
            filename='contract.pdf',
            file_size_bytes=1024
        )
        
        assert isinstance(result, ComprehensiveAnalysisResult)
        # Should have empty section instances
        assert result.administrative_and_commercial_terms is not None
        assert result.technical_and_performance_terms is not None
    
    def test_parse_api_response_default_schema_version(self, parser, sample_contract_overview):
        """Test that default schema version is used when not provided."""
        api_response = {
            'contract_overview': sample_contract_overview
            # schema_version missing
        }
        
        result = parser.parse_api_response(
            api_response,
            filename='contract.pdf',
            file_size_bytes=1024
        )
        
        assert result.schema_version == 'v1.0.0'
    
    def test_parse_api_response_metadata_from_response(self, parser, sample_contract_overview):
        """Test that page_count can be extracted from API response metadata."""
        api_response = {
            'schema_version': 'v1.0.0',
            'contract_overview': sample_contract_overview,
            'metadata': {
                'page_count': 100
            }
        }
        
        result = parser.parse_api_response(
            api_response,
            filename='contract.pdf',
            file_size_bytes=1024
            # page_count not provided - should use from response
        )
        
        assert result.metadata.page_count == 100


class TestSchemaValidationIntegration:
    """
    Tests for schema validation integration in parsing pipeline.
    
    Validates: Requirements 6.2, 6.4
    """
    
    @pytest.fixture
    def schema_loader(self):
        """Create a SchemaLoader instance."""
        return SchemaLoader()
    
    @pytest.fixture
    def schema_validator(self, schema_loader):
        """Create a SchemaValidator instance."""
        return SchemaValidator(schema_loader)
    
    @pytest.fixture
    def parser(self, schema_validator):
        """Create a ComprehensiveResultParser instance."""
        return ComprehensiveResultParser(schema_validator)
    
    @pytest.fixture
    def valid_response(self):
        """Create a valid comprehensive API response."""
        return {
            'schema_version': 'v1.0.0',
            'contract_overview': {
                'Project Title': 'Test Project',
                'Solicitation No.': 'SOL-001',
                'Owner': 'Test Owner',
                'Contractor': 'Test Contractor',
                'Scope': 'Test scope',
                'General Risk Level': 'Medium',
                'Bid Model': 'Lump Sum',
                'Notes': 'Test notes'
            },
            'administrative_and_commercial_terms': {},
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'regulatory_and_compliance_terms': {},
            'data_technology_and_deliverables': {},
            'supplemental_operational_risks': []
        }
    
    def test_validation_called_before_parsing(self, parser, valid_response, caplog):
        """
        Test that SchemaValidator is called before parsing API response.
        
        Validates: Requirement 6.2
        """
        import logging
        caplog.set_level(logging.DEBUG)
        
        result = parser.parse_api_response(
            valid_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Check that validation was performed
        assert any('Validating API response against schema' in record.message 
                  for record in caplog.records)
        assert isinstance(result, ComprehensiveAnalysisResult)
    
    def test_validation_errors_logged(self, parser, caplog):
        """
        Test that validation errors are logged with field paths.
        
        Validates: Requirement 6.2
        """
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create response with invalid enum value in a non-critical field
        # Note: Invalid enum values in critical fields (like contract_overview) will cause parsing to fail
        # This is correct behavior - we log validation errors but critical data integrity issues should fail
        invalid_response = {
            'schema_version': 'v1.0.0',
            'contract_overview': {
                'Project Title': 'Test Project',
                'Solicitation No.': 'SOL-001',
                'Owner': 'Test Owner',
                'Contractor': 'Test Contractor',
                'Scope': 'Test scope',
                'General Risk Level': 'InvalidLevel',  # Invalid enum value - will cause failure
                'Bid Model': 'Lump Sum',
                'Notes': 'Test notes'
            },
            'administrative_and_commercial_terms': {},
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'regulatory_and_compliance_terms': {},
            'data_technology_and_deliverables': {},
            'supplemental_operational_risks': []
        }
        
        # Should raise exception for invalid critical field, but validation errors should be logged first
        with pytest.raises(ValueError, match="Invalid contract overview data"):
            parser.parse_api_response(
                invalid_response,
                filename='test.pdf',
                file_size_bytes=1024
            )
        
        # Check that validation errors were logged before the exception
        assert any('Schema validation failed' in record.message 
                  for record in caplog.records)
        assert any('Validation error' in record.message 
                  for record in caplog.records)
    
    def test_validation_warnings_logged(self, parser, valid_response, caplog):
        """
        Test that validation warnings are logged.
        
        Validates: Requirement 6.2
        """
        import logging
        caplog.set_level(logging.DEBUG)
        
        # Note: The test response has empty sections which will fail schema validation
        # (schema requires all clause categories to be present)
        # But parsing should continue with best-effort approach
        result = parser.parse_api_response(
            valid_response,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Check that validation was performed and logged
        assert any('Validating API response against schema' in record.message 
                  for record in caplog.records)
        # With empty sections, validation will fail but parsing continues
        assert any('Continuing with best-effort parsing' in record.message 
                  for record in caplog.records)
        assert isinstance(result, ComprehensiveAnalysisResult)
    
    def test_continues_processing_on_non_critical_failures(self, parser, caplog):
        """
        Test that processing continues on non-critical validation failures.
        
        Validates: Requirement 6.4
        """
        import logging
        caplog.set_level(logging.INFO)
        
        # Create response with missing optional fields
        response_with_missing_fields = {
            'schema_version': 'v1.0.0',
            'contract_overview': {
                'Project Title': 'Test Project',
                'Solicitation No.': 'SOL-001',
                'Owner': 'Test Owner',
                'Contractor': 'Test Contractor',
                'Scope': 'Test scope',
                'General Risk Level': 'Medium',
                'Bid Model': 'Lump Sum',
                'Notes': 'Test notes'
            }
            # Missing all section fields - non-critical
        }
        
        # Should not raise exception
        result = parser.parse_api_response(
            response_with_missing_fields,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Check that processing continued despite validation issues
        assert any('Continuing with best-effort parsing' in record.message 
                  for record in caplog.records)
        
        # Should still return a valid result
        assert isinstance(result, ComprehensiveAnalysisResult)
        assert result.contract_overview.project_title == 'Test Project'
    
    def test_validation_with_invalid_clause_block(self, parser, caplog):
        """
        Test validation with invalid clause block structure.
        
        Validates: Requirements 6.2, 6.4
        """
        import logging
        caplog.set_level(logging.WARNING)
        
        # Create response with invalid clause block
        response_with_invalid_clause = {
            'schema_version': 'v1.0.0',
            'contract_overview': {
                'Project Title': 'Test Project',
                'Solicitation No.': 'SOL-001',
                'Owner': 'Test Owner',
                'Contractor': 'Test Contractor',
                'Scope': 'Test scope',
                'General Risk Level': 'Medium',
                'Bid Model': 'Lump Sum',
                'Notes': 'Test notes'
            },
            'administrative_and_commercial_terms': {
                'Bonding, Surety, & Insurance Obligations': {
                    'Clause Language': 'Test clause',
                    'Clause Summary': 'Test summary',
                    'Risk Triggers Identified': ['Risk 1'],
                    'Flow-Down Obligations': ['Obligation 1'],
                    'Redline Recommendations': [
                        {
                            'action': 'invalid_action',  # Invalid action
                            'text': 'Test text'
                        }
                    ],
                    'Harmful Language / Policy Conflicts': []
                }
            },
            'technical_and_performance_terms': {},
            'legal_risk_and_enforcement': {},
            'regulatory_and_compliance_terms': {},
            'data_technology_and_deliverables': {},
            'supplemental_operational_risks': []
        }
        
        # Should log validation errors but continue processing
        result = parser.parse_api_response(
            response_with_invalid_clause,
            filename='test.pdf',
            file_size_bytes=1024
        )
        
        # Should still return a result
        assert isinstance(result, ComprehensiveAnalysisResult)
    
    def test_validation_result_structure(self, parser, valid_response):
        """
        Test that validation result contains expected structure.
        
        Validates: Requirement 6.2
        """
        # Directly test the validator
        validation_result = parser._validator.validate(valid_response)
        
        # Check validation result structure
        assert hasattr(validation_result, 'is_valid')
        assert hasattr(validation_result, 'errors')
        assert hasattr(validation_result, 'warnings')
        assert isinstance(validation_result.errors, list)
        assert isinstance(validation_result.warnings, list)
