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

## Explicitly deferred to M2

- The concrete lookup table (impact × urgency → priority).
- API schema (`PriorityRequest`/`PriorityResponse` Pydantic models).
- Where in the incident-submission flow impact/urgency are captured (explicit
  form fields, not inferred).
