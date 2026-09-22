# Priority policy — contract (M1)

Escalation priority is **not** a learned model output in this project. It is a
transparent, versioned rule-based policy over explicitly supplied impact and
urgency, kept deliberately separate from the ML category classifier (see
[`architecture.md`](architecture.md)).

## Why not learn it from the dataset

Whatever dataset is selected (see [`dataset_decision.md`](dataset_decision.md))
carries historical *ticket* priority fields (e.g. Bugzilla P1–P5) that are
typically reporter-assigned, sparsely used, and not independently validated —
they reflect developer-ticket triage conventions, not observed operational
incident severity. Training a classifier on them would launder that label
noise into something that looks like a calibrated recommendation. The brief
explicitly rules this out; we are not revisiting that in M1.

## M1 contract (implementation deferred to M2)

**Inputs** (to be supplied explicitly by the caller — never inferred from free
text by a model):

- `impact`: enum, e.g. `{low, medium, high, critical}` — scope of affected
  users/systems.
- `urgency`: enum, e.g. `{low, medium, high, critical}` — time-sensitivity.

**Output:**

- `priority`: one of a small enum (e.g. `P1`–`P4`), OR `undetermined` when
  `impact`/`urgency` are missing or out of the policy's defined domain.
- `policy_version`: string, so recommendations are auditable/reproducible as
  the policy evolves.
- `basis`: short structured explanation (which impact/urgency combination
  produced the result), so the recommendation is inspectable, not a black box.

**Rules:**

- The mapping from `(impact, urgency) → priority` is a static lookup table,
  versioned alongside the code (not persisted per-incident as if it were a
  model artifact).
- If either input is missing, unset, or not in the known domain, the policy
  returns `undetermined` and flags the incident for human assessment — it does
  not guess.
- Priority output is always advisory; it does not auto-close, auto-assign, or
  auto-escalate anything in M1/M2.

## M2 implementation

Implemented in `backend/app/priority_policy.py` (policy version `0.1.0`).

Impact and urgency are each ranked `low`=1, `medium`=2, `high`=3, `critical`=4.
Priority is derived from `impact_rank + urgency_rank`:

| Score | Priority |
|---|---|
| 7–8 | P1 |
| 5–6 | P2 |
| 3–4 | P3 |
| 2 | P4 |

If `impact` or `urgency` is missing, `None`, or outside the four known
levels, the result is `undetermined` with a `basis` string explaining why —
never a guessed score. The API captures `impact`/`urgency` as explicit,
optional form fields on incident submission (`backend/app/schemas.py`); they
are never inferred from the free-text title/description.

Every response includes `policy_version`, so a future policy change is
auditable against historical predictions.
