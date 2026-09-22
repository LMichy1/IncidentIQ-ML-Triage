# IncidentIQ — Frontend

Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui client for the
M2 vertical slice: submit an incident, see its predicted category and
advisory priority, and browse history — all against the real FastAPI
backend, no mocks.

See [`../docs/architecture.md`](../docs/architecture.md) and
[`../docs/priority_policy.md`](../docs/priority_policy.md) for the contract
this UI renders.

## Run

Requires the backend running (see `../backend/README.md`), which in turn
requires the M1 model artifact (see `../ml/README.md`).

```bash
cd frontend
npm install
cp .env.local.example .env.local   # points at the backend; edit if it's not on localhost:8000
npm run dev
```

## Pages

- `/` — incident submission form + inline prediction result.
- `/history` — paginated incident history.
- `/incidents/[id]` — a single incident's full record.

Every prediction view shows `confidence_status: "uncalibrated"` explicitly
and a banner noting the model was trained on a synthetic, development-stage
dataset (see `../docs/dataset_decision.md`) — this is not hidden or
downplayed anywhere in the UI.

## Test

```bash
npm run test:e2e
```

Real browser (Playwright/Chromium) driving the real Next.js app against a
real backend + real trained artifact + a disposable SQLite database
(`playwright.config.ts` starts both servers on dedicated ports and points
the backend at `backend/e2e-test.sqlite3`, gitignored). Covers: a
clear-signal incident getting the correct real prediction, an ambiguous one
being flagged for human review with an undetermined priority, client-side
validation, persisted history, incident detail retrieval, and the 404 error
state for an unknown incident id.
