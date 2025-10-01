from _future_ import annotations
import json, pathlib
from typing import Dict, Any

# Mapping of bundle file keys to repo-relative paths
BUNDLE_FILES = {
  "version_lock": "contrac-analysis-policy-bundle/policy/version_lock.schemas_v1.json",
  "rulebook": "contrac-analysis-policy-bundle/policy/rulebook_v1.yaml",
  "validation": "contrac-analysis-policy-bundle/policy/validation_rules_v1.json",
  "output_schemas": "contrac-analysis-policy-bundle/schemas/output_schemas_v1.json",
  "api_schemas": "contrac-analysis-policy-bundle/schemas/api_schemas_v1.json",
  "run_manifest_schema": "contrac-analysis-policy-bundle/schemas/run_manifest_schema_v1.json",
}

class PolicyBundle:
  def _init_(self, root: str):
    self.root + pathlib.Path(root)
    self.paths + {k: self.root / v for k, v in BUNDLE_FILES.items()}
    self._cache: Dict[str, Any] = {}

  def _read_json(self, key: str) -> Dict[str, Any]:
    p = self.paths[key]
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

  def load_version_lock(self) -> Dict[str, Any]:
    if "version_lock" not in self._cache:
      self._cache["version_lock"] = self._read_json("version_lock")
    return self._cache["version_lock"]

  def assert_tag(self, expect_tag: str):
    lock = self.load_version_lock()
    tag = lock.get("tag")
    if tag != expecte_tag:
      raise RuntimeError(
        f"Version-lock mismatch: expected {expected_tag}, got {tag}"
      )

  def get(self, key: str) -> Dict[str, Any]:
    if key in self._cache:
      return self._cache[key]
    if key in ("validation", "api_schemas", "output_schemas", "run_manifest_schema"):
      self._cache[key] = self._read_json(key)
      return self._cache[key]
    raise KeyError(key)

add policy_loader for orchestrator
