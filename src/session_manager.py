"""
Session State Manager

Manages automatic persistence and restoration of application session state.
Session data is stored in .cr2a/session.json alongside the contract files.

Auto-saves after each analysis event (category complete, bid item complete).
Restores previous session when the same contract is re-loaded.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SessionManagerError(Exception):
    """Exception raised for session manager errors."""
    pass


class SessionManager:
    """
    Manages session state persistence to .cr2a/session.json.

    Provides auto-save after analysis events and restore on contract load.
    Uses atomic write (temp file + rename) for crash safety.
    """

    SCHEMA_VERSION = "1.0"

    def __init__(self, storage_root: Path):
        self.session_path = Path(storage_root) / "session.json"
        self._dirty = False
        self._state: Dict[str, Any] = self._empty_state()
        logger.info("SessionManager initialized: %s", self.session_path)

    def _empty_state(self) -> Dict[str, Any]:
        return {
            "session_version": self.SCHEMA_VERSION,
            "last_saved": None,
            "contract_file": None,
            "contract_file_path": None,
            "upload_mode": "file",
            "category_results": {},
            "categories_not_found": [],
            "bid_review_result": None,
            "bid_review_item_results": {},
        }

    # ------------------------------------------------------------------
    # Save helpers (update in-memory state, mark dirty)
    # ------------------------------------------------------------------

    def set_contract_info(self, contract_file: str, contract_file_path: str,
                          upload_mode: str = "file") -> None:
        self._state["contract_file"] = contract_file
        self._state["contract_file_path"] = contract_file_path
        self._state["upload_mode"] = upload_mode
        self._dirty = True

    def update_category_result(self, cat_key: str, clause_block: dict) -> None:
        self._state["category_results"][cat_key] = clause_block
        nf = self._state["categories_not_found"]
        if cat_key in nf:
            nf.remove(cat_key)
        self._dirty = True

    def mark_category_not_found(self, cat_key: str) -> None:
        nf = self._state["categories_not_found"]
        if cat_key not in nf:
            nf.append(cat_key)
        self._state["category_results"].pop(cat_key, None)
        self._dirty = True

    def update_bid_review_item(self, item_key: str, item_dict: Dict[str, Any]) -> None:
        self._state["bid_review_item_results"][item_key] = item_dict
        self._dirty = True

    def update_bid_review_result(self, result_dict: Optional[Dict[str, Any]]) -> None:
        self._state["bid_review_result"] = result_dict
        self._dirty = True

    # ------------------------------------------------------------------
    # Persist to disk
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Atomic write to session.json. Only writes when dirty."""
        if not self._dirty:
            return

        self._state["last_saved"] = datetime.now().isoformat()
        temp_path = self.session_path.with_suffix(".tmp")

        try:
            self.session_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)

            # Atomic rename
            temp_path.replace(self.session_path)
            self._dirty = False
            logger.info("Session saved (%d categories, %d bid items)",
                        len(self._state["category_results"]),
                        len(self._state["bid_review_item_results"]))

        except Exception as e:
            logger.error("Failed to save session: %s", e)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Load / Restore
    # ------------------------------------------------------------------

    def load(self) -> bool:
        """Load session from disk. Returns True on success."""
        if not self.session_path.exists():
            logger.info("No session file at %s", self.session_path)
            return False

        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            version = data.get("session_version", "")
            if not version.startswith("1."):
                logger.warning("Unknown session version: %s", version)
                return False

            self._state = data
            self._dirty = False
            logger.info("Session loaded: %s (saved %s, %d categories, %d bid items)",
                        data.get("contract_file"),
                        data.get("last_saved"),
                        len(data.get("category_results", {})),
                        len(data.get("bid_review_item_results", {})))
            return True

        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load session: %s", e)
            return False

    def has_session_for(self, contract_file_path: str) -> bool:
        """Check if the loaded session matches a specific contract file."""
        saved_path = self._state.get("contract_file_path", "")
        if not saved_path:
            return False
        try:
            return Path(saved_path).resolve() == Path(contract_file_path).resolve()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Property accessors
    # ------------------------------------------------------------------

    @property
    def contract_file(self) -> Optional[str]:
        return self._state.get("contract_file")

    @property
    def contract_file_path(self) -> Optional[str]:
        return self._state.get("contract_file_path")

    @property
    def category_results(self) -> Dict[str, dict]:
        return self._state.get("category_results", {})

    @property
    def categories_not_found(self) -> List[str]:
        return self._state.get("categories_not_found", [])

    @property
    def bid_review_result(self) -> Optional[Dict[str, Any]]:
        return self._state.get("bid_review_result")

    @property
    def bid_review_item_results(self) -> Dict[str, Dict[str, Any]]:
        return self._state.get("bid_review_item_results", {})

    def clear(self) -> None:
        """Reset to empty state."""
        self._state = self._empty_state()
        self._dirty = False
