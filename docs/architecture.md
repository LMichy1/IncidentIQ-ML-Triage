# IncidentIQ — Architecture

Concise reference for module boundaries and key decisions. Expand only as M2/M3
introduce new components — this is not a speculative design doc.

## Modules

| Module | Responsibility | Runs when |
|---|---|---|
| `ml/` | Offline: dataset loading, preprocessing, training, evaluation, artifact export. | Explicitly invoked by a developer/CI job (`scripts/train.py`). **Never** imported or executed by the backend at request time or startup. |
| `backend/` | FastAPI service: loads one explicitly-versioned trusted model artifact, runs inference, applies the priority policy, persists incidents/predictions/feedback to SQLite. | Serves HTTP requests (M2). |
| `frontend/` | Next.js UI for submitting incidents, viewing predictions/uncertainty, and reviewer feedback. | Serves the browser client (M2). |
| `docs/` | Architecture decisions, dataset audit, model card. | N/A |

## Key decisions

- **No implicit training.** The backend loads a versioned artifact
  (`ml/artifacts/<model_name>/<version>/`) from disk; it does not train,
  retrain, or download data on startup. Training is a separate, explicit,
  reproducible CLI step.
- **Preprocessing lives once, in `ml/`.** The exact preprocessing
  (text cleaning, TF-IDF vectorizer, label encoder) is fit during training and
  serialized as part of the artifact bundle, so inference uses byte-identical
  preprocessing to training. The backend does not reimplement or duplicate
  preprocessing logic.
- **Category classification and escalation priority are separate concerns.**
  The ML model predicts an issue *category* (see
  [`dataset_decision.md`](dataset_decision.md) for target definition). Priority
  is a transparent, versioned, rule-based policy over explicitly supplied
  impact/urgency (see `docs/priority_policy.md`, added in M2) — it is not
  learned from noisy historical priority labels.
- **SQLite by default.** No requirement in M1/M2 justifies the operational
  overhead of Postgres (single-writer web app, modest scale, three-day
  deadline). Persistence sits behind a data-access module in `backend/` so a
  swap remains possible without touching route/service code.
- **Shared contracts.** Backend Pydantic models are the source of truth for
  the API shape; frontend TypeScript types are kept in sync manually in M1/M2
  (a generated-client step is a candidate M3 improvement, not a blocker now).
- **No microservices/Kubernetes/Kafka.** Single FastAPI process, single
  Next.js app, single SQLite file, Docker Compose for local/dev orchestration.

## Artifact contract (`ml` → `backend`)

An exported artifact directory contains:

- `model.joblib` — fitted pipeline (vectorizer + classifier), or the
  vectorizer/classifier as separate joblib files.
- `metadata.json` — model version, training date, dataset reference + hash,
  library versions, class label mapping, evaluation metric references,
  documented limitations, and a content hash of the artifact for integrity
  checking.

The backend validates `metadata.json` against an expected schema before
loading and refuses to start on a mismatch (implemented in M2).
