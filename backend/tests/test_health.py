def test_health_always_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ready_when_model_loaded(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["model_loaded"] is True
    assert body["model_name"] == "incident_category_classifier"
    assert body["dataset_is_synthetic"] is True


def test_not_ready_when_model_missing(client_no_model):
    resp = client_no_model.get("/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["ready"] is False
    assert body["model_loaded"] is False
    assert body["model_error"]
