"""ORM schema. One table: an incident plus the prediction/priority that was
computed for it at submission time (denormalized on purpose — a prediction
is meaningless detached from the incident it was made for)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(String(20), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Prediction
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str] = mapped_column(String(50))
    predicted_category: Mapped[str] = mapped_column(String(100))
    top_score: Mapped[float] = mapped_column(Float)
    margin_to_second: Mapped[float] = mapped_column(Float)
    confidence_status: Mapped[str] = mapped_column(String(30))
    requires_human_review: Mapped[bool] = mapped_column(Boolean)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Priority (advisory)
    priority: Mapped[str] = mapped_column(String(20))
    policy_version: Mapped[str] = mapped_column(String(50))
    priority_basis: Mapped[str] = mapped_column(Text)

    # Human review, populated later (full feedback workflow is M3)
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
