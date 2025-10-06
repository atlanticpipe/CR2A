#!/usr/bin/env python3
"""
CLI entrypoint to run the contract analysis pipeline end-to-end in Codespaces.

This file is intentionally self-contained so you can drop it in
`src/orchestrator/cli.py` and run:

    python -m orchestrator.cli \
      --input ./contracts/sample.pdf \
      --out ./out \
      --policy-bundle ./contract-analysis-policy-bundle

It enforces conformance via code (schema + checks), not just prompts.
Every meaningful line/block has inline comments as requested.
"""
from __future__ import annotations

# --- stdlib imports
import argparse  # parse CLI args
import json      # read/write JSON artifacts
import os        # env + path utils
import sys       # exit codes
import hashlib   # build SHA256 checksums
import fnmatch  # filename pattern matching for batch
from pathlib import Path  # path handling
from orchestrator.validator import validate_filled_template  # our wrapper
from typing import Any, Dict, List

# --- third-party imports (install via `pip install -e .` or `pip install <pkgs>`)
from dotenv import load_dotenv  # load .env so OPENAI_API_KEY is available
import jsonschema               # validate model output against our schema
import json5                    # parse JSONC runtime config
from pypdf import PdfReader     # extract text from PDFs (simple text layer)
import docx2txt                 # extract text from .docx if needed
from jinja2 import Template     # render HTML for the filled template
import asyncio                                  # stdlib: event loop
from utils.error_handler import handle_exception  # our handler function

# `pdfkit` is our HTML->PDF bridge (wkhtmltopdf must be available in PATH)
try:
    import pdfkit  # type: ignore
    WKHTMLTOPDF_AVAILABLE = True
except Exception:
    WKHTMLTOPDF_AVAILABLE = False

# OpenAI Python SDK (>=1.0)
try:
    from openai import OpenAI  # new-style client
except Exception as e:
    print("[fatal] openai package not available. pip install openai>=1.0", file=sys.stderr)
    raise


# -------------------------------
# Helpers: file I/O + text extract
# -------------------------------

def discover_input_files(root: Path, patterns: List[str], recursive: bool) -> List[Path]:
    """Resolve --input (file or directory) into a sorted list of files."""
    if root.is_file():                                   # single-file: return as-is
        return [root]
    files: List[Path] = []                               # start empty list
    if recursive:                                        # walk all subdirs if requested
        for p in root.rglob("*"):
            if p.is_file() and not any(part.startswith(".") for part in p.parts):
                if any(fnmatch.fnmatch(p.name.lower(), pat.lower()) for pat in patterns):
                    files.append(p)
    else:                                                # only top-level
        for p in root.iterdir():
            if p.is_file() and not p.name.startswith("."):
                if any(fnmatch.fnmatch(p.name.lower(), pat.lower()) for pat in patterns):
                    files.append(p)
    return sorted(files, key=lambda x: x.as_posix())     # deterministic ordering


def ensure_out_dir(base_out: Path, input_file: Path) -> Path:
    """Make a per-file output folder: <out>/<file-stem>/ to keep artifacts separate."""
    out_dir = base_out / input_file.stem                 # e.g., ./out/MasterAgreement/
    out_dir.mkdir(parents=True, exist_ok=True)           # create if missing
    return out_dir

def read_text_from_file(path: Path) -> str:
    """Extract raw text from a supported file.

    Supports: .pdf, .docx, .txt. Falls back to reading bytes as utf-8.
    """
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


# ---------------------------------------
# Policy bundle: integrity + schema loader
# ---------------------------------------

def sha256_of_file(path: Path) -> str:
    """Compute SHA256 of a file efficiently."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_policy_checksums(policy_dir: Path) -> None:
    """Ensure policy files match the manifest to prevent drift/tampering.

    Looks for `policy/checksums_manifest_v1.json` and compares every listed
    file's hash to its current hash in the repo.
    """
    manifest_path = policy_dir / "policy" / "checksums_manifest_v1.json"
    if not manifest_path.exists():
        print("[warn] No checksums manifest found; skipping integrity check.")
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))  # load manifest JSON
    mismatches = []  # collect any mismatched (path, expected, actual)

    for rel_path, expected_sha in manifest.get("files", {}).items():
        # Join policy root with the relative path from the manifest
        file_path = policy_dir / rel_path
        if not file_path.exists():
            mismatches.append((rel_path, expected_sha, "<missing>"))
            continue
        actual_sha = sha256_of_file(file_path)
        if actual_sha != expected_sha:
            mismatches.append((rel_path, expected_sha, actual_sha))

    if mismatches:
        # Fail fast if anything doesn't match — we want deterministic behavior.
        lines = [f" - {p}: expected {e}, got {a}" for (p, e, a) in mismatches]
        raise SystemExit("Policy checksum verification failed:\n" + "\n".join(lines))


def load_output_schema(policy_dir: Path) -> Dict[str, Any]:
    """Load the JSON Schema that defines the filled template structure.

    Expected at `contract-analysis-policy-bundle/schemas/output_schemas_v1.json`.
    We select the top-level schema with key `template_v1` by convention.
    """
    schema_path = policy_dir / "schemas" / "output_schemas_v1.json"
    if not schema_path.exists():
        raise SystemExit(f"Missing output schema file: {schema_path}")

    bundle = json.loads(schema_path.read_text(encoding="utf-8"))  # load schemas

    # Allow either a single schema object or a dict of named schemas
    if isinstance(bundle, dict) and "template_v1" in bundle:
        return bundle["template_v1"]  # return the canonical template schema
    else:
        return bundle  # assume it's already the schema object

def process_one_contract(input_path: Path, out_dir: Path, policy_root: Path, args) -> None:
    """
    Run the full pipeline for ONE contract file.

    This function uses helpers you already have:
      - verify_policy_checksums(policy_root)   # integrity guard for the policy bundle
      - load_output_schema(policy_root)        # loads the canonical JSON Schema
      - read_text_from_file(input_path)        # extracts raw text from pdf/docx/txt
      - validate_filled_template(output_json, policy_root)  # schema+rules validator

    Replace the STUB block with your real OpenAI client call when you're ready.
    """
    # --- 0) Prepare output folder for this file ---
    out_dir.mkdir(parents=True, exist_ok=True)                            # ensure folder exists

    # --- 1) Verify policy bundle integrity ---
    verify_policy_checksums(policy_root)                                   # raises on mismatch

    # --- 2) Load the canonical output schema ---
    schema = load_output_schema(policy_root)                               # dict schema object

    # --- 3) Extract raw text from the contract file ---
    raw_text = read_text_from_file(input_path)                             # string of contract text

    # --- 4) Analyze via OpenAI (STUB for now; replace later with real client) ---
    # NOTE: When you're ready, wire this to your real client, e.g.:
    from orchestrator.openai_client import build_client_from_env  # inline import
    client = build_client_from_env()                              # honors OPENAI_MODEL
    system_msg = (
        "You are a contract analysis engine. Extract the fields required by the "
        "JSON schema precisely. Choose the best-fit section and do not duplicate."
    )
    output_json = client.extract_json(                              # returns dict that matches schema
        text=raw_text,                                             # extracted contract text
        schema=schema,                                            # schema from policy bundle
        system_prompt=system_msg,                                 # minimal, role-based instruction
        name="contract_template_v1"                               # traceable schema name
    )

    # --- 5) Validate output against schema + policy rules ---
    report = validate_filled_template(output_json, policy_root)            # returns {ok, findings}
    if not report.ok:                                                      # on any failure:
        for f in report.findings:                                          # show all issues
            print(f"[{f['level']}] {f['code']}: {f['message']}")           # human readable
        raise RuntimeError(f"Validation failed for {input_path.name}")     # stop this file

    # --- 6) Write artifacts (JSON and HTML now; add PDF when ready) ---
    (out_dir / "results.json").write_text(                                 # save structured output
        json.dumps(output_json, indent=2),
        encoding="utf-8"
    )

    # Simple HTML placeholder; replace with your real renderer when wired
    (out_dir / "results.html").write_text(
        f"<html><body><h1>Contract Analysis for {input_path.name}</h1>"
        f"<p>(Replace with the real HTML renderer.)</p></body></html>",
        encoding="utf-8"
    )

    print(f"✔ Done: {input_path.name} → {out_dir.as_posix()}")              # success line

# ---------------------------
# Runtime config (JSON with //)
# ---------------------------

def load_runtime_config(config_path: Path) -> Dict[str, Any]:
    """Parse JSONC runtime config (allows comments) for model + flags."""
    if not config_path.exists():
        # Provide sane defaults if no runtime file is present
        return {
            "model": "gpt-4o-mini",  # default small model for extraction
            "temperature": 0,          # deterministic outputs
            "max_output_tokens": 2000  # keep outputs bounded
        }
    return json5.loads(config_path.read_text(encoding="utf-8"))  # parse JSONC


# -----------------------
# Model call + validation
# -----------------------

def call_model(contract_text: str, schema: Dict[str, Any], runtime: Dict[str, Any]) -> Dict[str, Any]:
    """Ask the model for a strictly-typed JSON per the provided schema.

    The enforcement happens via the SDK's JSON schema response format, and we
    *still* validate with `jsonschema` to be extra safe.
    """
    # Initialize OpenAI client with env var (dotenv already loaded in main())
    client = OpenAI()

    # Compose the instruction for the model — minimal and role-focused.
    system_msg = (
        "You are a contract analysis engine. "
        "Extract the fields required by the JSON schema precisely. "
        "Do not include commentary; output must conform to the schema. "
        "When multiple clauses seem to fit, choose the best section and do not duplicate."
    )

    # Truncate overly long contract text to fit context if needed (simple guardrail)
    max_chars = 180_000  # conservative; adjust as needed for your model/context
    payload_text = contract_text[:max_chars]

    # Prepare the new JSON schema response format
    response = client.responses.create(
        model=runtime.get("model", "gpt-4o-mini"),
        temperature=runtime.get("temperature", 0),
        max_output_tokens=runtime.get("max_output_tokens", 2000),
        # Use the JSON Schema tool to force well-formed structured output
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "contract_template_v1",
                "schema": schema,  # we pass through the policy bundle schema
                "strict": True     # require *only* fields defined in the schema
            },
        },
        input=[
            {"role": "system", "content": system_msg},             # set behavior
            {"role": "user", "content": payload_text},             # pass contract text
        ],
    )

    # Extract JSON from the SDK response (the SDK returns a structured object)
    raw_text = response.output_text  # SDK helper to get the combined text output
    try:
        data = json.loads(raw_text)  # model promised JSON; parse it
    except Exception as e:
        # If anything goes wrong, dump to help debugging
        raise SystemExit(f"Model did not return valid JSON. Raw output:\n{raw_text}")

    # Validate against our schema (double lock)
    jsonschema.validate(instance=data, schema=schema)
    return data


# -------------------------------------
# Post-processing: de-dup + best-fit pass
# -------------------------------------

def normalize_and_dedup(data: Dict[str, Any]) -> Dict[str, Any]:
    """Remove duplicate clauses across sections and pick a single best home.

    This is a conservative pass using normalized clause text as the key.
    If your schema uses different keys, adjust here.
    """
    # Collect all clauses by normalized text to see duplicates
    bucket: Dict[str, Dict[str, Any]] = {}

    # We assume a schema like: { "sections": [ {"name": ..., "items": [ {"clause_text": ...}, ... ] } ] }
    sections = data.get("sections", [])

    for sec in sections:
        for item in sec.get("items", []):
            txt = (item.get("clause_text") or "").strip().lower()  # normalize for dedup
            if not txt:
                continue
            if txt not in bucket:
                # First time we see this clause — keep it and record its home
                bucket[txt] = {"section": sec.get("name"), "item": item}
            else:
                # Duplicate: decide whether to keep the original placement
                # (Heuristic: keep the earliest section; later ones are removed)
                item["_dedup_removed"] = True  # tag so we can filter below

    # Filter items that were marked as duplicates
    for sec in sections:
        new_items = [it for it in sec.get("items", []) if not it.get("_dedup_removed")]
        sec["items"] = new_items

    data["sections"] = sections  # write back normalized list
    return data


# ------------------------------
# Render: HTML (always) + PDF (if possible)
# ------------------------------
HTML_TEMPLATE = Template(
    """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Filled Contract Template</title>
  <style>
    body { font-family: Arial, Helvetica, sans-serif; margin: 24px; }
    h1 { font-size: 22px; }
    h2 { font-size: 18px; margin-top: 18px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
    .item { margin: 10px 0; }
    .meta { color: #666; font-size: 12px; }
    .clause { white-space: pre-wrap; }
  </style>
</head>
<body>
  <h1>Contract Analysis — Filled Template</h1>
  {% if data.doc_meta %}
  <div class="meta">
    <div><strong>Document Title:</strong> {{ data.doc_meta.title or 'N/A' }}</div>
    <div><strong>Source File:</strong> {{ data.doc_meta.source_file or 'N/A' }}</div>
  </div>
  {% endif %}

  {% for section in data.sections or [] %}
    <h2>{{ loop.index }}. {{ section.name }}</h2>
    {% for item in section.items or [] %}
      <div class="item">
        <div><strong>{{ item.label or 'Item' }}</strong></div>
        <div class="clause">{{ item.clause_text }}</div>
        {% if item.citation %}
          <div class="meta">Citation: {{ item.citation }}</div>
        {% endif %}
      </div>
    {% endfor %}
  {% endfor %}
</body>
</html>
    """
)


def render_outputs(data: Dict[str, Any], out_dir: Path) -> None:
    """Write HTML, JSON, and (if available) PDF outputs to disk."""
    out_dir.mkdir(parents=True, exist_ok=True)  # ensure output directory exists

    # 1) JSON artifact for audit / downstream automation
    json_path = out_dir / "filled_template.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # 2) HTML view for quick inspection
    html = HTML_TEMPLATE.render(data=data)  # render Jinja2 template with our data
    html_path = out_dir / "filled_template.html"
    html_path.write_text(html, encoding="utf-8")

    # 3) PDF conversion (optional if wkhtmltopdf is missing)
    pdf_path = out_dir / "filled_template.pdf"
    if WKHTMLTOPDF_AVAILABLE:
        try:
            pdfkit.from_string(html, str(pdf_path))  # convert HTML string to PDF file
        except Exception as e:
            print(f"[warn] PDF generation failed: {e}. HTML is still available at {html_path}")
    else:
        print("[info] wkhtmltopdf not detected; skipped PDF creation. HTML is available.")


# -------------
# Main pipeline
# -------------

def run(input_path: Path, out_dir: Path, policy_dir: Path, args: argparse.Namespace) -> None:
    """Orchestrate the full flow: integrity -> schema -> model -> validate -> render."""
    # Load env vars from .env if present (makes OPENAI_API_KEY available).
    load_dotenv()

    # Resolve paths from CLI
    input_path = Path(args.input).resolve()
    out_dir = Path(args.out).resolve()
    policy_dir = Path(args.policy_bundle).resolve()

    # Fail early if inputs are missing
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")
    if not policy_dir.exists():
        raise SystemExit(f"Policy bundle folder not found: {policy_dir}")

    # Integrity gate — make sure policy pack hasn't changed unexpectedly
    verify_policy_checksums(policy_dir)

    # Schema — determine the structure we must fill
    schema = load_output_schema(policy_dir)

    # Runtime config — select model + parameters
    runtime = load_runtime_config(Path("orchestrator/config/runtime_v1.jsonc"))

    # Ingest the contract
    contract_text = read_text_from_file(input_path)

    # Model call — structured extraction under schema strictness
    from orchestrator.openai_client import build_client_from_env   # import wrapper
    client = build_client_from_env()                               # honor .env overrides
    system_msg = (
        "You are a contract analysis engine. Extract the fields required by the "
        "JSON schema precisely. Choose the best-fit section and do not duplicate."
    )
    raw = client.extract_json(                                     # returns dict that matches schema
        text=contract_text,                                        # extracted contract text
        schema=schema,                                             # schema from policy bundle
        system_prompt=system_msg,                                  # minimal, role-based instruction
        name="contract_template_v1"                                # traceable schema name
    )

def run_one(input_path: Path, out_dir: Path, policy_dir: Path, args: argparse.Namespace) -> None:
    """
    Orchestrate the full flow for ONE contract file.
    This is adapted from your current run(args).
    """
    load_dotenv()

    # --- Fail early if inputs are missing ---
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")
    if not policy_dir.exists():
        raise SystemExit(f"Policy bundle folder not found: {policy_dir}")

    # Integrity
    verify_policy_checksums(policy_dir)

    # Schema
    schema = load_output_schema(policy_dir)

    # Runtime config
    runtime = load_runtime_config(Path("orchestrator/config/runtime_v1.jsonc"))

    # Ingest contract
    contract_text = read_text_from_file(input_path)

    # Model call
    from orchestrator.openai_client import build_client_from_env
    client = build_client_from_env()
    system_msg = (
        "You are a contract analysis engine. Extract the fields required by the "
        "JSON schema precisely. Choose the best-fit section and do not duplicate."
    )
    raw = client.extract_json(
        text=contract_text,
        schema=schema,
        system_prompt=system_msg,
        name="contract template v1",
    )

    # Validate + render
    report = validate_filled_template(raw, policy_dir)
    if not report.ok:
        for f in report.findings:
            print(f"[{f['level']}] {f['code']}: {f['message']}")
        raise RuntimeError(f"Validation failed for {input_path.name}")

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(raw, indent=2), encoding="utf-8")
    (out_dir / "results.html").write_text(
        f"<html><body><h1>Contract Analysis for {input_path.name}</h1></body></html>",
        encoding="utf-8"
    )
    print(f"✔ Done: {input_path.name} → {out_dir}")

    # Post-process — ensure dedup + best-fit single placement
    normalized = normalize_and_dedup(raw)

    # Validate against the policy bundle before rendering artifacts
    from orchestrator.validator import validate_filled_template    # import validator
    report = validate_filled_template(
        normalized,                                                # the normalized payload
        policy_dir,                                                # contract-analysis-policy-bundle root
        policy_tag=(normalized.get("doc_meta") or {}).get("policy_version"),
    )
    if not report.ok:
        for f in report.findings:
            print(f"[{f.level}] {f.code} @ {'.'.join(f.path)}: {f.message}")
        raise SystemExit("Validation failed.")


    # Add doc metadata if schema supports it (non-fatal if not present)
    try:
        normalized.setdefault("doc_meta", {})
        normalized["doc_meta"].setdefault("title", Path(input_path).stem)
        normalized["doc_meta"].setdefault("source_file", str(input_path.name))
    except Exception:
        pass

    # Render artifacts (JSON, HTML, PDF)
    render_outputs(normalized, out_dir)

    # Final friendly message
    print(f"Done. Artifacts written to: {out_dir}")


# -------------
# CLI definition
# -------------

def build_parser() -> argparse.ArgumentParser:
    """Define and return the argument parser for this CLI."""
    p = argparse.ArgumentParser(description="Run contract analysis and fill template")

    # Path to the input contract (PDF/DOCX/TXT)
    p.add_argument("--input", required=True, help="Path to contract file (.pdf, .docx, .txt)")

    # Output folder where JSON/HTML/PDF will be written
    p.add_argument("--out", default="./out", help="Output directory (default: ./out)")

    # Location of the policy bundle root folder
    p.add_argument(
        "--policy-bundle",
        default="./contract-analysis-policy-bundle",
        help="Path to contract-analysis-policy-bundle folder (default: ./contract-analysis-policy-bundle)"
    )

    p.add_argument(
        "--recursive",
        action="store_true",
        help="If --input is a directory, recurse into subfolders"
    )  # add recursion

    p.add_argument(
        "--patterns",
        nargs="+",
        default=["*.pdf", "*.docx", "*.txt"],
        help="Filename patterns if --input is a directory (default: *.pdf *.docx *.txt)"
    )  # add patterns

    return p


def main() -> None:
    """Entrypoint when invoked as a module/script."""
    parser = build_parser()  # build the CLI parser
    args = parser.parse_args()  # parse CLI args
    run(args)  # execute orchestration


if __name__ == "__main__":
    main()  # delegate to main when run as `python src/orchestrator/cli.py`
