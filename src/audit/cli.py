"""Command-line interface for the Security Audit System."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .file_scanner import FileScanner
from .pattern_detector import PatternDetector
from .issue_classifier import IssueClassifier
from .report_generator import ReportGenerator
from .config_loader import ConfigLoader, ConfigurationError


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        prog='security-audit',
        description='Security Audit System - Scan codebase for security and configuration issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory
  security-audit .
  
  # Scan with custom config
  security-audit /path/to/project --config audit-config.yaml
  
  # Output to file
  security-audit . --output audit-report.md
  
  # Generate separate reports
  security-audit . --audit-output audit.md --remediation-output remediation.md
  
  # Verbose mode with error log
  security-audit . --verbose --error-log errors.md
        """
    )
    
    # Required arguments
    parser.add_argument(
        'root_path',
        type=str,
        help='Root directory to scan'
    )
    
    # Configuration
    parser.add_argument(
        '-c', '--config',
        type=str,
        metavar='FILE',
        help='Path to configuration file (JSON or YAML)'
    )
    
    # Output options
    parser.add_argument(
        '-o', '--output',
        type=str,
        metavar='FILE',
        help='Output file for combined report (default: stdout)'
    )
    
    parser.add_argument(
        '--audit-output',
        type=str,
        metavar='FILE',
        help='Output file for audit report only'
    )
    
    parser.add_argument(
        '--remediation-output',
        type=str,
        metavar='FILE',
        help='Output file for remediation plan only'
    )
    
    parser.add_argument(
        '--error-log',
        type=str,
        metavar='FILE',
        help='Output file for error log'
    )
    
    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )
    
    # File scanning options
    parser.add_argument(
        '--max-file-size',
        type=int,
        metavar='BYTES',
        help='Maximum file size to scan in bytes (default: 10MB)'
    )
    
    return parser


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Validate arguments
    if args.quiet and args.verbose:
        print("Error: Cannot use --quiet and --verbose together", file=sys.stderr)
        return 1
    
    # Load configuration if provided
    config_loader = None
    custom_patterns = None
    custom_extensions = None
    custom_exclusions = None
    
    if args.config:
        try:
            config_loader = ConfigLoader(args.config)
            custom_patterns = config_loader.get_custom_patterns()
            custom_extensions = config_loader.get_custom_extensions()
            custom_exclusions = config_loader.get_custom_exclusions()
            
            if args.verbose:
                print(f"Loaded configuration from: {args.config}")
                if custom_patterns:
                    print(f"  - Custom patterns: {len(custom_patterns)} categories")
                if custom_extensions:
                    print(f"  - Custom extensions: {len(custom_extensions)} types")
                if custom_exclusions:
                    print(f"  - Custom exclusions: {len(custom_exclusions)} patterns")
        
        except ConfigurationError as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            return 1
    
    # Initialize components
    try:
        # Create file scanner
        scanner = FileScanner(
            root_path=args.root_path,
            exclusions=custom_exclusions,
            extensions=custom_extensions,
            max_file_size=args.max_file_size
        )
        
        if args.verbose:
            print(f"Scanning directory: {args.root_path}")
        
        # Scan for files
        file_paths = scanner.scan()
        
        if args.verbose:
            print(f"Found {len(file_paths)} files to analyze")
        
        # Create pattern detector
        detector = PatternDetector(custom_patterns=custom_patterns)
        
        # Detect issues
        if args.verbose:
            print("Analyzing files for security and configuration issues...")
        
        findings = detector.detect_in_files(scanner, file_paths)
        
        if args.verbose:
            print(f"Detected {len(findings)} potential issues")
        
        # Classify issues
        classifier = IssueClassifier()
        classified_issues = classifier.classify(findings)
        
        # Generate reports
        generator = ReportGenerator()
        
        # Get errors from scanner
        errors = scanner.get_errors()
        
        # Generate audit report
        audit_report = generator.generate_audit_report(classified_issues, errors)
        
        # Generate remediation plan
        remediation_plan = generator.generate_remediation_plan(classified_issues)
        
        # Output reports
        if args.audit_output and args.remediation_output:
            # Separate outputs
            _write_output(audit_report, args.audit_output, args.verbose)
            _write_output(remediation_plan, args.remediation_output, args.verbose)
        elif args.output:
            # Combined output to file
            combined_report = f"{audit_report}\n\n---\n\n{remediation_plan}"
            _write_output(combined_report, args.output, args.verbose)
        else:
            # Output to stdout
            if not args.quiet:
                print(audit_report)
                print("\n---\n")
                print(remediation_plan)
        
        # Output error log if requested
        if args.error_log and errors:
            error_log = generator.generate_error_log(errors)
            _write_output(error_log, args.error_log, args.verbose)
        
        # Print summary if verbose
        if args.verbose:
            print("\nScan complete!")
            print(f"  - Total issues: {classified_issues.total_count}")
            print(f"  - Files with errors: {len(errors)}")
        
        return 0
    
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _write_output(content: str, output_path: str, verbose: bool = False) -> None:
    """Write content to output file.
    
    Args:
        content: Content to write
        output_path: Path to output file
        verbose: Whether to print verbose messages
    """
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        if verbose:
            print(f"Report written to: {output_path}")
    
    except Exception as e:
        print(f"Error writing to {output_path}: {e}", file=sys.stderr)
        raise


if __name__ == '__main__':
    sys.exit(main())
