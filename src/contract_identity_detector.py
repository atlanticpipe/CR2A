"""
Contract Identity Detector Module

Detects when an uploaded contract matches a previously analyzed contract
using file hashing and filename similarity matching.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from src.version_database import VersionDatabase


logger = logging.getLogger(__name__)


@dataclass
class ContractMatch:
    """Represents a potential contract match."""
    contract_id: str
    filename: str
    file_hash: str
    current_version: int
    match_type: str  # 'hash' or 'filename'
    similarity_score: float  # 1.0 for hash match, 0.0-1.0 for filename match


class ContractIdentityDetector:
    """
    Detects duplicate contracts using file hashing and filename similarity.
    
    This class implements contract identity detection as specified in
    Requirements 1.1, 1.2, and 1.3.
    """
    
    # Threshold for filename similarity matching (80%)
    FILENAME_SIMILARITY_THRESHOLD = 0.8
    
    def __init__(self, db: VersionDatabase):
        """
        Initialize the contract identity detector.
        
        Args:
            db: VersionDatabase instance for querying existing contracts
        """
        self.db = db
        logger.debug("ContractIdentityDetector initialized")
    
    def compute_file_hash(self, file_path: str) -> str:
        """
        Compute SHA-256 hash of file content.
        
        Implements Requirement 1.1: File hash computation for duplicate detection.
        
        Args:
            file_path: Path to the file to hash
            
        Returns:
            Hexadecimal string representation of SHA-256 hash
            
        Raises:
            FileNotFoundError: If file does not exist
            IOError: If file cannot be read
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                logger.error("File not found: %s", file_path)
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Read file in chunks for memory efficiency with large files
            sha256_hash = hashlib.sha256()
            
            with open(path, 'rb') as f:
                # Read in 64KB chunks
                for chunk in iter(lambda: f.read(65536), b''):
                    sha256_hash.update(chunk)
            
            file_hash = sha256_hash.hexdigest()
            logger.debug("Computed file hash for %s: %s", file_path, file_hash[:16] + "...")
            
            return file_hash
            
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to compute file hash for %s: %s", file_path, e)
            raise IOError(f"Failed to compute file hash: {e}")
    
    def calculate_filename_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity score between two filenames using Levenshtein distance.
        
        Implements Requirement 1.3: Filename similarity detection.
        
        The similarity score is normalized to a range of 0.0 to 1.0, where:
        - 1.0 = identical filenames
        - 0.0 = completely different filenames
        
        Args:
            name1: First filename
            name2: Second filename
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize filenames: lowercase and strip extensions for comparison
        norm1 = Path(name1).stem.lower()
        norm2 = Path(name2).stem.lower()
        
        # Handle empty strings
        if not norm1 or not norm2:
            return 0.0
        
        # If identical, return 1.0
        if norm1 == norm2:
            return 1.0
        
        # Calculate Levenshtein distance
        distance = self._levenshtein_distance(norm1, norm2)
        
        # Normalize to similarity score (0.0 to 1.0)
        max_length = max(len(norm1), len(norm2))
        similarity = 1.0 - (distance / max_length)
        
        logger.debug(
            "Filename similarity between '%s' and '%s': %.2f",
            name1, name2, similarity
        )
        
        return similarity
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Calculate Levenshtein distance between two strings.
        
        Uses dynamic programming approach for efficiency.
        
        Args:
            s1: First string
            s2: Second string
            
        Returns:
            Levenshtein distance (number of edits required)
        """
        # Create distance matrix
        len1, len2 = len(s1), len(s2)
        
        # Initialize matrix with dimensions (len1+1) x (len2+1)
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        # Initialize first column and row
        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j
        
        # Fill matrix using dynamic programming
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if s1[i - 1] == s2[j - 1]:
                    cost = 0
                else:
                    cost = 1
                
                matrix[i][j] = min(
                    matrix[i - 1][j] + 1,      # deletion
                    matrix[i][j - 1] + 1,      # insertion
                    matrix[i - 1][j - 1] + cost  # substitution
                )
        
        return matrix[len1][len2]
    
    def find_potential_matches(
        self,
        file_hash: str,
        filename: str
    ) -> List[ContractMatch]:
        """
        Find contracts that might match based on hash or filename similarity.
        
        Implements Requirements 1.2 and 1.3: Hash-based and filename-based
        duplicate detection.
        
        Args:
            file_hash: SHA-256 hash of the uploaded file
            filename: Name of the uploaded file
            
        Returns:
            List of ContractMatch objects, sorted by match quality
            (hash matches first, then filename matches by similarity score)
            
        Raises:
            ValueError: If file_hash or filename is empty
        """
        # Validate inputs (Requirement 8.2)
        if not file_hash or not isinstance(file_hash, str):
            logger.error("Invalid file_hash provided: %s", file_hash)
            raise ValueError("file_hash must be a non-empty string")
        
        if not filename or not isinstance(filename, str):
            logger.error("Invalid filename provided: %s", filename)
            raise ValueError("filename must be a non-empty string")
        
        matches = []
        
        try:
            # First, check for exact hash matches (Requirement 1.2)
            cursor = self.db.execute("""
                SELECT contract_id, filename, file_hash, current_version
                FROM contracts
                WHERE file_hash = ?
            """, (file_hash,))
            
            hash_matches = cursor.fetchall()
            
            for row in hash_matches:
                try:
                    match = ContractMatch(
                        contract_id=row['contract_id'],
                        filename=row['filename'],
                        file_hash=row['file_hash'],
                        current_version=row['current_version'],
                        match_type='hash',
                        similarity_score=1.0
                    )
                    matches.append(match)
                    logger.info(
                        "Found hash match: contract_id=%s, filename=%s",
                        match.contract_id, match.filename
                    )
                except Exception as e:
                    logger.warning("Failed to create ContractMatch from row: %s", e)
                    continue
            
            # If no hash matches, check for filename similarity (Requirement 1.3)
            if not matches:
                cursor = self.db.execute("""
                    SELECT contract_id, filename, file_hash, current_version
                    FROM contracts
                """)
                
                all_contracts = cursor.fetchall()
                
                for row in all_contracts:
                    try:
                        similarity = self.calculate_filename_similarity(
                            filename,
                            row['filename']
                        )
                        
                        # Only include matches above threshold
                        if similarity >= self.FILENAME_SIMILARITY_THRESHOLD:
                            match = ContractMatch(
                                contract_id=row['contract_id'],
                                filename=row['filename'],
                                file_hash=row['file_hash'],
                                current_version=row['current_version'],
                                match_type='filename',
                                similarity_score=similarity
                            )
                            matches.append(match)
                            logger.info(
                                "Found filename match: contract_id=%s, filename=%s, similarity=%.2f",
                                match.contract_id, match.filename, similarity
                            )
                    except Exception as e:
                        logger.warning("Failed to process contract row: %s", e)
                        continue
            
            # Sort matches: hash matches first, then by similarity score
            matches.sort(key=lambda m: (m.match_type != 'hash', -m.similarity_score))
            
            logger.info("Found %d potential matches for file: %s", len(matches), filename)
            
            return matches
            
        except ValueError:
            raise
        except Exception as e:
            logger.error("Error finding potential matches for file '%s': %s", filename, e, exc_info=True)
            # Return empty list on database error rather than failing
            return []
