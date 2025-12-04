from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))
MAX_FILE_BYTES = int(MAX_FILE_MB * 1024 * 1024)
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "uploads/")

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
    error: Optional[dict] = None


def _s3_client():
    if boto3 is None:
        raise HTTPException(status_code=500, detail="boto3 not installed; cannot presign S3 upload URLs.")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    return boto3.client("s3", region_name=region)


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
    now = datetime.now(timezone.utc)
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    manifest = {
        "contract_id": payload.contract_id,
        "contract_uri": payload.contract_uri,
        "fdot_contract": payload.fdot_contract,
        "assume_fdot_year": payload.assume_fdot_year,
        "policy_version": payload.policy_version,
        "notes": payload.notes,
        "ocr_mode": os.getenv("OCR_MODE", "auto"),
        "llm_refinement": os.getenv("LLM_REFINEMENT", "off"),
    }
    return AnalysisResponse(
        run_id=run_id,
        status="completed",
        completed_at=now,
        manifest=manifest,
        error=None,
    )
