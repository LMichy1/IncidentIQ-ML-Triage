import json
from datetime import datetime, timedelta

import joblib
import pandas as pd
import pytest

from incidentiq_ml.data.preprocess import combine_title_description
from incidentiq_ml.models import train as train_module


def _separable_dataset(n_per_class: int = 120) -> pd.DataFrame:
    """Small dataset with an obvious lexical signal per class, so a real
    classifier should clearly beat the DummyClassifier baseline — this is a
    pipeline smoke test, not a claim about real-world performance."""
    class_words = {"cat_fruit": "apple", "cat_animal": "elephant", "cat_color": "crimson"}
    rows = []
    incident_id = 0
    start = datetime(2025, 1, 1)
    # Interleave classes across time (round-robin by `i`) rather than
    # blocking each class into its own time range — a temporal split must
    # see every class in train/val/test, not just whichever class happens
    # to occupy the earliest/latest timestamps.
    for i in range(n_per_class):
        for category, word in class_words.items():
            title = f"{word} report number {i}"
            description = f"This incident concerns {word} and related systems, instance {i}."
            rows.append(
                {
                    "incident_id": incident_id,
                    "dup_group_id": incident_id,
                    "reporter_id": f"user_{i % 10}",
                    "created_at": (start + timedelta(hours=incident_id)).isoformat(),
                    "title": title,
                    "description": description,
                    "category": category,
                }
            )
            incident_id += 1
    df = pd.DataFrame(rows)
    df["combined_text"] = df.apply(
        lambda r: combine_title_description(r["title"], r["description"]), axis=1
    )
    return df


def test_train_and_compare_runs_all_candidates_and_picks_a_winner():
    df = _separable_dataset()
    comparison = train_module.train_and_compare(df)

    assert set(comparison["val_results"].keys()) == set(train_module.CANDIDATES.keys())
    assert comparison["best_model"] in train_module.CANDIDATES
    assert 0.0 <= comparison["test_metrics"]["macro_f1"] <= 1.0


def test_logistic_regression_beats_dummy_baseline_on_separable_data():
    df = _separable_dataset()
    comparison = train_module.train_and_compare(df)

    dummy_f1 = comparison["val_results"]["dummy_stratified"]["macro_f1"]
    lr_f1 = comparison["val_results"]["tfidf_logistic_regression"]["macro_f1"]
    assert lr_f1 > dummy_f1


def test_export_artifact_round_trips_predictions(tmp_path, monkeypatch):
    monkeypatch.setattr(train_module, "ARTIFACTS_DIR", tmp_path)
    df = _separable_dataset()
    comparison = train_module.train_and_compare(df)

    version_dir = train_module.export_artifact(comparison)

    model_path = version_dir / "model.joblib"
    metadata_path = version_dir / "metadata.json"
    assert model_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text())
    for key in ("model_name", "model_version", "algorithm", "class_labels", "artifact_sha256", "limitations"):
        assert key in metadata
    assert metadata["dataset"]["is_synthetic"] is True

    reloaded = joblib.load(model_path)
    sample_text = combine_title_description("apple report number 999", "concerns apple")
    original_pred = comparison["best_pipeline"].predict([sample_text])
    reloaded_pred = reloaded.predict([sample_text])
    assert list(original_pred) == list(reloaded_pred)


def test_train_and_compare_raises_if_a_category_is_missing_from_train():
    start = datetime(2025, 1, 1)
    rows = []
    for i in range(120):
        rows.append(
            {
                "incident_id": i,
                "dup_group_id": i,
                "created_at": (start + timedelta(hours=i)).isoformat(),
                "title": "apple report" if i % 2 == 0 else "elephant report",
                "description": "apple" if i % 2 == 0 else "elephant",
                "category": "cat_fruit" if i % 2 == 0 else "cat_animal",
            }
        )
    # A single occurrence of a third category, timestamped far after every
    # other row, so it can only ever land in the test split.
    rows.append(
        {
            "incident_id": 120,
            "dup_group_id": 120,
            "created_at": (start + timedelta(days=365)).isoformat(),
            "title": "crimson report",
            "description": "crimson",
            "category": "cat_color",
        }
    )
    df = pd.DataFrame(rows)
    df["combined_text"] = df.apply(
        lambda r: combine_title_description(r["title"], r["description"]), axis=1
    )

    with pytest.raises(ValueError):
        train_module.train_and_compare(df)
