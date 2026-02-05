"""
History Data Models

This module defines the data models for analysis history records.
All models support serialization to/from dictionaries for JSON compatibility.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


@dataclass
class AnalysisRecord:
    """
    Summary record for an analysis, used in history list.
    
    This is a lightweight record containing summary information for display
    in the history list, without the full analysis data.
    
    Attributes:
        id: Unique identifier (UUID)
        filename: Contract filename
        analyzed_at: When analysis was performed
        clause_count: Number of clauses found
        risk_count: Number of risks identified
        file_path: Path to full analysis JSON file
    """
    id: str
    filename: str
    analyzed_at: datetime
    clause_count: int
    risk_count: int
    file_path: Path
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.
        
        Returns:
            Dictionary representation of the analysis record
        """
        return {
            'id': self.id,
            'filename': self.filename,
            'analyzed_at': self.analyzed_at.isoformat(),
            'clause_count': self.clause_count,
            'risk_count': self.risk_count,
            'file_path': str(self.file_path)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AnalysisRecord':
        """
        Create from dictionary.
        
        Args:
            data: Dictionary containing analysis record data
            
        Returns:
            AnalysisRecord instance
            
        Raises:
            KeyError: If required fields are missing
            ValueError: If data types are invalid
        """
        return cls(
            id=data['id'],
            filename=data['filename'],
            analyzed_at=datetime.fromisoformat(data['analyzed_at']),
            clause_count=data['clause_count'],
            risk_count=data['risk_count'],
            file_path=Path(data['file_path'])
        )
    
    def validate(self) -> bool:
        """
        Validate that the analysis record has all required fields.
        
        Returns:
            True if valid, False otherwise
        """
        # Check that id is not empty
        if not self.id or not isinstance(self.id, str):
            return False
        
        # Check that filename is not empty
        if not self.filename or not isinstance(self.filename, str):
            return False
        
        # Check that analyzed_at is a datetime
        if not isinstance(self.analyzed_at, datetime):
            return False
        
        # Check that clause_count is a non-negative integer
        if not isinstance(self.clause_count, int) or self.clause_count < 0:
            return False
        
        # Check that risk_count is a non-negative integer
        if not isinstance(self.risk_count, int) or self.risk_count < 0:
            return False
        
        # Check that file_path is a Path object
        if not isinstance(self.file_path, Path):
            return False
        
        return True
