from __future__ import annotations

import json
import os
import tempfile
import uuid
import logging
import boto3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

# Core business logic
from src.core.analyzer import analyze_to_json
from src.core.validator import validate_filled_template

# Services
from src.services.openai_client import OpenAIClientError, refine_cr2a
from src.services.pdf_export import export_pdf_from_filled_json
from src.services.storage import (
    get_s3_client,
    load_upload_bucket,
    load_output_bucket,
    build_output_key,
    build_s3_uri,
    download_from_s3,
    upload_artifacts,
    generate_download_url,
    generate_upload_url,
    MAX_FILE_MB,
    MAX_FILE_BYTES,
    UPLOAD_EXPIRES_SECONDS,
    UPLOAD_PREFIX,
    OUTPUT_BUCKET,
    OUTPUT_PREFIX,
    OUTPUT_EXPIRES_SECONDS,
    AWS_REGION,
)

# Schema management
from src.schemas.policy_loader import load_validation_rules, load_output_schema
from src.schemas.normalizer import normalize_to_schema
from src.schemas.template_spec import CR2A_TEMPLATE_SPEC

# Utils
from src.utils.mime_utils import infer_extension_from_content_type_or_magic, infer_mime_type

# Initialize AWS clients
s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
dynamodb = boto3.resource('dynamodb')
jobs_table = dynamodb.Table('cr2a-jobs')
stepfunctions_client = boto3.client('stepfunctions')
STEP_FUNCTIONS_ARN = 'arn:aws:states:us-east-1:143895994429:stateMachine:cr2a-contract-analysis'

# Environment config
RUN_OUTPUT_ROOT = Path(os.getenv("RUN_OUTPUT_ROOT", "/tmp/cr2a_runs")).expanduser()
REPO_ROOT = Path(__file__).resolve().parents[2]

# FastAPI app
app = FastAPI(title="CR2A API", version="0.1.0")

# CORS
allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
origins: List[str] = [o.strip() for o in allow_origins.split(",")] if allow_origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["content-type", "authorization"],
)

LOG_LEVEL = os.getenv("CR2A_LOG_LEVEL", "INFO").upper()
# Configure root logging once so API + OpenAI client emit debug traces when requested.
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("src.api.main").setLevel(LOG_LEVEL)
logging.getLogger("src.services.openai_client").setLevel(LOG_LEVEL)

logger = logging.getLogger(__name__)

# API Models
class UploadUrlResponse(BaseModel):
    uploadUrl: str
    url: str
    upload_method: str = "PUT"
    fields: Optional[dict] = None
    bucket: str
    key: str
    expires_in: int
    headers: Optional[Dict[str, str]] = None

class AnalysisRequestPayload(BaseModel):
    contract_id: str
    contract_uri: Optional[str] = None
    key: Optional[str] = None
    llm_enabled: bool = True

class AnalysisResponse(BaseModel):
    run_id: str
    status: str
    completed_at: datetime
    manifest: dict
    download_url: Optional[str] = None
    filled_template_url: Optional[str] = None
    error: Optional[dict] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    status_url: str

# Helper Functions
def _http_error(status: int, category: str, message: str) -> HTTPException:
    """Standardized error envelope for consistent API responses."""
    return HTTPException(status_code=status, detail={"category": category, "message": message})

# Endpoints
@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True, "version": app.version}

@app.get("/upload-url", response_model=UploadUrlResponse)
def upload_url(
    filename: str = Query(..., description="Original filename"),
    contentType: str = Query("application/octet-stream", description="MIME type"),
    size: int = Query(..., description="File size in bytes"),
):
    """Generate a presigned S3 upload URL."""
    if size > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size} bytes. Limit is {MAX_FILE_BYTES} bytes ({MAX_FILE_MB} MB).",
        )

    try:
        result = generate_upload_url(filename, contentType)
        return UploadUrlResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")

@app.post("/upload-local")
async def upload_local(file: UploadFile = File(...), key: str = Query(..., description="Storage key from presign")):
    """Minimal local upload handler for when S3 is unavailable."""
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

def _run_analysis(payload: AnalysisRequestPayload):
    """Main analysis orchestration logic."""
    # Resolve contract URI
    contract_uri = payload.contract_uri
    if not contract_uri and payload.key:
        bucket = load_upload_bucket()
        contract_uri = build_s3_uri(payload.key, bucket)

    if not contract_uri:
        raise _http_error(400, "ValidationError", "Provide contract_uri or upload key to run analysis.")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    original_ext = Path(urlparse(str(contract_uri)).path).suffix.lower()
    dest_name = f"input{original_ext}" if original_ext else "input.bin"

    llm_mode = "off"
    artifact_refs: Dict[str, str] = {}

    try:
        RUN_OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=RUN_OUTPUT_ROOT) as tmpdir:
            run_dir = Path(tmpdir)
            input_path = run_dir / dest_name

            # Download contract from S3
            downloaded = download_from_s3(str(contract_uri), input_path)

            # Infer file type if needed
            inferred_ext = None
            target_path = downloaded
            if not original_ext or original_ext == ".bin":
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

            # Run heuristic analysis
            raw_json = analyze_to_json(downloaded, REPO_ROOT, ocr=os.getenv("OCR_MODE", "auto"))

            # LLM refinement - always enabled when llm_enabled=True
            if payload.llm_enabled:
                llm_mode = "on"
                try:
                    refined = refine_cr2a(raw_json)
                    if isinstance(refined, dict) and refined:
                        raw_json = refined
                except OpenAIClientError as exc:
                    # Trace OpenAI failures with category/status so status mapping is visible in logs.
                    logger.exception(
                        "LLM refinement failed",
                        extra={"contract_id": payload.contract_id, "category": exc.category, "error_message": str(exc)},
                    )
                    status_map = {
                        "ValidationError": 400,
                        "TimeoutError": 504,
                        "NetworkError": 502,
                        "ProcessingError": 500,
                    }
                    status = status_map.get(exc.category, 500)
                    raise _http_error(status, exc.category, str(exc))
                except HTTPException:
                    # Bubble up FastAPI errors untouched to preserve status code.
                    raise
                except Exception as exc:
                    # Wrap unexpected errors so callers always receive a typed HTTP envelope.
                    logger.exception(
                        "Unexpected LLM refinement failure",
                        extra={"contract_id": payload.contract_id, "category": "ProcessingError", "error_message": str(exc)},
                    )
                    raise _http_error(500, "ProcessingError", f"LLM refinement failed: {exc}") from exc

            # Normalize to schema
            rules = load_validation_rules(REPO_ROOT)
            val = rules.get("validation", rules)
            closing_line = val.get("mandatory_fields", {}).get(
                "section_II_to_VI_closing_line",
                "All applicable clauses for [Item #/Title] have been identified and analyzed.",
            )
            normalized = normalize_to_schema(raw_json, closing_line, None)

            # Validate
            schema = load_output_schema(REPO_ROOT)
            validation = validate_filled_template(normalized, schema, rules)
            if not validation.ok:
                details = "; ".join(f"{f.code}: {f.message}" for f in validation.findings)
                raise _http_error(400, "ValidationError", details)

            # Save filled template
            filled_path = run_dir / "filled_template.json"
            filled_path.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

            # Export PDF
            output_pdf = run_dir / "cr2a_export.pdf"
            export_path = export_pdf_from_filled_json(
                normalized,
                output_pdf,
                backend="reportlab",
                template_docx=REPO_ROOT / "templates" / "CR2A_Template.docx",
                title="Contract Risk & Compliance Analysis",
            )

            # Upload artifacts to S3
            artifact_refs = upload_artifacts(run_id, normalized, export_path)

    except HTTPException:
        raise
    except Exception as exc:
        raise _http_error(500, "ProcessingError", str(exc))

    # Build response
    completed_at = datetime.now(timezone.utc)
    manifest = {
        "contract_id": payload.contract_id,
        "contract_uri": contract_uri,
        "llm_enabled": payload.llm_enabled,
        "policy_version": "schemas@v1.0",
        "ocr_mode": os.getenv("OCR_MODE", "auto"),
        "llm_refinement": llm_mode,
        "validation": {"ok": True, "findings": len(validation.findings)},
        "export": {"pdf": artifact_refs["pdf_key"], "backend": "reportlab"},
    }

    pdf_url = generate_download_url(artifact_refs["pdf_key"])
    json_url = generate_download_url(artifact_refs["json_key"])

    return AnalysisResponse(
        run_id=run_id,
        status="completed",
        completed_at=completed_at,
        manifest=manifest,
        download_url=pdf_url,
        filled_template_url=json_url,
        error=None,
    )

@app.post("/analyze", response_model=JobResponse)
async def analyze_contract(payload: AnalysisRequestPayload):
    """
    Analyze a contract asynchronously using Step Functions.
    
    Accepts a pre-uploaded S3 key from the presigned upload workflow.
    Does NOT accept file binary uploads directly.
    
    Args:
        payload: AnalysisRequestPayload with:
            - key: S3 key of uploaded contract (from /upload-url presign)
            - contract_id: Identifier for this contract
            - llm_enabled: Whether to apply LLM refinement (default: true)
    
    Returns:
        JobResponse with job_id and status tracking URL
    """
    try:
        # Validate that we have either a key or contract_uri
        if not payload.key and not payload.contract_uri:
            raise _http_error(
                400,
                "ValidationError",
                "Provide either 'key' (from presigned upload) or 'contract_uri' (S3 URI)"
            )
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Determine S3 key: use provided key or extract from URI
        s3_key = payload.key
        if not s3_key and payload.contract_uri:
            parsed = urlparse(payload.contract_uri)
            s3_key = parsed.path.lstrip('/')
        
        # Get upload bucket name
        upload_bucket = load_upload_bucket()
        
        # Create job record in DynamoDB
        jobs_table.put_item(
            Item={
                'job_id': job_id,
                'status': 'queued',
                'progress': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'contract_id': payload.contract_id,
                'llm_enabled': payload.llm_enabled,
                's3_bucket': upload_bucket,
                's3_key': s3_key,
            }
        )
        
        # Prepare Step Functions input
        execution_input = {
            'job_id': job_id,
            'contract_id': payload.contract_id,
            's3_bucket': upload_bucket,
            's3_key': s3_key,
            'llm_enabled': payload.llm_enabled,
        }
        
        logger.info(
            "Starting contract analysis",
            extra={
                "job_id": job_id,
                "contract_id": payload.contract_id,
                "s3_key": s3_key,
                "llm_enabled": payload.llm_enabled,
            }
        )
        
        # Start Step Functions execution
        response = stepfunctions_client.start_execution(
            stateMachineArn=STEP_FUNCTIONS_ARN,
            name=f"analysis-{job_id}",
            input=json.dumps(execution_input)
        )
        
        # Update job with execution ARN
        jobs_table.update_item(
            Key={'job_id': job_id},
            UpdateExpression='SET execution_arn = :arn, #status = :status',
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':arn': response['executionArn'],
                ':status': 'processing'
            }
        )
        
        return JobResponse(
            job_id=job_id,
            status='queued',
            message='Analysis started. Use /status/{job_id} to check progress.',
            status_url=f'/status/{job_id}'
        )
        
    except _http_error as e:
        raise e
    except Exception as e:
        logger.exception("Failed to start analysis", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/status/{job_id}")
async def get_job_status(job_id: str):
    """Check the status of an analysis job"""
    try:
        response = jobs_table.get_item(Key={'job_id': job_id})
        
        if 'Item' not in response:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = response['Item']
        
        if job['status'] == 'completed' and 'result_key' in job:
            result_url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': 'cr2a-output',
                    'Key': job['result_key']
                },
                ExpiresIn=3600
            )
            job['result_url'] = result_url
        
        return job
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/runs/{run_id}/report")
def download_report(run_id: str):
    """Download analysis PDF report."""
    key = build_output_key(run_id, "cr2a_export.pdf")
    url = generate_download_url(key)
    return RedirectResponse(url=url, status_code=307)

@app.get("/runs/{run_id}/filled-template")
def download_json(run_id: str):
    """Download filled template JSON."""
    key = build_output_key(run_id, "filled_template.json")
    url = generate_download_url(key)
    return RedirectResponse(url=url, status_code=307)

# Lambda handler
from mangum import Mangum
handler = Mangum(app, lifespan="off", api_gateway_base_path="/prod")