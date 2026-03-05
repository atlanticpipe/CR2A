"""
Unit tests for HistoryStore class.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from datetime import datetime

from src.history_store import HistoryStore, HistoryStoreError
from src.history_models import AnalysisRecord
from src.analysis_models import AnalysisResult, ContractMetadata, Clause, Risk


class TestHistoryStore:
    """Test suite for HistoryStore class."""
    
    def create_sample_analysis_result(self, filename="test_contract.pdf"):
        """Helper to create a sample AnalysisResult for testing."""
        metadata = ContractMetadata(
            filename=filename,
            analyzed_at=datetime.now(),
            page_count=10,
            file_size_bytes=1024000
        )
        
        clauses = [
            Clause(
                id="clause_1",
                type="payment_terms",
                text="Payment shall be made within 30 days",
                page=1,
                risk_level="low"
            ),
            Clause(
                id="clause_2",
                type="liability",
                text="Liability is limited to contract value",
                page=2,
                risk_level="medium"
            )
        ]
        
        risks = [
            Risk(
                id="risk_1",
                clause_id="clause_2",
                severity="medium",
                description="Limited liability may not cover all damages",
                recommendation="Consider increasing liability coverage"
            )
        ]
        
        return AnalysisResult(
            metadata=metadata,
            clauses=clauses,
            risks=risks,
            compliance_issues=[],
            redlining_suggestions=[]
        )
    
    def test_initialization_creates_directory(self):
        """Test that HistoryStore creates storage directory on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            
            # Directory should not exist yet
            assert not storage_dir.exists()
            
            # Initialize HistoryStore
            store = HistoryStore(storage_dir)
            
            # Directory should now exist
            assert storage_dir.exists()
            assert store.storage_dir == storage_dir
    
    def test_initialization_creates_index_file(self):
        """Test that HistoryStore creates index.json on initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            
            store = HistoryStore(storage_dir)
            
            # Index file should exist
            assert store.index_path.exists()
            
            # Index should be valid JSON with correct structure
            with open(store.index_path, 'r') as f:
                index_data = json.load(f)
            
            assert "version" in index_data
            assert "records" in index_data
            assert index_data["records"] == []
    
    def test_save_creates_analysis_file(self):
        """Test that save() creates an analysis file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis = self.create_sample_analysis_result()
            record_id = store.save(analysis)
            
            # Record ID should be returned
            assert record_id is not None
            assert isinstance(record_id, str)
            
            # Analysis file should exist
            analysis_file = storage_dir / f"{record_id}.json"
            assert analysis_file.exists()
    
    def test_save_updates_index(self):
        """Test that save() updates the index file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis = self.create_sample_analysis_result("contract1.pdf")
            record_id = store.save(analysis)
            
            # Read index
            with open(store.index_path, 'r') as f:
                index_data = json.load(f)
            
            # Index should contain one record
            assert len(index_data["records"]) == 1
            
            record = index_data["records"][0]
            assert record["id"] == record_id
            assert record["filename"] == "contract1.pdf"
            assert record["clause_count"] == 2
            assert record["risk_count"] == 1
    
    def test_load_all_returns_empty_list_initially(self):
        """Test that load_all() returns empty list when no records exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            records = store.load_all()
            
            assert records == []
    
    def test_load_all_returns_saved_records(self):
        """Test that load_all() returns previously saved records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Save two analyses
            analysis1 = self.create_sample_analysis_result("contract1.pdf")
            analysis2 = self.create_sample_analysis_result("contract2.pdf")
            
            record_id1 = store.save(analysis1)
            record_id2 = store.save(analysis2)
            
            # Load all records
            records = store.load_all()
            
            assert len(records) == 2
            assert all(isinstance(r, AnalysisRecord) for r in records)
            
            # Check that both records are present
            record_ids = [r.id for r in records]
            assert record_id1 in record_ids
            assert record_id2 in record_ids
    
    def test_load_all_sorts_by_date_newest_first(self):
        """Test that load_all() returns records sorted by date (newest first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Create analyses with different timestamps
            analysis1 = self.create_sample_analysis_result("old_contract.pdf")
            analysis1.metadata.analyzed_at = datetime(2024, 1, 1, 10, 0, 0)
            
            analysis2 = self.create_sample_analysis_result("new_contract.pdf")
            analysis2.metadata.analyzed_at = datetime(2024, 1, 2, 10, 0, 0)
            
            # Save in reverse order
            store.save(analysis1)
            store.save(analysis2)
            
            # Load all records
            records = store.load_all()
            
            # Should be sorted newest first
            assert records[0].filename == "new_contract.pdf"
            assert records[1].filename == "old_contract.pdf"
    
    def test_get_returns_full_analysis(self):
        """Test that get() returns the full AnalysisResult."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            original_analysis = self.create_sample_analysis_result("test.pdf")
            record_id = store.save(original_analysis)
            
            # Get the analysis back
            loaded_analysis = store.get(record_id)
            
            assert loaded_analysis is not None
            assert isinstance(loaded_analysis, AnalysisResult)
            assert loaded_analysis.metadata.filename == "test.pdf"
            assert len(loaded_analysis.clauses) == 2
            assert len(loaded_analysis.risks) == 1
    
    def test_get_returns_none_for_nonexistent_id(self):
        """Test that get() returns None for non-existent record ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            result = store.get("nonexistent-id-12345")
            
            assert result is None
    
    def test_get_returns_none_for_invalid_structure(self):
        """Test that get() returns None when analysis file has invalid structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Create a file with invalid structure (missing "analysis" key)
            record_id = "test-invalid-structure"
            invalid_file = storage_dir / f"{record_id}.json"
            
            with open(invalid_file, 'w') as f:
                json.dump({"version": "1.0", "record_id": record_id}, f)
            
            # get() should return None for invalid structure
            result = store.get(record_id)
            
            assert result is None
    
    def test_get_returns_none_for_corrupted_json(self):
        """Test that get() returns None when analysis file has corrupted JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Create a file with corrupted JSON
            record_id = "test-corrupted-json"
            corrupted_file = storage_dir / f"{record_id}.json"
            
            with open(corrupted_file, 'w') as f:
                f.write("{ invalid json content }")
            
            # get() should return None for corrupted JSON
            result = store.get(record_id)
            
            assert result is None
    
    def test_delete_removes_file_and_index_entry(self):
        """Test that delete() removes both the file and index entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis = self.create_sample_analysis_result()
            record_id = store.save(analysis)
            
            # Verify file exists
            analysis_file = storage_dir / f"{record_id}.json"
            assert analysis_file.exists()
            
            # Delete the record
            result = store.delete(record_id)
            
            assert result is True
            assert not analysis_file.exists()
            
            # Verify index is updated
            records = store.load_all()
            assert len(records) == 0
    
    def test_delete_returns_false_for_nonexistent_id(self):
        """Test that delete() returns False for non-existent record ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            result = store.delete("nonexistent-id-12345")
            
            assert result is False
    
    def test_get_summary_returns_analysis_record(self):
        """Test that get_summary() returns AnalysisRecord without loading full data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis = self.create_sample_analysis_result("summary_test.pdf")
            record_id = store.save(analysis)
            
            # Get summary
            summary = store.get_summary(record_id)
            
            assert summary is not None
            assert isinstance(summary, AnalysisRecord)
            assert summary.id == record_id
            assert summary.filename == "summary_test.pdf"
            assert summary.clause_count == 2
            assert summary.risk_count == 1
    
    def test_get_summary_returns_none_for_nonexistent_id(self):
        """Test that get_summary() returns None for non-existent record ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            summary = store.get_summary("nonexistent-id-12345")
            
            assert summary is None
    
    def test_corrupted_index_rebuilds(self):
        """Test that corrupted index file triggers rebuild."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Save an analysis
            analysis = self.create_sample_analysis_result()
            record_id = store.save(analysis)
            
            # Corrupt the index file
            with open(store.index_path, 'w') as f:
                f.write("{ invalid json }")
            
            # Load all should trigger rebuild
            records = store.load_all()
            
            # Should still find the record
            assert len(records) == 1
            assert records[0].id == record_id
    
    def test_load_all_skips_corrupted_records(self):
        """Test that load_all() skips corrupted records and continues."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            # Save two analyses
            analysis1 = self.create_sample_analysis_result("good1.pdf")
            analysis2 = self.create_sample_analysis_result("good2.pdf")
            
            record_id1 = store.save(analysis1)
            record_id2 = store.save(analysis2)
            
            # Manually add a corrupted record to index
            with open(store.index_path, 'r') as f:
                index_data = json.load(f)
            
            corrupted_record = {
                "id": "corrupted-id",
                "filename": "corrupted.pdf",
                # Missing required fields
            }
            index_data["records"].append(corrupted_record)
            
            with open(store.index_path, 'w') as f:
                json.dump(index_data, f)
            
            # Load all should skip corrupted record
            records = store.load_all()
            
            # Should only return the two valid records
            assert len(records) == 2
            record_ids = [r.id for r in records]
            assert record_id1 in record_ids
            assert record_id2 in record_ids
            assert "corrupted-id" not in record_ids
    
    def test_save_load_round_trip_preserves_data(self):
        """Test that saving and loading preserves all analysis data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            original = self.create_sample_analysis_result("roundtrip.pdf")
            record_id = store.save(original)
            
            loaded = store.get(record_id)
            
            # Verify all data is preserved
            assert loaded.metadata.filename == original.metadata.filename
            assert loaded.metadata.page_count == original.metadata.page_count
            assert loaded.metadata.file_size_bytes == original.metadata.file_size_bytes
            
            assert len(loaded.clauses) == len(original.clauses)
            assert loaded.clauses[0].id == original.clauses[0].id
            assert loaded.clauses[0].text == original.clauses[0].text
            
            assert len(loaded.risks) == len(original.risks)
            assert loaded.risks[0].id == original.risks[0].id
            assert loaded.risks[0].description == original.risks[0].description
    
    def test_file_naming_convention(self):
        """Test that analysis files follow the naming convention {uuid}.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis = self.create_sample_analysis_result()
            record_id = store.save(analysis)
            
            # File should be named {record_id}.json
            expected_file = storage_dir / f"{record_id}.json"
            assert expected_file.exists()
            
            # Verify the file name matches the record ID
            assert expected_file.stem == record_id
    
    def test_default_storage_location(self):
        """Test that default storage location is %APPDATA%/CR2A/history/."""
        store = HistoryStore()
        
        expected_dir = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'CR2A' / 'history'
        assert store.storage_dir == expected_dir
    
    def test_multiple_saves_create_separate_files(self):
        """Test that multiple saves create separate files with unique IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir) / "test_history"
            store = HistoryStore(storage_dir)
            
            analysis1 = self.create_sample_analysis_result("contract1.pdf")
            analysis2 = self.create_sample_analysis_result("contract2.pdf")
            
            record_id1 = store.save(analysis1)
            record_id2 = store.save(analysis2)
            
            # IDs should be different
            assert record_id1 != record_id2
            
            # Both files should exist
            assert (storage_dir / f"{record_id1}.json").exists()
            assert (storage_dir / f"{record_id2}.json").exists()
