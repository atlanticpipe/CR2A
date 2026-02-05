"""
Version Database Module

Manages SQLite database for contract versioning and differential storage.
Provides schema creation, migration, and connection management.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional
import os


logger = logging.getLogger(__name__)


class VersionDatabaseError(Exception):
    """Exception raised for version database errors."""
    pass


class VersionDatabase:
    """
    Manages SQLite database for contract versioning.
    
    This class handles database initialization, schema creation, and connection
    management for the contract change tracking feature.
    
    Database location:
        %APPDATA%/CR2A/versions.db
    """
    
    # Schema version for migrations
    SCHEMA_VERSION = 1
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize version database.
        
        Args:
            db_path: Path to database file.
                    Defaults to %APPDATA%/CR2A/versions.db
        """
        if db_path is None:
            # Use %APPDATA%/CR2A/versions.db on Windows
            appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
            db_dir = Path(appdata) / 'CR2A'
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / 'versions.db'
        
        self.db_path = Path(db_path)
        self.connection: Optional[sqlite3.Connection] = None
        
        logger.info("Version database initialized at: %s", self.db_path)
        
        # Initialize database schema
        self._initialize_schema()
    
    def connect(self) -> sqlite3.Connection:
        """
        Get or create database connection.
        
        Returns:
            SQLite connection object
            
        Raises:
            VersionDatabaseError: If connection fails
        """
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False
                )
                # Enable foreign key constraints
                self.connection.execute("PRAGMA foreign_keys = ON")
                # Use Row factory for dict-like access
                self.connection.row_factory = sqlite3.Row
                logger.debug("Database connection established")
            
            return self.connection
            
        except sqlite3.Error as e:
            logger.error("Failed to connect to database: %s", e)
            raise VersionDatabaseError(f"Failed to connect to database: {e}")
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            logger.debug("Database connection closed")
    
    def _initialize_schema(self) -> None:
        """
        Initialize database schema if not exists.
        
        Creates all required tables, indexes, and constraints.
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            
            # Check if schema already exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='schema_version'
            """)
            
            if cursor.fetchone() is not None:
                # Schema exists, check version
                cursor.execute("SELECT version FROM schema_version LIMIT 1")
                row = cursor.fetchone()
                if row and row[0] == self.SCHEMA_VERSION:
                    logger.debug("Database schema up to date (version %d)", self.SCHEMA_VERSION)
                    return
                else:
                    logger.info("Database schema needs migration")
                    # Future: implement migration logic here
                    return
            
            logger.info("Creating database schema (version %d)", self.SCHEMA_VERSION)
            
            # Create schema_version table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create contracts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contracts (
                    contract_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    current_version INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create index on file_hash for duplicate detection
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_contracts_file_hash 
                ON contracts(file_hash)
            """)
            
            # Create clauses table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clauses (
                    clause_id TEXT PRIMARY KEY,
                    contract_id TEXT NOT NULL,
                    clause_version INTEGER NOT NULL,
                    clause_identifier TEXT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TIMESTAMP,
                    FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                )
            """)
            
            # Create composite index on contract_id and clause_version for efficient queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clauses_contract_version 
                ON clauses(contract_id, clause_version)
            """)
            
            # Create index on clause_identifier for matching
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_clauses_identifier 
                ON clauses(clause_identifier)
            """)
            
            # Create version_metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS version_metadata (
                    contract_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    changed_clause_ids TEXT NOT NULL,
                    change_summary TEXT NOT NULL,
                    PRIMARY KEY (contract_id, version),
                    FOREIGN KEY (contract_id) REFERENCES contracts(contract_id)
                        ON DELETE CASCADE
                        ON UPDATE CASCADE
                )
            """)
            
            # Insert schema version
            cursor.execute("""
                INSERT INTO schema_version (version) VALUES (?)
            """, (self.SCHEMA_VERSION,))
            
            conn.commit()
            logger.info("Database schema created successfully")
            
        except sqlite3.Error as e:
            logger.error("Failed to initialize schema: %s", e)
            if conn:
                conn.rollback()
            raise VersionDatabaseError(f"Failed to initialize schema: {e}")
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Cursor object
            
        Raises:
            VersionDatabaseError: If query execution fails
        """
        try:
            conn = self.connect()
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor
            
        except sqlite3.IntegrityError as e:
            # Handle referential integrity violations (Requirement 8.4)
            error_msg = str(e).lower()
            if 'foreign key' in error_msg:
                logger.error("Referential integrity violation: %s", e)
                raise VersionDatabaseError(f"Referential integrity violation: {e}")
            elif 'unique' in error_msg:
                logger.error("Unique constraint violation: %s", e)
                raise VersionDatabaseError(f"Unique constraint violation: {e}")
            else:
                logger.error("Integrity constraint violation: %s", e)
                raise VersionDatabaseError(f"Integrity constraint violation: {e}")
        except sqlite3.Error as e:
            logger.error("Query execution failed: %s", e, exc_info=True)
            raise VersionDatabaseError(f"Query execution failed: {e}")
    
    def commit(self) -> None:
        """
        Commit current transaction.
        
        Raises:
            VersionDatabaseError: If commit fails
        """
        try:
            if self.connection is not None:
                self.connection.commit()
                logger.debug("Transaction committed")
                
        except sqlite3.Error as e:
            logger.error("Commit failed: %s", e)
            raise VersionDatabaseError(f"Commit failed: {e}")
    
    def rollback(self) -> None:
        """
        Rollback current transaction.
        
        Raises:
            VersionDatabaseError: If rollback fails
        """
        try:
            if self.connection is not None:
                self.connection.rollback()
                logger.debug("Transaction rolled back")
                
        except sqlite3.Error as e:
            logger.error("Rollback failed: %s", e)
            raise VersionDatabaseError(f"Rollback failed: {e}")
    
    def begin_transaction(self) -> None:
        """
        Begin a new transaction.
        
        SQLite automatically begins transactions, but this method
        can be used to explicitly start a transaction.
        """
        conn = self.connect()
        # SQLite begins transaction automatically on first DML statement
        # This is a no-op but provided for API consistency
        logger.debug("Transaction begun (implicit)")
    
    def get_schema_version(self) -> int:
        """
        Get current schema version.
        
        Returns:
            Schema version number
        """
        try:
            cursor = self.execute("SELECT version FROM schema_version LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
            
        except VersionDatabaseError:
            return 0
    
    def verify_integrity(self) -> bool:
        """
        Verify database integrity.
        
        Returns:
            True if integrity check passes, False otherwise
        """
        try:
            cursor = self.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            is_ok = result and result[0] == 'ok'
            
            if is_ok:
                logger.info("Database integrity check passed")
            else:
                logger.error("Database integrity check failed: %s", result)
            
            return is_ok
            
        except VersionDatabaseError as e:
            logger.error("Integrity check failed: %s", e)
            return False
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()
