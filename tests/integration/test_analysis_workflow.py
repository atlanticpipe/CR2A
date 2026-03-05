"""
Integration tests for Analysis Engine workflow.

Tests the complete analysis workflow from file upload to result parsing.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch
from src.analysis_engine import AnalysisEngine
from src.analysis_models import AnalysisResult


class TestAnalysisWorkflow:
    """Integration tests for complete analysis workflow."""
    
    @patch('src.analysis_engine.OpenAIClient')
    def test_complete_workflow_with_mock_api(self, mock_client_class):
        """Test complete workflow with mocked OpenAI API."""
        # Setup mock OpenAI client
        mock_client = Mock()
        mock_client.analyze_contract.return_value = {
            'contract_metadata': {
                'page_count': 5
            },
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment shall be made within 30 days of invoice date.',
                    'page': 2,
                    'risk_level': 'low'
                },
                {
                    'id': 'clause_2',
                    'type': 'liability',
                    'text': 'Contractor shall indemnify and hold harmless the Owner.',
                    'page': 4,
                    'risk_level': 'high'
                }
            ],
            'risks': [
                {
                    'id': 'risk_1',
                    'clause_id': 'clause_2',
                    'severity': 'high',
                    'description': 'Unlimited liability exposure',
                    'recommendation': 'Negotiate a liability cap'
                }
            ],
            'compliance_issues': [
                {
                    'id': 'compliance_1',
                    'regulation': 'GDPR',
                    'issue': 'Missing data processing agreement',
                    'severity': 'medium'
                }
            ],
            'redlining_suggestions': [
                {
                    'clause_id': 'clause_2',
                    'original_text': 'Contractor shall indemnify and hold harmless the Owner.',
                    'suggested_text': 'Contractor shall indemnify and hold harmless the Owner, subject to a liability cap of $1,000,000.',
                    'rationale': 'Limit liability exposure'
                }
            ]
        }
        mock_client_class.return_value = mock_client
        
        # Create a test file (we'll use an existing test file)
        test_file = Path(__file__).parent.parent / 'fixtures' / 'sample_contract.txt'
        
        # Create the fixtures directory and sample file if they don't exist
        test_file.parent.mkdir(parents=True, exist_ok=True)
        if not test_file.exists():
            test_file.write_text("Sample contract text for testing purposes.\n\nThis is a test contract.")
        
        # Note: Since we're using ContractUploader which expects PDF/DOCX,
        # we'll need to mock the file validation or use a real PDF
        # For this test, we'll patch the uploader to accept our test file
        
        with patch('src.analysis_engine.ContractUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.validate_format.return_value = (True, "")
            mock_uploader.get_file_info.return_value = {
                'filename': 'sample_contract.txt',
                'file_size_bytes': 100,
                'page_count': 1
            }
            mock_uploader.extract_text.return_value = "Sample contract text for testing purposes.\n\nThis is a test contract."
            mock_uploader_class.return_value = mock_uploader
            
            # Create engine and analyze
            engine = AnalysisEngine(openai_api_key="sk-test-key")
            
            # Track progress
            progress_updates = []
            def progress_callback(status, percent):
                progress_updates.append((status, percent))
            
            # Analyze contract
            result = engine.analyze_contract(
                str(test_file),
                progress_callback=progress_callback
            )
        
        # Verify result structure
        assert isinstance(result, AnalysisResult)
        assert result.metadata.filename == 'sample_contract.txt'
        
        # Verify clauses
        assert len(result.clauses) == 2
        assert result.clauses[0].id == 'clause_1'
        assert result.clauses[0].type == 'payment_terms'
        assert result.clauses[1].risk_level == 'high'
        
        # Verify risks
        assert len(result.risks) == 1
        assert result.risks[0].severity == 'high'
        assert result.risks[0].clause_id == 'clause_2'
        
        # Verify compliance issues
        assert len(result.compliance_issues) == 1
        assert result.compliance_issues[0].regulation == 'GDPR'
        
        # Verify redlining suggestions
        assert len(result.redlining_suggestions) == 1
        assert result.redlining_suggestions[0].clause_id == 'clause_2'
        
        # Verify progress updates were made
        assert len(progress_updates) > 0
        assert any('complete' in status.lower() for status, _ in progress_updates)
        
        # Verify result validation passes
        assert result.validate_result() is True
    
    @patch('src.analysis_engine.OpenAIClient')
    def test_workflow_handles_partial_response(self, mock_client_class):
        """Test workflow handles partial API response gracefully."""
        # Setup mock with partial response (missing some fields)
        mock_client = Mock()
        mock_client.analyze_contract.return_value = {
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
        mock_client_class.return_value = mock_client
        
        with patch('src.analysis_engine.ContractUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.validate_format.return_value = (True, "")
            mock_uploader.get_file_info.return_value = {
                'filename': 'test.pdf',
                'file_size_bytes': 100,
                'page_count': 1
            }
            mock_uploader.extract_text.return_value = "Contract text"
            mock_uploader_class.return_value = mock_uploader
            
            engine = AnalysisEngine(openai_api_key="sk-test-key")
            result = engine.analyze_contract("test.pdf")
        
        # Should still return valid result with empty lists
        assert isinstance(result, AnalysisResult)
        assert len(result.clauses) == 1
        assert len(result.risks) == 0
        assert len(result.compliance_issues) == 0
        assert len(result.redlining_suggestions) == 0
    
    @patch('src.analysis_engine.OpenAIClient')
    def test_workflow_serialization_roundtrip(self, mock_client_class):
        """Test that analysis result can be serialized and deserialized."""
        # Setup mock
        mock_client = Mock()
        mock_client.analyze_contract.return_value = {
            'clauses': [
                {
                    'id': 'clause_1',
                    'type': 'payment_terms',
                    'text': 'Payment terms',
                    'page': 1,
                    'risk_level': 'low'
                }
            ],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        mock_client_class.return_value = mock_client
        
        with patch('src.analysis_engine.ContractUploader') as mock_uploader_class:
            mock_uploader = Mock()
            mock_uploader.validate_format.return_value = (True, "")
            mock_uploader.get_file_info.return_value = {
                'filename': 'test.pdf',
                'file_size_bytes': 100,
                'page_count': 1
            }
            mock_uploader.extract_text.return_value = "Contract text"
            mock_uploader_class.return_value = mock_uploader
            
            engine = AnalysisEngine(openai_api_key="sk-test-key")
            result = engine.analyze_contract("test.pdf")
        
        # Serialize to dict
        result_dict = result.to_dict()
        
        # Deserialize back
        restored_result = AnalysisResult.from_dict(result_dict)
        
        # Verify data is preserved
        assert restored_result.metadata.filename == result.metadata.filename
        assert len(restored_result.clauses) == len(result.clauses)
        assert restored_result.clauses[0].id == result.clauses[0].id
