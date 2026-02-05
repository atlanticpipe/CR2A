"""
Differential Storage Module

Provides storage operations for contract versioning with differential storage.
Only stores changes (deltas) between versions to minimize redundancy.
"""

import json
import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.version_database import VersionDatabase, VersionDatabaseError


logger = logging.getLogger(__name__)


@dataclass
class Contract:
    """
    Contract metadata record.
    
    Attributes:
        contract_id: Unique identifier for the contract
        filename: Original filename of the contract
        file_hash: SHA-256 hash of the file content
        current_version: Current version number
        created_at: When contract was first uploaded
        updated_at: When contract was last updated
    """
    contract_id: str
    filename: str
    file_hash: str
    current_version: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Contract':
        """Create from dictionary."""
        # Convert ISO format strings to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('updated_at'), str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class Clause:
    """
    Clause record with versioning information.
    
    Attributes:
        clause_id: Unique identifier for this clause version
        contract_id: References the parent contract
        clause_version: Version number when this clause was created/modified
        clause_identifier: Clause title or identifier (e.g., "Section 2.1")
        content: Full text content of the clause
        metadata: Additional metadata (risk level, category, etc.)
        created_at: When this clause version was created
        is_deleted: Whether this clause is marked as deleted
        deleted_at: When clause was marked as deleted
    """
    clause_id: str
    contract_id: str
    clause_version: int
    clause_identifier: Optional[str]
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    is_deleted: bool = False
    deleted_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format strings
        data['created_at'] = self.created_at.isoformat()
        if self.deleted_at:
            data['deleted_at'] = self.deleted_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Clause':
        """Create from dictionary."""
        # Convert ISO format strings to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('deleted_at') and isinstance(data['deleted_at'], str):
            data['deleted_at'] = datetime.fromisoformat(data['deleted_at'])
        return cls(**data)


@dataclass
class VersionMetadata:
    """
    Metadata about a specific contract version.
    
    Attributes:
        contract_id: References the parent contract
        version: Version number
        timestamp: When this version was created
        changed_clause_ids: List of clause IDs that changed in this version
        change_summary: Summary of changes (modified, added, deleted counts)
    """
    contract_id: str
    version: int
    timestamp: datetime
    changed_clause_ids: List[str]
    change_summary: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime to ISO format string
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionMetadata':
        """Create from dictionary."""
        # Convert ISO format string to datetime
        if isinstance(data.get('timestamp'), str):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class DifferentialStorageError(Exception):
    """Exception raised for differential storage errors."""
    pass


class DifferentialStorage:
    """
    Manages differential storage of contract versions.
    
    This class provides CRUD operations for contracts with differential versioning.
    Only changes (deltas) are stored between versions to minimize redundancy.
    """
    
    def __init__(self, database: Optional[VersionDatabase] = None):
        """
        Initialize differential storage.
        
        Args:
            database: VersionDatabase instance. If None, creates a new instance.
        """
        self.db = database if database is not None else VersionDatabase()
        logger.info("DifferentialStorage initialized")
    
    def store_new_contract(self, contract: Contract, clauses: List[Clause]) -> None:
        """
        Store a new contract with version 1.
        
        This method stores a new contract and all its clauses as version 1.
        All operations are performed within a transaction for atomicity.
        
        Implements Requirement 8.3: Transaction atomicity with rollback on failure.
        
        Args:
            contract: Contract metadata
            clauses: List of clauses for the contract
            
        Raises:
            ValueError: If inputs are invalid
            DifferentialStorageError: If storage operation fails
        """
        # Validate inputs (Requirement 8.2)
        if contract is None:
            logger.error("contract is None")
            raise ValueError("contract cannot be None")
        
        if not contract.contract_id or not isinstance(contract.contract_id, str):
            logger.error("Invalid contract_id: %s", contract.contract_id)
            raise ValueError("contract_id must be a non-empty string")
        
        if contract.current_version != 1:
            logger.error("Invalid version for new contract: %d", contract.current_version)
            raise ValueError("New contract must have version 1")
        
        if clauses is None:
            logger.error("clauses is None")
            raise ValueError("clauses cannot be None")
        
        logger.info("Storing new contract: %s (version 1)", contract.contract_id)
        
        conn = None
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Begin transaction (implicit in SQLite)
            logger.debug("Beginning transaction for new contract storage")
            
            # Insert contract record
            cursor.execute("""
                INSERT INTO contracts (
                    contract_id, filename, file_hash, current_version,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                contract.contract_id,
                contract.filename,
                contract.file_hash,
                contract.current_version,
                contract.created_at.isoformat(),
                contract.updated_at.isoformat()
            ))
            
            # Insert all clauses
            for clause in clauses:
                # Validate clause metadata (Requirement 8.2)
                if not clause.clause_id:
                    logger.error("Clause missing clause_id")
                    raise ValueError("All clauses must have a clause_id")
                
                if clause.contract_id != contract.contract_id:
                    logger.error(
                        "Clause contract_id mismatch: expected %s, got %s",
                        contract.contract_id,
                        clause.contract_id
                    )
                    raise ValueError("Clause contract_id must match contract")
                
                cursor.execute("""
                    INSERT INTO clauses (
                        clause_id, contract_id, clause_version, clause_identifier,
                        content, metadata, created_at, is_deleted, deleted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    clause.clause_id,
                    clause.contract_id,
                    clause.clause_version,
                    clause.clause_identifier,
                    clause.content,
                    json.dumps(clause.metadata),
                    clause.created_at.isoformat(),
                    1 if clause.is_deleted else 0,
                    clause.deleted_at.isoformat() if clause.deleted_at else None
                ))
            
            # Insert version metadata
            changed_clause_ids = [c.clause_id for c in clauses]
            change_summary = {
                "modified": 0,
                "added": len(clauses),
                "deleted": 0
            }
            
            cursor.execute("""
                INSERT INTO version_metadata (
                    contract_id, version, timestamp, changed_clause_ids, change_summary
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                contract.contract_id,
                contract.current_version,
                contract.created_at.isoformat(),
                json.dumps(changed_clause_ids),
                json.dumps(change_summary)
            ))
            
            # Commit transaction (Requirement 8.3)
            conn.commit()
            logger.debug("Transaction committed successfully")
            
            logger.info(
                "Successfully stored contract %s with %d clauses",
                contract.contract_id,
                len(clauses)
            )
            
        except ValueError:
            if conn:
                conn.rollback()
                logger.debug("Transaction rolled back due to validation error")
            raise
        except Exception as e:
            logger.error("Failed to store new contract: %s", e, exc_info=True)
            if conn:
                # Rollback transaction on failure (Requirement 8.3)
                conn.rollback()
                logger.debug("Transaction rolled back due to error")
            raise DifferentialStorageError(f"Failed to store new contract: {e}")
    
    def store_contract_version(
        self,
        contract_id: str,
        version: int,
        changed_clauses: List[Clause],
        version_metadata: VersionMetadata
    ) -> None:
        """
        Store a new version with only changed clauses.
        
        This method stores only the clauses that changed in the new version.
        Unchanged clauses are not duplicated. All operations are performed
        within a transaction for atomicity.
        
        Implements Requirement 8.3: Transaction atomicity with rollback on failure.
        
        Args:
            contract_id: ID of the contract being updated
            version: New version number
            changed_clauses: List of clauses that changed (modified, added, or deleted)
            version_metadata: Metadata about this version
            
        Raises:
            ValueError: If inputs are invalid
            DifferentialStorageError: If storage operation fails
        """
        # Validate inputs (Requirement 8.2)
        if not contract_id or not isinstance(contract_id, str):
            logger.error("Invalid contract_id: %s", contract_id)
            raise ValueError("contract_id must be a non-empty string")
        
        if not isinstance(version, int) or version < 2:
            logger.error("Invalid version: %s", version)
            raise ValueError("version must be an integer >= 2")
        
        if changed_clauses is None:
            logger.error("changed_clauses is None")
            raise ValueError("changed_clauses cannot be None")
        
        if version_metadata is None:
            logger.error("version_metadata is None")
            raise ValueError("version_metadata cannot be None")
        
        # Validate version metadata completeness (Requirement 8.2)
        if version_metadata.contract_id != contract_id:
            logger.error(
                "version_metadata contract_id mismatch: expected %s, got %s",
                contract_id,
                version_metadata.contract_id
            )
            raise ValueError("version_metadata contract_id must match contract_id")
        
        if version_metadata.version != version:
            logger.error(
                "version_metadata version mismatch: expected %d, got %d",
                version,
                version_metadata.version
            )
            raise ValueError("version_metadata version must match version")
        
        logger.info("Storing contract version: %s v%d", contract_id, version)
        
        conn = None
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Begin transaction (implicit in SQLite)
            logger.debug("Beginning transaction for version storage")
            
            # Validate sequential version (Requirement 8.1)
            cursor.execute("""
                SELECT current_version FROM contracts WHERE contract_id = ?
            """, (contract_id,))
            
            row = cursor.fetchone()
            if row is None:
                raise DifferentialStorageError(f"Contract {contract_id} not found")
            
            current_version = row[0]
            expected_version = current_version + 1
            
            if version != expected_version:
                logger.error(
                    "Version not sequential: current=%d, expected=%d, got=%d",
                    current_version,
                    expected_version,
                    version
                )
                raise ValueError(
                    f"Version must be sequential. Expected {expected_version}, got {version}"
                )
            
            # Update contract current_version and updated_at
            cursor.execute("""
                UPDATE contracts
                SET current_version = ?, updated_at = ?
                WHERE contract_id = ?
            """, (
                version,
                datetime.now().isoformat(),
                contract_id
            ))
            
            if cursor.rowcount == 0:
                raise DifferentialStorageError(
                    f"Failed to update contract {contract_id}"
                )
            
            # Insert or update changed clauses
            for clause in changed_clauses:
                # Validate clause metadata (Requirement 8.2)
                if not clause.clause_id:
                    logger.error("Clause missing clause_id")
                    raise ValueError("All clauses must have a clause_id")
                
                if clause.contract_id != contract_id:
                    logger.error(
                        "Clause contract_id mismatch: expected %s, got %s",
                        contract_id,
                        clause.contract_id
                    )
                    raise ValueError("Clause contract_id must match contract")
                
                if clause.is_deleted:
                    # Mark existing clause as deleted
                    cursor.execute("""
                        UPDATE clauses
                        SET is_deleted = 1, deleted_at = ?
                        WHERE clause_id = ? AND contract_id = ?
                    """, (
                        clause.deleted_at.isoformat() if clause.deleted_at else datetime.now().isoformat(),
                        clause.clause_id,
                        contract_id
                    ))
                    
                    if cursor.rowcount == 0:
                        logger.warning(
                            "Failed to mark clause %s as deleted (may not exist)",
                            clause.clause_id
                        )
                else:
                    # Insert new clause version (modified or added)
                    cursor.execute("""
                        INSERT INTO clauses (
                            clause_id, contract_id, clause_version, clause_identifier,
                            content, metadata, created_at, is_deleted, deleted_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        clause.clause_id,
                        clause.contract_id,
                        clause.clause_version,
                        clause.clause_identifier,
                        clause.content,
                        json.dumps(clause.metadata),
                        clause.created_at.isoformat(),
                        0,
                        None
                    ))
            
            # Insert version metadata
            cursor.execute("""
                INSERT INTO version_metadata (
                    contract_id, version, timestamp, changed_clause_ids, change_summary
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                version_metadata.contract_id,
                version_metadata.version,
                version_metadata.timestamp.isoformat(),
                json.dumps(version_metadata.changed_clause_ids),
                json.dumps(version_metadata.change_summary)
            ))
            
            # Commit transaction (Requirement 8.3)
            conn.commit()
            logger.debug("Transaction committed successfully")
            
            logger.info(
                "Successfully stored version %d for contract %s with %d changed clauses",
                version,
                contract_id,
                len(changed_clauses)
            )
            
        except (ValueError, DifferentialStorageError):
            if conn:
                conn.rollback()
                logger.debug("Transaction rolled back due to validation error")
            raise
        except Exception as e:
            logger.error("Failed to store contract version: %s", e, exc_info=True)
            if conn:
                # Rollback transaction on failure (Requirement 8.3)
                conn.rollback()
                logger.debug("Transaction rolled back due to error")
            raise DifferentialStorageError(f"Failed to store contract version: {e}")
    
    def get_contract(self, contract_id: str) -> Optional[Contract]:
        """
        Retrieve contract metadata.
        
        Args:
            contract_id: ID of the contract to retrieve
            
        Returns:
            Contract object or None if not found
            
        Raises:
            DifferentialStorageError: If retrieval operation fails
        """
        logger.debug("Retrieving contract: %s", contract_id)
        
        try:
            cursor = self.db.execute("""
                SELECT contract_id, filename, file_hash, current_version,
                       created_at, updated_at
                FROM contracts
                WHERE contract_id = ?
            """, (contract_id,))
            
            row = cursor.fetchone()
            
            if row is None:
                logger.debug("Contract not found: %s", contract_id)
                return None
            
            contract = Contract(
                contract_id=row[0],
                filename=row[1],
                file_hash=row[2],
                current_version=row[3],
                created_at=datetime.fromisoformat(row[4]),
                updated_at=datetime.fromisoformat(row[5])
            )
            
            logger.debug("Contract retrieved: %s", contract_id)
            return contract
            
        except Exception as e:
            logger.error("Failed to retrieve contract: %s", e)
            raise DifferentialStorageError(f"Failed to retrieve contract: {e}")
    
    def get_clauses(
        self,
        contract_id: str,
        version: Optional[int] = None
    ) -> List[Clause]:
        """
        Retrieve clauses for a contract, optionally filtered by version.
        
        If version is specified, returns clauses as they existed at that version.
        If version is None, returns all clauses for all versions.
        
        Args:
            contract_id: ID of the contract
            version: Optional version number to filter by
            
        Returns:
            List of Clause objects
            
        Raises:
            DifferentialStorageError: If retrieval operation fails
        """
        logger.debug("Retrieving clauses for contract: %s (version: %s)", contract_id, version)
        
        try:
            if version is None:
                # Get all clauses for all versions
                cursor = self.db.execute("""
                    SELECT clause_id, contract_id, clause_version, clause_identifier,
                           content, metadata, created_at, is_deleted, deleted_at
                    FROM clauses
                    WHERE contract_id = ?
                    ORDER BY clause_version, clause_id
                """, (contract_id,))
            else:
                # Get clauses for specific version
                # Include clauses created at or before the version
                # Exclude clauses deleted before or at the version
                cursor = self.db.execute("""
                    SELECT clause_id, contract_id, clause_version, clause_identifier,
                           content, metadata, created_at, is_deleted, deleted_at
                    FROM clauses
                    WHERE contract_id = ?
                      AND clause_version <= ?
                      AND (is_deleted = 0 OR deleted_at IS NULL OR deleted_at > ?)
                    ORDER BY clause_identifier, clause_version DESC
                """, (contract_id, version, datetime.now().isoformat()))
            
            clauses = []
            for row in cursor.fetchall():
                clause = Clause(
                    clause_id=row[0],
                    contract_id=row[1],
                    clause_version=row[2],
                    clause_identifier=row[3],
                    content=row[4],
                    metadata=json.loads(row[5]) if row[5] else {},
                    created_at=datetime.fromisoformat(row[6]),
                    is_deleted=bool(row[7]),
                    deleted_at=datetime.fromisoformat(row[8]) if row[8] else None
                )
                clauses.append(clause)
            
            logger.debug("Retrieved %d clauses", len(clauses))
            return clauses
            
        except Exception as e:
            logger.error("Failed to retrieve clauses: %s", e)
            raise DifferentialStorageError(f"Failed to retrieve clauses: {e}")
    
    def get_version_history(self, contract_id: str) -> List[VersionMetadata]:
        """
        Get all version metadata for a contract.
        
        Args:
            contract_id: ID of the contract
            
        Returns:
            List of VersionMetadata objects, ordered by version number
            
        Raises:
            DifferentialStorageError: If retrieval operation fails
        """
        logger.debug("Retrieving version history for contract: %s", contract_id)
        
        try:
            cursor = self.db.execute("""
                SELECT contract_id, version, timestamp, changed_clause_ids, change_summary
                FROM version_metadata
                WHERE contract_id = ?
                ORDER BY version
            """, (contract_id,))
            
            versions = []
            for row in cursor.fetchall():
                version_metadata = VersionMetadata(
                    contract_id=row[0],
                    version=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    changed_clause_ids=json.loads(row[3]),
                    change_summary=json.loads(row[4])
                )
                versions.append(version_metadata)
            
            logger.debug("Retrieved %d versions", len(versions))
            return versions
            
        except Exception as e:
            logger.error("Failed to retrieve version history: %s", e)
            raise DifferentialStorageError(f"Failed to retrieve version history: {e}")
    
    def get_all_contracts(self) -> List[Contract]:
        """
        Retrieve all contracts from storage.
        
        Returns:
            List of Contract objects
            
        Raises:
            DifferentialStorageError: If retrieval operation fails
        """
        logger.debug("Retrieving all contracts")
        
        try:
            cursor = self.db.execute("""
                SELECT contract_id, filename, file_hash, current_version,
                       created_at, updated_at
                FROM contracts
                ORDER BY updated_at DESC
            """)
            
            contracts = []
            for row in cursor.fetchall():
                contract = Contract(
                    contract_id=row[0],
                    filename=row[1],
                    file_hash=row[2],
                    current_version=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    updated_at=datetime.fromisoformat(row[5])
                )
                contracts.append(contract)
            
            logger.debug("Retrieved %d contracts", len(contracts))
            return contracts
            
        except Exception as e:
            logger.error("Failed to retrieve all contracts: %s", e)
            raise DifferentialStorageError(f"Failed to retrieve all contracts: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        self.db.close()
        logger.debug("DifferentialStorage closed")
