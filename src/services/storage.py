"""
S3 storage operations for contract uploads and analysis outputs.
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse, unquote
from fastapi import HTTPException

try:
    import boto3
except Exception:  # pragma: no cover
    boto3 = None  # type: ignore

logger = logging.getLogger(__name__)

# Configuration
MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))
MAX_FILE_BYTES = int(MAX_FILE_MB * 1024 * 1024)
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))
UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "upload/")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "cr2a-output")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "runs/")
OUTPUT_EXPIRES_SECONDS = int(os.getenv("OUTPUT_EXPIRES_SECONDS", "86400"))
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "cr2a-upload")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

# AWS bucket name validation pattern
_VALID_BUCKET = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{1,61}[a-z0-9])$")

# Initialize S3 client
S3 = boto3.client("s3", region_name=AWS_REGION) if boto3 else None

def _http_error(status: int, category: str, message: str) -> HTTPException:
    """Standardized error envelope so the UI can surface actionable messages."""
    return HTTPException(status_code=status, detail={"category": category, "message": message})

def get_s3_client():
    """Get the S3 client, raising an error if boto3 is not available."""
    if S3 is None:
        raise _http_error(500, "ConfigError", "boto3 not installed; S3 operations unavailable.")
    return S3

def is_valid_s3_bucket(name: str) -> bool:
    """
    Enforce AWS-safe bucket names to avoid runtime presign failures.
    AWS S3 bucket naming rules:
    - Must be 3-63 characters long
    - Can contain only lowercase letters, numbers, hyphens, and periods
    - Must start and end with a letter or number
    - Cannot be formatted as an IP address
    - Cannot contain consecutive periods or period-hyphen/hyphen-period combinations
    """
    if any(ch.isupper() for ch in name) or "_" in name:
        # AWS rejects uppercase and underscore characters
        return False
    if not _VALID_BUCKET.fullmatch(name):
        return False
    if ".." in name or ".-" in name or "-." in name:
        return False
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", name):
        # Reject IP address format
        return False
    return True

def load_upload_bucket() -> str:
    """Get and validate the upload bucket name."""
    bucket = UPLOAD_BUCKET or "cr2a-upload"
    if not is_valid_s3_bucket(bucket):
        raise _http_error(
            500,
            "ValidationError",
            f"Invalid S3 upload bucket '{bucket}'. Expected lowercase DNS-compatible name.",
        )
    return bucket

def load_output_bucket() -> str:
    """Get and validate the output bucket name."""
    bucket = (OUTPUT_BUCKET or "").strip()
    if not bucket:
        raise _http_error(500, "ConfigError", "OUTPUT_BUCKET is required for result downloads.")
    if not is_valid_s3_bucket(bucket):
        raise _http_error(500, "ValidationError", "Invalid S3 bucket for outputs; expected DNS-compatible name.")
    return bucket

def build_output_key(run_id: str, filename: str) -> str:
    """
    Build a predictable S3 key path while preventing path traversal and unsafe characters.
    Args:
        run_id: Run identifier (must be alphanumeric with ._- only)
        filename: Output filename
    Returns:
        S3 key path
    """
    if not re.fullmatch(r"[A-Za-z0-9._-]+", run_id):
        raise _http_error(400, "ValidationError", "Invalid run_id format.")
    prefix = OUTPUT_PREFIX.strip("/")
    parts = [part for part in (prefix, run_id, filename) if part]
    return "/".join(parts)

def resolve_s3_key_from_uri(contract_uri: str) -> str:
    """
    Validate the contract URI and extract the S3 object key.
    Supports both virtual-hosted-style and path-style S3 URLs:
    - https://bucket.s3.amazonaws.com/key
    - https://bucket.s3.region.amazonaws.com/key  
    - https://s3.region.amazonaws.com/bucket/key
    Args:
        contract_uri: S3 URI to parse
    Returns:
        S3 object key
    Raises:
        HTTPException: If URI is invalid or doesn't match expected bucket
    """
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
        # Path-style URL: extract bucket and key from path
        parts = path.split("/", 1)
        if len(parts) < 2:
            raise _http_error(400, "ValidationError", "contract_uri path missing bucket/key segments.")
        bucket_in_path, key = parts[0], parts[1]
        if bucket_in_path != UPLOAD_BUCKET:
            raise _http_error(400, "ConfigError", f"Unexpected bucket in contract_uri path: {bucket_in_path}")
    else:
        # Virtual-hosted-style URL: path is the key
        key = path

    if not key:
        raise _http_error(400, "ValidationError", "contract_uri path is missing an object key.")
    return key

def build_s3_uri(key: str, bucket: str) -> str:
    """
    Build a consistent S3 HTTPS URI from an object key.
    Args:
        key: S3 object key
        bucket: S3 bucket name
    Returns:
        Virtual-hosted-style S3 HTTPS URI
    """
    safe_key = quote(key)
    return f"https://{bucket}.s3.{AWS_REGION}.amazonaws.com/{safe_key}"

def download_from_s3(contract_uri: str, dest_path: Path) -> Path:
    """
    Stream a contract from S3 to disk to avoid double-buffering in memory.
    Args:
        contract_uri: S3 URI to download from
        dest_path: Local path to save the file
    Returns:
        Path to downloaded file
    Raises:
        HTTPException: If download fails or file exceeds size limit
    """
    key = resolve_s3_key_from_uri(contract_uri)
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
            chunk = body.read(1024 * 1024)  # Read in 1MB chunks
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_FILE_BYTES:
                raise _http_error(400, "ValidationError", f"File exceeds limit of {MAX_FILE_MB} MB")
            fh.write(chunk)

    body.close()
    return dest_path

def upload_artifacts(run_id: str, filled: Dict[str, Any], pdf_path: Path) -> Dict[str, str]:
    """
    Persist analysis outputs to S3 for download via presigned URLs.
    Args:
        run_id: Run identifier
        filled: Filled template JSON data
        pdf_path: Path to generated PDF
    Returns:
        Dict with 'bucket', 'json_key', 'pdf_key'
    Raises:
        HTTPException: If upload fails
    """
    bucket = load_output_bucket()
    client = get_s3_client()
    expiry = datetime.now(timezone.utc) + timedelta(seconds=OUTPUT_EXPIRES_SECONDS)
    tagging = f"ttl={OUTPUT_EXPIRES_SECONDS}"
    
    base_key = build_output_key(run_id, "").rstrip("/")
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

def generate_download_url(key: str) -> str:
    """
    Generate a short-lived presigned download URL for an S3 object.
    Args:
        key: S3 object key
    Returns:
        Presigned download URL
    Raises:
        HTTPException: If object doesn't exist or presigning fails
    """
    bucket = load_output_bucket()
    client = get_s3_client()
    
    # Verify object exists
    try:
        client.head_object(Bucket=bucket, Key=key)
    except Exception:
        raise _http_error(404, "NotFound", "Run artifact not found.")

    # Generate presigned URL
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=min(OUTPUT_EXPIRES_SECONDS, 604800),  # Max 7 days
        )
    except Exception as exc:  # pragma: no cover
        raise _http_error(500, "ProcessingError", f"Failed to presign download: {exc}")

def generate_upload_url(filename: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
    """
    Generate a presigned upload URL for direct client-to-S3 uploads.
    Args:
        filename: Original filename
        content_type: MIME type
    Returns:
        Dict with upload URL and metadata
    Raises:
        HTTPException: If presigning fails
    """
    import uuid
    from urllib.parse import quote
    
    bucket = load_upload_bucket()
    client = get_s3_client()
    
    safe_name = quote(os.path.basename(filename))
    key = f"{UPLOAD_PREFIX}{uuid.uuid4()}_{safe_name}"
    
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=UPLOAD_EXPIRES_SECONDS,
        )
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"Presign failed: {e}")

    return {
        "uploadUrl": url,
        "url": url,
        "bucket": bucket,
        "key": key,
        "expires_in": UPLOAD_EXPIRES_SECONDS,
        "headers": {"Content-Type": content_type},
    }