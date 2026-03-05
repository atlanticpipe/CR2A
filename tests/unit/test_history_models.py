"""
Unit tests for History data models.

Tests the data models for analysis history records including
serialization, deserialization, and validation.
"""

import pytest
from datetime import datetime
from pathlib import Path
from src.history_models import AnalysisRecord


class TestAnalysisRecord:
    """Tests for AnalysisRecord model."""
    
    def test_create_analysis_record(self):
        """Test creating AnalysisRecord instance."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.id == "test-uuid-123"
        assert record.filename == "contract.pdf"
        assert record.analyzed_at == now
        assert record.clause_count == 15
        assert record.risk_count == 3
        assert record.file_path == Path("test-uuid-123.json")
    
    def test_to_dict(self):
        """Test converting analysis record to dictionary."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        result = record.to_dict()
        
        assert result['id'] == "test-uuid-123"
        assert result['filename'] == "contract.pdf"
        assert result['analyzed_at'] == now.isoformat()
        assert result['clause_count'] == 15
        assert result['risk_count'] == 3
        assert result['file_path'] == "test-uuid-123.json"
    
    def test_from_dict(self):
        """Test creating analysis record from dictionary."""
        now = datetime.now()
        data = {
            'id': 'test-uuid-123',
            'filename': 'contract.pdf',
            'analyzed_at': now.isoformat(),
            'clause_count': 15,
            'risk_count': 3,
            'file_path': 'test-uuid-123.json'
        }
        
        record = AnalysisRecord.from_dict(data)
        
        assert record.id == "test-uuid-123"
        assert record.filename == "contract.pdf"
        assert record.clause_count == 15
        assert record.risk_count == 3
        assert record.file_path == Path("test-uuid-123.json")
    
    def test_from_dict_missing_field(self):
        """Test creating analysis record from dictionary with missing field."""
        data = {
            'id': 'test-uuid-123',
            'filename': 'contract.pdf',
            # Missing analyzed_at
            'clause_count': 15,
            'risk_count': 3,
            'file_path': 'test-uuid-123.json'
        }
        
        with pytest.raises(KeyError):
            AnalysisRecord.from_dict(data)
    
    def test_validate_valid_record(self):
        """Test validation of valid analysis record."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is True
    
    def test_validate_empty_id(self):
        """Test validation fails for empty id."""
        now = datetime.now()
        record = AnalysisRecord(
            id="",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is False
    
    def test_validate_empty_filename(self):
        """Test validation fails for empty filename."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is False
    
    def test_validate_negative_clause_count(self):
        """Test validation fails for negative clause count."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=-1,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is False
    
    def test_validate_negative_risk_count(self):
        """Test validation fails for negative risk count."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=-1,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is False
    
    def test_validate_zero_counts(self):
        """Test validation passes with zero counts."""
        now = datetime.now()
        record = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=0,
            risk_count=0,
            file_path=Path("test-uuid-123.json")
        )
        
        assert record.validate() is True
    
    def test_round_trip_serialization(self):
        """Test that serialization and deserialization preserve data."""
        now = datetime.now()
        original = AnalysisRecord(
            id="test-uuid-123",
            filename="contract.pdf",
            analyzed_at=now,
            clause_count=15,
            risk_count=3,
            file_path=Path("test-uuid-123.json")
        )
        
        # Serialize to dict
        data = original.to_dict()
        
        # Deserialize back
        restored = AnalysisRecord.from_dict(data)
        
        # Verify all fields match
        assert restored.id == original.id
        assert restored.filename == original.filename
        assert restored.analyzed_at == original.analyzed_at
        assert restored.clause_count == original.clause_count
        assert restored.risk_count == original.risk_count
        assert restored.file_path == original.file_path
