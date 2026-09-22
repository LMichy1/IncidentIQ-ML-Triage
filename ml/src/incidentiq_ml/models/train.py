"""Training pipeline: load -> preprocess -> split -> compare baselines ->
evaluate -> export a versioned artifact.

Design choices (see docs/architecture.md and docs/dataset_decision.md):
  - All learned preprocessing (TfidfVectorizer, LabelEncoder) is fit on the
    train split only.
  - Validation is used to pick a winner among candidates; test is scored
    exactly once, after the winner is already chosen, and never touched
    again.
  - No calibration is performed. Predicted probabilities from
    MultinomialNB/LogisticRegression are NOT presented as calibrated
    confidence — see the "pending" note in the exported metadata.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from incidentiq_ml.config import (
    ARTIFACTS_DIR,
    MODEL_NAME,
    MODEL_VERSION,
    RANDOM_SEED,
    RAW_DATASET_PATH,
)
from incidentiq_ml.data.dedup_audit import find_exact_duplicates, find_near_duplicate_pairs
from incidentiq_ml.data.preprocess import combine_title_description
from incidentiq_ml.data.split import split_dataset
from incidentiq_ml.models.evaluate import compute_metrics, summarize_for_log

CANDIDATES: dict[str, Any] = {
    "dummy_stratified": lambda: DummyClassifier(strategy="stratified", random_state=RANDOM_SEED),
    "tfidf_naive_bayes": lambda: MultinomialNB(),
    "tfidf_logistic_regression": lambda: LogisticRegression(
        max_iter=1000, random_state=RANDOM_SEED
    ),
}


def load_raw(path: Path = RAW_DATASET_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"No dataset at {path}. Run scripts/generate_dataset.py first."
        )
    df = pd.read_csv(path)
    df["combined_text"] = df.apply(
        lambda r: combine_title_description(r["title"], r["description"]), axis=1
    )
    return df


def run_dedup_audit(df: pd.DataFrame) -> dict[str, Any]:
    """Duplicate/near-duplicate audit over the full raw dataset (before
    splitting). Informational — dedup does not itself drop rows here, since
    `split_dataset` already keeps near-duplicate groups together to prevent
    leakage. See docs/dataset_decision.md for the threshold-tuning finding."""
    exact = find_exact_duplicates(df)
    try:
        near_pairs = find_near_duplicate_pairs(df)
    except ValueError as e:
        # Dataset too large for the O(n^2) scan — report and move on rather
        # than blocking the whole training run.
        return {"exact_duplicate_rows": int(len(exact)), "near_duplicate_pairs": None, "note": str(e)}
    return {
        "exact_duplicate_rows": int(len(exact)),
        "near_duplicate_pairs": len(near_pairs),
        "near_duplicate_threshold": 0.95,
    }


def _build_pipeline(classifier) -> Pipeline:
    return Pipeline(
        [
            ("tfidf", TfidfVectorizer(min_df=2, max_df=0.9, ngram_range=(1, 2))),
            ("clf", classifier),
        ]
    )


def train_and_compare(df: pd.DataFrame) -> dict[str, Any]:
    train_df, val_df, test_df = split_dataset(df)

    label_encoder = LabelEncoder()
    label_encoder.fit(train_df["category"])
    labels = list(label_encoder.classes_)

    missing_from_train = set(df["category"]) - set(labels)
    if missing_from_train:
        raise ValueError(
            f"Categories present in the full dataset but absent from the "
            f"train split: {missing_from_train}. Split fractions or category "
            f"weights need adjusting."
        )

    results: dict[str, Any] = {}
    fitted_pipelines: dict[str, Pipeline] = {}

    for name, make_classifier in CANDIDATES.items():
        # DummyClassifier ignores X's content but still needs a vectorizer
        # in the pipeline so fit/predict shapes line up identically across
        # candidates for a fair, uniform comparison harness.
        pipeline = _build_pipeline(make_classifier())
        pipeline.fit(train_df["combined_text"], train_df["category"])
        val_pred = pipeline.predict(val_df["combined_text"])
        metrics = compute_metrics(val_df["category"], val_pred, labels)
        results[name] = metrics
        fitted_pipelines[name] = pipeline

    best_name = max(results, key=lambda n: results[n]["macro_f1"])
    best_pipeline = fitted_pipelines[best_name]
    test_pred = best_pipeline.predict(test_df["combined_text"])
    test_metrics = compute_metrics(test_df["category"], test_pred, labels)

    return {
        "labels": labels,
        "val_results": results,
        "best_model": best_name,
        "best_pipeline": best_pipeline,
        "test_metrics": test_metrics,
        "split_sizes": {
            "train": len(train_df),
            "val": len(val_df),
            "test": len(test_df),
        },
    }


def _sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def export_artifact(
    comparison: dict[str, Any],
    dataset_path: Path = RAW_DATASET_PATH,
    dedup_audit: dict[str, Any] | None = None,
) -> Path:
    version_dir = ARTIFACTS_DIR / MODEL_NAME / MODEL_VERSION
    version_dir.mkdir(parents=True, exist_ok=True)

    model_path = version_dir / "model.joblib"
    joblib.dump(comparison["best_pipeline"], model_path)

    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "algorithm": comparison["best_model"],
        "trained_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "dataset": {
            "path": str(dataset_path.relative_to(dataset_path.parents[2])),
            "is_synthetic": True,
            "n_rows_total": sum(comparison["split_sizes"].values()),
            "split_sizes": comparison["split_sizes"],
            "reference": "docs/dataset_decision.md",
            "duplicate_audit": dedup_audit or {},
        },
        "class_labels": comparison["labels"],
        "evaluation": {
            "validation_macro_f1_by_candidate": {
                name: r["macro_f1"] for name, r in comparison["val_results"].items()
            },
            "selected_on": "validation macro F1",
            "test_macro_f1": comparison["test_metrics"]["macro_f1"],
            "test_per_class": comparison["test_metrics"]["per_class"],
            "result_stage": "development",
            "result_stage_note": (
                "The dataset generator was redesigned after an earlier version "
                "produced a meaningless 1.0 macro F1 on both validation AND "
                "test. Model selection here is still validation-only, but the "
                "dataset design itself was informed by a prior test score, so "
                "this test_macro_f1 is a development-stage number, not an "
                "independent frozen-holdout result. See "
                "docs/dataset_decision.md#evaluation-independence-caveat-development-stage-result."
            ),
        },
        "environment": {
            "python_version": platform.python_version(),
            "scikit_learn_version": importlib.metadata.version("scikit-learn"),
            "pandas_version": importlib.metadata.version("pandas"),
        },
        "limitations": [
            "Trained on a synthetic, templated demonstration dataset (see "
            "docs/dataset_decision.md) — evaluation metrics reflect pipeline "
            "correctness, not real-world predictive performance.",
            "No probability calibration has been performed. Predicted class "
            "probabilities from this model must NOT be presented to users as "
            "calibrated confidence scores. Confidence/abstention behavior is "
            "explicitly PENDING until validated on a suitable held-out "
            "calibration set from real or higher-fidelity data.",
            "Category taxonomy is fixed to the 8 categories in "
            "incidentiq_ml.config.CATEGORIES; inputs describing incidents "
            "outside this taxonomy will be forced into the nearest class.",
            "Priority/severity is intentionally out of scope for this model "
            "— see docs/priority_policy.md.",
        ],
    }
    metadata["artifact_sha256"] = _sha256_of_file(model_path)

    metadata_path = version_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2))

    return version_dir


def main() -> None:
    df = load_raw()
    print(f"Loaded {len(df)} rows from {RAW_DATASET_PATH}")

    dedup_audit = run_dedup_audit(df)
    print(f"\n=== Duplicate audit ===\n{dedup_audit}")

    comparison = train_and_compare(df)

    print("\n=== Validation results (candidate comparison) ===")
    for name, metrics in comparison["val_results"].items():
        print(f"\n[{name}]")
        print(summarize_for_log(metrics))

    print(f"\n=== Selected: {comparison['best_model']} ===")
    print("\n=== Held-out test results (evaluated once) ===")
    print(summarize_for_log(comparison["test_metrics"]))

    version_dir = export_artifact(comparison, dedup_audit=dedup_audit)
    print(f"\nArtifact written to {version_dir}")


if __name__ == "__main__":
    sys.exit(main() or 0)
