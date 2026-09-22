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
from app.schemas import IncidentCreate, IncidentListResponse, IncidentResponse
from app.serializers import to_incident_response

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
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    records, total = repository.list_incidents(db, limit=limit, offset=offset)
    return IncidentListResponse(
        items=[to_incident_response(r) for r in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)) -> IncidentResponse:
    record = repository.get_incident(db, incident_id)
    if record is None:
        raise IncidentNotFoundError(incident_id)
    return to_incident_response(record)
