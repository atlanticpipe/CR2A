"""
Chat history manager with file locking for multi-user access.

This module provides the ChatHistoryManager class which manages an append-only
chat history with user attribution, supporting concurrent access across network shares.

Author: CR2A Development Team
Date: 2026-02-06
"""

import json
import logging
import os
import platform
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ChatHistoryError(Exception):
    """Exception raised for chat history errors."""
    pass


class ChatHistoryManager:
    """
    Manages append-only chat history with file locking.

    Supports concurrent writes from multiple users on network shares using
    file locking and atomic writes with exponential backoff retry logic.

    Chat history is stored as a single JSON file with the following structure:
    {
        "version": "1.0",
        "project_path": "/path/to/project",
        "chats": [
            {
                "chat_id": "uuid",
                "timestamp": "ISO 8601",
                "username": "windows_username",
                "computer_name": "COMPUTER-NAME",
                "contract_file": "contract.pdf",
                "contract_version": 1,
                "question": "User question",
                "answer": "AI response",
                "metadata": {...}
            },
            ...
        ]
    }

    Attributes:
        chat_history_path: Path to chat_history.json file
        max_retries: Maximum number of retry attempts for file locking
        initial_backoff_ms: Initial backoff delay in milliseconds
    """

    SCHEMA_VERSION = "1.0"
    MAX_RETRIES = 3
    INITIAL_BACKOFF_MS = 100

    def __init__(self, chat_history_path: Path | str, max_retries: int = MAX_RETRIES):
        """
        Initialize chat history manager.

        Args:
            chat_history_path: Path to chat_history.json file
            max_retries: Maximum number of retry attempts (default: 3)
        """
        self.chat_history_path = Path(chat_history_path)
        self.max_retries = max_retries
        self.initial_backoff_ms = self.INITIAL_BACKOFF_MS

        # Ensure parent directory exists
        self.chat_history_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize empty file if it doesn't exist
        if not self.chat_history_path.exists():
            self._initialize_empty_history()

        logger.info(f"Chat history manager initialized: {self.chat_history_path}")

    def _initialize_empty_history(self) -> None:
        """Create an empty chat history file."""
        empty_history = {
            "version": self.SCHEMA_VERSION,
            "project_path": str(self.chat_history_path.parent.parent),
            "chats": []
        }

        try:
            with open(self.chat_history_path, 'w', encoding='utf-8') as f:
                json.dump(empty_history, f, indent=2, ensure_ascii=False)
            logger.debug("Created empty chat history file")
        except OSError as e:
            logger.error(f"Failed to create chat history file: {e}")
            raise ChatHistoryError(f"Failed to create chat history file: {e}")

    def _acquire_file_lock(self, file_handle, timeout: float = 5.0):
        """
        Acquire an exclusive file lock (Windows-specific).

        Args:
            file_handle: Open file handle
            timeout: Maximum time to wait for lock (seconds)

        Raises:
            TimeoutError: If lock cannot be acquired within timeout
        """
        import msvcrt

        start_time = time.time()
        while True:
            try:
                # Lock the entire file (0 = from start, -1 = to end)
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, -1)
                return
            except OSError:
                if time.time() - start_time > timeout:
                    raise TimeoutError(f"Failed to acquire file lock after {timeout}s")
                time.sleep(0.05)  # Wait 50ms before retrying

    def _release_file_lock(self, file_handle):
        """
        Release file lock (Windows-specific).

        Args:
            file_handle: Open file handle
        """
        import msvcrt
        try:
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, -1)
        except OSError as e:
            logger.warning(f"Failed to release file lock: {e}")

    def append_chat(self, chat_entry: Dict[str, Any]) -> None:
        """
        Append a chat entry to the history with user attribution.

        Uses file locking and atomic writes to support concurrent access.
        Retries with exponential backoff if lock cannot be acquired.

        Args:
            chat_entry: Dictionary containing:
                - chat_id: Unique identifier (UUID string)
                - timestamp: ISO 8601 timestamp
                - username: Windows username
                - computer_name: Computer name
                - contract_file: Contract filename
                - contract_version: Contract version number
                - question: User's question
                - answer: AI's answer
                - metadata: Additional metadata (dict)

        Raises:
            ChatHistoryError: If append operation fails after all retries
        """
        backoff_ms = self.initial_backoff_ms

        for attempt in range(self.max_retries):
            try:
                self._append_chat_atomic(chat_entry)
                logger.info(f"Chat entry saved: {chat_entry.get('chat_id', 'unknown')}")
                return

            except TimeoutError as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"File lock timeout (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {backoff_ms}ms..."
                    )
                    time.sleep(backoff_ms / 1000.0)
                    backoff_ms *= 2  # Exponential backoff
                else:
                    logger.error(f"Failed to acquire file lock after {self.max_retries} attempts")
                    raise ChatHistoryError(
                        f"Failed to save chat history: Could not acquire file lock after "
                        f"{self.max_retries} attempts. The file may be locked by another user."
                    )

            except Exception as e:
                logger.error(f"Failed to append chat (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(backoff_ms / 1000.0)
                    backoff_ms *= 2
                else:
                    raise ChatHistoryError(f"Failed to save chat history: {e}")

    def _append_chat_atomic(self, chat_entry: Dict[str, Any]) -> None:
        """
        Atomically append a chat entry using file locking.

        This method:
        1. Acquires an exclusive lock on the file
        2. Reads the current data
        3. Appends the new entry
        4. Writes to a temporary file
        5. Atomically renames the temp file
        6. Releases the lock

        Args:
            chat_entry: Chat entry dictionary

        Raises:
            TimeoutError: If file lock cannot be acquired
            OSError: If file operations fail
        """
        temp_path = self.chat_history_path.with_suffix('.tmp')

        try:
            # Open file for reading with exclusive lock
            with open(self.chat_history_path, 'r+', encoding='utf-8') as f:
                # Acquire lock
                self._acquire_file_lock(f, timeout=5.0)

                try:
                    # Read current data
                    f.seek(0)
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning("Corrupted chat history, reinitializing")
                        data = {
                            "version": self.SCHEMA_VERSION,
                            "project_path": str(self.chat_history_path.parent.parent),
                            "chats": []
                        }

                    # Append new chat
                    data['chats'].append(chat_entry)

                    # Write to temporary file
                    with open(temp_path, 'w', encoding='utf-8') as temp_f:
                        json.dump(data, temp_f, indent=2, ensure_ascii=False)

                finally:
                    # Release lock
                    self._release_file_lock(f)

            # Atomic rename (replaces original file)
            temp_path.replace(self.chat_history_path)

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            raise

    def load_all_chats(self) -> List[Dict[str, Any]]:
        """
        Load all chat entries from history.

        Returns:
            List of chat entry dictionaries, in chronological order

        Raises:
            ChatHistoryError: If loading fails
        """
        try:
            with open(self.chat_history_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('chats', [])
        except FileNotFoundError:
            logger.warning("Chat history file not found, returning empty list")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse chat history: {e}")
            raise ChatHistoryError(f"Chat history file is corrupted: {e}")
        except OSError as e:
            logger.error(f"Failed to read chat history: {e}")
            raise ChatHistoryError(f"Failed to read chat history: {e}")

    def get_chats_for_contract(self, contract_file: str) -> List[Dict[str, Any]]:
        """
        Get all chat entries for a specific contract file.

        Args:
            contract_file: Contract filename (e.g., "contract_v1.pdf")

        Returns:
            List of chat entries for the specified contract, in chronological order
        """
        all_chats = self.load_all_chats()
        return [
            chat for chat in all_chats
            if chat.get('contract_file') == contract_file
        ]

    def get_recent_chats(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent chat entries.

        Args:
            limit: Maximum number of entries to return (default: 10)

        Returns:
            List of most recent chat entries, newest first
        """
        all_chats = self.load_all_chats()
        return list(reversed(all_chats[-limit:]))

    def clear_history(self) -> None:
        """
        Clear all chat history (WARNING: This is destructive!).

        This should only be used for testing or user-initiated cleanup.
        """
        logger.warning("Clearing all chat history")
        self._initialize_empty_history()

    @staticmethod
    def create_chat_entry(
        question: str,
        answer: str,
        contract_file: str,
        contract_version: int = 1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a properly formatted chat entry with automatic user attribution.

        Args:
            question: User's question
            answer: AI's answer
            contract_file: Contract filename
            contract_version: Contract version number (default: 1)
            metadata: Additional metadata (optional)

        Returns:
            Formatted chat entry dictionary
        """
        # Get user information
        try:
            username = os.getlogin()
        except Exception:
            username = os.getenv('USERNAME', 'unknown')

        try:
            computer_name = platform.node()
        except Exception:
            computer_name = 'unknown'

        entry = {
            'chat_id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'username': username,
            'computer_name': computer_name,
            'contract_file': contract_file,
            'contract_version': contract_version,
            'question': question,
            'answer': answer,
            'metadata': metadata or {}
        }

        return entry

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"ChatHistoryManager(path={self.chat_history_path})"
