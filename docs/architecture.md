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
  Next.js app, single SQLite file, Docker Compose for local/dev
  orchestration (implemented in M3 — see `docker-compose.yml`).
- **Feedback is append-only and separate from the prediction it reviews.**
  See "Feedback data model" below.

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

## Feedback data model (M3)

`incident_feedback` is a separate table from `incidents` (`backend/app/models_db.py`),
one row per review, foreign-keyed to the incident it reviews:

- `corrected_category` / `corrected_priority` are `NULL` when a reviewer
  confirms the original prediction rather than correcting it.
- Rows are never updated or deleted by the API — submitting feedback again
  (same or a different reviewer) always inserts a new row. `GET
  /api/v1/incidents/{id}` returns the full ordered history, alongside the
  original, untouched prediction fields on `incidents` — a reviewer's
  correction is never written back into `predicted_category`, `priority`,
  etc.
- `incidents.reviewed` flips to `true` (monotonically — never reset) the
  first time feedback is recorded; `incidents.reviewer_note` is deprecated
  as of M3, superseded by the feedback table, and kept only so an existing
  SQLite file doesn't need a destructive column migration.
- Adding this table is additive-only via SQLAlchemy's `create_all()` — an
  existing pre-M3 database upgrades in place with no data loss (verified by
  hand-constructing a pre-M3-schema SQLite file and confirming the old row
  and the new endpoint both work against it; see `backend/README.md`).
- Feedback is read-only input from the backend's perspective: nothing
  currently consumes it to retrain the model, flag drift, or compute
  reviewer-agreement metrics. That would be a real, separate feature, not
  implied by this table's existence.
