#!/usr/bin/env python3
"""
Repository Cleanup Script

This script removes test artifacts, temporary files, and redundant code from the repository.
It provides dry-run support for safe preview before actual cleanup.

Usage:
    # Preview what would be removed (recommended first)
    python cleanup_repo.py --dry-run
    
    # Run actual cleanup
    python cleanup_repo.py
    
    # Run with verbose logging
    python cleanup_repo.py --verbose
    
    # Remove backup files and folders
    python cleanup_repo.py --remove-backups
    
    # Skip duplicate file detection
    python cleanup_repo.py --skip-duplicates

Examples:
    # Dry run to see what would be removed
    python cleanup_repo.py --dry-run
    
    # Actually perform the cleanup
    python cleanup_repo.py
    
    # Verbose output with detailed logging
    python cleanup_repo.py --verbose --dry-run
    
    # Remove backup files and folders (with dry-run preview)
    python cleanup_repo.py --remove-backups --dry-run
    
    # Skip duplicate detection and remove backups
    python cleanup_repo.py --skip-duplicates --remove-backups
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.cleanup import CleanupOrchestrator


def setup_logging(verbose: bool = False):
    """Configure logging based on verbosity level."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main entry point for the cleanup script."""
    parser = argparse.ArgumentParser(
        description='Clean up repository by removing test artifacts, temporary files, and redundant code.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be removed without actually deleting files'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--remove-backups',
        action='store_true',
        help='Remove backup files and folders (e.g., *_updated.js, *_backup.html, .backups/, backups/)'
    )
    
    parser.add_argument(
        '--skip-duplicates',
        action='store_true',
        help='Skip duplicate file detection and removal'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Create orchestrator
    orchestrator = CleanupOrchestrator(dry_run=args.dry_run)
    
    # Print mode
    mode = "DRY RUN" if args.dry_run else "ACTUAL CLEANUP"
    print(f"\n{'='*60}")
    print(f"Repository Cleanup - {mode}")
    print(f"{'='*60}\n")
    
    try:
        # Run cleanup
        report = orchestrator.run_cleanup(
            remove_backups=args.remove_backups,
            skip_duplicates=args.skip_duplicates
        )
        
        # Print summary
        print(f"\n{'='*60}")
        print("Cleanup Summary")
        print(f"{'='*60}")
        print(f"Files removed: {report.total_files_removed()}")
        print(f"Space saved: {orchestrator.remover._format_size(report.total_space_saved()) if hasattr(orchestrator.remover, '_format_size') else report.total_space_saved()}")
        print(f"Failed removals: {len(report.failed_removals())}")
        
        if report.failed_removals():
            print("\nFailed removals:")
            for result in report.failed_removals():
                print(f"  - {result.path}: {result.error_message}")
        
        print(f"\nReport saved to: .kiro/specs/repository-reorganization/cleanup-report.md")
        print(f"{'='*60}\n")
        
        # Exit with success
        return 0
        
    except Exception as e:
        print(f"\nERROR: Cleanup failed: {e}", file=sys.stderr)
        logging.exception("Cleanup failed with exception")
        return 1


if __name__ == "__main__":
    sys.exit(main())
