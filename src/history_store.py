"""
History Store Module

Manages persistence of analysis records to local storage.
Stores analysis results as JSON files in the application data directory.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid

from src.history_models import AnalysisRecord
from src.analysis_models import AnalysisResult


logger = logging.getLogger(__name__)


class HistoryStoreError(Exception):
    """Exception raised for history store errors."""
    pass


class HistoryStore:
    """
    Manages persistence of analysis records to local storage.
    
    This class handles saving and loading analysis results to/from JSON files
    in the application data directory. Each analysis is stored as a separate
    JSON file, with an index file tracking all records.
    
    Storage structure:
        %APPDATA%/CR2A/history/
        ├── index.json              # Index of all records
        ├── {uuid1}.json           # Full analysis result 1
        ├── {uuid2}.json           # Full analysis result 2
        └── ...
    """
    
    # Index file format version
    INDEX_VERSION = "1.0"
    ANALYSIS_VERSION = "1.0"
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize history store.
        
        Args:
            storage_dir: Directory for storing history files.
                        Defaults to %APPDATA%/CR2A/history/
        """
        if storage_dir is None:
            # Use %APPDATA%/CR2A/history/ on Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            storage_dir = Path(appdata) / 'CR2A' / 'history'
        
        self.storage_dir = Path(storage_dir)
        self.index_path = self.storage_dir / 'index.json'
        
        # Create storage directory if it doesn't exist
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info("History store initialized at: %s", self.storage_dir)
        except Exception as e:
            logger.error("Failed to create storage directory: %s", e)
            raise HistoryStoreError(f"Failed to create storage directory: {e}")
        
        # Initialize index file if it doesn't exist
        if not self.index_path.exists():
            self._create_empty_index()
    
    def _create_empty_index(self) -> None:
        """Create an empty index file."""
        try:
            index_data = {
                "version": self.INDEX_VERSION,
                "records": []
            }
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
            logger.debug("Created empty index file")
        except Exception as e:
            logger.error("Failed to create index file: %s", e)
            raise HistoryStoreError(f"Failed to create index file: {e}")
    
    def _read_index(self) -> Dict[str, Any]:
        """
        Read the index file.
        
        Returns:
            Index data dictionary
            
        Raises:
            HistoryStoreError: If index cannot be read
        """
        try:
            if not self.index_path.exists():
                logger.warning("Index file not found, creating empty index")
                self._create_empty_index()
                return {"version": self.INDEX_VERSION, "records": []}
            
            with open(self.index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # Validate index structure
            if "records" not in index_data:
                logger.warning("Invalid index structure, creating new index")
                self._create_empty_index()
                return {"version": self.INDEX_VERSION, "records": []}
            
            return index_data
            
        except json.JSONDecodeError as e:
            logger.error("Index file corrupted: %s", e)
            # Attempt to rebuild from individual files
            logger.info("Attempting to rebuild index from individual files")
            return self._rebuild_index()
        except Exception as e:
            logger.error("Error reading index file: %s", e)
            raise HistoryStoreError(f"Error reading index file: {e}")
    
    def _write_index(self, index_data: Dict[str, Any]) -> None:
        """
        Write the index file.
        
        Args:
            index_data: Index data dictionary
            
        Raises:
            HistoryStoreError: If index cannot be written
        """
        try:
            with open(self.index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
            logger.debug("Index file updated")
        except Exception as e:
            logger.error("Failed to write index file: %s", e)
            raise HistoryStoreError(f"Failed to write index file: {e}")
    
    def _rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild index from individual analysis files.
        
        Returns:
            Rebuilt index data dictionary
        """
        logger.info("Rebuilding index from individual files")
        records = []
        
        try:
            # Find all JSON files in storage directory (except index.json)
            for file_path in self.storage_dir.glob("*.json"):
                if file_path.name == "index.json":
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Extract record information from analysis file
                    if "record_id" in data and "analysis" in data:
                        analysis = data["analysis"]
                        metadata = analysis.get("contract_metadata", {})
                        
                        record = {
                            "id": data["record_id"],
                            "filename": metadata.get("filename", "unknown"),
                            "analyzed_at": metadata.get("analyzed_at", ""),
                            "clause_count": len(analysis.get("clauses", [])),
                            "risk_count": len(analysis.get("risks", [])),
                            "file_path": file_path.name
                        }
                        records.append(record)
                        logger.debug("Recovered record: %s", record["id"])
                
                except Exception as e:
                    logger.warning("Failed to read file %s: %s", file_path, e)
                    continue
            
            index_data = {
                "version": self.INDEX_VERSION,
                "records": records
            }
            
            # Write the rebuilt index
            self._write_index(index_data)
            logger.info("Index rebuilt with %d records", len(records))
            
            return index_data
            
        except Exception as e:
            logger.error("Failed to rebuild index: %s", e)
            # Return empty index as fallback
            return {"version": self.INDEX_VERSION, "records": []}
    
    def save(self, analysis_result) -> str:
        """
        Save an analysis result to storage.
        
        Args:
            analysis_result: The completed analysis to save (AnalysisResult, 
                           ComprehensiveAnalysisResult, or VerifiedAnalysisResult)
            
        Returns:
            Unique identifier for the saved record
            
        Raises:
            HistoryStoreError: If save fails
        """
        # Generate unique ID
        record_id = str(uuid.uuid4())
        
        try:
            # Import here to avoid circular dependency
            from src.analysis_models import ComprehensiveAnalysisResult
            
            # Handle different result types
            if hasattr(analysis_result, 'verification_metadata'):
                # This is a VerifiedAnalysisResult
                # Extract metadata from base_result
                base_result = analysis_result.base_result
                if isinstance(base_result, dict):
                    # base_result is already a dict
                    metadata = base_result.get('contract_metadata', {})
                    filename = metadata.get('filename', 'unknown')
                    analyzed_at = metadata.get('analyzed_at', '')
                    clauses = base_result.get('clauses', [])
                    risks = base_result.get('risks', [])
                else:
                    # base_result is an AnalysisResult object
                    filename = base_result.metadata.filename
                    analyzed_at = base_result.metadata.analyzed_at.isoformat()
                    clauses = base_result.clauses
                    risks = base_result.risks
            elif isinstance(analysis_result, ComprehensiveAnalysisResult):
                # This is a ComprehensiveAnalysisResult
                filename = analysis_result.metadata.filename
                analyzed_at = analysis_result.metadata.analyzed_at.isoformat()
                # Count clauses and risks from all sections
                clauses = []
                risks = []
                # Count non-None clause blocks across all sections
                for section in [
                    analysis_result.administrative_and_commercial_terms,
                    analysis_result.technical_and_performance_terms,
                    analysis_result.legal_risk_and_enforcement,
                    analysis_result.regulatory_and_compliance_terms,
                    analysis_result.data_technology_and_deliverables
                ]:
                    for field_name in section.__dataclass_fields__:
                        clause_block = getattr(section, field_name)
                        if clause_block is not None:
                            clauses.append(clause_block)
                            risks.extend(clause_block.risk_triggers_identified)
                # Add supplemental operational risks
                clauses.extend(analysis_result.supplemental_operational_risks)
                for block in analysis_result.supplemental_operational_risks:
                    risks.extend(block.risk_triggers_identified)
            else:
                # This is a standard AnalysisResult
                filename = analysis_result.metadata.filename
                analyzed_at = analysis_result.metadata.analyzed_at.isoformat()
                clauses = analysis_result.clauses
                risks = analysis_result.risks
            
            # Create analysis file
            analysis_file = self.storage_dir / f"{record_id}.json"
            analysis_data = {
                "version": self.ANALYSIS_VERSION,
                "record_id": record_id,
                "analysis": analysis_result.to_dict()
            }
            
            with open(analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2)
            
            logger.debug("Saved analysis to: %s", analysis_file)
            
            # Update index
            index_data = self._read_index()
            
            record = {
                "id": record_id,
                "filename": filename,
                "analyzed_at": analyzed_at if isinstance(analyzed_at, str) else analyzed_at.isoformat(),
                "clause_count": len(clauses),
                "risk_count": len(risks),
                "file_path": f"{record_id}.json"
            }
            
            index_data["records"].append(record)
            self._write_index(index_data)
            
            logger.info("Saved analysis record: %s (%s)", record_id, filename)
            return record_id
            
        except Exception as e:
            logger.error("Failed to save analysis: %s", e)
            # Clean up partial save
            try:
                if analysis_file.exists():
                    analysis_file.unlink()
            except:
                pass
            raise HistoryStoreError(f"Failed to save analysis: {e}")
    
    def load_all(self) -> List[AnalysisRecord]:
        """
        Load all analysis records from storage.
        
        Returns:
            List of AnalysisRecord objects, sorted by date (newest first)
        """
        try:
            index_data = self._read_index()
            records = []
            
            for record_data in index_data.get("records", []):
                try:
                    # Convert file_path to full path
                    record_data_copy = record_data.copy()
                    record_data_copy["file_path"] = str(self.storage_dir / record_data["file_path"])
                    
                    record = AnalysisRecord.from_dict(record_data_copy)
                    
                    # Validate the record
                    if record.validate():
                        records.append(record)
                    else:
                        logger.warning("Invalid record skipped: %s", record_data.get("id", "unknown"))
                
                except Exception as e:
                    logger.warning("Failed to load record: %s. Error: %s", record_data.get("id", "unknown"), e)
                    continue
            
            # Sort by date, newest first
            records.sort(key=lambda r: r.analyzed_at, reverse=True)
            
            logger.info("Loaded %d analysis records", len(records))
            return records
            
        except Exception as e:
            logger.error("Failed to load records: %s", e)
            return []
    
    def get(self, record_id: str):
        """
        Get full analysis result by record ID.
        
        Supports both legacy AnalysisResult and comprehensive ComprehensiveAnalysisResult formats.
        
        Args:
            record_id: Unique identifier of the record
            
        Returns:
            Full AnalysisResult or ComprehensiveAnalysisResult, or None if not found
        """
        try:
            # Import here to avoid circular dependency
            from src.analysis_models import ComprehensiveAnalysisResult
            from src.result_parser import ComprehensiveResultParser
            
            analysis_file = self.storage_dir / f"{record_id}.json"
            
            if not analysis_file.exists():
                logger.warning("Analysis file not found: %s", record_id)
                return None
            
            with open(analysis_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if "analysis" not in data:
                logger.error("Invalid analysis file structure: %s", record_id)
                return None
            
            # Detect schema format
            analysis_data = data["analysis"]
            schema_format = ComprehensiveResultParser.detect_schema_format(analysis_data)
            
            logger.debug("Detected schema format: %s for record %s", schema_format, record_id)
            
            # Deserialize based on detected format
            if schema_format == "comprehensive":
                analysis_result = ComprehensiveAnalysisResult.from_dict(analysis_data)
                # Validate the result
                if not analysis_result.validate():
                    logger.error("Invalid comprehensive analysis data: %s", record_id)
                    return None
            elif schema_format == "legacy":
                analysis_result = AnalysisResult.from_dict(analysis_data)
                # Validate the result
                if not analysis_result.validate_result():
                    logger.error("Invalid legacy analysis data: %s", record_id)
                    return None
            else:
                logger.error("Unknown schema format for record: %s", record_id)
                return None
            
            logger.debug("Loaded analysis: %s (format: %s)", record_id, schema_format)
            return analysis_result
            
        except json.JSONDecodeError as e:
            logger.error("Corrupted analysis file: %s. Error: %s", record_id, e)
            return None
        except Exception as e:
            logger.error("Failed to load analysis: %s. Error: %s", record_id, e)
            return None
    
    def delete(self, record_id: str) -> bool:
        """
        Delete an analysis record.
        
        Args:
            record_id: Unique identifier of the record
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            HistoryStoreError: If deletion fails
        """
        try:
            analysis_file = self.storage_dir / f"{record_id}.json"
            
            # Remove the analysis file
            if analysis_file.exists():
                analysis_file.unlink()
                logger.debug("Deleted analysis file: %s", record_id)
            else:
                logger.warning("Analysis file not found for deletion: %s", record_id)
            
            # Update index
            index_data = self._read_index()
            original_count = len(index_data["records"])
            
            index_data["records"] = [
                r for r in index_data["records"] 
                if r.get("id") != record_id
            ]
            
            new_count = len(index_data["records"])
            
            if original_count == new_count:
                logger.warning("Record not found in index: %s", record_id)
                return False
            
            self._write_index(index_data)
            
            logger.info("Deleted analysis record: %s", record_id)
            return True
            
        except Exception as e:
            logger.error("Failed to delete analysis: %s. Error: %s", record_id, e)
            raise HistoryStoreError(f"Failed to delete analysis: {e}")
    
    def get_summary(self, record_id: str) -> Optional[AnalysisRecord]:
        """
        Get summary information for a record without loading full data.
        
        Args:
            record_id: Unique identifier of the record
            
        Returns:
            AnalysisRecord or None if not found
        """
        try:
            index_data = self._read_index()
            
            for record_data in index_data.get("records", []):
                if record_data.get("id") == record_id:
                    # Convert file_path to full path
                    record_data_copy = record_data.copy()
                    record_data_copy["file_path"] = str(self.storage_dir / record_data["file_path"])
                    
                    record = AnalysisRecord.from_dict(record_data_copy)
                    
                    if record.validate():
                        return record
                    else:
                        logger.warning("Invalid record: %s", record_id)
                        return None
            
            logger.warning("Record not found: %s", record_id)
            return None
            
        except Exception as e:
            logger.error("Failed to get summary: %s. Error: %s", record_id, e)
            return None
