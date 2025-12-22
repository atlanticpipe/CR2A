from pathlib import Path
import json
from typing import Any, Dict, Optional, Union, cast

def load_policy(root: Union[str, Path], policy_file: str) -> Dict[str, Any]:
    base = Path(root).expanduser().resolve()
    path = base / "schemas" / policy_file
    text = path.read_text(encoding="utf-8")
    return json.loads(text)

def load_validation_rules(root: Union[str, Path], file_name: str = "validation_rules.json") -> Dict[str, Any]:
    return load_policy(root, file_name)

def load_output_schema(root: Union[str, Path], file_name: str = "output_schemas.json") -> Dict[str, Any]:
    return load_policy(root, file_name)

def get_schema(root: Union[str, Path], key: Optional[str] = None, file_name: str = "output_schemas.json") -> Dict[str, Any]:
    doc = load_output_schema(root, file_name)
    
    if key:
        if key not in doc or not isinstance(doc[key], dict):
            raise KeyError(f"Schema key not found: {key}")
        return doc[key]
    
    # If no key specified, return entire doc (already Dict[str, Any])
    return doc

def get_validation_config(root: Union[str, Path], file_name: str = "validation_rules.json") -> Dict[str, Any]:
    cfg = load_validation_rules(root, file_name)
    
    if "validation" not in cfg:
        raise ValueError("Missing 'validation' section in validation rules")
    
    val = cfg["validation"]  # Direct access instead of .get()
    
    if not isinstance(val, dict):
        raise ValueError("Missing 'validation' section in validation rules")
    
    return cast(Dict[str, Any], val)

# Section map loader

def _json_loads_lenient(text: str) -> Dict[str, Any]:
    import json
    out: list[str] = []  # ← Explicit type annotation
    in_str, esc = False, False
    
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
    base = root / "schemas"
    primary = base / "section_map.map.json"
    fallback = base / "section_map.json"
    target = primary if primary.exists() else fallback
    text = target.read_text(encoding="utf-8")
    try:
        import json as _json
        return _json.loads(text)
    except Exception:
        return _json_loads_lenient(text)