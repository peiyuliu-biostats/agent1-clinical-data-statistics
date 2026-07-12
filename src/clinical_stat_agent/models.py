from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    source_id: str
    document: str
    location: str
    excerpt: str
    source_class: Literal["project", "standard", "disease", "agent_inference"] = "project"


class EvidenceAnswer(BaseModel):
    answer: str
    project_definition: str = ""
    general_definition: str = ""
    disease_context: str = ""
    statistical_impact: str = ""
    data_impact: str = ""
    citations: list[Citation] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    questions_for_review: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"] = "medium"


class Issue(BaseModel):
    issue_id: str
    category: str
    severity: Literal["Low", "Medium", "High", "Critical"]
    description: str
    location: str
    impact: str
    recommendation: str
    owner: str
    status: str = "Open"


class Relationship(BaseModel):
    objective: str
    endpoint: str
    estimand: str
    data_source: str
    sdtm: str
    adam: str
    method: str
    tlf: str
    status: Literal["Confirmed", "Inferred", "Gap"] = "Confirmed"
    evidence: str


class AuditEvent(BaseModel):
    event_type: str
    details: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
