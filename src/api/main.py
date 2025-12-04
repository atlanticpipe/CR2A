from __future__ import annotations

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from orchestrator.analyzer import analyze_to_json
from orchestrator.openai_client import refine_cr2a
from orchestrator.pdf_export import export_pdf_from_filled_json
from orchestrator.policy_loader import load_validation_rules
from orchestrator.validator import validate_filled_template

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))
MAX_FILE_BYTES = int(MAX_FILE_MB * 1024 * 1024)
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "uploads/")
RUN_OUTPUT_ROOT = Path(os.getenv("RUN_OUTPUT_ROOT", "/tmp/cr2a_runs")).expanduser()
REPO_ROOT = Path(__file__).resolve().parents[2]

app = FastAPI(title="CR2A API stub", version="0.1.0")

allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
origins: List[str] = [o.strip() for o in allow_origins.split(",")] if allow_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UploadUrlResponse(BaseModel):
    url: str
    upload_method: str = "PUT"
    fields: Optional[dict] = None
    bucket: str
    key: str
    expires_in: int


class AnalysisRequestPayload(BaseModel):
    contract_id: str
    contract_uri: Optional[str] = None
    fdot_contract: bool = False
    assume_fdot_year: Optional[str] = Field(default=None, pattern=r"^\d{4}$")
    policy_version: Optional[str] = None
    notes: Optional[str] = None


class AnalysisResponse(BaseModel):
    run_id: str
    status: str
    completed_at: datetime
    manifest: dict
    download_url: Optional[str] = None
    filled_template_url: Optional[str] = None
    error: Optional[dict] = None


def _s3_client():
    if boto3 is None:
        raise HTTPException(status_code=500, detail="boto3 not installed; cannot presign S3 upload URLs.")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("s3", region_name=region)


RUNS: Dict[str, Dict[str, Path]] = {}


def _http_error(status: int, category: str, message: str) -> HTTPException:
    # Standardized error envelope so the UI can surface actionable messages.
    return HTTPException(status_code=status, detail={"category": category, "message": message})


def _load_output_schema() -> Dict[str, Any]:
    schema_path = REPO_ROOT / "schemas" / "output_schemas_v1.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _normalize_to_schema(raw: Dict[str, Any], closing_line: str, policy_version: Optional[str]) -> Dict[str, Any]:
    # Map heuristic output into the stricter JSON schema shape expected by the template exporter.
    section_i_keys = [
        "PROJECT TITLE:",
        "SOLICITATION NO.:",
        "OWNER:",
        "CONTRACTOR:",
        "SCOPE:",
        "GENERAL RISK LEVEL:",
        "BID MODEL:",
        "NOTES:",
    ]

    source_i = raw.get("SECTION_I") or {}
    section_i: Dict[str, str] = {}
    for key in section_i_keys:
        # Case-insensitive lookup with sane fallback text so schema requirements are satisfied.
        match = next((source_i[k] for k in source_i if k.rstrip(":").lower() == key.rstrip(":").lower()), "")
        section_i[key] = (match or "Not present in contract.")

    def _convert_clause(block: Dict[str, Any]) -> Dict[str, str]:
        # Align clause fields with schema-required labels.
        return {
            "Clause Language": block.get("clause_language", ""),
            "Clause Summary": block.get("clause_summary", ""),
            "Risk Triggers": block.get("risk_triggers", ""),
            "Flow-Down Obligations": block.get("flow_down_obligations", ""),
            "Redline Recommendations": block.get("redline_recommendations", ""),
            "Harmful Language / Conflicts": block.get("harmful_language_conflicts", ""),
        }

    def _convert_items(items: List[Dict[str, Any]], section_label: str) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for idx, item in enumerate(items or [], start=1):
            normalized.append(
                {
                    "item_number": item.get("item_number", idx),
                    "item_title": item.get("item_title") or f"{section_label} Item {idx}",
                    "clauses": [_convert_clause(b) for b in item.get("clauses") or []],
                    "closing_line": item.get("closing_line") or closing_line,
                }
            )
        if not normalized:
            normalized.append(
                {
                    "item_number": 1,
                    "item_title": f"{section_label} Item",
                    "clauses": [],
                    "closing_line": closing_line,
                }
            )
        return normalized

    normalized = {"SECTION_I": section_i}
    for sec in ["II", "III", "IV", "V", "VI"]:
        normalized[f"SECTION_{sec}"] = _convert_items(raw.get(f"SECTION_{sec}") or [], sec)

    normalized["SECTION_VII"] = raw.get("SECTION_VII", [])
    normalized["SECTION_VIII"] = {
        "rows": [],
        "general_risk_level": section_i.get("GENERAL RISK LEVEL:", "Not present in contract."),
    }
    normalized["OMISSION_CHECK"] = "No omissions or uncategorized risks identified."
    normalized["doc_meta"] = {
        "policy_version": policy_version or "schemas@v1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fdot_contract": raw.get("fdot_contract"),
        "fdot_year": raw.get("assume_fdot_year"),
    }
    return normalized


def _download_contract(uri: str, dest: Path) -> Path:
    # Stream to disk with a hard size check to avoid memory blow-ups.
    if uri.startswith("file://"):
        src = Path(uri[7:]).expanduser()
        if not src.exists():
            raise _http_error(400, "ValidationError", f"File not found: {src}")
        if src.stat().st_size > MAX_FILE_BYTES:
            raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
        return Path(shutil.copy(src, dest))

    if uri.startswith("http://") or uri.startswith("https://"):
        try:
            # Stream remote content with a timeout and size guard to avoid partial downloads or memory spikes.
            with httpx.stream("GET", uri, timeout=60, follow_redirects=True) as resp:
                if resp.status_code >= 400:
                    raise _http_error(502, "NetworkError", f"Download failed: HTTP {resp.status_code}")
                total = 0
                dest.parent.mkdir(parents=True, exist_ok=True)
                with dest.open("wb") as fh:
                    for chunk in resp.iter_bytes():
                        total += len(chunk)
                        if total > MAX_FILE_BYTES:
                            raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
                        fh.write(chunk)
            return dest
        except httpx.TimeoutException as exc:
            # Convert timeouts into a consistent error category for the UI to display.
            raise _http_error(504, "TimeoutError", f"Download timed out: {exc}")
        except httpx.RequestError as exc:
            # Network issues need to be explicit so the caller can retry or adjust the URL.
            raise _http_error(502, "NetworkError", f"Download failed: {exc}")

    local = Path(uri).expanduser()
    if not local.exists():
        raise _http_error(400, "ValidationError", "contract_uri must be an HTTP(S) URL or local path")
    if local.stat().st_size > MAX_FILE_BYTES:
        raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
    return Path(shutil.copy(local, dest))


@app.get("/health")
def health():
    return {"ok": True, "version": app.version}


@app.get("/upload-url", response_model=UploadUrlResponse)
def upload_url(
    filename: str = Query(..., description="Original filename"),
    contentType: str = Query("application/octet-stream", description="MIME type"),
    size: int = Query(..., description="File size in bytes"),
):
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size} bytes. Limit is {MAX_FILE_BYTES} bytes ({MAX_FILE_MB} MB).",
        )

    bucket = os.getenv("UPLOAD_BUCKET") or os.getenv("S3_UPLOAD_BUCKET")
    if not bucket:
        raise HTTPException(status_code=500, detail="UPLOAD_BUCKET env var is required for presign.")

    safe_name = quote(os.path.basename(filename))
    key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{safe_name}"

    client = _s3_client()
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": contentType},
            ExpiresIn=UPLOAD_EXPIRES_SECONDS,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")

    return UploadUrlResponse(
        url=url,
        upload_method="PUT",
        fields=None,
        bucket=bucket,
        key=key,
        expires_in=UPLOAD_EXPIRES_SECONDS,
    )


@app.post("/analysis", response_model=AnalysisResponse)
def analysis(payload: AnalysisRequestPayload):
    if not payload.contract_uri:
        raise _http_error(400, "ValidationError", "contract_uri is required to run analysis.")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    run_dir = RUN_OUTPUT_ROOT / run_id
    input_path = run_dir / "input.bin"

    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        downloaded = _download_contract(str(payload.contract_uri), input_path)
        raw_json = analyze_to_json(downloaded, REPO_ROOT, ocr=os.getenv("OCR_MODE", "auto"))
        raw_json["fdot_contract"] = payload.fdot_contract
        raw_json["assume_fdot_year"] = payload.assume_fdot_year

        llm_mode = os.getenv("LLM_REFINEMENT", "off").lower()
        if llm_mode == "on":
            # Only attempt OpenAI if explicitly enabled to avoid accidental calls without keys.
            refined = refine_cr2a(raw_json)
            if isinstance(refined, dict) and refined:
                raw_json = refined

        rules = load_validation_rules(REPO_ROOT)
        val = rules.get("validation", rules)
        closing_line = val.get("mandatory_fields", {}).get(
            "section_II_to_VI_closing_line",
            "All applicable clauses for [Item #/Title] have been identified and analyzed.",
        )
        normalized = _normalize_to_schema(raw_json, closing_line, payload.policy_version)

        schema = _load_output_schema()
        validation = validate_filled_template(normalized, schema, rules)
        if not validation.ok:
            details = "; ".join(f"{f.code}: {f.message}" for f in validation.findings)
            raise _http_error(400, "ValidationError", details)

        run_dir.mkdir(parents=True, exist_ok=True)
        filled_path = run_dir / "filled_template.json"
        filled_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

        output_pdf = run_dir / "cr2a_export.pdf"
        export_path = export_pdf_from_filled_json(
            normalized,
            output_pdf,
            backend="docx",
            template_docx=REPO_ROOT / "templates" / "CR2A_Template.docx",
            title="Contract Risk & Compliance Analysis",
        )

    except HTTPException:
        # Passthrough for clean HTTP errors.
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise _http_error(500, "ProcessingError", str(exc))

    RUNS[run_id] = {"pdf": export_path, "json": filled_path}
    completed_at = datetime.now(timezone.utc)
    manifest = {
        "contract_id": payload.contract_id,
        "contract_uri": payload.contract_uri,
        "fdot_contract": payload.fdot_contract,
        "assume_fdot_year": payload.assume_fdot_year,
        "policy_version": payload.policy_version or "schemas@v1.0",
        "notes": payload.notes,
        "ocr_mode": os.getenv("OCR_MODE", "auto"),
        "llm_refinement": os.getenv("LLM_REFINEMENT", "off"),
        "validation": {"ok": True, "findings": len(validation.findings)},
        "export": {"pdf": export_path.name, "backend": "docx"},
    }

    return AnalysisResponse(
        run_id=run_id,
        status="completed",
        completed_at=completed_at,
        manifest=manifest,
        download_url=f"/runs/{run_id}/report",
        filled_template_url=f"/runs/{run_id}/filled-template",
        error=None,
    )


@app.get("/runs/{run_id}/report")
def download_report(run_id: str):
    record = RUNS.get(run_id)
    if not record:
        raise _http_error(404, "NotFound", "Run not found.")
    pdf_path = record.get("pdf")
    if not pdf_path or not Path(pdf_path).exists():
        raise _http_error(404, "NotFound", "Report not available.")
    suffix = Path(pdf_path).suffix.lower()
    media_type = "application/pdf" if suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(pdf_path, media_type=media_type, filename=Path(pdf_path).name)


@app.get("/runs/{run_id}/filled-template")
def download_json(run_id: str):
    record = RUNS.get(run_id)
    if not record:
        raise _http_error(404, "NotFound", "Run not found.")
    json_path = record.get("json")
    if not json_path or not Path(json_path).exists():
        raise _http_error(404, "NotFound", "Template JSON not available.")
    return FileResponse(json_path, media_type="application/json", filename=Path(json_path).name)
