#!/usr/bin/env python3
"""
Requirements update script for CR2A project.
Helps update package versions while maintaining consistency across files.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional


def get_latest_version(package: str) -> Optional[str]:
    """Get the latest version of a package from PyPI."""
    try:
        result = subprocess.run(
            ["python", "-m", "pip", "index", "versions", package],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Parse output like "package (1.2.3)"
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'Available versions:' in line:
                    # Get the first version (latest)
                    versions_line = lines[lines.index(line) + 1]
                    latest = versions_line.strip().split(',')[0].strip()
                    return latest
        
        # Fallback: try pip show
        result = subprocess.run(
            ["python", "-m", "pip", "show", package],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
                    
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
        print(f"Warning: Could not get latest version for {package}: {e}")
    
    return None


def parse_requirements_file(file_path: Path) -> List[str]:
    """Parse requirements file and return list of lines."""
    if not file_path.exists():
        return []
    
    with open(file_path, 'r') as f:
        return f.readlines()


def update_package_version(lines: List[str], package: str, new_version: str) -> List[str]:
    """Update package version in requirements lines."""
    updated_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{package}=="):
            # Replace the version
            updated_line = f"{package}=={new_version}\n"
            updated_lines.append(updated_line)
            print(f"  Updated {package}: {stripped.split('==')[1]} → {new_version}")
        else:
            updated_lines.append(line)
    
    return updated_lines


def update_requirements_file(file_path: Path, updates: Dict[str, str]) -> bool:
    """Update a requirements file with new versions."""
    if not file_path.exists():
        print(f"Warning: {file_path} not found")
        return False
    
    lines = parse_requirements_file(file_path)
    updated = False
    
    for package, new_version in updates.items():
        old_lines = lines[:]
        lines = update_package_version(lines, package, new_version)
        if lines != old_lines:
            updated = True
    
    if updated:
        with open(file_path, 'w') as f:
            f.writelines(lines)
        return True
    
    return False


def get_current_versions() -> Dict[str, str]:
    """Get current versions from requirements-core.txt."""
    versions = {}
    core_file = Path("requirements-core.txt")
    
    if core_file.exists():
        with open(core_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '==' in line and not line.startswith('#'):
                    package, version = line.split('==', 1)
                    versions[package] = version
    
    return versions


def main():
    """Main update function."""
    print("🔄 Checking for package updates...")
    
    # Key packages to check for updates
    key_packages = [
        "boto3", "botocore", "openai", "fastapi", "flask", 
        "pandas", "numpy", "pydantic", "requests", "pillow"
    ]
    
    current_versions = get_current_versions()
    updates_available = {}
    
    print("\n📦 Checking latest versions...")
    for package in key_packages:
        if package in current_versions:
            current = current_versions[package]
            latest = get_latest_version(package)
            
            if latest and latest != current:
                print(f"  📈 {package}: {current} → {latest}")
                updates_available[package] = latest
            else:
                print(f"  ✅ {package}: {current} (up to date)")
    
    if not updates_available:
        print("\n✅ All packages are up to date!")
        return 0
    
    # Ask user for confirmation
    print(f"\n🤔 Found {len(updates_available)} updates available.")
    response = input("Apply updates? (y/N): ").strip().lower()
    
    if response != 'y':
        print("❌ Updates cancelled.")
        return 0
    
    # Apply updates to all requirements files
    requirements_files = [
        Path("requirements.txt"),
        Path("requirements-core.txt"),
        Path("requirements-optional.txt"),
        Path("requirements-minimal.txt")
    ]
    
    print("\n🔧 Applying updates...")
    for req_file in requirements_files:
        if req_file.exists():
            print(f"\nUpdating {req_file}...")
            updated = update_requirements_file(req_file, updates_available)
            if updated:
                print(f"  ✅ {req_file} updated")
            else:
                print(f"  ℹ️  {req_file} - no changes needed")
    
    # Special handling for boto3/botocore sync
    if "boto3" in updates_available or "botocore" in updates_available:
        print("\n🔗 Syncing boto3/botocore versions...")
        boto3_version = updates_available.get("boto3", current_versions.get("boto3"))
        botocore_version = updates_available.get("botocore", current_versions.get("botocore"))
        
        # Use the higher version for both
        sync_version = max(boto3_version, botocore_version) if boto3_version and botocore_version else (boto3_version or botocore_version)
        
        if sync_version:
            sync_updates = {"boto3": sync_version, "botocore": sync_version}
            for req_file in requirements_files:
                if req_file.exists():
                    update_requirements_file(req_file, sync_updates)
            print(f"  ✅ Synced boto3/botocore to {sync_version}")
    
    print("\n✅ Updates completed!")
    print("\n🧪 Running validation...")
    
    # Run validation
    try:
        result = subprocess.run(["python", "scripts/validate_requirements.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Validation passed!")
        else:
            print("❌ Validation failed:")
            print(result.stdout)
            return 1
    except Exception as e:
        print(f"Warning: Could not run validation: {e}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())