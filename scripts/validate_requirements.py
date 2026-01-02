#!/usr/bin/env python3
"""
Requirements validation script for CR2A project.
Ensures version consistency across requirements files and checks for security issues.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


def parse_requirements(file_path: Path) -> Dict[str, str]:
    """Parse a requirements file and return package:version mapping."""
    requirements = {}
    
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return requirements
    
    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse package==version
            match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+(?:[a-zA-Z0-9.+-]*)?)', line)
            if match:
                package, version = match.groups()
                requirements[package.lower()] = version
            else:
                print(f"Warning: Could not parse line {line_num} in {file_path}: {line}")
    
    return requirements


def check_version_consistency(requirements_files: Dict[str, Dict[str, str]]) -> List[str]:
    """Check for version inconsistencies across requirements files."""
    issues = []
    
    # Find all packages across all files
    all_packages = set()
    for reqs in requirements_files.values():
        all_packages.update(reqs.keys())
    
    # Check each package for version consistency
    for package in sorted(all_packages):
        versions = {}
        for file_name, reqs in requirements_files.items():
            if package in reqs:
                versions[file_name] = reqs[package]
        
        if len(set(versions.values())) > 1:
            version_info = ", ".join([f"{file}: {ver}" for file, ver in versions.items()])
            issues.append(f"Version mismatch for {package}: {version_info}")
    
    return issues


def check_critical_pairs() -> List[str]:
    """Check critical package pairs that must be in sync."""
    issues = []
    
    # Load main requirements
    main_reqs = parse_requirements(Path("requirements.txt"))
    core_reqs = parse_requirements(Path("requirements-core.txt"))
    
    # Critical pairs that must match
    critical_pairs = [
        ("boto3", "botocore"),
    ]
    
    for pkg1, pkg2 in critical_pairs:
        for file_name, reqs in [("requirements.txt", main_reqs), ("requirements-core.txt", core_reqs)]:
            if pkg1 in reqs and pkg2 in reqs:
                v1, v2 = reqs[pkg1], reqs[pkg2]
                # boto3 and botocore should have same version
                if v1 != v2:
                    issues.append(f"{file_name}: {pkg1}=={v1} and {pkg2}=={v2} should match")
    
    return issues


def check_security_concerns() -> List[str]:
    """Check for known security issues with specific versions."""
    issues = []
    
    # Load all requirements
    all_files = {
        "requirements.txt": parse_requirements(Path("requirements.txt")),
        "requirements-core.txt": parse_requirements(Path("requirements-core.txt")),
        "requirements-optional.txt": parse_requirements(Path("requirements-optional.txt")),
        "requirements-minimal.txt": parse_requirements(Path("requirements-minimal.txt")),
    }
    
    # Known security issues (add as needed)
    security_issues = {
        "pillow": {
            "vulnerable_versions": ["<10.0.0"],
            "reason": "Multiple security vulnerabilities in older versions"
        },
        "requests": {
            "vulnerable_versions": ["<2.31.0"],
            "reason": "Security vulnerabilities in older versions"
        }
    }
    
    for file_name, reqs in all_files.items():
        for package, version in reqs.items():
            if package in security_issues:
                issue_info = security_issues[package]
                for vuln_pattern in issue_info["vulnerable_versions"]:
                    if vuln_pattern.startswith("<"):
                        min_version = vuln_pattern[1:]
                        if version < min_version:
                            issues.append(
                                f"{file_name}: {package}=={version} has security issues. "
                                f"Upgrade to >={min_version}. Reason: {issue_info['reason']}"
                            )
    
    return issues


def main():
    """Main validation function."""
    print("🔍 Validating requirements files...")
    
    # Define requirements files to check
    req_files = {
        "requirements.txt": parse_requirements(Path("requirements.txt")),
        "requirements-core.txt": parse_requirements(Path("requirements-core.txt")),
        "requirements-optional.txt": parse_requirements(Path("requirements-optional.txt")),
        "requirements-minimal.txt": parse_requirements(Path("requirements-minimal.txt")),
    }
    
    all_issues = []
    
    # Check version consistency
    print("\n📋 Checking version consistency...")
    consistency_issues = check_version_consistency(req_files)
    if consistency_issues:
        all_issues.extend(consistency_issues)
        for issue in consistency_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ All versions are consistent")
    
    # Check critical pairs
    print("\n🔗 Checking critical package pairs...")
    critical_issues = check_critical_pairs()
    if critical_issues:
        all_issues.extend(critical_issues)
        for issue in critical_issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ Critical package pairs are in sync")
    
    # Check security concerns
    print("\n🛡️  Checking for security issues...")
    security_issues = check_security_concerns()
    if security_issues:
        all_issues.extend(security_issues)
        for issue in security_issues:
            print(f"  ⚠️  {issue}")
    else:
        print("  ✅ No known security issues found")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"  Total files checked: {len(req_files)}")
    print(f"  Total issues found: {len(all_issues)}")
    
    if all_issues:
        print("\n❌ Validation failed. Please fix the issues above.")
        return 1
    else:
        print("\n✅ All requirements files are valid!")
        return 0


if __name__ == "__main__":
    sys.exit(main())