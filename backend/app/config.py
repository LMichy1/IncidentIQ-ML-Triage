"""Backend settings. Environment-overridable, no framework magic needed for
a service this small."""

import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

# The artifact this backend is pinned to. Overridable via env var so a
# deploy can pin a different trained version without a code change — but
# there is always exactly one version loaded, never "latest" resolved
# implicitly.
MODEL_NAME = os.environ.get("INCIDENTIQ_MODEL_NAME", "incident_category_classifier")
MODEL_VERSION = os.environ.get("INCIDENTIQ_MODEL_VERSION", "0.1.0")
ARTIFACT_DIR = (
    REPO_ROOT / "ml" / "artifacts" / MODEL_NAME / MODEL_VERSION
)

DATABASE_PATH = Path(
    os.environ.get("INCIDENTIQ_DB_PATH", str(BACKEND_ROOT / "incidentiq.sqlite3"))
)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Comma-separated. Defaults cover the normal frontend dev port (3000) and
# the port the Playwright e2e config runs the frontend on (3100) so the
# committed test suite works out of the box.
CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "INCIDENTIQ_CORS_ORIGINS", "http://localhost:3000,http://localhost:3100"
    ).split(",")
    if origin.strip()
]

# Heuristic, NOT a statistically validated confidence threshold — see
# app/ml_runtime.py docstring. Chosen as a conservative placeholder pending
# calibration against real or higher-fidelity data.
LOW_MARGIN_REVIEW_THRESHOLD = float(
    os.environ.get("INCIDENTIQ_REVIEW_MARGIN_THRESHOLD", "0.20")
)
