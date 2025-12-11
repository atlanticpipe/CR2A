#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from .validator import validate_filled_template  # type: ignore
except Exception:
    from src.orchestrator.validator import validate_filled_template  # type: ignore

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA = DEFAULT_ROOT / "contract-analysis-policy-bundle" / "policy" / "section_map_v1.json"
DEFAULT_RULES = DEFAULT_ROOT / "contract-analysis-policy-bundle" / "policy" / "validation_rules_v1.json"
DEFAULT_TEMPLATE = DEFAULT_ROOT / "templates" / "CR2A_Template.docx"

MAX_FILE_MB_DEFAULT = 500


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _size_mb(p: Path) -> float:
    try:
        return p.stat().st_size / (1024 * 1024)
    except FileNotFoundError:
        return 0.0


def cmd_validate(args: argparse.Namespace) -> int:
    schema_path = Path(args.schema).expanduser().resolve() if args.schema else DEFAULT_SCHEMA
    rules_path = Path(args.rules).expanduser().resolve() if args.rules else DEFAULT_RULES
    output_path = Path(args.output_json).expanduser().resolve()

    if not output_path.exists():
        logging.error("Output JSON not found: %s", output_path); return 2
    if not schema_path.exists():
        logging.error("Schema file not found: %s", schema_path); return 2
    if not rules_path.exists():
        logging.error("Validation rules not found: %s", rules_path); return 2

    output_obj = _load_json(output_path)
    schema = _load_json(schema_path)
    rules = _load_json(rules_path)

    report = validate_filled_template(output_obj, schema, rules)
    if not report.ok:
        logging.error("Validation failed with %d finding(s).", len(report.findings))
        for f in report.findings:
            logging.error("[%s] %s: %s", f.level, f.code, f.message)
        return 1

    logging.info("Validation passed.")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    # Lazy import to avoid optional dependency issues at module import time
    try:
        from .analyzer import analyze_to_json  # type: ignore
    except Exception:
        from src.orchestrator.analyzer import analyze_to_json  # type: ignore

    root = Path(args.root).expanduser().resolve() if args.root else DEFAULT_ROOT
    input_path = Path(args.input).expanduser().resolve()
    out_path = Path(args.output_json).expanduser().resolve() if args.output_json else Path("filled_template.from_input.json")

    if not input_path.exists():
        logging.error("Input file not found: %s", input_path); return 2

    max_mb = float(args.max_file_mb or MAX_FILE_MB_DEFAULT)
    size_mb = _size_mb(input_path)
    if size_mb > max_mb:
        logging.error("Input file %.2f MB exceeds limit of %.2f MB.", size_mb, max_mb)
        return 2

    try:
        obj = analyze_to_json(input_path, root, ocr=args.ocr)
    except Exception as e:
        logging.exception("Analyze failed: %s", e); return 1

    # Optional LLM refinement
    if args.llm == "on":
        try:
            try:
                from .openai_client import refine_cr2a  # type: ignore
            except Exception:
                from src.orchestrator.openai_client import refine_cr2a  # type: ignore
            refined = refine_cr2a(obj)
            if isinstance(refined, dict) and refined:
                obj = refined
                logging.info("LLM refinement applied.")
            else:
                logging.warning("LLM refinement returned empty/invalid result; keeping heuristic output.")
        except Exception as e:
            logging.error("LLM refinement failed: %s; keeping heuristic output.", e)

    out_path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    logging.info("Wrote %s", out_path)

    # Post-validate
    try:
        schema = _load_json(DEFAULT_SCHEMA)
        rules = _load_json(DEFAULT_RULES)
        report = validate_filled_template(obj, schema, rules)
        if not report.ok:
            logging.error("Post-analyze validation found %d issue(s).", len(report.findings))
            for f in report.findings:
                logging.error("[%s] %s: %s", f.level, f.code, f.message)
            return 1
        logging.info("Validation passed.")
    except Exception as e:
        logging.warning("Skipped automatic validation: %s", e)

    return 0


def cmd_export_pdf(args: argparse.Namespace) -> int:
    try:
        from .pdf_export import export_pdf_from_filled_json  # type: ignore
    except Exception:
        from src.orchestrator.pdf_export import export_pdf_from_filled_json  # type: ignore

    input_json = Path(args.input_json).expanduser().resolve()
    output_pdf = Path(args.output_pdf).expanduser().resolve() if args.output_pdf else Path("cr2a_export.pdf")
    template_docx = Path(args.template_docx).expanduser().resolve() if args.template_docx else DEFAULT_TEMPLATE

    if not input_json.exists(): logging.error("Input JSON not found: %s", input_json); return 2
    if args.backend == "docx" and not template_docx.exists():
        logging.error("Template DOCX not found: %s", template_docx); return 2

    data = _load_json(input_json)

    # Optional pre-export validation
    try:
        schema = _load_json(DEFAULT_SCHEMA)
        rules = _load_json(DEFAULT_RULES)
        report = validate_filled_template(data, schema, rules)
        if not report.ok:
            logging.error("Validation failed; refusing to export.")
            for f in report.findings:
                logging.error("[%s] %s: %s", f.level, f.code, f.message)
            return 1
    except Exception as e:
        logging.warning("Skipped pre-export validation: %s", e)

    result_path = export_pdf_from_filled_json(
        data,
        output_pdf,
        backend=args.backend,
        template_docx=template_docx,
        title=args.title or "Contract Risk & Compliance Analysis",
    )
    logging.info("Report written to %s", result_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="CR2A CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a filled template against schema + policy rules")
    v.add_argument("--output-json", required=True, help="Path to the filled template JSON to validate")
    v.add_argument("--schema", default=str(DEFAULT_SCHEMA), help="Path to the JSON schema file")
    v.add_argument("--rules", default=str(DEFAULT_RULES), help="Path to validation_rules_v1.json")
    v.set_defaults(func=cmd_validate)

    a = sub.add_parser("analyze", help="Analyze a DOCX/PDF into a filled CR2A JSON")
    a.add_argument("--input", required=True, help="Path to input DOCX or PDF")
    a.add_argument("--output-json", help="Where to write the filled template JSON (default: ./filled_template.from_input.json)")
    a.add_argument("--ocr", default=os.getenv("OCR_MODE", "auto"), choices=["auto","textract","tesseract","none"],
                   help="OCR mode for scanned PDFs (default from OCR_MODE env, else 'auto')")
    a.add_argument("--llm", default="off", choices=["off","on"], help="Enable OpenAI-assisted refinement (requires OPENAI_API_KEY or OPENAI_SECRET_ARN)")
    a.add_argument("--max-file-mb", type=float, default=MAX_FILE_MB_DEFAULT, help="Maximum input file size in megabytes")
    a.add_argument("--root", default=str(DEFAULT_ROOT), help="Repo root (used to read policy files)")
    a.set_defaults(func=cmd_analyze)

    e = sub.add_parser("export-pdf", help="Export a filled template JSON to a formatted PDF/DOCX")
    e.add_argument("--input-json", required=True, help="Path to filled_template.json")
    e.add_argument("--output-pdf", help="Where to write the PDF")
    e.add_argument("--backend", default="docx", choices=["reportlab", "docx"], help="Export backend")
    e.add_argument("--template-docx", default=str(DEFAULT_TEMPLATE), help="Optional DOCX template path for backend=docx")
    e.add_argument("--title", help="Report title")
    e.set_defaults(func=cmd_export_pdf)

    return ap


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        parser.print_help(sys.stderr)
        return 0
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help(sys.stderr)
        return 2
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())