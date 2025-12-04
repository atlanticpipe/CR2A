# -*- coding: utf-8 -*-
from __future__ import annotations           # enable future typing features
from enum import Enum                        # safe, fixed enumerations
from typing import Optional, Dict, Any, List # precise type hints for fields
from datetime import datetime                # standard ISO timestamps
from pydantic import BaseModel, Field        # runtime validation and schema support
import re

# Status enums for orchestration
class SubmissionStatus(str, Enum):
    """Workflow status for a submission before or during processing."""
    queued = "queued"   # accepted, waiting to start
    started = "started" # actively running
    error = "error"     # failed before analysis began

class CompletionStatus(str, Enum):
    """Terminal status for a completed or failed analysis run."""
    completed = "completed" # succeeded with outputs
    failed = "failed"       # ended with an error

class AnalysisRequest(BaseModel):
    contract_id: str = Field(..., min_length=1, description="Internal id or filename for the contract.")
    contract_uri: Optional[AnyUrl] = Field(
        default=None,
        description="Optional URI / storage path to fetch the contract from."
    )
    fdot_contract: bool = Field(
        ...,
        description="True if the base document is an FDOT contract/spec."
    )
    assume_fdot_year: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}$",  # included for JSON Schema; validator below enforces at runtime
        description="If FDOT but year is unknown, hint the assumed spec year (YYYY)."
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Policy bundle tag (must match version_lock tag)."
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Freeform operator note (not used by the model)."
    )
    @field_validator("assume_fdot_year")
    @classmethod
    def _validate_year(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.fullmatch(r"\d{4}", v):
            raise ValueError("assume_fdot_year must be a 4-digit year (YYYY).")
        return v

class SubmissionResponse(BaseModel):
    """Response object returned when a run is queued or started."""
    run_id: str = Field(
        ...,
        description="Server-generated id for tracking the run.",
        example="run_8a23f9e1d1234"
    )
    status: SubmissionStatus = Field(
        ...,
        description="Current non-terminal state (queued|started|error)."
    )
    queued_at: datetime = Field(
        ...,
        description="ISO-8601 timestamp when the run was queued (parsed to datetime)."
    )
    @field_validator("queued_at")
    @classmethod
    def enforce_utc(cls, v: datetime) -> datetime:
        """Normalize queued_at timestamps to UTC."""
        from datetime import timezone
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

# Module export guard
__all__ = [
    "SubmissionStatus",
    "CompletionStatus",
    "AnalysisRequest",
    "SubmissionResponse",
    "AnalysisResult",
]
class AnalysisResult(BaseModel):
    run_id: str = Field(
        ...,
        min_length=1,
        description="Run identifier (matches SubmissionResponse.run_id).",
        example="run_8a23f9e1d1234",
    )
    status: CompletionStatus = Field(
        ...,
        description="Terminal state (completed|failed).",
    )
    completed_at: datetime = Field(
        ...,
        description="ISO-8601 timestamp when the run completed (parsed to datetime).",
    )
    manifest: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured record of inputs, parameters, metrics, and outputs.",
    )
    error: Optional[Dict[str, Any]] = Field(
        default=None,
        description="If failed, machine-readable error with message/trace/category.",
    )

    # ---- validators / invariants ------------------------------------------

    @field_validator("completed_at")
    @classmethod
    def _utcify(cls, v: datetime) -> datetime:
        """Normalize to UTC for consistent storage/serialization."""
        from datetime import timezone
        return v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)

    @field_validator("error")
    @classmethod
    def _error_is_dict(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """If provided, error must be a dict (helps catch accidental strings)."""
        if v is not None and not isinstance(v, dict):
            raise ValueError("error must be an object/dict when present.")
        return v

    @model_validator(mode="after")
    def _status_error_consistency(self) -> "AnalysisResult":
        """
        Enforce: failed ⇒ error present; completed ⇒ error absent.
        Keeps terminal state and payload consistent.
        """
        if self.status == CompletionStatus.failed and not self.error:
            raise ValueError("status=failed requires an error payload.")
        if self.status == CompletionStatus.completed and self.error:
            raise ValueError("status=completed must not include an error payload.")
        return self