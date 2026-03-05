"""
Unit tests for VersionDatabase module.

Tests database schema creation, connection management, and basic operations.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.version_database import VersionDatabase, VersionDatabaseError


class TestVersionDatabase:
    """Test suite for VersionDatabase class."""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database file path."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()
    
    def test_database_initialization(self, temp_db_path):
        """Test database initialization creates schema."""
        db = VersionDatabase(db_path=temp_db_path)
        
        # Verify database file was created
        assert temp_db_path.exists()
        
        # Verify schema version
        assert db.get_schema_version() == 1
        
        db.close()
    
    def test_contracts_table_exists(self, temp_db_path):
        """Test contracts table is created with correct schema."""
        db = VersionDatabase(db_path=temp_db_path)
        conn = db.connect()
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='contracts'
        """)
        assert cursor.fetchone() is not None
        
        # Check columns
        cursor.execute("PRAGMA table_info(contracts)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            'contract_id', 'filename', 'file_hash', 
            'current_version', 'created_at', 'updated_at'
        }
        assert columns == expected_columns
        
        db.close()
    
    def test_clauses_table_exists(self, temp_db_path):
        """Test clauses table is created with correct schema."""
        db = VersionDatabase(db_path=temp_db_path)
        conn = db.connect()
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='clauses'
        """)
        assert cursor.fetchone() is not None
        
        # Check columns
        cursor.execute("PRAGMA table_info(clauses)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            'clause_id', 'contract_id', 'clause_version', 
            'clause_identifier', 'content', 'metadata',
            'created_at', 'is_deleted', 'deleted_at'
        }
        assert columns == expected_columns
        
        db.close()
    
    def test_version_metadata_table_exists(self, temp_db_path):
        """Test version_metadata table is created with correct schema."""
        db = VersionDatabase(db_path=temp_db_path)
        conn = db.connect()
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='version_metadata'
        """)
        assert cursor.fetchone() is not None
        
        # Check columns
        cursor.execute("PRAGMA table_info(version_metadata)")
        columns = {row[1] for row in cursor.fetchall()}
        expected_columns = {
            'contract_id', 'version', 'timestamp',
            'changed_clause_ids', 'change_summary'
        }
        assert columns == expected_columns
        
        db.close()
    
    def test_indexes_created(self, temp_db_path):
        """Test that performance indexes are created."""
        db = VersionDatabase(db_path=temp_db_path)
        conn = db.connect()
        cursor = conn.cursor()
        
        # Check indexes exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index'
        """)
        indexes = {row[0] for row in cursor.fetchall()}
        
        expected_indexes = {
            'idx_contracts_file_hash',
            'idx_clauses_contract_version',
            'idx_clauses_identifier'
        }
        
        assert expected_indexes.issubset(indexes)
        
        db.close()
    
    def test_foreign_key_constraints(self, temp_db_path):
        """Test that foreign key constraints are enforced."""
        db = VersionDatabase(db_path=temp_db_path)
        conn = db.connect()
        cursor = conn.cursor()
        
        # Verify foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        assert result[0] == 1  # Foreign keys enabled
        
        # Test referential integrity - insert clause without contract should fail
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO clauses (clause_id, contract_id, clause_version, content)
                VALUES ('clause1', 'nonexistent_contract', 1, 'test content')
            """)
            conn.commit()
        
        db.close()
    
    def test_transaction_commit(self, temp_db_path):
        """Test transaction commit."""
        db = VersionDatabase(db_path=temp_db_path)
        
        # Insert a contract
        db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash)
            VALUES ('test_id', 'test.pdf', 'hash123')
        """)
        db.commit()
        
        # Verify data persists
        cursor = db.execute("""
            SELECT contract_id FROM contracts WHERE contract_id = 'test_id'
        """)
        assert cursor.fetchone() is not None
        
        db.close()
    
    def test_transaction_rollback(self, temp_db_path):
        """Test transaction rollback."""
        db = VersionDatabase(db_path=temp_db_path)
        
        # Insert a contract
        db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash)
            VALUES ('test_id', 'test.pdf', 'hash123')
        """)
        db.rollback()
        
        # Verify data was not persisted
        cursor = db.execute("""
            SELECT contract_id FROM contracts WHERE contract_id = 'test_id'
        """)
        assert cursor.fetchone() is None
        
        db.close()
    
    def test_context_manager_commit(self, temp_db_path):
        """Test context manager commits on success."""
        with VersionDatabase(db_path=temp_db_path) as db:
            db.execute("""
                INSERT INTO contracts (contract_id, filename, file_hash)
                VALUES ('test_id', 'test.pdf', 'hash123')
            """)
        
        # Verify data persists after context exit
        db = VersionDatabase(db_path=temp_db_path)
        cursor = db.execute("""
            SELECT contract_id FROM contracts WHERE contract_id = 'test_id'
        """)
        assert cursor.fetchone() is not None
        db.close()
    
    def test_context_manager_rollback(self, temp_db_path):
        """Test context manager rolls back on exception."""
        try:
            with VersionDatabase(db_path=temp_db_path) as db:
                db.execute("""
                    INSERT INTO contracts (contract_id, filename, file_hash)
                    VALUES ('test_id', 'test.pdf', 'hash123')
                """)
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify data was not persisted after exception
        db = VersionDatabase(db_path=temp_db_path)
        cursor = db.execute("""
            SELECT contract_id FROM contracts WHERE contract_id = 'test_id'
        """)
        assert cursor.fetchone() is None
        db.close()
    
    def test_integrity_check(self, temp_db_path):
        """Test database integrity check."""
        db = VersionDatabase(db_path=temp_db_path)
        
        # Fresh database should pass integrity check
        assert db.verify_integrity() is True
        
        db.close()
    
    def test_cascade_delete(self, temp_db_path):
        """Test that deleting a contract cascades to clauses and version_metadata."""
        db = VersionDatabase(db_path=temp_db_path)
        
        # Insert contract
        db.execute("""
            INSERT INTO contracts (contract_id, filename, file_hash)
            VALUES ('test_contract', 'test.pdf', 'hash123')
        """)
        
        # Insert clause
        db.execute("""
            INSERT INTO clauses (clause_id, contract_id, clause_version, content)
            VALUES ('clause1', 'test_contract', 1, 'test content')
        """)
        
        # Insert version metadata
        db.execute("""
            INSERT INTO version_metadata (contract_id, version, changed_clause_ids, change_summary)
            VALUES ('test_contract', 1, '[]', '{}')
        """)
        
        db.commit()
        
        # Delete contract
        db.execute("DELETE FROM contracts WHERE contract_id = 'test_contract'")
        db.commit()
        
        # Verify clauses were deleted
        cursor = db.execute("SELECT * FROM clauses WHERE contract_id = 'test_contract'")
        assert cursor.fetchone() is None
        
        # Verify version_metadata was deleted
        cursor = db.execute("SELECT * FROM version_metadata WHERE contract_id = 'test_contract'")
        assert cursor.fetchone() is None
        
        db.close()
