# IncidentIQ

Intelligent incident triage: submit a software incident report, get a
category prediction, an advisory escalation priority, and a clear signal
for when human review is required.

## Status

- **M1 (Foundation & ML)** — done. See [`docs/dataset_decision.md`](docs/dataset_decision.md)
  and [`docs/model_card.md`](docs/model_card.md).
- **M2 (Full-stack vertical slice)** — done. FastAPI backend + Next.js
  frontend, real inference end-to-end, no mocks. See
  [`docs/architecture.md`](docs/architecture.md) and
  [`docs/priority_policy.md`](docs/priority_policy.md).
- **M3 (Release readiness)** — **not started.** No human-review/feedback
  loop, no Docker, no CI. See the M3 issue in the project tracker for scope.

## Repository layout

```
IncidentIQ/
├── ml/          # Offline training package (scikit-learn). Never imported by the API at runtime.
├── backend/     # FastAPI service — inference, priority policy, persistence
├── frontend/    # Next.js app — submission, prediction display, history
└── docs/        # Architecture, dataset provenance, model card, priority policy
```

## Run the whole stack

Three terminals, in this order (each has its own `README.md` with more
detail):

```bash
# 1. ML — produces the artifact the backend loads
cd ml
uv venv --python python3.10 && uv pip install -e ".[dev]"
uv run python scripts/generate_dataset.py
uv run python scripts/train.py

# 2. Backend
cd backend
uv venv --python python3.10 && uv pip install -e ".[dev]"
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`. There is no Docker Compose setup yet — this
is a real limitation (see "Known limitations" below), not an oversight.

## Test

```bash
cd ml && uv run pytest          # 16 tests
cd backend && uv run pytest     # 29 tests
cd frontend && npm run test:e2e # 7 tests — real browser, real backend, real model, disposable DB
```

## Known limitations

- **Synthetic training data.** No real incident dataset was used — three
  candidates were investigated and rejected for license/schema/access
  reasons (full audit in `docs/dataset_decision.md`). Reported metrics
  (~0.89 test macro F1) demonstrate the pipeline works, not real-world
  accuracy, and are themselves a development-stage result (the generator
  was iterated after seeing an earlier test score — see the
  "evaluation-independence caveat" in that doc).
- **Uncalibrated confidence.** Raw model scores are surfaced but always
  labeled `confidence_status: "uncalibrated"`, never presented as a
  validated confidence percentage.
- **Heuristic review threshold.** The 0.20 margin threshold that flags a
  prediction for human review is a documented placeholder, not
  statistically derived.
- **No human-review/feedback workflow.** The database has `reviewed` /
  `reviewer_note` columns and the API returns them, but nothing writes to
  them yet — there is no endpoint or UI to submit feedback. This is M3
  scope, not implemented.
- **No authentication, no Docker, no CI.** This is a local-run demo
  application, not a hardened deployment.
- **Minor API contract inconsistency:** 422 validation errors use FastAPI's
  default `{"detail": [...]}` shape, while other errors use this project's
  `{"error_code", "detail"}` shape. The frontend client handles both; this
  is a documented rough edge, not a functional bug.
