"""Shared constants for the IncidentIQ ML pipeline.

Single source of truth for the category taxonomy, paths, and the random seed,
so generation, training, and tests can't drift apart.
"""

from pathlib import Path

RANDOM_SEED = 42

ML_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW_DIR = ML_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = ML_ROOT / "data" / "processed"
ARTIFACTS_DIR = ML_ROOT / "artifacts"

RAW_DATASET_PATH = DATA_RAW_DIR / "incidents.csv"

# Documented target taxonomy — see docs/dataset_decision.md.
CATEGORIES = [
    "authentication_access",
    "database_data_integrity",
    "api_backend_error",
    "ui_frontend",
    "performance_latency",
    "infrastructure_deployment",
    "third_party_integration",
    "security_vulnerability",
]

# Split proportions (temporal + group-aware — see data/split.py).
TRAIN_FRACTION = 0.70
VAL_FRACTION = 0.15
TEST_FRACTION = 0.15

MODEL_NAME = "incident_category_classifier"
MODEL_VERSION = "0.1.0"
