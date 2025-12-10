from __future__ import annotations

import json
import os
from typing import Any, Dict

# Static headers for JSON responses; API Gateway passes them through to callers.
_DEFAULT_HEADERS = {"content-type": "application/json"}

# Environment-driven limits so Amplify can tune behavior per environment.
UPLOAD_BUCKET = os.getenv("UPLOAD_BUCKET", "")
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
MAX_FILE_MB = float(os.getenv("MAX_FILE_MB", "500"))
UPLOAD_EXPIRES_SECONDS = int(os.getenv("UPLOAD_EXPIRES_SECONDS", "3600"))
MAX_ANALYSIS_SECONDS = int(os.getenv("MAX_ANALYSIS_SECONDS", "900"))


def _response(status: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Shape responses consistently for API Gateway."""
    return {"statusCode": status, "headers": _DEFAULT_HEADERS, "body": json.dumps(payload)}


def _normalize_path(raw_path: str | None) -> str:
    """Collapse blank or trailing slash paths so routing stays predictable."""
    path = (raw_path or "/").strip()
    return "/" if path in {"", "/"} else path.rstrip("/")


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    """Handle lightweight health and placeholder analysis routes."""
    path = _normalize_path(event.get("rawPath") or event.get("path"))
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    ).upper()

    if path == "/health" and method == "GET":
        # Simple status endpoint Amplify can use for monitoring.
        return _response(
            200,
            {
                "status": "ok",
                "region": AWS_REGION,
                "upload_bucket": UPLOAD_BUCKET,
                "output_bucket": OUTPUT_BUCKET,
            },
        )

    if path == "/analysis" and method == "POST":
        # Placeholder until the orchestrator is wired into Lambda.
        return _response(
            202,
            {
                "status": "accepted",
                "message": "Analysis Lambda stub is wired; connect orchestrator logic here.",
                "limits": {
                    "max_file_mb": MAX_FILE_MB,
                    "upload_expires_seconds": UPLOAD_EXPIRES_SECONDS,
                    "max_runtime_seconds": MAX_ANALYSIS_SECONDS,
                },
            },
        )

    # Fall back to a structured error so callers get actionable feedback.
    return _response(
        404,
        {"category": "ValidationError", "message": f"No route for {method} {path}"},
    )
