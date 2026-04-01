"""
Project-based storage manager.

This module provides the ProjectStorage class which manages the .cr2a/ directory
structure for storing contract analysis data alongside the contract files.

Author: CR2A Development Team
Date: 2026-02-06
"""

import logging
import os
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ProjectStorageError(Exception):
    """Exception raised for project storage errors."""
    pass


class ProjectStorage:
    """
    Manages project-based storage structure.

    Creates and manages a .cr2a/ subdirectory for storing:
    - versions.db: SQLite database for differential storage
    - chat_history.json: Append-only chat log with user attribution
    - analyses/: Directory for analysis result JSON files

    Attributes:
        project_root: Path to the project folder (contains contract files)
        storage_root: Path to .cr2a/ directory
        versions_db_path: Path to versions.db file
        chat_history_path: Path to chat_history.json file
        analyses_dir: Path to analyses/ directory
    """

    STORAGE_DIR_NAME = ".cr2a"

    def __init__(self, source_path: Path | str):
        """
        Initialize project storage from a file or folder path.

        Args:
            source_path: Either a contract file path or a folder path.
                        If a file, the parent directory becomes the project root.
                        If a folder, that folder becomes the project root.

        Raises:
            ProjectStorageError: If the source path doesn't exist.
        """
        source_path = Path(source_path)

        if not source_path.exists():
            raise ProjectStorageError(f"Source path does not exist: {source_path}")

        # Determine project root
        if source_path.is_file():
            self.project_root = source_path.parent
        elif source_path.is_dir():
            self.project_root = source_path
        else:
            raise ProjectStorageError(f"Source path is neither a file nor directory: {source_path}")

        # Define storage paths
        self.storage_root = self.project_root / self.STORAGE_DIR_NAME
        self.versions_db_path = self.storage_root / "versions.db"
        self.chat_history_path = self.storage_root / "chat_history.json"
        self.analyses_dir = self.storage_root / "analyses"
        self.session_path = self.storage_root / "session.json"

        logger.info(f"Project storage initialized: {self.project_root}")

    def initialize_structure(self) -> None:
        """
        Create .cr2a/ directory structure if it doesn't exist.

        Creates:
        - .cr2a/ (hidden directory on Windows)
        - .cr2a/analyses/ (for analysis result JSON files)

        The versions.db and chat_history.json files will be created
        by their respective managers when first used.

        Raises:
            ProjectStorageError: If directory creation fails.
        """
        try:
            # Create .cr2a/ directory
            self.storage_root.mkdir(exist_ok=True)

            # Hide the directory on Windows
            if os.name == 'nt':  # Windows
                try:
                    import ctypes
                    FILE_ATTRIBUTE_HIDDEN = 0x02
                    ctypes.windll.kernel32.SetFileAttributesW(
                        str(self.storage_root),
                        FILE_ATTRIBUTE_HIDDEN
                    )
                    logger.debug(f"Set hidden attribute on: {self.storage_root}")
                except Exception as e:
                    logger.warning(f"Failed to hide directory (non-critical): {e}")

            # Create analyses/ subdirectory
            self.analyses_dir.mkdir(exist_ok=True)

            logger.info(f"Project storage structure initialized: {self.storage_root}")

        except OSError as e:
            raise ProjectStorageError(f"Failed to create storage structure: {e}")

    def is_valid_project_directory(self) -> Tuple[bool, str]:
        """
        Check if the project directory is valid and writable.

        Validates:
        - Directory exists
        - Directory is writable (tests by creating a temporary file)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if directory is valid and writable
            - error_message: Empty string if valid, error description otherwise
        """
        # Check if directory exists
        if not self.project_root.exists():
            return False, f"Directory does not exist: {self.project_root}"

        # Check if it's actually a directory
        if not self.project_root.is_dir():
            return False, f"Path is not a directory: {self.project_root}"

        # Test write permissions by creating a temporary file
        test_file = self.project_root / '.cr2a_write_test'
        try:
            test_file.touch()
            test_file.unlink()
            return True, ""
        except PermissionError:
            return False, (
                "This folder is read-only or you don't have write permissions.\n\n"
                "Please select a writable location or contact your network administrator."
            )
        except OSError as e:
            return False, f"Cannot write to folder: {e}"

    def get_analysis_path(self, contract_name: str, version: int = 1) -> Path:
        """
        Get the file path for storing a specific analysis result.

        Creates a subdirectory structure:
        .cr2a/analyses/{contract_name}/v{version}_{timestamp}.json

        Args:
            contract_name: Base name of the contract file (without extension)
            version: Version number (default: 1)

        Returns:
            Path object for the analysis JSON file
        """
        from datetime import datetime

        # Sanitize contract name (remove path separators and invalid chars)
        safe_name = contract_name.replace('/', '_').replace('\\', '_')
        safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '_', '-', '.'))

        # Create contract-specific subdirectory
        contract_dir = self.analyses_dir / safe_name
        contract_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"v{version}_{timestamp}.json"

        return contract_dir / filename

    @property
    def excel_path(self) -> Path:
        """Path to the CR2A analysis workbook in the project folder."""
        return self.project_root / "CR2A_Analysis.xlsx"

    def exists(self) -> bool:
        """
        Check if the .cr2a/ storage directory already exists.

        Returns:
            True if .cr2a/ directory exists, False otherwise
        """
        return self.storage_root.exists()

    def get_contract_files(self, extensions: list[str] = None) -> list[Path]:
        """
        Get all contract files in the project directory.

        Args:
            extensions: List of file extensions to include (e.g., ['.pdf', '.docx'])
                       If None, defaults to ['.pdf', '.docx', '.txt']

        Returns:
            List of Path objects for contract files, sorted by name
        """
        if extensions is None:
            extensions = ['.pdf', '.docx', '.txt', '.xlsx']

        ext_set = set(extensions)

        # Exclude CR2A output files and temp files
        exclude_names = {"cr2a_analysis.xlsx", "template.xlsx"}
        cr2a_storage = self.project_root / self.STORAGE_DIR_NAME

        files = []
        for f in self.project_root.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in ext_set:
                continue
            # Skip .cr2a storage directory
            try:
                f.relative_to(cr2a_storage)
                continue
            except ValueError:
                pass
            # Skip CR2A output files and Excel temp files
            if f.name.lower() in exclude_names:
                continue
            if f.name.startswith("~$"):
                continue
            files.append(f)

        # Sort by filename
        return sorted(files, key=lambda f: f.name.lower())

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ProjectStorage(project_root={self.project_root})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Project storage at: {self.project_root}"
