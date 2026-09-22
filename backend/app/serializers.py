"""Maps the flat ORM record to the nested API response shape."""

from __future__ import annotations

from app.models_db import FeedbackRecord, IncidentRecord
from app.schemas import FeedbackResponse, IncidentResponse, PredictionInfo, PriorityInfo


def to_feedback_response(record: FeedbackRecord) -> FeedbackResponse:
    return FeedbackResponse(
        id=record.id,
        incident_id=record.incident_id,
        created_at=record.created_at,
        reviewer_name=record.reviewer_name,
        corrected_category=record.corrected_category,
        corrected_priority=record.corrected_priority,
        note=record.note,
    )


def to_incident_response(
    record: IncidentRecord, feedback: list[FeedbackRecord] = ()
) -> IncidentResponse:
    return IncidentResponse(
        id=record.id,
        created_at=record.created_at,
        title=record.title,
        description=record.description,
        impact=record.impact,
        urgency=record.urgency,
        prediction=PredictionInfo(
            category=record.predicted_category,
            model_name=record.model_name,
            model_version=record.model_version,
            top_score=record.top_score,
            margin_to_second=record.margin_to_second,
            confidence_status=record.confidence_status,
            requires_human_review=record.requires_human_review,
            review_reason=record.review_reason,
        ),
        priority=PriorityInfo(
            priority=record.priority,
            policy_version=record.policy_version,
            basis=record.priority_basis,
        ),
        reviewed=record.reviewed,
        reviewer_note=record.reviewer_note,
        feedback=[to_feedback_response(f) for f in feedback],
    )
