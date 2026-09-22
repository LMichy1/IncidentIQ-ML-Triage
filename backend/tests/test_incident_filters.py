"""review_status filtering on GET /api/v1/incidents.

Three distinct states are exercised, deliberately kept separate:
  - a clear-signal incident that never needed review at all
    (requires_human_review=False, reviewed=False)
  - an ambiguous incident awaiting review
    (requires_human_review=True, reviewed=False) -> "pending_review"
  - an incident that has received feedback -> "reviewed"

Not needing review and awaiting review must never be conflated.
"""

CLEAR_SIGNAL_PAYLOAD = {
    "title": "Login fails with a 401",
    "description": "Users cannot sign in via SSO, seeing a 401 error on the auth service in production.",
    "impact": "high",
    "urgency": "high",
}

AMBIGUOUS_PAYLOAD = {
    "title": "System issue reported by support",
    "description": (
        "Users report an issue affecting multiple customers, needs "
        "investigation, was flagged by monitoring."
    ),
}


def _create_clear_signal(client):
    resp = client.post("/api/v1/incidents", json=CLEAR_SIGNAL_PAYLOAD)
    body = resp.json()
    assert body["prediction"]["requires_human_review"] is False
    assert body["reviewed"] is False
    return body


def _create_pending_review(client):
    resp = client.post("/api/v1/incidents", json=AMBIGUOUS_PAYLOAD)
    body = resp.json()
    assert body["prediction"]["requires_human_review"] is True
    assert body["reviewed"] is False
    return body


def _create_reviewed(client):
    incident = _create_pending_review(client)
    client.post(f"/api/v1/incidents/{incident['id']}/feedback", json={"note": "confirmed"})
    return client.get(f"/api/v1/incidents/{incident['id']}").json()


def test_default_review_status_is_all(client):
    resp = client.get("/api/v1/incidents")
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "all"


def test_filter_all_returns_every_incident_regardless_of_review_state(client):
    clear = _create_clear_signal(client)
    pending = _create_pending_review(client)
    reviewed = _create_reviewed(client)

    resp = client.get("/api/v1/incidents?review_status=all")
    body = resp.json()
    ids = {item["id"] for item in body["items"]}
    assert body["total"] == 3
    assert ids == {clear["id"], pending["id"], reviewed["id"]}


def test_filter_pending_review_excludes_incidents_that_never_needed_review(client):
    clear = _create_clear_signal(client)
    pending = _create_pending_review(client)
    reviewed = _create_reviewed(client)

    resp = client.get("/api/v1/incidents?review_status=pending_review")
    body = resp.json()
    ids = {item["id"] for item in body["items"]}

    assert pending["id"] in ids
    assert clear["id"] not in ids, "an incident that never required review must not appear as pending"
    assert reviewed["id"] not in ids, "an already-reviewed incident must not appear as pending"
    assert body["total"] == 1


def test_filter_reviewed_only_includes_incidents_with_feedback(client):
    clear = _create_clear_signal(client)
    pending = _create_pending_review(client)
    reviewed = _create_reviewed(client)

    resp = client.get("/api/v1/incidents?review_status=reviewed")
    body = resp.json()
    ids = {item["id"] for item in body["items"]}

    assert reviewed["id"] in ids
    assert clear["id"] not in ids
    assert pending["id"] not in ids
    assert body["total"] == 1


def test_filter_pagination_is_correct_against_the_filtered_total_not_the_global_total(client):
    _create_clear_signal(client)  # noise: should never appear below
    pending_ids = [_create_pending_review(client)["id"] for _ in range(3)]

    resp = client.get("/api/v1/incidents?review_status=pending_review&limit=2&offset=0")
    body = resp.json()
    assert body["total"] == 3  # filtered total, not 4 (which would include the clear-signal one)
    assert len(body["items"]) == 2
    assert all(item["id"] in pending_ids for item in body["items"])

    resp_page2 = client.get("/api/v1/incidents?review_status=pending_review&limit=2&offset=2")
    body2 = resp_page2.json()
    assert len(body2["items"]) == 1
    assert body2["items"][0]["id"] in pending_ids

    # No overlap between pages, and together they cover all 3.
    page1_ids = {item["id"] for item in body["items"]}
    page2_ids = {item["id"] for item in body2["items"]}
    assert page1_ids.isdisjoint(page2_ids)
    assert page1_ids | page2_ids == set(pending_ids)


def test_filter_with_no_matching_incidents_returns_empty_not_an_error(client):
    _create_clear_signal(client)
    resp = client.get("/api/v1/incidents?review_status=reviewed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_invalid_review_status_value_is_rejected(client):
    resp = client.get("/api/v1/incidents?review_status=not_a_real_status")
    assert resp.status_code == 422
