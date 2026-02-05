# Contract Versioning User Guide
## CR2A Application - Contract Change Tracking & Differential Versioning

This guide explains how to use the contract versioning features in the CR2A application.

## Overview

The CR2A application now automatically tracks changes to contracts over time. When you re-analyze a contract, the system:
- Detects if it's an updated version of a previous contract
- Stores only the changes (not the entire contract again)
- Maintains complete version history
- Allows you to compare versions and see what changed

## Getting Started

### First Time Upload

When you upload a contract for the first time:

1. Click **Upload Contract** in the Upload tab
2. Select your contract file (PDF, DOCX, or TXT)
3. The system analyzes the contract
4. Results are stored as **Version 1**

That's it! The system automatically tracks this as the first version.

### Uploading an Updated Contract

When you upload an updated version of a contract:

1. Click **Upload Contract** in the Upload tab
2. Select the updated contract file
3. The system detects it might be a duplicate:

```
┌─────────────────────────────────────────────┐
│  Duplicate Contract Detected                │
├─────────────────────────────────────────────┤
│  This file appears to be similar to a       │
│  previously analyzed contract:              │
│                                             │
│  Contract: my_contract_v1.pdf               │
│  Current Version: 1                         │
│  Similarity: 95%                            │
│                                             │
│  Is this an updated version of the same     │
│  contract?                                  │
│                                             │
│         [Yes]           [No]                │
└─────────────────────────────────────────────┘
```

4. Click **Yes** if it's an updated version
5. Click **No** if it's a different contract

If you click **Yes**:
- The system analyzes the new version
- Compares it with the previous version
- Stores only the changes
- Creates **Version 2** (or next version number)

## Viewing Version History

### In the History Tab

The History tab shows all your analyzed contracts with version information:

```
┌─────────────────────────────────────────────────────────┐
│  📄 my_contract.pdf                    2024-01-15 10:30  │
│  📋 25 clauses  ⚠️ 5 risks  📌 Version 3  🔄 8 versioned │
│                                                          │
│  View version: [v3 ▼]  [Compare Versions]               │
│                                                          │
│  [View Analysis]  [Delete]                               │
└─────────────────────────────────────────────────────────┘
```

**Version Information**:
- **📌 Version 3**: Current version number
- **🔄 8 versioned**: Number of clauses that have changed across versions

### Viewing a Specific Version

To view a specific historical version:

1. Open the **History** tab
2. Find the contract you want to view
3. Click the **version dropdown** (e.g., "v3 ▼")
4. Select the version you want to view (e.g., "v1", "v2", "v3")
5. The analysis screen shows that version's state

**Note**: When viewing an old version, you see the contract exactly as it was at that point in time.

## Comparing Versions

### Opening the Comparison View

To compare two versions of a contract:

1. Open the **History** tab
2. Find the contract you want to compare
3. Click **Compare Versions** button
4. The Version Comparison window opens

### Using the Comparison View

The comparison view shows:

```
┌─────────────────────────────────────────────────────────┐
│  Version Comparison: my_contract.pdf                     │
├─────────────────────────────────────────────────────────┤
│  Compare: [v1 ▼]  with  [v3 ▼]  [Compare]               │
├─────────────────────────────────────────────────────────┤
│  Change Summary:                                         │
│  • 3 clauses modified                                    │
│  • 2 clauses added                                       │
│  • 1 clause deleted                                      │
│  • 19 clauses unchanged                                  │
├─────────────────────────────────────────────────────────┤
│  Changes:                                                │
│                                                          │
│  🟢 Added: Clause 2.5 - Termination Notice              │
│     "Either party may terminate this agreement..."       │
│                                                          │
│  🟡 Modified: Clause 3.1 - Payment Terms                │
│     Old: "Payment due within 30 days"                    │
│     New: "Payment due within 45 days"                    │
│                                                          │
│  🔴 Deleted: Clause 4.2 - Warranty Period               │
│     "Warranty period is 90 days from delivery"           │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Color Coding**:
- 🟢 **Green**: Clauses added in the newer version
- 🟡 **Yellow**: Clauses modified between versions
- 🔴 **Red**: Clauses deleted in the newer version
- ⚪ **White**: Clauses unchanged (not shown by default)

### Understanding Text Diffs

For modified clauses, you can see exactly what changed:

```
Clause 3.1 - Payment Terms

Old version:
  Payment due within 30 days of invoice date.
  ─────────────────────────────────────────
  
New version:
  Payment due within 45 days of invoice date.
                     ^^
```

Changed text is highlighted to show the exact differences.

## How Duplicate Detection Works

The system uses two methods to detect duplicates:

### 1. File Hash Matching (Exact Match)

- Computes a SHA-256 hash of the file content
- If the hash matches exactly, it's the same file
- **Result**: "This file appears to be identical to..."

### 2. Filename Similarity Matching (Fuzzy Match)

- Compares filenames using Levenshtein distance
- Matches if similarity is 80% or higher
- **Result**: "This file has a similar name to..."

**Examples of Filename Matches**:
- `contract_v1.pdf` → `contract_v2.pdf` (95% similar) ✓
- `my_contract_2024.pdf` → `my_contract_2025.pdf` (90% similar) ✓
- `agreement.pdf` → `contract.pdf` (40% similar) ✗

## What Gets Stored

### Version 1 (New Contract)
- Complete contract metadata (filename, hash, date)
- All clauses with full content
- All risk assessments
- All metadata

**Storage**: ~100% of contract size

### Version 2+ (Updated Contract)
- Contract metadata (updated date, new version number)
- **Only changed clauses** (modified, added, or deleted)
- Version metadata (what changed, when, summary)

**Storage**: ~20-40% of contract size (60-80% savings!)

### Example Storage Comparison

**Without Versioning** (storing full duplicates):
```
Version 1: 500 KB
Version 2: 500 KB
Version 3: 500 KB
Total: 1,500 KB
```

**With Differential Versioning**:
```
Version 1: 500 KB (full)
Version 2: 100 KB (only changes)
Version 3: 80 KB (only changes)
Total: 680 KB (55% savings!)
```

## Best Practices

### Naming Conventions

Use consistent naming for contract versions:

**Good**:
- `contract_v1.pdf`, `contract_v2.pdf`, `contract_v3.pdf`
- `agreement_2024-01.pdf`, `agreement_2024-02.pdf`
- `NDA_draft1.pdf`, `NDA_draft2.pdf`

**Avoid**:
- `contract.pdf`, `contract_final.pdf`, `contract_FINAL_v2.pdf`
- Random names that don't indicate relationship

### When to Confirm "Yes" (It's an Update)

Confirm **Yes** when:
- ✓ It's a revised version of the same contract
- ✓ The parties are the same
- ✓ The contract purpose is the same
- ✓ You want to track changes over time

### When to Confirm "No" (It's Different)

Confirm **No** when:
- ✗ It's a completely different contract
- ✗ Different parties involved
- ✗ Different contract purpose
- ✗ You want to track it separately

## Troubleshooting

### "No version information shown"

**Possible causes**:
- Versioning components not initialized
- Database file missing or corrupted
- Insufficient permissions

**Solution**:
1. Check application logs for errors
2. Restart the application
3. Verify database file exists at `~/.cr2a/versions.db`
4. Check file permissions

### "Duplicate not detected"

**Possible causes**:
- File content changed significantly (different hash)
- Filename too different (< 80% similarity)
- Contract not in database

**Solution**:
1. Verify the original contract was analyzed
2. Check filename similarity
3. Use consistent naming conventions
4. Manually confirm it's an update if prompted

### "Comparison shows no changes"

**Possible causes**:
- Comparing same version with itself
- Changes too minor (< 5% difference)
- Clause identifiers changed

**Solution**:
1. Verify you selected different versions
2. Check if changes are very minor
3. Review the change summary statistics

### "Version reconstruction failed"

**Possible causes**:
- Database corruption
- Missing clause data
- Invalid version number

**Solution**:
1. Check application logs for details
2. Verify database integrity
3. Try a different version
4. Contact support if issue persists

## Technical Details

### Storage Location

Version data is stored in:
- **Database**: `~/.cr2a/versions.db` (SQLite)
- **Size**: Typically 1-5 MB for 100 contracts

### Performance

- **Duplicate detection**: < 1 second
- **Version storage**: < 3 seconds for 100 clauses
- **Version retrieval**: < 2 seconds for 100 clauses
- **Comparison**: < 1 second for 2 versions

### Limitations

- **Maximum versions**: No hard limit (tested up to 50 versions)
- **Maximum clauses**: No hard limit (tested up to 500 clauses)
- **File size**: Limited by available disk space
- **Comparison granularity**: Clause-level only (not word-level)

## FAQ

### Q: Can I delete old versions?

**A**: Currently, you can only delete entire contracts (all versions). Individual version deletion is not supported yet.

### Q: Can I export version history?

**A**: Not yet. This feature is planned for a future release.

### Q: What happens if I delete a contract?

**A**: All versions of that contract are deleted. This action cannot be undone.

### Q: Can I compare non-consecutive versions?

**A**: Yes! You can compare any two versions (e.g., v1 with v5).

### Q: How accurate is the change detection?

**A**: Very accurate. The system uses text similarity algorithms with a 95% threshold for "unchanged" classification.

### Q: Can I disable versioning?

**A**: Versioning is automatic and cannot be disabled. However, you can always choose "No" when asked if a file is an update.

### Q: What if I accidentally confirm the wrong option?

**A**: You can delete the incorrect version and re-upload the contract. The system will prompt you again.

## Support

For additional help or to report issues:
- Check the application logs at `~/.cr2a/logs/`
- Review the technical documentation in `docs/`
- Contact your system administrator

---

**Version**: 1.0
**Last Updated**: 2026-02-05
**Feature**: Contract Change Tracking & Differential Versioning
