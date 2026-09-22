# IncidentIQ — Backend

FastAPI service. **Not implemented yet — scheduled for Milestone 2.**

Planned responsibilities (see [`../docs/architecture.md`](../docs/architecture.md)):

- Load one explicitly-versioned model artifact produced by `../ml/`.
- Serve incident submission, category prediction, and priority-recommendation
  endpoints.
- Persist incidents, predictions, and reviewer feedback to SQLite.
- Expose the API contract consumed by `../frontend/`.
