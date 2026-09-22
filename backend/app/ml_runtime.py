"""Explicit, validated loading of the trained model artifact.

This is the ONLY place the backend touches the model. It never trains,
retrains, or downloads anything — it loads exactly one pinned version
(app.config.MODEL_NAME/MODEL_VERSION) and refuses to serve inference if
that artifact is missing, corrupted, or structurally incompatible.

Confidence/uncertainty policy (see docs/dataset_decision.md and the
artifact's own metadata["limitations"]): the underlying model has not been
calibrated. We surface the raw top-class probability and the margin to the
second-ranked class, but ALWAYS labeled `confidence_status="uncalibrated"` —
never as a validated confidence score. Human-review gating uses a heuristic
margin threshold (LOW_MARGIN_REVIEW_THRESHOLD) that is explicitly documented
as a conservative placeholder, not a statistically derived cutoff.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib

from app.config import ARTIFACT_DIR, LOW_MARGIN_REVIEW_THRESHOLD

logger = logging.getLogger("incidentiq.ml_runtime")

REQUIRED_METADATA_KEYS = {
    "model_name",
    "model_version",
    "algorithm",
    "class_labels",
    "artifact_sha256",
    "dataset",
    "evaluation",
    "limitations",
}


class ArtifactLoadError(Exception):
    """Raised when the pinned model artifact can't be loaded or trusted."""


@dataclass
class PredictionResult:
    category: str
    top_score: float
    margin_to_second: float
    confidence_status: str  # always "uncalibrated" until real calibration exists
    requires_human_review: bool
    review_reason: str | None


class ModelRuntime:
    """Loaded once at startup; read-only for the lifetime of the process."""

    def __init__(self, artifact_dir: Path = ARTIFACT_DIR):
        self.artifact_dir = artifact_dir
        self.pipeline: Any = None
        self.metadata: dict[str, Any] = {}
        self._loaded = False
        self._load_error: str | None = None

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> str | None:
        return self._load_error

    def load(self) -> None:
        try:
            self._load()
            self._loaded = True
            self._load_error = None
            logger.info(
                "Loaded model artifact %s v%s (%s)",
                self.metadata["model_name"],
                self.metadata["model_version"],
                self.metadata["algorithm"],
            )
        except ArtifactLoadError as e:
            self._loaded = False
            self._load_error = str(e)
            logger.error("Failed to load model artifact: %s", e)

    def _load(self) -> None:
        metadata_path = self.artifact_dir / "metadata.json"
        model_path = self.artifact_dir / "model.joblib"

        if not metadata_path.exists():
            raise ArtifactLoadError(f"metadata.json not found at {metadata_path}")
        if not model_path.exists():
            raise ArtifactLoadError(f"model.joblib not found at {model_path}")

        try:
            metadata = json.loads(metadata_path.read_text())
        except json.JSONDecodeError as e:
            raise ArtifactLoadError(f"metadata.json is not valid JSON: {e}") from e

        missing = REQUIRED_METADATA_KEYS - set(metadata)
        if missing:
            raise ArtifactLoadError(f"metadata.json missing required keys: {missing}")

        expected_hash = metadata["artifact_sha256"]
        actual_hash = _sha256_of_file(model_path)
        if actual_hash != expected_hash:
            raise ArtifactLoadError(
                f"model.joblib content hash mismatch (expected {expected_hash}, "
                f"got {actual_hash}) — artifact may be corrupted or tampered with"
            )

        if not metadata["class_labels"]:
            raise ArtifactLoadError("metadata.json class_labels is empty")

        try:
            pipeline = joblib.load(model_path)
        except Exception as e:  # joblib/pickle can raise many exception types
            raise ArtifactLoadError(f"failed to deserialize model.joblib: {e}") from e

        if not hasattr(pipeline, "predict") or not hasattr(pipeline, "predict_proba"):
            raise ArtifactLoadError(
                "loaded artifact does not expose predict/predict_proba"
            )

        self.pipeline = pipeline
        self.metadata = metadata

    def predict(self, combined_text: str) -> PredictionResult:
        if not self.is_loaded:
            raise ArtifactLoadError("model not loaded — cannot run inference")

        proba = self.pipeline.predict_proba([combined_text])[0]
        labels = self.pipeline.classes_
        ranked = sorted(zip(labels, proba), key=lambda pair: pair[1], reverse=True)

        top_label, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = float(top_score - second_score)

        low_margin = margin < LOW_MARGIN_REVIEW_THRESHOLD
        requires_review = low_margin
        reason = None
        if low_margin:
            reason = (
                f"Top two categories are close (margin={margin:.3f} < "
                f"{LOW_MARGIN_REVIEW_THRESHOLD} heuristic threshold, not a "
                "validated confidence cutoff) — flagged for human review."
            )

        return PredictionResult(
            category=str(top_label),
            top_score=float(top_score),
            margin_to_second=margin,
            confidence_status="uncalibrated",
            requires_human_review=requires_review,
            review_reason=reason,
        )


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
