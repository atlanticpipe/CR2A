"""File scanning component for the Security Audit System."""

import os
from pathlib import Path
from typing import List, Set, Dict, Optional
import fnmatch


class FileError:
    """Represents an error encountered during file scanning."""
    
    def __init__(self, file_path: str, error_type: str, message: str):
        """Initialize a file error.
        
        Args:
            file_path: Path to the file that caused the error
            error_type: Type of error (e.g., 'permission', 'encoding', 'binary', 'size')
            message: Detailed error message
        """
        self.file_path = file_path
        self.error_type = error_type
        self.message = message
    
    def __repr__(self):
        return f"FileError(file_path='{self.file_path}', error_type='{self.error_type}', message='{self.message}')"


class FileScanner:
    """Discovers and filters files for security analysis.
    
    Handles recursive directory traversal, file type filtering,
    and exclusion pattern matching.
    """
    
    # Default supported file extensions
    DEFAULT_EXTENSIONS = {
        '.js', '.ts', '.jsx', '.tsx',  # JavaScript/TypeScript
        '.py',                          # Python
        '.json', '.yaml', '.yml', '.env',  # Config files
        '.html', '.htm'                 # HTML/templates
    }
    
    # Default exclusion patterns
    DEFAULT_EXCLUSIONS = [
        'node_modules',
        '.git',
        'build',
        'dist',
        '__pycache__',
        '.pytest_cache',
        '.hypothesis',
        'venv',
        '.venv',
        'env',
        '*.pyc',
        '*.pyo',
        '*.so',
        '*.dll',
        '*.dylib'
    ]
    
    # Maximum file size in bytes (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024
    
    def __init__(self, root_path: str, exclusions: List[str] = None, 
                 extensions: Set[str] = None, max_file_size: Optional[int] = None):
        """Initialize scanner with root path and optional exclusion patterns.
        
        Args:
            root_path: Root directory to scan
            exclusions: List of glob patterns to exclude (added to defaults)
            extensions: Set of file extensions to include (overrides defaults if provided)
            max_file_size: Maximum file size in bytes (default: 10MB)
        """
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {root_path}")
            
        # Combine default and custom exclusions
        self.exclusions = self.DEFAULT_EXCLUSIONS.copy()
        if exclusions:
            self.exclusions.extend(exclusions)
            
        # Use provided extensions or defaults
        self.extensions = extensions if extensions is not None else self.DEFAULT_EXTENSIONS.copy()
        
        # Set maximum file size
        self.max_file_size = max_file_size if max_file_size is not None else self.MAX_FILE_SIZE
        
        # Track visited directories to handle symlinks safely
        self._visited_dirs: Set[Path] = set()
        
        # Track errors encountered during scanning
        self.errors: List[FileError] = []
    
    def scan(self) -> List[str]:
        """Scan directory tree and return list of files to analyze.
        
        Returns:
            List of file paths (as strings) relative to root_path
        """
        files = []
        self._visited_dirs.clear()
        self.errors.clear()
        
        for file_path in self._walk_directory(self.root_path):
            files.append(str(file_path.relative_to(self.root_path)))
        
        return sorted(files)
    
    def read_file(self, file_path: str) -> Optional[str]:
        """Read file content with error handling.
        
        Attempts to read file with UTF-8 encoding, falls back to latin-1.
        Skips binary files and files exceeding size limit.
        
        Args:
            file_path: Path to file (relative to root_path)
            
        Returns:
            File content as string, or None if file cannot be read
        """
        full_path = self.root_path / file_path
        
        # Check file size
        try:
            file_size = full_path.stat().st_size
            if file_size > self.max_file_size:
                self.errors.append(FileError(
                    file_path=file_path,
                    error_type='size',
                    message=f'File exceeds maximum size limit ({file_size} > {self.max_file_size} bytes)'
                ))
                return None
        except OSError as e:
            self.errors.append(FileError(
                file_path=file_path,
                error_type='permission',
                message=f'Cannot stat file: {str(e)}'
            ))
            return None
        
        # Try to read file with UTF-8 encoding
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check if content looks like binary (contains null bytes)
                if '\x00' in content:
                    self.errors.append(FileError(
                        file_path=file_path,
                        error_type='binary',
                        message='File appears to be binary (contains null bytes)'
                    ))
                    return None
                return content
        except UnicodeDecodeError:
            # Try latin-1 fallback
            try:
                with open(full_path, 'r', encoding='latin-1') as f:
                    content = f.read()
                    # Check if content looks like binary (contains null bytes)
                    if '\x00' in content:
                        self.errors.append(FileError(
                            file_path=file_path,
                            error_type='binary',
                            message='File appears to be binary (contains null bytes)'
                        ))
                        return None
                    return content
            except Exception as e:
                self.errors.append(FileError(
                    file_path=file_path,
                    error_type='encoding',
                    message=f'Cannot decode file with UTF-8 or latin-1: {str(e)}'
                ))
                return None
        except PermissionError as e:
            self.errors.append(FileError(
                file_path=file_path,
                error_type='permission',
                message=f'Permission denied: {str(e)}'
            ))
            return None
        except OSError as e:
            self.errors.append(FileError(
                file_path=file_path,
                error_type='read',
                message=f'Cannot read file: {str(e)}'
            ))
            return None
    
    def get_errors(self) -> List[FileError]:
        """Get list of errors encountered during scanning.
        
        Returns:
            List of FileError objects
        """
        return self.errors.copy()
    
    def get_error_summary(self) -> Dict[str, int]:
        """Get summary of errors by type.
        
        Returns:
            Dictionary mapping error types to counts
        """
        summary = {}
        for error in self.errors:
            summary[error.error_type] = summary.get(error.error_type, 0) + 1
        return summary
    
    def _walk_directory(self, directory: Path):
        """Recursively walk directory tree, yielding files to scan.
        
        Args:
            directory: Directory to walk
            
        Yields:
            Path objects for files that should be scanned
        """
        # Resolve symlinks and check if we've visited this directory
        try:
            real_dir = directory.resolve()
        except (OSError, RuntimeError):
            # Handle broken symlinks or permission errors
            return
            
        if real_dir in self._visited_dirs:
            # Avoid infinite loops from circular symlinks
            return
        
        self._visited_dirs.add(real_dir)
        
        try:
            entries = list(directory.iterdir())
        except (PermissionError, OSError):
            # Skip directories we can't read
            return
        
        for entry in entries:
            # Check exclusions
            if self.should_exclude(entry):
                continue
            
            if entry.is_file():
                # Check if file has supported extension
                if entry.suffix in self.extensions:
                    yield entry
            elif entry.is_dir():
                # Recursively scan subdirectories
                yield from self._walk_directory(entry)
    
    def should_exclude(self, path: Path) -> bool:
        """Check if path matches any exclusion patterns.
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be excluded, False otherwise
        """
        path_name = path.name
        
        for pattern in self.exclusions:
            # Check if pattern matches the file/directory name exactly
            if fnmatch.fnmatch(path_name, pattern):
                return True
            
            # Check if any part of the path matches the pattern
            for part in path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True
        
        return False
