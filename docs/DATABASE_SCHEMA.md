# Database Schema Documentation

## Overview

The Contract Change Tracking feature uses a SQLite database to store contract versions and differential changes. The database is located at `%APPDATA%/CR2A/versions.db` on Windows.

## Schema Version

Current schema version: **1**

## Tables

### 1. contracts

Stores base contract information with one record per unique contract.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| contract_id | TEXT | PRIMARY KEY | Unique identifier for the contract |
| filename | TEXT | NOT NULL | Original filename of the contract |
| file_hash | TEXT | NOT NULL | SHA-256 hash of the file content |
| current_version | INTEGER | NOT NULL, DEFAULT 1 | Current version number |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When contract was first uploaded |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When contract was last updated |

**Indexes:**
- `idx_contracts_file_hash` on `file_hash` - For duplicate detection

### 2. clauses

Stores clause data with differential versioning. Only changed clauses create new records.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| clause_id | TEXT | PRIMARY KEY | Unique identifier for this clause version |
| contract_id | TEXT | NOT NULL, FOREIGN KEY | References contracts(contract_id) |
| clause_version | INTEGER | NOT NULL | Version number when this clause was created/modified |
| clause_identifier | TEXT | NULL | Clause title or identifier (e.g., "Section 2.1") |
| content | TEXT | NOT NULL | Full text content of the clause |
| metadata | TEXT | NULL | JSON string with additional metadata |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When this clause version was created |
| is_deleted | INTEGER | DEFAULT 0 | Boolean flag (0=active, 1=deleted) |
| deleted_at | TIMESTAMP | NULL | When clause was marked as deleted |

**Foreign Keys:**
- `contract_id` → `contracts(contract_id)` ON DELETE CASCADE ON UPDATE CASCADE

**Indexes:**
- `idx_clauses_contract_version` on `(contract_id, clause_version)` - For version queries
- `idx_clauses_identifier` on `clause_identifier` - For clause matching

### 3. version_metadata

Stores metadata about each contract version, tracking what changed.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| contract_id | TEXT | NOT NULL, PRIMARY KEY | References contracts(contract_id) |
| version | INTEGER | NOT NULL, PRIMARY KEY | Version number |
| timestamp | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When this version was created |
| changed_clause_ids | TEXT | NOT NULL | JSON array of clause IDs that changed |
| change_summary | TEXT | NOT NULL | JSON object with change counts |

**Foreign Keys:**
- `contract_id` → `contracts(contract_id)` ON DELETE CASCADE ON UPDATE CASCADE

**Composite Primary Key:** `(contract_id, version)`

### 4. schema_version

Tracks database schema version for migrations.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| version | INTEGER | PRIMARY KEY | Schema version number |
| applied_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When schema was applied |

## Differential Storage Strategy

The database uses a differential storage approach to minimize redundancy:

1. **New Contract (Version 1):**
   - Insert one record in `contracts` table
   - Insert all clauses in `clauses` table with `clause_version = 1`
   - Insert version metadata in `version_metadata` table

2. **Updated Contract (Version N):**
   - Update `current_version` in `contracts` table
   - For **unchanged clauses**: No new records (reuse existing)
   - For **modified clauses**: Insert new records with `clause_version = N`
   - For **added clauses**: Insert new records with `clause_version = N`
   - For **deleted clauses**: Update `is_deleted = 1` and set `deleted_at`
   - Insert version metadata in `version_metadata` table

## Version Reconstruction

To reconstruct a specific version of a contract:

```sql
SELECT * FROM clauses
WHERE contract_id = ?
  AND clause_version <= ?
  AND (is_deleted = 0 OR deleted_at > ?)
GROUP BY clause_identifier
HAVING MAX(clause_version)
```

This query:
1. Filters clauses for the contract
2. Includes only clauses created at or before the target version
3. Excludes clauses deleted before the target version
4. Groups by clause identifier and takes the latest version

## Performance Optimizations

1. **Indexes:**
   - `idx_contracts_file_hash` - Fast duplicate detection on upload
   - `idx_clauses_contract_version` - Fast version queries
   - `idx_clauses_identifier` - Fast clause matching during comparison

2. **Foreign Key Constraints:**
   - Enabled with `PRAGMA foreign_keys = ON`
   - CASCADE deletes ensure referential integrity
   - Prevents orphaned clauses and version metadata

3. **Transaction Support:**
   - All multi-step operations wrapped in transactions
   - Automatic rollback on errors
   - Context manager support for clean resource management

## Data Integrity

1. **Referential Integrity:**
   - Foreign key constraints prevent orphaned records
   - CASCADE deletes maintain consistency

2. **Transaction Atomicity:**
   - All version updates are atomic
   - Rollback on any failure ensures consistency

3. **Validation:**
   - Schema version tracking for migrations
   - Integrity checks available via `PRAGMA integrity_check`

## Example Usage

```python
from src.version_database import VersionDatabase

# Initialize database
db = VersionDatabase()

# Use context manager for automatic commit/rollback
with db:
    # Insert a new contract
    db.execute("""
        INSERT INTO contracts (contract_id, filename, file_hash)
        VALUES (?, ?, ?)
    """, ('contract_123', 'agreement.pdf', 'abc123...'))
    
    # Insert clauses
    db.execute("""
        INSERT INTO clauses (clause_id, contract_id, clause_version, content)
        VALUES (?, ?, ?, ?)
    """, ('clause_1', 'contract_123', 1, 'Clause content...'))

# Query contracts
cursor = db.execute("SELECT * FROM contracts WHERE file_hash = ?", ('abc123...',))
contract = cursor.fetchone()
```

## Migration Strategy

Future schema changes will:
1. Increment `SCHEMA_VERSION` constant
2. Check current version in `schema_version` table
3. Apply migration SQL if version mismatch
4. Update `schema_version` table

## Storage Location

- **Windows:** `%APPDATA%/CR2A/versions.db`
- **Linux/Mac:** `~/.config/CR2A/versions.db` (future support)

## Backup Recommendations

1. Regular backups of `versions.db` file
2. Export to JSON for portability
3. Test restore procedures periodically
