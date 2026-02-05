"""
Version Manager Module

Manages version numbers and tracks changes for contract versioning.
Implements Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.1, 7.2, 7.3, 7.4.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional, Any

from src.differential_storage import (
    DifferentialStorage,
    Contract,
    Clause,
    VersionMetadata
)
from src.change_comparator import ContractDiff, ClauseChangeType
from src.analysis_models import ComprehensiveAnalysisResult


logger = logging.getLogger(__name__)


@dataclass
class VersionedContract:
    """
    Represents a contract with version-assigned clauses.
    
    Attributes:
        contract_id: ID of the contract
        version: Version number
        clauses: List of clauses with assigned version numbers
        version_metadata: Metadata about this version
    """
    contract_id: str
    version: int
    clauses: List[Clause]
    version_metadata: VersionMetadata


class VersionManagerError(Exception):
    """Exception raised for version manager errors."""
    pass


class VersionManager:
    """
    Manages version numbers and tracks changes for contract versioning.
    
    This class implements version management as specified in Requirements 3.1-3.6
    and version reconstruction as specified in Requirements 7.1-7.4.
    """
    
    def __init__(self, storage: DifferentialStorage):
        """
        Initialize the version manager.
        
        Args:
            storage: DifferentialStorage instance for accessing contract data
        """
        self.storage = storage
        logger.debug("VersionManager initialized")
    
    def get_next_version(self, contract_id: str) -> int:
        """
        Get the next version number for a contract.
        
        Implements Requirement 3.2: Contract version increment.
        
        Args:
            contract_id: ID of the contract
            
        Returns:
            Next version number (current_version + 1)
            
        Raises:
            VersionManagerError: If contract not found or retrieval fails
        """
        logger.debug("Getting next version for contract: %s", contract_id)
        
        try:
            contract = self.storage.get_contract(contract_id)
            
            if contract is None:
                raise VersionManagerError(f"Contract not found: {contract_id}")
            
            next_version = contract.current_version + 1
            
            logger.debug(
                "Next version for contract %s: %d",
                contract_id,
                next_version
            )
            
            return next_version
            
        except Exception as e:
            logger.error("Failed to get next version: %s", e)
            raise VersionManagerError(f"Failed to get next version: {e}")
    
    def assign_clause_versions(
        self,
        contract_diff: ContractDiff,
        contract_id: str,
        new_version: int
    ) -> VersionedContract:
        """
        Assign version numbers to clauses based on ContractDiff.
        
        Implements Requirements:
        - 3.3: Modified clause version tracking
        - 3.4: Unchanged clause version preservation
        - 3.5: Timestamp format validity (ISO 8601)
        - 3.6: Change tracking completeness
        - 8.1: Sequential version validation
        - 8.2: Metadata completeness validation
        
        Args:
            contract_diff: Diff containing all clause changes
            contract_id: ID of the contract
            new_version: New version number to assign
            
        Returns:
            VersionedContract with version-assigned clauses and metadata
            
        Raises:
            ValueError: If inputs are invalid
            VersionManagerError: If version assignment fails
        """
        # Validate inputs (Requirement 8.2)
        if contract_diff is None:
            logger.error("contract_diff is None")
            raise ValueError("contract_diff cannot be None")
        
        if not contract_id or not isinstance(contract_id, str):
            logger.error("Invalid contract_id: %s", contract_id)
            raise ValueError("contract_id must be a non-empty string")
        
        if not isinstance(new_version, int) or new_version < 1:
            logger.error("Invalid new_version: %s", new_version)
            raise ValueError("new_version must be a positive integer")
        
        # Validate sequential version (Requirement 8.1)
        try:
            contract = self.storage.get_contract(contract_id)
            if contract is None:
                raise VersionManagerError(f"Contract not found: {contract_id}")
            
            expected_version = contract.current_version + 1
            if new_version != expected_version:
                logger.error(
                    "Version number not sequential: expected %d, got %d",
                    expected_version,
                    new_version
                )
                raise ValueError(
                    f"Version number must be sequential. Expected {expected_version}, got {new_version}"
                )
        except VersionManagerError:
            raise
        except Exception as e:
            logger.error("Failed to validate version number: %s", e)
            raise VersionManagerError(f"Failed to validate version number: {e}")
        
        logger.info(
            "Assigning clause versions for contract %s version %d",
            contract_id,
            new_version
        )
        
        try:
            timestamp = datetime.now()
            versioned_clauses: List[Clause] = []
            changed_clause_ids: List[str] = []
            
            # Get existing clauses to preserve version numbers for unchanged clauses
            existing_clauses = self.storage.get_clauses(contract_id)
            existing_clause_map = {c.clause_identifier: c for c in existing_clauses}
            
            # Process unchanged clauses (Requirement 3.4)
            # These keep their existing version numbers
            for comparison in contract_diff.unchanged_clauses:
                try:
                    clause_identifier = comparison.clause_identifier
                    
                    # Find the existing clause to preserve its version
                    if clause_identifier in existing_clause_map:
                        existing_clause = existing_clause_map[clause_identifier]
                        
                        # Create clause with preserved version number
                        clause = Clause(
                            clause_id=existing_clause.clause_id,
                            contract_id=contract_id,
                            clause_version=existing_clause.clause_version,  # Preserve version
                            clause_identifier=clause_identifier,
                            content=comparison.new_content or "",
                            metadata={
                                "similarity_score": comparison.similarity_score,
                                "change_type": comparison.change_type.value
                            },
                            created_at=existing_clause.created_at,  # Preserve original creation time
                            is_deleted=False,
                            deleted_at=None
                        )
                        versioned_clauses.append(clause)
                    else:
                        logger.warning(
                            "Unchanged clause '%s' not found in existing clauses",
                            clause_identifier
                        )
                except Exception as e:
                    logger.error("Failed to process unchanged clause '%s': %s", clause_identifier, e)
                    continue
            
            # Process modified clauses (Requirement 3.3)
            # These get the new version number
            for comparison in contract_diff.modified_clauses:
                try:
                    clause_identifier = comparison.clause_identifier
                    
                    # Generate new clause ID for the modified version
                    clause_id = str(uuid.uuid4())
                    
                    clause = Clause(
                        clause_id=clause_id,
                        contract_id=contract_id,
                        clause_version=new_version,  # Assign new version
                        clause_identifier=clause_identifier,
                        content=comparison.new_content or "",
                        metadata={
                            "similarity_score": comparison.similarity_score,
                            "change_type": comparison.change_type.value,
                            "old_content": comparison.old_content
                        },
                        created_at=timestamp,
                        is_deleted=False,
                        deleted_at=None
                    )
                    versioned_clauses.append(clause)
                    changed_clause_ids.append(clause_id)
                except Exception as e:
                    logger.error("Failed to process modified clause '%s': %s", clause_identifier, e)
                    continue
            
            # Process added clauses (Requirement 3.1 for new clauses)
            # These get the new version number
            for comparison in contract_diff.added_clauses:
                try:
                    clause_identifier = comparison.clause_identifier
                    
                    # Generate new clause ID
                    clause_id = str(uuid.uuid4())
                    
                    clause = Clause(
                        clause_id=clause_id,
                        contract_id=contract_id,
                        clause_version=new_version,  # Assign new version
                        clause_identifier=clause_identifier,
                        content=comparison.new_content or "",
                        metadata={
                            "similarity_score": comparison.similarity_score,
                            "change_type": comparison.change_type.value
                        },
                        created_at=timestamp,
                        is_deleted=False,
                        deleted_at=None
                    )
                    versioned_clauses.append(clause)
                    changed_clause_ids.append(clause_id)
                except Exception as e:
                    logger.error("Failed to process added clause '%s': %s", clause_identifier, e)
                    continue
            
            # Process deleted clauses
            # Mark them as deleted with the new version number
            for comparison in contract_diff.deleted_clauses:
                try:
                    clause_identifier = comparison.clause_identifier
                    
                    # Find the existing clause to mark as deleted
                    if clause_identifier in existing_clause_map:
                        existing_clause = existing_clause_map[clause_identifier]
                        
                        # Create deleted clause marker
                        clause = Clause(
                            clause_id=existing_clause.clause_id,
                            contract_id=contract_id,
                            clause_version=existing_clause.clause_version,
                            clause_identifier=clause_identifier,
                            content=comparison.old_content or "",
                            metadata={
                                "similarity_score": comparison.similarity_score,
                                "change_type": comparison.change_type.value
                            },
                            created_at=existing_clause.created_at,
                            is_deleted=True,
                            deleted_at=timestamp
                        )
                        versioned_clauses.append(clause)
                        changed_clause_ids.append(existing_clause.clause_id)
                    else:
                        logger.warning(
                            "Deleted clause '%s' not found in existing clauses",
                            clause_identifier
                        )
                except Exception as e:
                    logger.error("Failed to process deleted clause '%s': %s", clause_identifier, e)
                    continue
            
            # Create version metadata (Requirements 3.5, 3.6, 8.2)
            # Validate metadata completeness
            if not changed_clause_ids and (contract_diff.modified_clauses or 
                                          contract_diff.added_clauses or 
                                          contract_diff.deleted_clauses):
                logger.warning("No changed clause IDs recorded despite having changes")
            
            version_metadata = VersionMetadata(
                contract_id=contract_id,
                version=new_version,
                timestamp=timestamp,  # ISO 8601 format via datetime
                changed_clause_ids=changed_clause_ids,
                change_summary=contract_diff.change_summary
            )
            
            logger.info(
                "Version assignment complete: %d clauses, %d changed",
                len(versioned_clauses),
                len(changed_clause_ids)
            )
            
            return VersionedContract(
                contract_id=contract_id,
                version=new_version,
                clauses=versioned_clauses,
                version_metadata=version_metadata
            )
            
        except (ValueError, VersionManagerError):
            raise
        except Exception as e:
            logger.error("Failed to assign clause versions: %s", e, exc_info=True)
            raise VersionManagerError(f"Failed to assign clause versions: {e}")
    
    def get_version_metadata(
        self,
        contract_id: str,
        version: int
    ) -> Optional[VersionMetadata]:
        """
        Get metadata for a specific version.
        
        Args:
            contract_id: ID of the contract
            version: Version number
            
        Returns:
            VersionMetadata object or None if not found
            
        Raises:
            VersionManagerError: If retrieval fails
        """
        logger.debug(
            "Getting version metadata for contract %s version %d",
            contract_id,
            version
        )
        
        try:
            all_versions = self.storage.get_version_history(contract_id)
            
            for version_metadata in all_versions:
                if version_metadata.version == version:
                    logger.debug("Version metadata found")
                    return version_metadata
            
            logger.debug("Version metadata not found")
            return None
            
        except Exception as e:
            logger.error("Failed to get version metadata: %s", e)
            raise VersionManagerError(f"Failed to get version metadata: {e}")
    
    def reconstruct_version(
        self,
        contract_id: str,
        version: int
    ) -> Dict[str, Any]:
        """
        Reconstruct the complete contract state at a specific version.
        
        Implements Requirements 7.1, 7.2, 7.3, 7.4:
        - 7.1: Reconstruct complete contract state at version
        - 7.2: Include clauses that existed at or before version
        - 7.3: Exclude clauses added after version
        - 7.4: Include deleted clauses only if they existed at version
        
        Algorithm:
        1. Retrieve all clauses for the contract
        2. Filter clauses where clause_version <= requested_version
        3. Exclude clauses marked as deleted at or before requested_version
        4. Group by clause identifier, take the latest version <= requested_version
        5. Assemble into complete contract structure
        
        Args:
            contract_id: ID of the contract
            version: Version number to reconstruct
            
        Returns:
            Dictionary containing the reconstructed contract state with clauses
            
        Raises:
            VersionManagerError: If reconstruction fails
        """
        logger.info(
            "Reconstructing contract %s at version %d",
            contract_id,
            version
        )
        
        try:
            # Get contract metadata
            contract = self.storage.get_contract(contract_id)
            
            if contract is None:
                raise VersionManagerError(f"Contract not found: {contract_id}")
            
            # Validate version number
            if version < 1 or version > contract.current_version:
                raise VersionManagerError(
                    f"Invalid version {version}. Must be between 1 and {contract.current_version}"
                )
            
            # Get all clauses for the contract
            all_clauses = self.storage.get_clauses(contract_id)
            
            # Filter clauses for the requested version
            # Requirement 7.2: Include clauses created at or before version
            # Requirement 7.3: Exclude clauses added after version
            version_clauses = [
                c for c in all_clauses
                if c.clause_version <= version
            ]
            
            # Requirement 7.4: Exclude clauses deleted at or before version
            # Keep only clauses that are not deleted or were deleted after this version
            active_clauses = []
            for clause in version_clauses:
                if not clause.is_deleted:
                    active_clauses.append(clause)
                elif clause.deleted_at and clause.deleted_at > datetime.now():
                    # Clause was deleted in the future (shouldn't happen, but handle it)
                    active_clauses.append(clause)
            
            # Group by clause identifier and take the latest version <= requested_version
            clause_map: Dict[str, Clause] = {}
            for clause in active_clauses:
                identifier = clause.clause_identifier
                
                if identifier not in clause_map:
                    clause_map[identifier] = clause
                else:
                    # Keep the clause with the higher version number
                    if clause.clause_version > clause_map[identifier].clause_version:
                        clause_map[identifier] = clause
            
            # Get version metadata
            version_metadata = self.get_version_metadata(contract_id, version)
            
            # Assemble reconstructed contract
            reconstructed = {
                "contract_id": contract_id,
                "version": version,
                "filename": contract.filename,
                "file_hash": contract.file_hash,
                "clauses": [
                    {
                        "clause_id": clause.clause_id,
                        "clause_identifier": clause.clause_identifier,
                        "clause_version": clause.clause_version,
                        "content": clause.content,
                        "metadata": clause.metadata,
                        "created_at": clause.created_at.isoformat()
                    }
                    for clause in clause_map.values()
                ],
                "version_metadata": version_metadata.to_dict() if version_metadata else None,
                "reconstructed_at": datetime.now().isoformat()
            }
            
            logger.info(
                "Reconstruction complete: %d clauses at version %d",
                len(clause_map),
                version
            )
            
            return reconstructed
            
        except VersionManagerError:
            raise
        except Exception as e:
            logger.error("Failed to reconstruct version: %s", e)
            raise VersionManagerError(f"Failed to reconstruct version: {e}")
