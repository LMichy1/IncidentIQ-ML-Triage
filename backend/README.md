# IncidentIQ — Backend

FastAPI service. Implements the M2 vertical slice: loads the versioned M1
model artifact explicitly, runs real inference, applies the advisory
priority policy, and persists incidents to SQLite.

See [`../docs/architecture.md`](../docs/architecture.md) for module
boundaries and [`../docs/priority_policy.md`](../docs/priority_policy.md) for
the priority contract.

## Run

```bash
cd backend
uv venv --python python3.10
uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload --port 8000
```

Requires the M1 artifact to exist at
`../ml/artifacts/incident_category_classifier/0.1.0/` (see `../ml/README.md`).
If it's missing, the server still starts, but `GET /ready` reports 503 and
`POST /api/v1/incidents` returns 503 until the artifact is present.

## API

- `GET /health` — liveness only.
- `GET /ready` — 200 once the model artifact is loaded and validated, 503 otherwise.
- `POST /api/v1/incidents` — submit `{title, description, impact?, urgency?}`, returns the incident with its prediction and advisory priority.
- `GET /api/v1/incidents` — paginated history (`limit`, `offset`).
- `GET /api/v1/incidents/{id}` — a single incident.

Every prediction response includes `confidence_status: "uncalibrated"` —
the underlying model has not been calibrated (see the M1 artifact's
`metadata.json` limitations), so raw scores are exposed but never presented
as validated confidence. `requires_human_review` is set by a documented
heuristic margin threshold, not a statistically derived cutoff.

## Test

```bash
uv run pytest
```

29 tests: priority-policy boundaries, artifact-loading success/failure
paths (missing files, hash-mismatch/corruption, malformed metadata), and
full API integration tests running real inference against the real M1
artifact with an in-memory SQLite database.
