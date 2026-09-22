from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from incidentiq_ml.data.preprocess import combine_title_description
from sqlalchemy.orm import Session

from app import repository
from app.dependencies import get_db, get_model_runtime
from app.errors import IncidentNotFoundError, ModelUnavailableError
from app.ml_runtime import ModelRuntime
from app.priority_policy import determine_priority
from app.schemas import (
    FeedbackCreate,
    FeedbackResponse,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    ReviewStatusFilter,
)
from app.serializers import to_feedback_response, to_incident_response

logger = logging.getLogger("incidentiq.incidents")

router = APIRouter(prefix="/api/v1/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
def submit_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    model: ModelRuntime = Depends(get_model_runtime),
) -> IncidentResponse:
    if not model.is_loaded:
        raise ModelUnavailableError(model.load_error or "model not loaded")

    combined_text = combine_title_description(payload.title, payload.description)
    prediction = model.predict(combined_text)
    priority = determine_priority(payload.impact, payload.urgency)

    record = repository.create_incident(
        db,
        title=payload.title,
        description=payload.description,
        impact=payload.impact,
        urgency=payload.urgency,
        model_name=model.metadata["model_name"],
        model_version=model.metadata["model_version"],
        prediction=prediction,
        priority=priority,
    )
    logger.info(
        "incident created id=%s category=%s priority=%s review=%s",
        record.id,
        prediction.category,
        priority.priority,
        prediction.requires_human_review,
    )
    return to_incident_response(record)


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    review_status: ReviewStatusFilter = Query(default="all"),
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    records, total = repository.list_incidents(
        db, limit=limit, offset=offset, review_status=review_status
    )
    return IncidentListResponse(
        items=[
            to_incident_response(r, repository.list_feedback(db, r.id)) for r in records
        ],
        total=total,
        limit=limit,
        offset=offset,
        review_status=review_status,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> IncidentResponse:
    record = repository.get_incident(db, incident_id)
    if record is None:
        raise IncidentNotFoundError(incident_id)
    return to_incident_response(record, repository.list_feedback(db, incident_id))


@router.post(
    "/{incident_id}/feedback", response_model=FeedbackResponse, status_code=201
)
def submit_feedback(
    incident_id: str,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """Records a human review. Never overwrites the original prediction or
    any prior feedback — always appends. Submitting feedback again for the
    same incident (e.g. two reviewers, or one reviewer changing their mind)
    is expected and simply adds another row to the history."""
    record = repository.get_incident(db, incident_id)
    if record is None:
        raise IncidentNotFoundError(incident_id)

    feedback = repository.create_feedback(
        db,
        incident_id=incident_id,
        reviewer_name=payload.reviewer_name,
        corrected_category=payload.corrected_category,
        corrected_priority=payload.corrected_priority,
        note=payload.note,
    )
    logger.info(
        "feedback recorded incident_id=%s feedback_id=%s corrected_category=%s corrected_priority=%s",
        incident_id,
        feedback.id,
        payload.corrected_category,
        payload.corrected_priority,
    )
    return to_feedback_response(feedback)


@router.get("/{incident_id}/feedback", response_model=list[FeedbackResponse])
def list_feedback(incident_id: str, db: Session = Depends(get_db)) -> list[FeedbackResponse]:
    record = repository.get_incident(db, incident_id)
    if record is None:
        raise IncidentNotFoundError(incident_id)
    return [to_feedback_response(f) for f in repository.list_feedback(db, incident_id)]
