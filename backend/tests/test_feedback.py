VALID_INCIDENT = {
    "title": "Login fails with a 401",
    "description": "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
    "impact": "high",
    "urgency": "high",
}


def _create_incident(client):
    return client.post("/api/v1/incidents", json=VALID_INCIDENT).json()


def test_submit_valid_feedback_confirming_the_prediction(client):
    incident = _create_incident(client)
    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"reviewer_name": "alex", "note": "Looks right to me."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] == incident["id"]
    assert body["corrected_category"] is None
    assert body["corrected_priority"] is None
    assert body["note"] == "Looks right to me."


def test_submit_feedback_correcting_category_and_priority(client):
    incident = _create_incident(client)
    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={
            "reviewer_name": "sam",
            "corrected_category": "security_vulnerability",
            "corrected_priority": "P1",
            "note": "This is actually a security issue, escalate.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["corrected_category"] == "security_vulnerability"
    assert body["corrected_priority"] == "P1"


def test_feedback_does_not_overwrite_the_original_prediction(client):
    incident = _create_incident(client)
    original_category = incident["prediction"]["category"]
    original_priority = incident["priority"]["priority"]

    client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"corrected_category": "security_vulnerability", "corrected_priority": "P1"},
    )

    refreshed = client.get(f"/api/v1/incidents/{incident['id']}").json()
    assert refreshed["prediction"]["category"] == original_category
    assert refreshed["priority"]["priority"] == original_priority
    # The correction is visible in the feedback history, distinct from the
    # untouched original prediction/priority above.
    assert refreshed["feedback"][-1]["corrected_category"] == "security_vulnerability"


def test_repeated_feedback_is_retained_as_history_not_overwritten(client):
    incident = _create_incident(client)
    client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"reviewer_name": "alex", "note": "First pass: looks fine."},
    )
    client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"reviewer_name": "sam", "corrected_category": "ui_frontend", "note": "Disagree, reclassifying."},
    )

    resp = client.get(f"/api/v1/incidents/{incident['id']}/feedback")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2
    assert entries[0]["reviewer_name"] == "alex"
    assert entries[1]["reviewer_name"] == "sam"
    assert entries[1]["corrected_category"] == "ui_frontend"


def test_incident_reviewed_flag_flips_true_after_feedback(client):
    incident = _create_incident(client)
    assert incident["reviewed"] is False

    client.post(f"/api/v1/incidents/{incident['id']}/feedback", json={})

    refreshed = client.get(f"/api/v1/incidents/{incident['id']}").json()
    assert refreshed["reviewed"] is True


def test_feedback_for_nonexistent_incident_returns_structured_404(client):
    resp = client.post(
        "/api/v1/incidents/does-not-exist/feedback", json={"note": "irrelevant"}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "incident_not_found"


def test_list_feedback_for_nonexistent_incident_returns_404(client):
    resp = client.get("/api/v1/incidents/does-not-exist/feedback")
    assert resp.status_code == 404


def test_invalid_corrected_category_is_rejected(client):
    incident = _create_incident(client)
    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"corrected_category": "not_a_real_category"},
    )
    assert resp.status_code == 422


def test_invalid_corrected_priority_is_rejected(client):
    incident = _create_incident(client)
    resp = client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"corrected_priority": "P0-super-urgent"},
    )
    assert resp.status_code == 422


def test_empty_feedback_body_is_valid_and_means_pure_confirmation(client):
    incident = _create_incident(client)
    resp = client.post(f"/api/v1/incidents/{incident['id']}/feedback", json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["corrected_category"] is None
    assert body["corrected_priority"] is None
    assert body["reviewer_name"] is None


def test_feedback_embedded_in_incident_list_response(client):
    incident = _create_incident(client)
    client.post(
        f"/api/v1/incidents/{incident['id']}/feedback",
        json={"reviewer_name": "alex", "note": "confirmed"},
    )
    resp = client.get("/api/v1/incidents")
    items = resp.json()["items"]
    matching = next(i for i in items if i["id"] == incident["id"])
    assert len(matching["feedback"]) == 1
    assert matching["feedback"][0]["reviewer_name"] == "alex"
