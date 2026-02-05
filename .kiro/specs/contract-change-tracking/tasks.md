# Implementation Plan: Contract Change Tracking & Differential Versioning

## Overview

This implementation plan breaks down the Contract Change Tracking & Differential Versioning feature into discrete coding tasks. The approach follows a bottom-up strategy: first implementing core utilities (hashing, comparison), then storage layer, then business logic (version management), and finally UI integration. Each task builds on previous work and includes testing sub-tasks to validate functionality incrementally.

## Tasks

- [x] 1. Set up database schema and storage foundation
  - Create database migration for contracts, clauses, and version_metadata tables
  - Add indexes for performance optimization (file_hash, contract_id + clause_version)
  - Set up foreign key constraints for referential integrity
  - _Requirements: 2.1, 2.6, 8.4, 9.5_

- [ ]* 1.1 Write property test for referential integrity
  - **Property 31: Referential Integrity**
  - **Validates: Requirements 8.4**

- [x] 2. Implement Contract Identity Detector
  - [x] 2.1 Create ContractIdentityDetector class with file hashing
    - Implement compute_file_hash() using SHA-256
    - Implement find_potential_matches() to query storage for hash and filename matches
    - Implement calculate_filename_similarity() using Levenshtein distance
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]* 2.2 Write property tests for identity detection
    - **Property 1: File Hash Consistency**
    - **Validates: Requirements 1.1**

  - [ ]* 2.3 Write property test for hash-based duplicate detection
    - **Property 2: Hash-Based Duplicate Detection**
    - **Validates: Requirements 1.2**

  - [ ]* 2.4 Write property test for filename similarity
    - **Property 3: Filename Similarity Detection**
    - **Validates: Requirements 1.3**

  - [ ]* 2.5 Write unit tests for edge cases
    - Test empty files, large files, special characters in filenames
    - Test exact filename matches vs. fuzzy matches
    - _Requirements: 1.1, 1.3_

- [x] 3. Implement Change Comparator
  - [x] 3.1 Create ChangeComparator class with text comparison
    - Implement normalize_text() for whitespace and case normalization
    - Implement calculate_text_similarity() using difflib.SequenceMatcher
    - Implement compare_clauses() to classify changes (unchanged, modified, added, deleted)
    - Implement compare_contracts() to generate full ContractDiff
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* 3.2 Write property test for text normalization
    - **Property 20: Text Normalization Invariance**
    - **Validates: Requirements 4.6**

  - [ ]* 3.3 Write property tests for change classification
    - **Property 16: Modification Classification Threshold**
    - **Property 17: Addition Detection**
    - **Property 18: Deletion Detection**
    - **Property 19: Unchanged Classification Threshold**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**

  - [ ]* 3.4 Write unit tests for specific comparison scenarios
    - Test clauses with known similarity scores
    - Test edge cases: empty clauses, very long clauses, special characters
    - _Requirements: 4.1, 4.2, 4.5_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Differential Storage layer
  - [x] 5.1 Create DifferentialStorage class with CRUD operations
    - Implement store_new_contract() for initial contract storage
    - Implement store_contract_version() for storing deltas
    - Implement get_contract() to retrieve contract metadata
    - Implement get_clauses() with optional version filtering
    - Implement get_version_history() to retrieve all version metadata
    - Add transaction support for atomic operations
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 8.3_

  - [ ]* 5.2 Write property tests for storage invariants
    - **Property 4: Single Contract Record Per ID**
    - **Property 5: Unchanged Clause Non-Duplication**
    - **Property 6: Modified Clause Version Increment**
    - **Property 7: Added Clause Version Assignment**
    - **Property 8: Deleted Clause Preservation**
    - **Property 9: Clause Metadata Completeness**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

  - [ ]* 5.3 Write property test for transaction atomicity
    - **Property 30: Transaction Atomicity**
    - **Validates: Requirements 8.3**

  - [ ]* 5.4 Write unit tests for storage operations
    - Test storing contracts with various clause configurations
    - Test transaction rollback scenarios
    - Test edge cases: empty contracts, contracts with no clauses
    - _Requirements: 2.1, 8.3_

- [x] 6. Implement Version Manager
  - [x] 6.1 Create VersionManager class with version logic
    - Implement get_next_version() to calculate next version number
    - Implement assign_clause_versions() to assign versions based on ContractDiff
    - Implement get_version_metadata() to retrieve version info
    - Implement reconstruct_version() to rebuild historical contract state
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 7.1, 7.2, 7.3, 7.4_

  - [ ]* 6.2 Write property tests for version assignment
    - **Property 10: Initial Version Assignment**
    - **Property 11: Contract Version Increment**
    - **Property 12: Modified Clause Version Tracking**
    - **Property 13: Unchanged Clause Version Preservation**
    - **Property 14: Timestamp Format Validity**
    - **Property 15: Change Tracking Completeness**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

  - [ ]* 6.3 Write property test for version reconstruction
    - **Property 25: Version Reconstruction Accuracy**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [ ]* 6.4 Write property test for sequential version validation
    - **Property 28: Sequential Version Validation**
    - **Validates: Requirements 8.1**

  - [ ]* 6.5 Write property test for metadata validation
    - **Property 29: Metadata Completeness Validation**
    - **Validates: Requirements 8.2**

  - [ ]* 6.6 Write unit tests for version scenarios
    - Test version assignment with specific scenarios
    - Test reconstruction with known version states
    - Test edge cases: version 1, large version numbers
    - _Requirements: 3.1, 7.1_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Integrate versioning into contract upload workflow
  - [x] 8.1 Modify contract upload handler to use ContractIdentityDetector
    - Add hash computation on file upload
    - Add duplicate detection logic
    - Add user prompt for confirming updated version vs. new contract
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 8.2 Integrate ChangeComparator and VersionManager into upload flow
    - When user confirms update: compare with previous version
    - Assign version numbers to changed clauses
    - Store differential changes via DifferentialStorage
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 3.2, 3.3, 3.4_

  - [ ]* 8.3 Write integration tests for upload workflow
    - Test end-to-end: upload → detect → compare → store
    - Test both new contract and updated contract paths
    - _Requirements: 1.4, 1.5, 1.6_

- [x] 9. Implement History Display enhancements
  - [x] 9.1 Update HistoryDisplay to show version information
    - Modify contract list to show current version number
    - Add count of clauses with multiple versions
    - Add version selector UI component
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [x] 9.2 Implement version retrieval and display
    - Add functionality to retrieve and display specific versions
    - Use VersionManager.reconstruct_version() to get historical state
    - _Requirements: 5.5, 7.1_

  - [ ]* 9.3 Write property tests for history display data
    - **Property 21: Unique Contract Entries**
    - **Property 22: Current Version Display Accuracy**
    - **Property 23: Versioned Clause Count Accuracy**
    - **Property 24: Complete Version Listing**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [ ]* 9.4 Write unit tests for UI data preparation
    - Test history data with specific contracts
    - Test edge cases: contracts with no versions, contracts with many versions
    - _Requirements: 5.1, 5.2_

- [x] 10. Implement Change Visualization UI
  - [x] 10.1 Create comparison view component
    - Add UI for selecting two versions to compare
    - Implement diff rendering with color-coded highlighting
    - Add change summary display (counts of modified/added/deleted clauses)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 10.2 Implement text diff highlighting
    - Use difflib to generate detailed text diffs
    - Render diffs with HTML/CSS highlighting
    - _Requirements: 6.5_

  - [ ]* 10.3 Write property tests for diff and summary
    - **Property 26: Text Diff Completeness**
    - **Property 27: Change Summary Accuracy**
    - **Validates: Requirements 6.5, 6.6**

  - [ ]* 10.4 Write unit tests for diff rendering
    - Test diff rendering with known text pairs
    - Test color-coding for different change types
    - _Requirements: 6.2, 6.3, 6.4, 6.5_

- [x] 11. Add error handling and validation
  - [x] 11.1 Implement error handlers for all components
    - Add try-catch blocks with appropriate error messages
    - Implement transaction rollback on storage failures
    - Add validation for version numbers and metadata
    - Add logging for all error scenarios
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 11.2 Write unit tests for error scenarios
    - Test file hash computation failure
    - Test storage transaction failure and rollback
    - Test invalid version number rejection
    - Test referential integrity violation handling
    - _Requirements: 8.1, 8.2, 8.3_

- [x] 12. Final integration and end-to-end testing
  - [x] 12.1 Wire all components together
    - Ensure ContractIdentityDetector, ChangeComparator, VersionManager, and DifferentialStorage work together
    - Integrate with existing CR2A upload and history components
    - _Requirements: All_

  - [ ]* 12.2 Write end-to-end integration tests
    - Test complete workflow: upload v1 → upload v2 → view history → compare versions
    - Test multi-version scenarios: create 5+ versions and verify reconstruction
    - Test error recovery: simulate failures at each step
    - _Requirements: All_

- [x] 13. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with minimum 100 iterations each
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end workflows
- The implementation follows a bottom-up approach: utilities → storage → business logic → UI
