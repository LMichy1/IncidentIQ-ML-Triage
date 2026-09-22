"""API contract. These are the source of truth for the frontend's TypeScript
types (kept in sync manually for M1/M2 — see docs/architecture.md)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from incidentiq_ml.config import CATEGORIES
from pydantic import BaseModel, Field, field_validator

from app.priority_policy import VALID_PRIORITY_VALUES

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


class FeedbackCreate(BaseModel):
    """None on corrected_category/corrected_priority means the reviewer is
    confirming the original prediction/priority, not correcting it.
    reviewer_name is free text and explicitly unverified — this is an
    unauthenticated local demo, not an identity system."""

    reviewer_name: str | None = Field(default=None, max_length=200)
    corrected_category: str | None = None
    corrected_priority: str | None = None
    note: str | None = Field(default=None, max_length=2_000)

    @field_validator("corrected_category")
    @classmethod
    def _validate_category(cls, v: str | None) -> str | None:
        if v is not None and v not in CATEGORIES:
            raise ValueError(f"corrected_category must be one of {sorted(CATEGORIES)} or omitted")
        return v

    @field_validator("corrected_priority")
    @classmethod
    def _validate_priority(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_PRIORITY_VALUES:
            raise ValueError(
                f"corrected_priority must be one of {sorted(VALID_PRIORITY_VALUES)} or omitted"
            )
        return v


class FeedbackResponse(BaseModel):
    id: str
    incident_id: str
    created_at: datetime
    reviewer_name: str | None
    corrected_category: str | None
    corrected_priority: str | None
    note: str | None

    model_config = {"from_attributes": True}


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
    feedback: list[FeedbackResponse]

    model_config = {"from_attributes": True}


ReviewStatusFilter = Literal["all", "pending_review", "reviewed"]


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    limit: int
    offset: int
    review_status: ReviewStatusFilter


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
