"""
Code Signing Configuration for CR2A Application

This module provides configuration and utilities for signing the CR2A executable
with Atlantic Pipe Services LLC's code signing certificate.

Requirements:
- Windows SDK installed (for signtool.exe)
- Code signing certificate (.pfx file)
- Certificate password (stored securely, not in code)
"""

import os
import subprocess
from pathlib import Path
from typing import Optional


class SigningConfig:
    """Configuration for code signing."""
    
    # Company information
    COMPANY_NAME = "Atlantic Pipe Services LLC"
    PRODUCT_NAME = "CR2A Contract Analysis"
    PRODUCT_URL = "https://atlanticpipeservices.com"  # Update with actual URL
    
    # Certificate configuration (DO NOT commit certificate or password to git)
    CERT_PATH = Path("certs/atlantic_pipe_services.pfx")  # Path to certificate
    CERT_PASSWORD_ENV = "CR2A_CERT_PASSWORD"  # Environment variable for password
    
    # Timestamp server (for certificate validation after expiry)
    TIMESTAMP_URL = "http://timestamp.digicert.com"
    
    @classmethod
    def get_signtool_path(cls) -> Optional[Path]:
        """
        Locate signtool.exe from Windows SDK.
        
        Returns:
            Path to signtool.exe if found, None otherwise
        """
        # Common Windows SDK locations
        sdk_paths = [
            Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.22621.0/x64/signtool.exe"),
            Path("C:/Program Files (x86)/Windows Kits/10/bin/10.0.19041.0/x64/signtool.exe"),
            Path("C:/Program Files (x86)/Windows Kits/10/bin/x64/signtool.exe"),
        ]
        
        for path in sdk_paths:
            if path.exists():
                return path
        
        return None
    
    @classmethod
    def sign_executable(cls, exe_path: Path) -> bool:
        """
        Sign an executable with the code signing certificate.
        
        Args:
            exe_path: Path to the executable to sign
            
        Returns:
            True if signing succeeded, False otherwise
        """
        # Check if certificate exists
        if not cls.CERT_PATH.exists():
            print(f"ERROR: Certificate not found at {cls.CERT_PATH}")
            print("Please place your code signing certificate at this location.")
            return False
        
        # Get certificate password from environment
        cert_password = os.environ.get(cls.CERT_PASSWORD_ENV)
        if not cert_password:
            print(f"ERROR: Certificate password not found in environment variable {cls.CERT_PASSWORD_ENV}")
            print("Please set the environment variable with your certificate password.")
            return False
        
        # Locate signtool
        signtool = cls.get_signtool_path()
        if not signtool:
            print("ERROR: signtool.exe not found. Please install Windows SDK.")
            print("Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
            return False
        
        # Build signing command
        cmd = [
            str(signtool),
            "sign",
            "/f", str(cls.CERT_PATH),
            "/p", cert_password,
            "/t", cls.TIMESTAMP_URL,
            "/d", cls.PRODUCT_NAME,
            "/du", cls.PRODUCT_URL,
            str(exe_path)
        ]
        
        print(f"Signing {exe_path.name}...")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print(f"✓ Successfully signed {exe_path.name}")
                return True
            else:
                print(f"✗ Signing failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ Signing failed with exception: {e}")
            return False


def sign_cr2a_executable(exe_path: Path) -> bool:
    """
    Sign the CR2A executable.
    
    Args:
        exe_path: Path to CR2A.exe
        
    Returns:
        True if signing succeeded, False otherwise
    """
    return SigningConfig.sign_executable(exe_path)


def sign_installer(installer_path: Path) -> bool:
    """
    Sign the CR2A installer.
    
    Args:
        installer_path: Path to CR2A_Setup.exe
        
    Returns:
        True if signing succeeded, False otherwise
    """
    return SigningConfig.sign_executable(installer_path)


if __name__ == "__main__":
    # Test signing configuration
    print("CR2A Code Signing Configuration")
    print("=" * 60)
    print(f"Company: {SigningConfig.COMPANY_NAME}")
    print(f"Product: {SigningConfig.PRODUCT_NAME}")
    print(f"Certificate Path: {SigningConfig.CERT_PATH}")
    print(f"Certificate Exists: {SigningConfig.CERT_PATH.exists()}")
    print(f"Signtool Path: {SigningConfig.get_signtool_path()}")
    print(f"Password Set: {'Yes' if os.environ.get(SigningConfig.CERT_PASSWORD_ENV) else 'No'}")
