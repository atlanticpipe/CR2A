from pathlib import Path
import json
from typing import Any, Dict, Optional, Union

def load_policy(root: Union[str, Path], policy_file: str) -> Dict[str, Any]:
    base = Path(root).expanduser().resolve()
    path = base / "contract-analysis-policy-bundle" / "policy" / policy_file
    text = path.read_text(encoding="utf-8")
    return json.loads(text)

def load_validation_rules(root: Union[str, Path], file_name: str = "validation_rules_v1.json") -> Dict[str, Any]:
    return load_policy(root, file_name)

def load_output_schema(root: Union[str, Path], file_name: str = "output_schemas_v1.json") -> Dict[str, Any]:
    return load_policy(root, file_name)

def get_schema(root: Union[str, Path], key: Optional[str] = None, file_name: str = "output_schemas_v1.json") -> Dict[str, Any]:
    doc = load_output_schema(root, file_name)
    if key:
        obj = doc.get(key)
        if not isinstance(obj, dict):
            raise KeyError(f"Schema key not found: {key}")
        return obj
    if not isinstance(doc, dict):
        raise ValueError("Invalid schema document")
    return doc

def get_validation_config(root: Union[str, Path], file_name: str = "validation_rules_v1.json") -> Dict[str, Any]:
    cfg = load_validation_rules(root, file_name)
    val = cfg.get("validation") if isinstance(cfg, dict) else None
    if not isinstance(val, dict):
        raise ValueError("Missing 'validation' section in validation rules")
    return val

# --- Section map loader (non-breaking addition) --------------------------------
from typing import Any, Dict, Union

def _json_loads_lenient(text: str) -> Dict[str, Any]:
    import json
    out, in_str, esc = [], False, False
    for i, ch in enumerate(text):
        if not in_str:
            if ch == '"':
                in_str = True
            out.append(ch)
            continue
        if esc:
            esc = False
            out.append(ch)
            continue
        if ch == '\\':
            nxt = text[i+1] if i+1 < len(text) else ''
            if nxt not in ['"', '\\', '/', 'b', 'f', 'n', 'r', 't', 'u']:
                out.append('\\\\')
            else:
                out.append('\\')
            continue
        if ch == '"':
            in_str = False
            out.append(ch)
            continue
        out.append(ch)
    return json.loads(''.join(out))

def load_section_map(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load the CR2A section map. Prefer the dedicated map file; fall back to the old JSON if present.
    """
    root = Path(path).expanduser().resolve()
    base = root / "contract-analysis-policy-bundle" / "policy"
    primary = base / "section_map_v1.map.json"
    fallback = base / "section_map_v1.json"
    target = primary if primary.exists() else fallback
    text = target.read_text(encoding="utf-8")
    try:
        import json as _json
        return _json.loads(text)
    except Exception:
        return _json_loads_lenient(text)