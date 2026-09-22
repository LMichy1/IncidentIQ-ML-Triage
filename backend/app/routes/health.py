from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.dependencies import get_model_runtime
from app.ml_runtime import ModelRuntime
from app.schemas import ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Liveness only — the process is up. Does not imply the model is
    loaded; use /ready for that."""
    return {"status": "ok"}


@router.get("/ready", response_model=ReadinessResponse)
def ready(
    response: Response, model: ModelRuntime = Depends(get_model_runtime)
) -> ReadinessResponse:
    if not model.is_loaded:
        response.status_code = 503
        return ReadinessResponse(
            ready=False,
            model_loaded=False,
            model_error=model.load_error,
            model_name=None,
            model_version=None,
            dataset_is_synthetic=None,
            result_stage=None,
        )

    dataset_meta = model.metadata.get("dataset", {})
    evaluation_meta = model.metadata.get("evaluation", {})
    return ReadinessResponse(
        ready=True,
        model_loaded=True,
        model_error=None,
        model_name=model.metadata["model_name"],
        model_version=model.metadata["model_version"],
        dataset_is_synthetic=dataset_meta.get("is_synthetic"),
        result_stage=evaluation_meta.get("result_stage"),
    )
