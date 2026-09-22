import hashlib
import json

import joblib
import pytest
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline

from app.config import ARTIFACT_DIR
from app.ml_runtime import ModelRuntime


def _valid_metadata(sha256: str) -> dict:
    return {
        "model_name": "test_model",
        "model_version": "0.0.1",
        "algorithm": "dummy",
        "class_labels": ["a", "b"],
        "artifact_sha256": sha256,
        "dataset": {"is_synthetic": True},
        "evaluation": {"result_stage": "development"},
        "limitations": ["test artifact, not a real model"],
    }


def _write_fake_artifact(tmp_path, pipeline, metadata_overrides=None):
    model_path = tmp_path / "model.joblib"
    joblib.dump(pipeline, model_path)
    sha256 = hashlib.sha256(model_path.read_bytes()).hexdigest()
    metadata = _valid_metadata(sha256)
    if metadata_overrides:
        metadata.update(metadata_overrides)
    (tmp_path / "metadata.json").write_text(json.dumps(metadata))
    return tmp_path


def _fitted_dummy_pipeline():
    pipeline = Pipeline([("tfidf", TfidfVectorizer()), ("clf", DummyClassifier(strategy="most_frequent"))])
    pipeline.fit(["hello world", "goodbye world"], ["a", "b"])
    return pipeline


def test_loads_the_real_m1_artifact():
    runtime = ModelRuntime(artifact_dir=ARTIFACT_DIR)
    runtime.load()
    assert runtime.is_loaded, runtime.load_error
    assert runtime.metadata["model_name"] == "incident_category_classifier"
    assert len(runtime.metadata["class_labels"]) == 8


def test_real_artifact_predict_returns_a_known_label():
    runtime = ModelRuntime(artifact_dir=ARTIFACT_DIR)
    runtime.load()
    result = runtime.predict("login fails with a 401 error on the auth service")
    assert result.category in runtime.metadata["class_labels"]
    assert result.confidence_status == "uncalibrated"
    assert 0.0 <= result.top_score <= 1.0


def test_missing_directory_fails_gracefully(tmp_path):
    runtime = ModelRuntime(artifact_dir=tmp_path / "does_not_exist")
    runtime.load()
    assert not runtime.is_loaded
    assert "metadata.json not found" in runtime.load_error


def test_missing_required_metadata_key_fails(tmp_path):
    artifact_dir = _write_fake_artifact(tmp_path, _fitted_dummy_pipeline())
    metadata = json.loads((artifact_dir / "metadata.json").read_text())
    del metadata["class_labels"]
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata))

    runtime = ModelRuntime(artifact_dir=artifact_dir)
    runtime.load()
    assert not runtime.is_loaded
    assert "missing required keys" in runtime.load_error


def test_corrupted_model_file_hash_mismatch_is_rejected(tmp_path):
    artifact_dir = _write_fake_artifact(tmp_path, _fitted_dummy_pipeline())
    # Tamper with the model file after the hash was recorded.
    with (artifact_dir / "model.joblib").open("ab") as f:
        f.write(b"corruption")

    runtime = ModelRuntime(artifact_dir=artifact_dir)
    runtime.load()
    assert not runtime.is_loaded
    assert "hash mismatch" in runtime.load_error


def test_invalid_json_metadata_fails(tmp_path):
    model_path = tmp_path / "model.joblib"
    joblib.dump(_fitted_dummy_pipeline(), model_path)
    (tmp_path / "metadata.json").write_text("{not valid json")

    runtime = ModelRuntime(artifact_dir=tmp_path)
    runtime.load()
    assert not runtime.is_loaded
    assert "not valid JSON" in runtime.load_error


def test_predict_before_load_raises():
    runtime = ModelRuntime(artifact_dir=ARTIFACT_DIR)
    with pytest.raises(Exception):
        runtime.predict("some text")
