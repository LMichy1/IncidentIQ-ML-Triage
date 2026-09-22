"""ORM schema. One table: an incident plus the prediction/priority that was
computed for it at submission time (denormalized on purpose — a prediction
is meaningless detached from the incident it was made for)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
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

    # True once at least one FeedbackRecord exists for this incident.
    # Monotonic (never reset to False) — the authoritative review history
    # lives in `incident_feedback`, this is just a fast "has it been looked
    # at" flag for list views.
    reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    # Deprecated as of M3: superseded by IncidentRecord's associated
    # FeedbackRecord rows (see below), which preserve full review history
    # instead of a single overwritable note. Left in place, always None
    # going forward, so existing SQLite databases don't need a destructive
    # column migration.
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class FeedbackRecord(Base):
    """A single human review of an incident's prediction. Append-only —
    submitting feedback again creates a new row rather than overwriting a
    previous one, so the full review history (including disagreements
    between reviewers) is preserved. The original prediction on
    `IncidentRecord` is never modified by feedback."""

    __tablename__ = "incident_feedback"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    incident_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("incidents.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Explicitly unverified — this is an unauthenticated local demo, so any
    # reviewer-supplied name is free text, never treated as an identity.
    reviewer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # None on either of these means "reviewer confirmed the original
    # prediction/priority as-is" rather than correcting it.
    corrected_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corrected_priority: Mapped[str | None] = mapped_column(String(20), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
