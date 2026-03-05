"""
Unit tests for Analysis Engine.

Tests the orchestration of contract analysis workflow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.analysis_engine import AnalysisEngine
from src.analysis_models import AnalysisResult, ContractMetadata
from datetime import datetime


class TestAnalysisEngine:
    """Tests for AnalysisEngine class."""
    
    def test_init_with_valid_api_key(self):
        """Test initialization with valid API key."""
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        
        assert engine.uploader is not None
        assert engine.openai_client is not None
        assert engine.parser is not None
    
    def test_init_with_invalid_api_key(self):
        """Test initialization with invalid API key raises ValueError."""
        with pytest.raises(ValueError):
            AnalysisEngine(openai_api_key="invalid-key")
    
    @patch('src.analysis_engine.ContractUploader')
    @patch('src.analysis_engine.OpenAIClient')
    @patch('src.analysis_engine.ResultParser')
    def test_analyze_contract_success(self, mock_parser_class, mock_client_class, mock_uploader_class):
        """Test successful contract analysis workflow."""
        # Setup mocks
        mock_uploader = Mock()
        mock_uploader.validate_format.return_value = (True, "")
        mock_uploader.get_file_info.return_value = {
            'filename': 'test.pdf',
            'file_size_bytes': 1024,
            'page_count': 10
        }
        mock_uploader.extract_text.return_value = "Contract text content"
        mock_uploader_class.return_value = mock_uploader
        
        mock_client = Mock()
        mock_client.analyze_contract.return_value = {
            'contract_metadata': {'page_count': 10},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        mock_client_class.return_value = mock_client
        
        mock_parser = Mock()
        mock_result = Mock(spec=AnalysisResult)
        mock_result.validate_result.return_value = True
        mock_result.clauses = []
        mock_result.risks = []
        mock_result.compliance_issues = []
        mock_result.redlining_suggestions = []
        mock_parser.parse_api_response.return_value = mock_result
        mock_parser_class.return_value = mock_parser
        
        # Create engine and analyze
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        result = engine.analyze_contract("test.pdf")
        
        # Verify workflow
        mock_uploader.validate_format.assert_called_once_with("test.pdf")
        mock_uploader.get_file_info.assert_called_once_with("test.pdf")
        mock_uploader.extract_text.assert_called_once_with("test.pdf")
        mock_client.analyze_contract.assert_called_once()
        mock_parser.parse_api_response.assert_called_once()
        
        assert result == mock_result
    
    @patch('src.analysis_engine.ContractUploader')
    def test_analyze_contract_invalid_file(self, mock_uploader_class):
        """Test analysis fails with invalid file."""
        mock_uploader = Mock()
        mock_uploader.validate_format.return_value = (False, "Invalid file format")
        mock_uploader_class.return_value = mock_uploader
        
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        
        with pytest.raises(ValueError, match="File validation failed"):
            engine.analyze_contract("invalid.txt")
    
    @patch('src.analysis_engine.ContractUploader')
    def test_analyze_contract_empty_text(self, mock_uploader_class):
        """Test analysis fails when no text is extracted."""
        mock_uploader = Mock()
        mock_uploader.validate_format.return_value = (True, "")
        mock_uploader.get_file_info.return_value = {
            'filename': 'test.pdf',
            'file_size_bytes': 1024,
            'page_count': 10
        }
        mock_uploader.extract_text.return_value = ""  # Empty text
        mock_uploader_class.return_value = mock_uploader
        
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        
        with pytest.raises(ValueError, match="No text could be extracted"):
            engine.analyze_contract("test.pdf")
    
    @patch('src.analysis_engine.ContractUploader')
    @patch('src.analysis_engine.OpenAIClient')
    def test_analyze_contract_with_progress_callback(self, mock_client_class, mock_uploader_class):
        """Test analysis with progress callback."""
        # Setup mocks
        mock_uploader = Mock()
        mock_uploader.validate_format.return_value = (True, "")
        mock_uploader.get_file_info.return_value = {
            'filename': 'test.pdf',
            'file_size_bytes': 1024,
            'page_count': 10
        }
        mock_uploader.extract_text.return_value = "Contract text"
        mock_uploader_class.return_value = mock_uploader
        
        mock_client = Mock()
        mock_client.analyze_contract.return_value = {
            'contract_metadata': {'page_count': 10},
            'clauses': [],
            'risks': [],
            'compliance_issues': [],
            'redlining_suggestions': []
        }
        mock_client_class.return_value = mock_client
        
        # Create progress callback mock
        progress_callback = Mock()
        
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        
        # Patch parser to avoid actual parsing
        with patch('src.analysis_engine.ResultParser') as mock_parser_class:
            mock_parser = Mock()
            mock_result = Mock(spec=AnalysisResult)
            mock_result.validate_result.return_value = True
            mock_result.clauses = []
            mock_result.risks = []
            mock_result.compliance_issues = []
            mock_result.redlining_suggestions = []
            mock_parser.parse_api_response.return_value = mock_result
            mock_parser_class.return_value = mock_parser
            
            result = engine.analyze_contract("test.pdf", progress_callback=progress_callback)
        
        # Verify progress callback was called
        assert progress_callback.call_count > 0
        
        # Verify it was called with expected arguments
        calls = progress_callback.call_args_list
        assert any("Validating" in str(call) for call in calls)
        assert any("complete" in str(call).lower() for call in calls)
    
    @patch('src.analysis_engine.OpenAIClient')
    def test_validate_api_key(self, mock_client_class):
        """Test API key validation."""
        mock_client = Mock()
        mock_client.validate_api_key.return_value = True
        mock_client_class.return_value = mock_client
        
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        result = engine.validate_api_key()
        
        assert result is True
        mock_client.validate_api_key.assert_called_once()
    
    @patch('src.analysis_engine.OpenAIClient')
    def test_validate_api_key_failure(self, mock_client_class):
        """Test API key validation failure."""
        mock_client = Mock()
        mock_client.validate_api_key.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client
        
        engine = AnalysisEngine(openai_api_key="sk-test-key")
        result = engine.validate_api_key()
        
        assert result is False
