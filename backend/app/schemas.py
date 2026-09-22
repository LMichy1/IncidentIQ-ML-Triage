"""API contract. These are the source of truth for the frontend's TypeScript
types (kept in sync manually for M1/M2 — see docs/architecture.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ImpactLevel = Literal["low", "medium", "high", "critical"]
UrgencyLevel = Literal["low", "medium", "high", "critical"]


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str = Field(min_length=10, max_length=10_000)
    impact: ImpactLevel | None = None
    urgency: UrgencyLevel | None = None


class PredictionInfo(BaseModel):
    category: str
    model_name: str
    model_version: str
    top_score: float
    margin_to_second: float
    confidence_status: Literal["uncalibrated"]
    requires_human_review: bool
    review_reason: str | None


class PriorityInfo(BaseModel):
    priority: str  # "P1".."P4" or "undetermined"
    policy_version: str
    basis: str


class IncidentResponse(BaseModel):
    id: str
    created_at: datetime
    title: str
    description: str
    impact: ImpactLevel | None
    urgency: UrgencyLevel | None
    prediction: PredictionInfo
    priority: PriorityInfo
    reviewed: bool
    reviewer_note: str | None

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    error_code: str
    detail: str


class ReadinessResponse(BaseModel):
    ready: bool
    model_loaded: bool
    model_error: str | None
    model_name: str | None
    model_version: str | None
    dataset_is_synthetic: bool | None
    result_stage: str | None
