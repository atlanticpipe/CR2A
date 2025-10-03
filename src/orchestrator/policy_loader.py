# -*- coding: utf-8 -*-
# Policy bundle loader: reads version lock, schemas, and rulebook with integrity checks.

from __future__ import annotations

import json                      # parse JSON files
import hashlib                   # compute/verify sha256 checksums
from pathlib import Path         # path-safe file handling
from typing import Dict, Any, Union, Optional

try:
    import yaml                  # parse YAML rulebook (install pyyaml if missing)
except Exception:
    yaml = None                  # we'll error clearly if YAML is requested and not available


# ---- repo-relative locations (fixed typos: 'contract-analysis-policy-bundle') ----
BUNDLE_FILES: Dict[str, str] = {
    "version_lock":        "contract-analysis-policy-bundle/policy/version_lock.schemas_v1.json",
    "rulebook":            "contract-analysis-policy-bundle/policy/rulebook_v1.yaml",
    "validation":          "contract-analysis-policy-bundle/policy/validation_rules_v1.json",
    "output_schemas":      "contract-analysis-policy-bundle/schemas/output_schemas_v1.json",
    "api_schemas":         "contract-analysis-policy-bundle/schemas/api_schemas_v1.json",
    "run_manifest_schema": "contract-analysis-policy-bundle/schemas/run_manifest_schema_v1.json",
}


class PolicyBundle:
    """Small helper around the policy bundle folder with memoized reads and checks."""

    def __init__(self, root: Union[str, Path]) -> None:
        self.root: Path = Path(root)                                     # repo root
        self.paths: Dict[str, Path] = {k: self.root / v                  # key → absolute path
                                       for k, v in BUNDLE_FILES.items()}
        self._cache: Dict[str, Any] = {}                                 # memoized file contents

    # --------------------------
    # Core file-loading routines
    # --------------------------
    def _read_json(self, key: str) -> Dict[str, Any]:
        """Read a JSON file for a given bundle key."""
        p = self.paths[key]                                              # resolve path
        if not p.exists():
            raise FileNotFoundError(f"Missing policy file: {p}")         # clear error if missing
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)                                          # return parsed JSON

    def _read_yaml(self, key: str) -> Dict[str, Any]:
        """Read a YAML file for a given bundle key."""
        if yaml is None:
            raise RuntimeError("PyYAML is required. Add `pyyaml>=6.0` to pyproject.")
        p = self.paths[key]                                              # resolve path
        if not p.exists():
            raise FileNotFoundError(f"Missing policy file: {p}")         # clear error if missing
        with p.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}                               # return parsed YAML

    # --------------------------
    # Public accessors + checks
    # --------------------------
    def load_version_lock(self) -> Dict[str, Any]:
        """Load and cache the version-lock manifest once."""
        if "version_lock" not in self._cache:                            # lazy-load cache
            self._cache["version_lock"] = self._read_json("version_lock")
        return self._cache["version_lock"]                               # return cached dict

    def assert_tag(self, expected_tag: str) -> None:
        """Ensure the current bundle matches the expected release tag."""
        lock = self.load_version_lock()                                   # read version lock
        tag = lock.get("tag")                                             # actual tag value
        if tag != expected_tag:
            raise RuntimeError(f"Version-lock mismatch: expected {expected_tag}, got {tag}")

    def verify_checksums(self) -> None:
        """Verify sha256 checksums in the version-lock for all listed components."""
        lock = self.load_version_lock()                                   # manifest describing files
        comps = lock.get("components") or []                              # list of components
        if not isinstance(comps, list):
            return                                                        # be tolerant if absent

        def sha256_file(path: Path) -> str:
            # compute sha256 in streaming mode to be safe on large files
            h = hashlib.sha256()
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()

        for comp in comps:
            rel = comp.get("path")                                        # manifest path
            want = (comp.get("sha256") or "").lower()                     # expected checksum
            if not rel or not want:
                continue                                                  # skip items without hash
            p = self.root / rel                                           # absolute path
            if not p.exists():
                raise FileNotFoundError(f"Version-lock lists missing file: {p}")
            have = sha256_file(p).lower()                                 # actual checksum
            if have != want:
                raise RuntimeError(f"Checksum mismatch for {rel}: expected {want}, got {have}")

    def get(self, key: str) -> Dict[str, Any]:
        """Fetch and cache a bundle component by key (json or yaml)."""
        if key in self._cache:                                            # return if already cached
            return self._cache[key]

        if key == "rulebook":                                             # YAML rulebook
            self._cache[key] = self._read_yaml(key)
            return self._cache[key]

        if key in {"validation", "api_schemas", "output_schemas", "run_manifest_schema"}:
            self._cache[key] = self._read_json(key)                       # JSON components
            return self._cache[key]

        raise KeyError(f"Unknown policy bundle key: {key}")

    # Convenience helpers used by the CLI
    def get_output_schema(self) -> Dict[str, Any]:
        """Return the canonical output schema object the model must satisfy."""
        return self.get("output_schemas")

    @property
    def bundle_root(self) -> Path:
        """Expose the resolved root path (used by validators for provenance)."""
        return self.root


# -----------------------
# Top-level helper (CLI)
# -----------------------
def load_policy_bundle(path: Union[str, Path],
                       expected_tag: Optional[str] = "schemas@v1.0") -> PolicyBundle:
    """
    Factory used by the CLI.
    - Builds a PolicyBundle rooted at `path`.
    - Asserts the version-lock release tag.
    - Verifies sha256 checksums for components listed in the lock file.
    """
    bundle = PolicyBundle(path)                                           # build loader
    if expected_tag:
        bundle.assert_tag(expected_tag)                                   # check release tag
    bundle.verify_checksums()                                             # integrity verification
    return bundle                                                         # ready-to-use bundle
