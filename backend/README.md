# IncidentIQ — Backend

FastAPI service. Loads the versioned M1 model artifact explicitly, runs
real inference, applies the advisory priority policy, persists incidents
to SQLite, and records human-review feedback without ever overwriting the
original prediction.

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

Or via Docker (see `../README.md` for the full `docker compose` flow):
`Dockerfile` here (built with the repo root as context) builds the
artifact in a dedicated build stage and copies it into the runtime image —
training never happens at container startup, and a missing/corrupt
artifact still fails the same `/ready` check.

## API

- `GET /health` — liveness only.
- `GET /ready` — 200 once the model artifact is loaded and validated, 503 otherwise.
- `POST /api/v1/incidents` — submit `{title, description, impact?, urgency?}`, returns the incident with its prediction, advisory priority, and (empty, on creation) feedback history.
- `GET /api/v1/incidents` — paginated history (`limit`, `offset`), each item includes its feedback.
- `GET /api/v1/incidents/{id}` — a single incident, with its full feedback history embedded.
- `POST /api/v1/incidents/{id}/feedback` — submit `{reviewer_name?, corrected_category?, corrected_priority?, note?}`. `None`/omitted on `corrected_category`/`corrected_priority` means "confirm the original as-is." Always appends a new record — never overwrites the original prediction or a prior review. Repeated feedback (same or different reviewer) is expected and simply grows the history.
- `GET /api/v1/incidents/{id}/feedback` — the feedback history for one incident, oldest first.

Every prediction response includes `confidence_status: "uncalibrated"` —
the underlying model has not been calibrated (see the M1 artifact's
`metadata.json` limitations), so raw scores are exposed but never presented
as validated confidence. `requires_human_review` is set by a documented
heuristic margin threshold, not a statistically derived cutoff. Feedback
never triggers retraining — there is no automated loop from reviewer
corrections back into the model.

## Test

```bash
uv run pytest
```

40 tests: priority-policy boundaries, artifact-loading success/failure
paths (missing files, hash-mismatch/corruption, malformed metadata), full
API integration tests running real inference against the real M1 artifact
with an in-memory SQLite database, and the feedback workflow (valid/invalid
submissions, missing incident, repeated feedback retained as history,
original prediction immutability). The feedback migration path (a new
`incident_feedback` table added via SQLAlchemy's additive `create_all()`,
with no changes to the existing `incidents` table) was also verified by
hand-building a pre-feedback-era SQLite database, pointing this code at it,
and confirming the old row survives and the new endpoint works against it.
