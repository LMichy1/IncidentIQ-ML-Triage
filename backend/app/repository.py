"""The only module allowed to write SQLAlchemy queries. Routes call this,
never the ORM/session directly."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ml_runtime import PredictionResult
from app.models_db import IncidentRecord
from app.priority_policy import PriorityResult


def create_incident(
    session: Session,
    *,
    title: str,
    description: str,
    impact: str | None,
    urgency: str | None,
    model_name: str,
    model_version: str,
    prediction: PredictionResult,
    priority: PriorityResult,
) -> IncidentRecord:
    record = IncidentRecord(
        title=title,
        description=description,
        impact=impact,
        urgency=urgency,
        model_name=model_name,
        model_version=model_version,
        predicted_category=prediction.category,
        top_score=prediction.top_score,
        margin_to_second=prediction.margin_to_second,
        confidence_status=prediction.confidence_status,
        requires_human_review=prediction.requires_human_review,
        review_reason=prediction.review_reason,
        priority=priority.priority,
        policy_version=priority.policy_version,
        priority_basis=priority.basis,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def get_incident(session: Session, incident_id: str) -> IncidentRecord | None:
    return session.get(IncidentRecord, incident_id)


def list_incidents(
    session: Session, *, limit: int = 50, offset: int = 0
) -> tuple[list[IncidentRecord], int]:
    total = session.scalar(select(func.count()).select_from(IncidentRecord)) or 0
    stmt = (
        select(IncidentRecord)
        .order_by(IncidentRecord.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = list(session.scalars(stmt))
    return items, total
