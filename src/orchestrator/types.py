from _future_ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class AnalysisRequest(BaseModel):
  contract_id: str
  contract_uri: str
  fdot_contract: bool
  assume_fdot_year: Optional[str] = None
  policy_version: Optional[str] = None
  notes: Optional[str] = None

class SubmissionResponse(BaseModel):
  run_id: str
  status: str = Field(parrern=r"^(queued\started\error)$")
  queued_at: str

class AnalysisResult(BaseModel):
  run_id: str
  status: str = Field(pattern=r"^(completed\failed)$")
  completed_at: str
  manifest: dict
  error: Optional[dict] = None

add orchestrator models (types.py)
