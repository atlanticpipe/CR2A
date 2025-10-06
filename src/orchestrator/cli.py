#!/usr/bin/env python3
from __future__ import annotations  # <- enable future typing semantics
# stdlib imports
import argparse                   # parse CLI args
import fnmatch                    # filename pattern matching for batch
import hashlib                    # build SHA256 checksums
import json                       # read/write JSON artifacts
import os                         # env + path utils
import sys                        # exit codes / excepthook
import html                       # escape for HTML rendering
from pathlib import Path          # path handling
from typing import Any, Dict, List  # typing helpers  <-- fixed iList -> List
# Install our global error handler (prints friendly tracebacks on uncaught errors)
import utils.error_handler        # side effect: sets sys.excepthook
# third-party (optional extras)
from dotenv import load_dotenv    # load .env so OPENAI_API_KEY is available
# Optional PDF/DOCX readers — guard so missing deps don't crash CLI import
try:
    from pypdf import PdfReader   # extract text from PDFs
except Exception:
    PdfReader = None              # fallback if pypdf not installed
try:
    import docx2txt               # extract text from .docx
except Exception:
    docx2txt = None
# local project imports
from orchestrator.validator import validate_filled_template  # our wrapper

# Helpers: file I/O + text extract
# Resolve --input (file or directory) into a sorted list of files.
def discover_input_files(root: Path, patterns: list[str], recursive: bool) -> list[Path]:
    if root.is_file():                                   # single-file: return as-is
        return [root]                                    # single-file path, just return it
    files: List[Path] = []                               # start empty list
    iterator = root.rglob("*") if recursive else root.iterdir()
    for p in iterator:
        if not p.is_file():  # skip directories
            continue
        if any(part.startswith(".") for part in p.parts):  # skip hidden paths
            continue
        if any(fnmatch.fnmatch(p.name.lower(), pat.lower()) for pat in patterns):
            files.append(p)  # add matching file
        # deterministic ordering (important for reproducibility)
        return sorted(files, key=lambda x: x.as_posix())
    continue

def ensure_out_dir(base_out: Path, input_file: Path) -> Path:
    # Normalize paths to avoid accidental nested relative dirs
    base_out = base_out.expanduser().resolve()            # make absolute
    input_file = input_file.resolve()                      # absolute path for consistent .stem
    stem = (input_file.stem or "").strip()                 # get filename w/o extension
    if not stem:                                           # defensive: no empty folder names
        raise ValueError(f"Cannot derive output folder from: {input_file}")
    out_dir = base_out / stem                              # e.g., ./out/MasterAgreement/
    if out_dir.exists() and not out_dir.is_dir():          # if a file blocks the path, fail clearly
        raise FileExistsError(f"Output path exists and is not a directory: {out_dir}")
    # If directory exists, keep it; otherwise create parents as needed
    out_dir.mkdir(parents=True, exist_ok=True)             # idempotent creation
    return out_dir                                         # caller writes artifacts here

def read_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()  # normalize extension
    if suffix == ".pdf":
        # Use pypdf to pull the text layer page-by-page
        reader = PdfReader(str(path))
        pages = []  # collect page texts to preserve natural order
        for p in reader.pages:
            pages.append(p.extract_text() or "")  # be robust to empty pages
        return "\n\n".join(pages)
    elif suffix in {".docx"}:
        # Use docx2txt for quick .docx extraction
        return docx2txt.process(str(path)) or ""
    elif suffix in {".txt", ".md"}:
        # Plain text is easy
        return path.read_text(encoding="utf-8", errors="ignore")
    else:
        # Last-resort: try reading as utf-8 text
        return path.read_text(encoding="utf-8", errors="ignore")

# Policy bundle: integrity + schema loader
def sha256_of_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Cannot compute SHA256: {path} does not exist")
    h = hashlib.sha256()                              # initialize SHA-256
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):  # read 8 KB blocks
                h.update(chunk)
    except Exception as e:
        raise IOError(f"Error reading {path}: {e}") from e
    return h.hexdigest()                              # return hex digest

def hash_of_file(path: Path, algo: str = "sha256") -> str:
    h = getattr(hashlib, algo)()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def verify_policy_checksums(policy_dir: Path) -> None:
    manifest_path = policy_dir / "policy" / "checksums_manifest_v1.json"  # manifest location
    if not manifest_path.exists():
        print("[warn] No checksums manifest found; skipping integrity check.")
        return  # manifest optional for local runs
    # load and normalize to a { rel_path -> expected_sha } map
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))       # parse JSON
    files_map: Dict[str, str] = {}
    # Preferred shape: "files": { "policy/..": "sha", "schemas/..": "sha" }
    raw_files = manifest.get("files")
    if isinstance(raw_files, dict) and raw_files:
        files_map = dict(raw_files)  # shallow copy
    # Fallback: build from "canonical" array if "files" missing
    if not files_map and isinstance(manifest.get("canonical"), list):
        # Trim bundle-root prefix and map to sha256
        # e.g., "contract-analysis-policy-bundle/policy/xyz.json" -> "policy/xyz.json"
        for item in manifest["canonical"]:
            try:
                full = str(item["path"])
                sha  = str(item["sha256"])
            except Exception:
                continue  # skip malformed entries
            rel = full.replace("contract-analysis-policy-bundle/", "", 1)
            files_map[rel] = sha
    if not files_map:
        raise SystemExit("Policy checksum manifest has neither 'files' nor 'canonical' entries.")
    mismatches: list[tuple[str, str, str]] = []  # collect (rel_path, expected, actual_or_reason)
    # verify each file
    for rel_path, expected_sha in files_map.items():
        file_path = (policy_dir / rel_path).resolve()  # resolve against bundle root
        # Validate the expected SHA format early for clearer diagnostics
        exp = expected_sha.strip().lower()
        if len(exp) != 64 or any(c not in "0123456789abcdef" for c in exp):
            mismatches.append((rel_path, expected_sha, "invalid_expected_sha256"))
            continue
        if not file_path.exists():
            mismatches.append((rel_path, expected_sha, "missing"))
            continue
        actual_sha = sha256_of_file(file_path)  # compute digest from disk
        if actual_sha != exp:
            mismatches.append((rel_path, expected_sha, actual_sha))
    # report
    if mismatches:
        lines = []
        for p, e, a in mismatches:
            if a == "missing":
                lines.append(f"{p}: expected {e}, but file is missing")
            elif a == "invalid_expected_sha256":
                lines.append(f"{p}: invalid expected sha256 '{e}' (must be 64 lowercase hex chars)")
            else:
                lines.append(f"{p}: expected {e}, got {a}")
        raise SystemExit("Policy checksum verification failed:\n  - " + "\n  - ".join(lines))

def load_output_schema(policy_dir: Path) -> Dict[str, Any]:
    schema_path = policy_dir / "schemas" / "output_schemas_v1.json"   # canonical location
    if not schema_path.exists():                                       # ensure file exists
        raise SystemExit(f"Missing output schema file: {schema_path}")
    try:
        text = schema_path.read_text(encoding="utf-8")                 # read bytes → str
        bundle = json.loads(text)                                      # parse JSON
    except json.JSONDecodeError as e:                                  # friendly JSON error
        raise SystemExit(f"Invalid JSON in output schema file {schema_path}: {e}") from e
    # Allow either a single schema object or a dict of named schemas
    if isinstance(bundle, dict) and "template_v1" in bundle:           # dict-of-schemas case
        schema = bundle["template_v1"]                                  # pick the canonical template
    else:
        schema = bundle                                                 # assume it's already a schema object
    # Basic sanity: we expect a dict schema, not a list/str/etc.
    if not isinstance(schema, dict):
        raise SystemExit(
            f"Output schema at {schema_path} is not a JSON object (got {type(schema).__name__})."
        )
    # Normalize: ensure Draft-07 meta (repo standard) to keep validators consistent
    schema.setdefault("$schema", "http://json-schema.org/draft-07/schema#")
    return schema

def load_validation_rules(policy_dir: Path) -> Dict[str, Any]:
    p = policy_dir / "policy" / "validation_rules_v1.json"
    if not p.exists():
        raise SystemExit(f"Missing validation rules: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Invalid JSON in validation rules file {p}: {e}")
    if "validation" not in data:
        raise SystemExit(f"{p} missing top-level 'validation' key.")
    return data
    # Validate output against schema + policy rules
    report = validate_filled_template(output_json, policy_root)  # returns {ok, findings}
    if not report.ok:
        for f in (report.findings or []):
            print(f"[{f.get('level','?')}] {f.get('code','?')}: {f.get('message','')}")
         raise RuntimeError(f"Validation failed for {input_path.name}")
    # Write artifacts (JSON and HTML now; add PDF when ready)
    (out_dir / "results.json").write_text(
        json.dumps(output_json, indent=2),
        encoding="utf-8"
    )
    (out_dir / "results.html").write_text(
        f"<html><body><h1>Contract Analysis for {html.escape(input_path.name)}</h1>"
        f"<p>(Replace with the real HTML renderer.)</p></body></html>",
        encoding="utf-8"
    )
    print(f"✓ Done: {input_path.name} → {out_dir.as_posix()}")  # success indicator

def load_runtime_config(config_path: Path) -> Dict[str, Any]:
    defaults = {
        "model": "gpt-4o-mini",        # default small model for extraction
        "temperature": 0,              # deterministic outputs
        "max_output_tokens": 2000,     # bounded output length
    }
    if not config_path.exists():
        return defaults
    try:
        user_cfg = json5.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(user_cfg, dict):
            raise ValueError("Runtime config must be a JSON object")
    except Exception as e:
        raise SystemExit(f"Invalid runtime config {config_path}: {e}")
    return {**defaults, **user_cfg}  # merge defaults with user-specified overrides

# Model call + validation
def call_model(contract_text: str, schema: Dict[str, Any], runtime: Dict[str, Any]) -> Dict[str, Any]:
    # Build a minimal, role-focused system message
    system_msg = (
        "You are a contract analysis engine.\n"
        "Extract the fields required by the JSON schema precisely.\n"
        "Do not include commentary; output must conform to the schema.\n"
        "When multiple clauses seem to fit, choose the best section and do not duplicate."
    )
    # Truncate very long inputs (simple guardrail)
    max_chars = int(runtime.get("max_chars", 100_000))     # soft limit to keep context sane
    payload_text = contract_text[:max_chars]               # trim if needed

    # Instantiate our OpenAI client from env & runtime
    # This uses OPENAI_API_KEY/OPENAI_BASE_URL and applies overrides.
    from openai_client import build_client_from_env        # local wrapper:contentReference[oaicite:2]{index=2}
    client = build_client_from_env(
        model=runtime.get("model", "gpt-4o-mini"),         # model override if provided
        temperature=runtime.get("temperature", 0),         # deterministic by default
        timeout=int(runtime.get("timeout", 120)),          # request timeout
    )
    # Make the structured call (strict JSON Schema)
    # The wrapper will fall back to json_object if strict mode is rejected
    # and will parse+return the JSON for us, or raise OpenAIError.
    output_json = client.extract_json(
        text=payload_text,                  # contract content
        schema=schema,                      # JSON Schema loaded from bundle
        system_prompt=system_msg,           # role instruction
        name="contract_template_v1",        # schema label for tracing
        policy_root=None,                   # optional; not needed here
    )
    # Return parsed JSON (dict)
    return output_json
    # Extract JSON from the SDK response (the SDK returns a structured object)
    # Try several known shapes used by OpenAI Responses API, then fall back.
    text_out = None                                                    # will hold the JSON string
    try:
        # SDK helper (newer responses): best case
        text_out = getattr(response, "output_text", None)              # e.g., "..." or None
    except Exception:
        text_out = None
    if not text_out:
        try:
            # SDK structured form: response.output -> [{"content":[{"type":"output_text","text":"..."}]}]
            items = getattr(response, "output", None)                  # could be list
            if items and isinstance(items, list):
                text_out = items[0]["content"][0].get("text")
        except Exception:
            text_out = None
    if not text_out:
        try:
            # Raw HTTP JSON (as dict) from httpx client
            text_out = (
                response.get("output_text") or                         # direct text field
                (response.get("output", [{}])[0].get("content", [{}])[0].get("text")) or
                response.get("content")                                # older compatibility
         )
        except Exception:
            text_out = None
# Guard: we must have some text to parse
if not text_out or not isinstance(text_out, str) or not text_out.strip():
    raise SystemExit("Model returned empty output; cannot parse JSON.")
# Parse JSON safely
try:
    data = orjson.loads(text_out)                                  # fast JSON parse
except Exception as e:
    preview = text_out if len(text_out) <= 400 else (text_out[:400] + "…")
    raise SystemExit(f"Model did not return valid JSON: {e}\nPreview:\n{preview}")
# Validate against our schema (double lock)
try:
    jsonschema.validate(instance=data, schema=schema)              # raise on mismatch
except jsonschema.ValidationError as ve:
    # Show where it failed and why (path → human readable)
    path = "$" + "".join(f"[{repr(p)}]" if isinstance(p, int) else f".{p}" for p in ve.path)
    raise SystemExit(f"Schema validation failed at {path}: {ve.message}")
return data                                                        # dict that matches schema

# Post-processing: de-dup + best-fit pass
def normalize_and_dedup(data: Dict[str, Any]) -> Dict[str, Any]:
    import copy, re
    # helpers
    def norm(s: str) -> str:
        # collapse internal whitespace, strip ends, casefold for locale-robust matching
        return re.sub(r"\s+", " ", s or "").strip().casefold()
    out = copy.deepcopy(data)                        # avoid mutating caller's object
    sections = out.get("sections", []) or []
    if not isinstance(sections, list):
        return out                                   # unexpected shape; leave as-is
    seen: Dict[str, Dict[str, Any]] = {}            # normalized_text -> record
    # first pass: mark duplicates (global across sections, earliest wins)
    for s_idx, sec in enumerate(sections):
        items = sec.get("items", []) or []
        if not isinstance(items, list):
            continue
        for i_idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            txt_raw = item.get("clause_text")
            if not isinstance(txt_raw, str):
                continue
            key = norm(txt_raw)
            if not key:
                continue
            if key in seen:
                # mark as duplicate; we'll filter in pass 2
                item["_dedup_removed"] = True
                # optional: record that it collided (for debugging/QA)
                # item["_dedup_note"] = f"dup of section {seen[key]['section']} idx {seen[key]['index']}"
            else:
                # first occurrence wins (keep earliest section/item index)
                seen[key] = {"section": s_idx, "index": i_idx}
    # second pass: filter out marked duplicates and clean temp keys
    for sec in sections:
        items = sec.get("items", []) or []
        if not isinstance(items, list):
            continue
        new_items = []
        for item in items:
            if isinstance(item, dict) and item.get("_dedup_removed"):
                continue
            if isinstance(item, dict) and "_dedup_removed" in item:
                item.pop("_dedup_removed", None)     # scrub temp flag
            new_items.append(item)
        sec["items"] = new_items
    out["sections"] = sections                       # write back normalized list
    return out

# Render: HTML (always) + PDF (if possible)
HTML_TEMPLATE = Template("""
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>Filled Contract Template</title>
<style>
  body { font-family: "DejaVu Sans", Arial, Helvetica, sans-serif; margin: 24px; }
  h1 { font-size: 22px; margin-bottom: 16px; }
  h2 { font-size: 18px; margin-top: 18px; border-bottom: 1px solid #ccc; padding-bottom: 4px;
       page-break-before: always; }
  .meta { color: #666; font-size: 12px; margin-bottom: 8px; }
  .item { margin: 10px 0; }
  .clause { white-space: pre-wrap; }
</style>
</head>
<body>
  <h1>Contract Analysis – Filled Template</h1>

  {% if data.doc_meta %}
  <div class="meta">
    <div><strong>Document Title:</strong> {{ data.doc_meta.title | default("N/A") | e }}</div>
    <div><strong>Source File:</strong> {{ data.doc_meta.source_file | default("N/A") | e }}</div>
  </div>
  {% endif %}

  {% for section in data.sections or [] %}
  <section>
    <h2>{{ loop.index }}. {{ section.name | e }}</h2>
    {% for item in section.items or [] %}
    <article class="item">
      <div><strong>{{ item.label or "Item" | e }}</strong></div>
      <div class="clause">{{ item.clause_text | e }}</div>
      {% if item.citation %}
      <div class="meta">Citation: {{ item.citation | e }}</div>
      {% endif %}
    </article>
    {% endfor %}
  </section>
  {% endfor %}
</body>
</html>
""")

def render_outputs(data: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)                     # ensure output dir exists
    # JSON artifact (atomic write)
    json_path = out_dir / "filled_template.json"                   # canonical name
    tmp_json  = json_path.with_suffix(".json.tmp")                 # temp path for atomic move
    tmp_json.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp_json.replace(json_path)                                    # atomic rename on same fs
    # HTML artifact via Jinja2 template
    try:
        html = HTML_TEMPLATE.render(data=data)                     # render HTML from template
    except Exception as e:
        raise RuntimeError(f"HTML render failed: {e}")             # fail w/ actionable message
    html_path = out_dir / "filled_template.html"                   # canonical name
    tmp_html  = html_path.with_suffix(".html.tmp")
    tmp_html.write_text(html, encoding="utf-8")                    # always UTF-8
    tmp_html.replace(html_path)                                    # atomic move
    # Optional PDF (wkhtmltopdf via pdfkit)
    pdf_path: Optional[Path] = None                                # default if PDF not produced
    if WKHTMLTOPDF_AVAILABLE:                                      # set earlier during imports
        try:
            pdf_path = out_dir / "filled_template.pdf"             # canonical name
            # pdfkit needs a string path; it returns True on success
            ok = pdfkit.from_string(html, str(pdf_path))           # convert HTML → PDF
            if not ok:                                             # pdfkit sometimes returns False
                print(f"[warn] PDF generation returned False; HTML still at {html_path}")
                pdf_path = None
        except Exception as e:
            print(f"[warn] PDF generation failed: {e}. HTML is still available at {html_path}")
            pdf_path = None
    else:
        print("[info] wkhtmltopdf not detected; skipped PDF creation. HTML is available.")
    # Compute checksums for manifest
    def _sha256(p: Path) -> str:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    json_sha = _sha256(json_path)                                  # required by run manifest
    pdf_sha  = _sha256(pdf_path) if pdf_path and pdf_path.exists() else None
    # Return artifact bundle (URIs + checksums)
    # These fields map directly to the run_manifest schema: json_uri/pdf_uri + checksums.  # schema
    # If you later upload to object storage, swap paths for URLs here.
    artifacts = {
        "json_uri": json_path.as_posix(),                          # path (or URL)
        "pdf_uri": pdf_path.as_posix() if pdf_path else "",        # empty if not produced
        "checksums": {
            "json_sha256": json_sha,
            "pdf_sha256": pdf_sha or "",                           # empty when no PDF
        },
    }
    return artifacts                                               # caller can populate manifest

# Main pipeline
def run(input_path: Path, out_dir: Path, policy_dir: Path, args: argparse.Namespace) -> None:
    # Environment & setup
    load_dotenv()
    input_path = Path(args.input).resolve()
    out_dir = Path(args.out).resolve()
    policy_dir = Path(args.policy_bundle).resolve()
    if not input_path.exists():
        raise SystemExit(f"[error] Input file not found: {input_path}")
    if not policy_dir.exists():
        raise SystemExit(f"[error] Policy bundle not found: {policy_dir}")
    # Integrity & schema
    verify_policy_checksums(policy_dir)
    schema = load_output_schema(policy_dir)
    # Runtime configuration
    runtime_cfg = Path(__file__).parent / "config" / "runtime_v1.jsonc"
    runtime = load_runtime_config(runtime_cfg)
    # Ingest contract
    contract_text = read_text_from_file(input_path)
    # Structured model call
    from openai_client import build_client_from_env
    client = build_client_from_env()
    system_msg = (
        "You are a contract analysis engine.\n"
        "Extract the fields required by the JSON schema precisely.\n"
        "Do not include commentary; output must conform to the schema.\n"
        "When multiple clauses seem to fit, choose the best section and do not duplicate."
    )
    try:
        raw = client.extract_json(
            text=contract_text,
            schema=schema,
            system_prompt=system_msg,
            name="contract_template_v1",
        )
    except Exception as e:
        raise SystemExit(f"[error] Model extraction failed: {e}")
    # Validation + normalization
    from validator import validate_filled_template
    from policy_loader import load_validation_rules
    validation_rules = load_validation_rules(policy_dir)
    report = validate_filled_template(raw, policy_dir)
    if not report.ok:
        for f in report.findings:
            print(f"[warn] {f['message']}")
        raise SystemExit("[error] Validation failed; aborting output rendering.")
    clean_data = normalize_and_dedup(raw)
    # Render outputs (JSON, HTML, PDF)
    artifacts = render_outputs(clean_data, out_dir)
    print(f"[ok] Done: outputs written to {out_dir.as_posix()}")
    print(f"      JSON: {artifacts['json_uri']}")
    if artifacts.get("pdf_uri"):
        print(f"      PDF : {artifacts['pdf_uri']}")

def run_one(input_path: Path, out_dir: Path, policy_dir: Path, args: argparse.Namespace) -> None:
    load_dotenv()  # make OPENAI_* available
    # Fail early if inputs are missing
    if not input_path.exists():
        raise SystemExit(f"[error] Input file not found: {input_path}")
    if not policy_dir.exists():
        raise SystemExit(f"[error] Policy bundle folder not found: {policy_dir}")
    # Integrity
    verify_policy_checksums(policy_dir)  # raises on mismatch
    # Schema
    schema = load_output_schema(policy_dir)  # dict schema object
    # Runtime config (resolve relative to this module)
    runtime_cfg = Path(__file__).parent / "config" / "runtime_v1.jsonc"
    runtime = load_runtime_config(runtime_cfg)
    # Ingest contract
    contract_text = read_text_from_file(input_path)
    # Model call (structured extraction under schema strictness)
    from orchestrator.openai_client import build_client_from_env  # import wrapper
    client = build_client_from_env()  # honors OPENAI_* overrides
    system_msg = (
        "You are a contract analysis engine. Extract the fields required by the "
        "JSON schema precisely. Choose the best-fit section and do not duplicate."
    )
    try:
        raw = client.extract_json(                 # returns dict that matches schema
            text=contract_text,                    # extracted contract text
            schema=schema,                         # schema from policy bundle
            system_prompt=system_msg,              # minimal, role-based instruction
            name="contract_template_v1",           # traceable schema name
        )
    except Exception as e:
        raise SystemExit(f"[error] Model extraction failed: {e}")
    # Validate + render
    # early schema-only validation of raw (quick fail)
    report = validate_filled_template(raw, policy_dir)  # wrapper expects (data, policy_root)
    if not report.ok:
        for f in (report.findings or []):
            print(f"[{f.get('level','?')}] {f.get('code','?')}: {f.get('message','')}")
        raise RuntimeError(f"Validation failed for {input_path.name}")
    # Normalize & de-duplicate (earliest occurrence wins)
    normalized = normalize_and_dedup(raw)
    # Validate *final* payload before writing artifacts
    report = validate_filled_template(normalized, policy_dir)
    if not report.ok:
        for f in (report.findings or []):
            path_str = ".".join(map(str, f.get("path", []))) if f.get("path") else ""
            print(f"[{f.get('level','?')}] {f.get('code','?')} @ {path_str}: {f.get('message','')}")
        raise SystemExit("Validation failed.")
    # Enrich doc metadata (non-fatal if the object isn’t present yet)
    try:
        meta = normalized.setdefault("doc_meta", {})
        meta.setdefault("title", Path(input_path).stem)
        meta.setdefault("source_file", str(input_path.name))
    except Exception:
        pass  # keep going even if meta injection fails

# Write artifacts (JSON, HTML, and PDF if available)
out_dir.mkdir(parents=True, exist_ok=True)
artifacts = render_outputs(normalized, out_dir)  # returns {json_uri, pdf_uri, checksums{...}}
print(f"✓ Done: {input_path.name} → {out_dir.as_posix()}")
    # Render artifacts (JSON, HTML, PDF)
    render_outputs(normalized, out_dir)
    # Final friendly message
    print(f"Done. Artifacts written to: {out_dir}")

# CLI definition
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Run contract analysis and fill template",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,  # pretty printing
    )
    # Input file or directory
    p.add_argument(
        "-i", "--input", required=True,
        help="Path to contract file or directory (.pdf, .docx, .txt)"
    )
    # Output folder
    p.add_argument(
        "-o", "--out", default="./out",
        help="Output directory where JSON/HTML/PDF files will be written"
    )
    # Policy bundle root
    p.add_argument(
        "-b", "--policy-bundle", default="./contract-analysis-policy-bundle",
        help="Path to policy bundle folder"
    )
    # Recursion (for directories)
    p.add_argument(
        "-r", "--recursive", action="store_true",
        help="If --input is a directory, recurse into subfolders"
    )
    # Filename patterns for batch mode
    p.add_argument(
        "-p", "--patterns", nargs="+",
        default=["*.pdf", "*.docx", "*.txt"],
        help="Filename patterns to include when --input is a directory"
    )
    # Version flag (optional)
    p.add_argument(
        "--version", action="version", version="APS CLI 1.0"
    )
    return p

# Main entrypoint
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()                             # build argparse config
    args = parser.parse_args(argv)                      # parse CLI args
    in_path = Path(args.input).resolve()                # normalize input path
    out_base = Path(args.out).resolve()                 # base output folder
    policy_dir = Path(args.policy_bundle).resolve()     # policy bundle root
    # Make sure the policy bundle exists up front
    if not policy_dir.exists():
        print(f"[error] Policy bundle not found: {policy_dir}")
        return 2
    # Single file run
    if in_path.is_file():
        out_dir = ensure_out_dir(out_base, in_path)     # e.g., ./out/<stem>/
        try:
            run_one(in_path, out_dir, policy_dir, args) # one file pipeline
            return 0                                    # success
        except SystemExit as e:
            return int(e.code or 1)                     # propagate failure cleanly
        except Exception as e:
            print(f"[error] Unhandled exception: {e}")
            return 1
    # Directory run (batch)
    if in_path.is_dir():
        files = discover_input_files(                   # collect matching files
            root=in_path,
            patterns=list(args.patterns),
            recursive=bool(args.recursive),
        )
        if not files:
            print(f"[warn] No input files found under {in_path} with patterns {args.patterns}")
            return 3
        failures = 0
        for f in files:
            out_dir = ensure_out_dir(out_base, f)       # per-file output folder
            try:
                run_one(f, out_dir, policy_dir, args)   # run pipeline
            except SystemExit as e:                     # structured failure
                code = int(e.code or 1)
                failures += 1
                print(f"[fail] {f.name}: exited with code {code}")
            except Exception as e:                      # unexpected error
                failures += 1
                print(f"[fail] {f.name}: unhandled exception: {e}")
        print(f"[summary] processed={len(files)} failures={failures}")
        return 0 if failures == 0 else 1
    # Neither file nor directory
    print(f"[error] Input path is not a file or directory: {in_path}")
    return 2

if __name__ == "__main__":
    # Exit with the code from main() so CI can detect failures.
    sys.exit(main())
