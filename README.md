# IncidentIQ

Intelligent incident triage platform: submit a software incident report, get a
category classification, an uncertainty-aware escalation-priority recommendation,
and a clear signal for when human review is required.

## Status

**Milestone 1 (Foundation & ML baseline)** — in progress. See
[`docs/architecture.md`](docs/architecture.md) for module boundaries and
[`docs/dataset_decision.md`](docs/dataset_decision.md) for the dataset
provenance audit and target definition.

## Repository layout

```
IncidentIQ/
├── ml/          # Offline training package (scikit-learn). Never imported by the API at runtime.
├── backend/     # FastAPI service (M2)
├── frontend/    # Next.js app (M2)
└── docs/        # Architecture decisions, dataset audit, model card
```

## Milestones

1. **Foundation & ML** — repo setup, dataset validation, preprocessing, baseline
   models, reproducible training, versioned artifact.
2. **Full-stack vertical slice** — versioned FastAPI inference, priority policy,
   persistence, Next.js UI.
3. **Release readiness** — human review/feedback loop, tests, Docker, CI,
   model card, docs.

## Getting started (ML package)

```bash
cd ml
uv venv --python python3.10   # numpy/scipy/scikit-learn wheels aren't yet built for 3.13
uv pip install -e ".[dev]"
uv run python scripts/generate_dataset.py   # writes data/raw/incidents.csv (synthetic, see docs/dataset_decision.md)
uv run python scripts/train.py              # trains, evaluates, writes artifacts/incident_category_classifier/<version>/
uv run pytest
```
