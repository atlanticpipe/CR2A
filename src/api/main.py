from __future__ import annotations

import json
import os
import re
import uuid
import logging
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlparse, unquote
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from orchestrator.analyzer import analyze_to_json
from orchestrator.openai_client import OpenAIClientError, refine_cr2a
from orchestrator.pdf_export import export_pdf_from_filled_json
from orchestrator.policy_loader import load_validation_rules
from orchestrator.validator import validate_filled_template
from orchestrator.mime_utils import infer_extension_from_content_type_or_magic, infer_mime_type

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))
MAX_FILE_BYTES = int(MAX_FILE_MB * 1024 * 1024)
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "upload/")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "cr2a-output")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "runs/")
OUTPUT_EXPIRES_SECONDS = int(os.getenv("OUTPUT_EXPIRES_SECONDS", "86400"))
RUN_OUTPUT_ROOT = Path(os.getenv("RUN_OUTPUT_ROOT", "/tmp/cr2a_runs")).expanduser()
REPO_ROOT = Path(__file__).resolve().parents[2]
_VALID_BUCKET = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,61}[a-z0-9])$")
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "cr2a-upload")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
S3 = boto3.client("s3", region_name=AWS_REGION) if boto3 else None

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

logger = logging.getLogger(__name__)

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
    llm_enabled: bool = True

class AnalysisResponse(BaseModel):
    run_id: str
    status: str
    completed_at: datetime
    manifest: dict
    download_url: Optional[str] = None
    filled_template_url: Optional[str] = None
    error: Optional[dict] = None

def _s3_client():
    if S3 is None:
        raise HTTPException(status_code=500, detail="boto3 not installed; cannot presign S3 upload URLs.")
    return S3

def _http_error(status: int, category: str, message: str) -> HTTPException:
    # Standardized error envelope so the UI can surface actionable messages.
    return HTTPException(status_code=status, detail={"category": category, "message": message})

def _is_truthy(value: Optional[str]) -> bool:
    # Normalize common truthy env strings so "true"/"1" enable features reliably.
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y", "on"}

def _is_valid_s3_bucket(name: str) -> bool:
    # Enforce AWS-safe bucket names to avoid runtime presign failures.
    if any(ch.isupper() for ch in name) or "_" in name:
        # AWS rejects uppercase and underscore characters.
        return False
    if not _VALID_BUCKET.fullmatch(name):
        return False
    if ".." in name or ".-" in name or "-." in name:
        return False
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", name):
        return False
    return True

def _load_upload_bucket() -> Optional[str]:
    # Normalize the configured upload bucket to avoid presign/runtime misconfigurations.
    bucket = UPLOAD_BUCKET or "cr2a-upload"
    if not _is_valid_s3_bucket(bucket):
        # Fail fast if the pinned bucket ever violates AWS rules (defensive guard).
        raise _http_error(
            500,
            "ValidationError",
            "Invalid S3 bucket 'cr2a-upload'. Expected lowercase DNS-compatible name.",
        )
    return bucket

def _load_output_bucket() -> str:
    # Require an explicit output bucket so Lambda can persist results for download.
    bucket = (OUTPUT_BUCKET or "").strip()
    if not bucket:
        raise _http_error(500, "ConfigError", "OUTPUT_BUCKET is required for result downloads.")
    if not _is_valid_s3_bucket(bucket):
        raise _http_error(500, "ValidationError", "Invalid S3 bucket for outputs; expected DNS-compatible name.")
    return bucket

def _output_key(run_id: str, filename: str) -> str:
    # Build a predictable key path while preventing path traversal and unsafe characters.
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise _http_error(400, "ValidationError", "Invalid run_id format.")
    prefix = OUTPUT_PREFIX.strip("/")
    parts = [part for part in (prefix, run_id, filename) if part]
    return "/".join(parts)

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

def _resolve_contract_key(contract_uri: str) -> str:
    # Validate the contract URI and extract the S3 object key, rejecting unexpected hosts.
    if S3 is None:
        raise _http_error(500, "ProcessingError", "boto3 not installed; cannot fetch contract from S3.")
    if not UPLOAD_BUCKET:
        raise _http_error(500, "ConfigError", "UPLOAD_BUCKET is required to fetch contract files.")

    parsed = urlparse(contract_uri)

    if parsed.scheme != "https":
        raise _http_error(400, "ConfigError", f"Unexpected contract_uri scheme: {parsed.scheme}")

    host = parsed.netloc
    expected_global_host = f"{UPLOAD_BUCKET}.s3.amazonaws.com"
    expected_regional_host = f"{UPLOAD_BUCKET}.s3.{AWS_REGION}.amazonaws.com"
    path_style_host = f"s3.{AWS_REGION}.amazonaws.com"

    if host not in (expected_global_host, expected_regional_host, path_style_host):
        raise _http_error(400, "ConfigError", f"Unexpected contract_uri host: {host}")

    path = unquote(parsed.path.lstrip("/"))

    if host == path_style_host:
        parts = path.split("/", 1)
        if len(parts) < 2:
            raise _http_error(400, "ValidationError", "contract_uri path missing bucket/key segments.")
        bucket_in_path, key = parts[0], parts[1]
        if bucket_in_path != UPLOAD_BUCKET:
            raise _http_error(400, "ConfigError", f"Unexpected bucket in contract_uri path: {bucket_in_path}")
    else:
        key = path

    if not key:
        raise _http_error(400, "ValidationError", "contract_uri path is missing an object key.")
    return key

def _download_contract_to_path(contract_uri: str, dest_path: Path) -> Path:
    # Stream the contract from S3 onto disk to avoid double-buffering in memory.
    key = _resolve_contract_key(contract_uri)
    try:
        obj = S3.get_object(Bucket=UPLOAD_BUCKET, Key=key)
    except Exception as exc:
        logger.exception("Failed to download contract from S3", extra={"bucket": UPLOAD_BUCKET, "key": key})
        raise _http_error(502, "NetworkError", f"Download failed: {exc}")

    content_length = obj.get("ContentLength")
    if content_length and content_length > MAX_FILE_BYTES:
        raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")

    body = obj.get("Body")
    if body is None:
        raise _http_error(502, "NetworkError", "Download failed: empty body")

    written = 0
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with dest_path.open("wb") as fh:
        while True:
            chunk = body.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_FILE_BYTES:
                raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
            fh.write(chunk)

    body.close()

    return dest_path

@app.get("/health")
def health():
    return {"ok": True, "version": app.version}

def _presign_output_url(key: str) -> str:
    # Return a short-lived download URL to avoid serving large files from Lambda directly.
    bucket = _load_output_bucket()
    client = _s3_client()
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception:
        raise _http_error(404, "NotFound", "Run artifact not found.")

    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=min(OUTPUT_EXPIRES_SECONDS, 604800),
        )
    except Exception as exc:  # pragma: no cover
        raise _http_error(500, "ProcessingError", f"Failed to presign download: {exc}")

def _upload_run_artifacts(run_id: str, filled: Dict[str, Any], pdf_path: Path) -> Dict[str, str]:
    # Persist outputs to S3 so subsequent downloads rely on signed URLs instead of local disk.
    bucket = _load_output_bucket()
    client = _s3_client()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=OUTPUT_EXPIRES_SECONDS)
    tagging = f"ttl={OUTPUT_EXPIRES_SECONDS}"
    base_key = _output_key(run_id, "").rstrip("/")
    if base_key:
        base_key = f"{base_key}/"

    json_key = f"{base_key}filled_template.json"
    pdf_key = f"{base_key}cr2a_export.pdf"

    try:
        client.put_object(
            Bucket=bucket,
            Key=json_key,
            Body=json.dumps(filled, indent=2).encode("utf-8"),
            ContentType="application/json",
            Expires=expiry,
            Tagging=tagging,
        )
        client.upload_file(
            Filename=str(pdf_path),
            Bucket=bucket,
            Key=pdf_key,
            ExtraArgs={"ContentType": "application/pdf", "Expires": expiry, "Tagging": tagging},
        )
    except Exception as exc:
        raise _http_error(500, "ProcessingError", f"Failed to store outputs: {exc}")

    return {"bucket": bucket, "json_key": json_key, "pdf_key": pdf_key}

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

    bucket = _load_upload_bucket()
    if not bucket:
        # Graceful local-mode fallback so deployments without S3 can still accept uploads.
        key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{quote(os.path.basename(filename))}"
        return UploadUrlResponse(
            url="/upload-local",
            upload_method="POST",
            fields={"key": key},
            bucket="local",
            key=key,
            expires_in=UPLOAD_EXPIRES_SECONDS,
        )

    safe_name = quote(os.path.basename(filename))
    key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{safe_name}"

    client = _s3_client()
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key},
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

@app.post("/upload-local")
async def upload_local(file: UploadFile = File(...), key: str = Query(..., description="Storage key from presign")):
    # Minimal local upload handler to mirror the presign contract when S3 is unavailable.
    size = 0
    dest = RUN_OUTPUT_ROOT / "uploads" / key
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        with dest.open("wb") as fh:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
                fh.write(chunk)
    finally:
        await file.close()

    return {"location": f"file://{dest}"}

@app.post("/analysis", response_model=AnalysisResponse)
def analysis(payload: AnalysisRequestPayload):
    if not payload.contract_uri:
        raise _http_error(400, "ValidationError", "contract_uri is required to run analysis.")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    original_ext = Path(urlparse(str(payload.contract_uri)).path).suffix.lower()
    dest_name = f"input{original_ext}" if original_ext else "input.bin"

    llm_mode = "off"
    artifact_refs: Dict[str, str] = {}

    try:
        RUN_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=RUN_OUTPUT_ROOT) as tmpdir:
            run_dir = Path(tmpdir)
            input_path = run_dir / dest_name
            downloaded = _download_contract_to_path(str(payload.contract_uri), input_path)

            inferred_ext = None
            target_path = downloaded
            if not original_ext or original_ext == ".bin":
                # Fall back to MIME sniffing when the URI lacks a useful extension.
                try:
                    inferred_ext = infer_extension_from_content_type_or_magic(downloaded)
                except ValueError as exc:
                    raise _http_error(400, "ValidationError", f"Unable to determine file type: {exc}")

                if inferred_ext and downloaded.suffix.lower() != inferred_ext:
                    target_path = downloaded.with_suffix(inferred_ext)
                    downloaded = downloaded.rename(target_path)

            input_path = target_path

            try:
                mime_type = infer_mime_type(input_path)
            except ValueError:
                mime_type = "unknown"

            logger.debug(
                "Prepared analysis input",
                extra={
                    "file_name": input_path.name,
                    "original_ext": original_ext or "none",
                    "inferred_ext": inferred_ext or input_path.suffix,
                    "mime_type": mime_type,
                    "detected_via": "uri-extension" if original_ext and original_ext != ".bin" else "content-sniff",
                },
            )
            raw_json = analyze_to_json(downloaded, REPO_ROOT, ocr=os.getenv("OCR_MODE", "auto"))

            # Respect user toggle and env flag before invoking OpenAI refinement.
            llm_mode = "on" if payload.llm_enabled and _is_truthy(os.getenv("LLM_REFINEMENT", "off")) else "off"
            if llm_mode == "on":
                # Only attempt OpenAI if explicitly enabled to avoid accidental calls without keys.
                try:
                    refined = refine_cr2a(raw_json)
                except OpenAIClientError as exc:
                    # Map typed OpenAI errors onto HTTP status codes for clear client feedback.
                    status_map = {
                        "ValidationError": 400,
                        "TimeoutError": 504,
                        "NetworkError": 502,
                        "ProcessingError": 500,
                    }
                    status = status_map.get(exc.category, 500)
                    raise _http_error(status, exc.category, str(exc))

                if isinstance(refined, dict) and refined:
                    raw_json = refined

            rules = load_validation_rules(REPO_ROOT)
            val = rules.get("validation", rules)
            closing_line = val.get("mandatory_fields", {}).get(
                "section_II_to_VI_closing_line",
                "All applicable clauses for [Item #/Title] have been identified and analyzed.",
            )
            normalized = _normalize_to_schema(raw_json, closing_line, None)

            schema = _load_output_schema()
            validation = validate_filled_template(normalized, schema, rules)
            if not validation.ok:
                details = "; ".join(f"{f.code}: {f.message}" for f in validation.findings)
                raise _http_error(400, "ValidationError", details)

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

            artifact_refs = _upload_run_artifacts(run_id, normalized, export_path)

    except HTTPException:
        # Passthrough for clean HTTP errors.
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise _http_error(500, "ProcessingError", str(exc))

    completed_at = datetime.now(timezone.utc)
    manifest = {
        "contract_id": payload.contract_id,
        "contract_uri": payload.contract_uri,
        "llm_enabled": payload.llm_enabled,
        "policy_version": "schemas@v1.0",
        "ocr_mode": os.getenv("OCR_MODE", "auto"),
        "llm_refinement": llm_mode,
        "validation": {"ok": True, "findings": len(validation.findings)},
        "export": {"pdf": artifact_refs["pdf_key"], "backend": "docx"},
    }

    pdf_url = _presign_output_url(artifact_refs["pdf_key"])
    json_url = _presign_output_url(artifact_refs["json_key"])

    return AnalysisResponse(
        run_id=run_id,
        status="completed",
        completed_at=completed_at,
        manifest=manifest,
        download_url=pdf_url,
        filled_template_url=json_url,
        error=None,
    )

@app.get("/runs/{run_id}/report")
def download_report(run_id: str):
    key = _output_key(run_id, "cr2a_export.pdf")
    url = _presign_output_url(key)
    return RedirectResponse(url=url, status_code=307)

@app.get("/runs/{run_id}/filled-template")
def download_json(run_id: str):
    key = _output_key(run_id, "filled_template.json")
    url = _presign_output_url(key)
    return RedirectResponse(url=url, status_code=307)

from mangum import Asgi

handler = Asgi(app)