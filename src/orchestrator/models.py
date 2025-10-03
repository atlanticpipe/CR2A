# -*- coding: utf-8 -*-
# Every meaningful piece is commented, per your standard.

from __future__ import annotations  # ensures future-compatible typing (e.g., | for unions)
from enum import Enum               # use Enums for safe, fixed status values
from typing import Optional, Dict, Any  # precise typing for structured fields
from datetime import datetime            # strong type for timestamps (parsed by Pydantic)
from pydantic import BaseModel, Field    # runtime data validation / parsing


# -----------------------------
# Status enums for orchestration
# -----------------------------

class SubmissionStatus(str, Enum):
    """States a run can be in right after submission."""
    queued = "queued"   # accepted, waiting to start
    started = "started" # actively running
    error = "error"     # failed before analysis began


class CompletionStatus(str, Enum):
    """Terminal states for a run once finished."""
    completed = "completed"  # succeeded with outputs
    failed = "failed"        # ended with an error


# -----------------------
# Public request/response
# -----------------------

class AnalysisRequest(BaseModel):
    """
    The shape of a request to start an analysis job.
    Pydantic will validate and coerce types at runtime.
    """
    contract_id: str = Field(..., description="Internal id or filename for the contract.")
    contract_uri: Optional[str] = Field(
        default=None,
        description="Optional URI / storage path to fetch the contract from."
    )
    fdot_contract: bool = Field(
        ...,
        description="True if the base document is an FDOT contract/spec."
    )
    assume_fdot_year: Optional[str] = Field(
        default=None,
        pattern=r"^\d{4}$",  # 4-digit year, e.g., '2022'
        description="If FDOT but year is unknown, hint the assumed spec year."
    )
    policy_version: Optional[str] = Field(
        default=None,
        description="Policy bundle tag (must match version_lock tag)."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Freeform operator note (not used by the model)."
    )


class SubmissionResponse(BaseModel):
    """
    Returned immediately after a run is queued/started.
    """
    run_id: str = Field(..., description="Server-generated id for tracking the run.")
    status: SubmissionStatus = Field(
        ...,
        description="Current non-terminal state (queued|started|error)."
    )
    queued_at: datetime = Field(
        ...,
        description="ISO-8601 timestamp when the run was queued (parsed to datetime)."
    )


class AnalysisResult(BaseModel):
    """
    Returned when a run reaches a terminal state.
    """
    run_id: str = Field(..., description="Run identifier (matches SubmissionResponse.run_id).")
    status: CompletionStatus = Field(
        ...,
        description="Terminal state (completed|failed)."
    )
    completed_at: datetime = Field(
        ...,
        description="ISO-8601 timestamp when the run completed (parsed to datetime)."
    )
    manifest: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured record of inputs, parameters, metrics, and outputs."
    )
    error: Optional[Dict[str, Any]] = Field(
        default=None,
        description="If failed, machine-readable error with message/trace/category."
    )


# -------------------
# Module export guard
# -------------------

__all__ = [
    "SubmissionStatus",
    "CompletionStatus",
    "AnalysisRequest",
    "SubmissionResponse",
    "AnalysisResult",
]
