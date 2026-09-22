# IncidentIQ — ML

Offline training pipeline for the incident-category classifier. Never
imported or run by the backend at request time — the backend only ever
loads the versioned artifact this package exports.

See [`../docs/dataset_decision.md`](../docs/dataset_decision.md) for the
dataset provenance audit and target definition, and
[`../docs/model_card.md`](../docs/model_card.md) for the model's documented
evaluation and limitations.

## Run

```bash
cd ml
uv venv --python python3.10   # numpy/scipy/scikit-learn wheels aren't yet built for 3.13
uv pip install -e ".[dev]"
uv run python scripts/generate_dataset.py   # writes data/raw/incidents.csv (synthetic — see docs/dataset_decision.md)
uv run python scripts/train.py              # trains, evaluates, writes artifacts/incident_category_classifier/<version>/
```

Both scripts are deterministic (seeded) — re-running them reproduces the
same dataset and the same evaluation numbers.

## Test

```bash
uv run pytest
```

16 tests: text preprocessing, the temporal + group-aware split (no
leakage across train/val/test, no duplicate group split across sets),
the duplicate/near-duplicate audit's precision at its chosen threshold, and
a full train → export → reload → predict round-trip on a small synthetic
fixture (separate from the real generated dataset, so tests don't depend on
`generate_dataset.py` having been run first).
