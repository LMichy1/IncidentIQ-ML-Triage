VALID_PAYLOAD = {
    "title": "Login fails with a 401",
    "description": "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
    "impact": "high",
    "urgency": "high",
}


def test_submit_incident_returns_real_prediction(client):
    resp = client.post("/api/v1/incidents", json=VALID_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()

    assert body["prediction"]["category"] == "authentication_access"
    assert body["prediction"]["confidence_status"] == "uncalibrated"
    assert body["prediction"]["model_name"] == "incident_category_classifier"
    assert body["priority"]["priority"] == "P2"
    assert body["priority"]["policy_version"] == "0.1.0"
    assert body["reviewed"] is False


def test_missing_impact_urgency_yields_undetermined_priority_not_a_guess(client):
    payload = {
        "title": "Dashboard chart is blank",
        "description": "The dashboard chart renders blank on load in staging.",
    }
    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["priority"]["priority"] == "undetermined"
    assert body["impact"] is None
    assert body["urgency"] is None


def test_ambiguous_text_is_flagged_for_human_review(client):
    payload = {
        "title": "System issue reported by support",
        "description": (
            "Users report an issue affecting multiple customers, needs "
            "investigation, was flagged by monitoring."
        ),
    }
    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["prediction"]["requires_human_review"] is True
    assert body["prediction"]["review_reason"] is not None


def test_title_too_short_is_rejected(client):
    resp = client.post(
        "/api/v1/incidents", json={"title": "a", "description": "this is long enough"}
    )
    assert resp.status_code == 422


def test_description_too_short_is_rejected(client):
    resp = client.post(
        "/api/v1/incidents", json={"title": "valid title", "description": "short"}
    )
    assert resp.status_code == 422


def test_invalid_impact_value_is_rejected(client):
    payload = {**VALID_PAYLOAD, "impact": "super-critical"}
    resp = client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 422


def test_get_incident_retrieves_persisted_record(client):
    created = client.post("/api/v1/incidents", json=VALID_PAYLOAD).json()
    resp = client.get(f"/api/v1/incidents/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_unknown_incident_returns_structured_404(client):
    resp = client.get("/api/v1/incidents/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "incident_not_found"


def test_list_incidents_returns_persisted_records_newest_first(client):
    first = client.post("/api/v1/incidents", json=VALID_PAYLOAD).json()
    second = client.post(
        "/api/v1/incidents",
        json={**VALID_PAYLOAD, "title": "A second distinct incident title"},
    ).json()

    resp = client.get("/api/v1/incidents")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    ids_in_order = [item["id"] for item in body["items"]]
    assert ids_in_order == [second["id"], first["id"]]


def test_list_incidents_respects_limit(client):
    for i in range(3):
        client.post(
            "/api/v1/incidents",
            json={**VALID_PAYLOAD, "title": f"Incident number {i} for pagination"},
        )
    resp = client.get("/api/v1/incidents?limit=2")
    body = resp.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2
    assert body["limit"] == 2


def test_submit_incident_returns_503_when_model_unavailable(client_no_model):
    resp = client_no_model.post("/api/v1/incidents", json=VALID_PAYLOAD)
    assert resp.status_code == 503
    body = resp.json()
    assert body["error_code"] == "model_unavailable"
