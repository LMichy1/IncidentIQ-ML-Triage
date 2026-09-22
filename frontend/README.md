# IncidentIQ — Frontend

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui client: submit
an incident, see its predicted category and advisory priority, browse
history, and record human-review feedback — all against the real FastAPI
backend, no mocks.

See [`../docs/architecture.md`](../docs/architecture.md) and
[`../docs/priority_policy.md`](../docs/priority_policy.md) for the contract
this UI renders.

## Run

Requires the backend running (see `../backend/README.md`), which in turn
requires the M1 model artifact (see `../ml/README.md`). Or run the whole
stack via Docker Compose — see `../README.md`.

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at the backend; edit if it's not on localhost:8000
npm run dev
```

## Pages

- `/` — incident submission form + inline prediction result.
- `/history` — paginated incident history, with a "Reviewed" indicator once
  feedback exists and an All / Pending review / Reviewed filter (applied
  server-side, before pagination). "Pending review" means the model flagged
  the incident for review *and* it hasn't been reviewed yet — distinct from
  incidents that never needed review in the first place.
- `/incidents/[id]` — a single incident's full record, plus the human-review feedback form and review history.

Every prediction view shows `confidence_status: "uncalibrated"` explicitly
and a banner noting the model was trained on a synthetic, development-stage
dataset (see `../docs/dataset_decision.md`) — this is not hidden or
downplayed anywhere in the UI. The feedback form lets a reviewer confirm or
correct the predicted category/priority; confirming and correcting are both
recorded as feedback history, never as a silent overwrite of the original
prediction.

## Test

```bash
npm run test:e2e
```

Real browser (Playwright/Chromium) driving the real Next.js app against a
real backend + real trained artifact + a disposable SQLite database
(`playwright.config.ts` starts both servers on dedicated ports and points
the backend at `backend/e2e-test.sqlite3`, gitignored). 15 tests across
three files:

- `e2e/smoke.spec.ts` — clear-signal incident getting the correct real
  prediction, an ambiguous one flagged for human review with an
  undetermined priority, client-side validation, persisted history,
  incident detail retrieval, and the 404 error state for an unknown
  incident id.
- `e2e/feedback.spec.ts` — confirming a prediction, correcting it, and
  confirming the correction survives a full page reload (real backend
  persistence, not local component state).
- `e2e/history-filters.spec.ts` — All/Pending review/Reviewed filtering
  correctly separates never-needed-review, awaiting-review, and reviewed
  incidents; a filter change resets to the first page and is retained on
  the request (verified at the network level); the empty-state message is
  filter-specific (one request intercepted for this case only, since the
  shared real backend always has at least one reviewed incident by this
  point in the suite).

All three spec files share one backend/database instance in this config, so
assertions about total row counts use `expect.poll(...).toBeGreaterThanOrEqual(...)`
rather than exact counts — each test only asserts on the records it itself
created.
