#!/usr/bin/env python3
"""Generate the synthetic IncidentIQ demonstration dataset.

Why synthetic: see docs/dataset_decision.md for the full provenance/license
audit of the real candidates we rejected (Eclipse/Mozilla Bugzilla exports).

This is a templated generator, not a language model — every row is built by
combining a category's vocabulary and sentence templates with randomized
slot values, using the stdlib `random` module seeded with
`incidentiq_ml.config.RANDOM_SEED` for reproducibility. Every row is tagged
`is_synthetic=True` so it can never be mistaken for real incident data
downstream.

Usage:
    uv run python scripts/generate_dataset.py
"""

from __future__ import annotations

import csv
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from incidentiq_ml.config import CATEGORIES, RANDOM_SEED, RAW_DATASET_PATH  # noqa: E402

N_BASE_ROWS = 3000
N_REPORTERS = 180
NEAR_DUPLICATE_FRACTION = 0.05
START_DATE = datetime(2025, 3, 1)
SPAN_DAYS = 18 * 30

# Deliberately imbalanced — mirrors realistic operational distributions
# (auth/API errors dominate, security reports are rare) rather than a
# convenient uniform split across classes.
CATEGORY_WEIGHTS = {
    "authentication_access": 0.20,
    "api_backend_error": 0.22,
    "ui_frontend": 0.15,
    "database_data_integrity": 0.12,
    "performance_latency": 0.12,
    "infrastructure_deployment": 0.08,
    "third_party_integration": 0.07,
    "security_vulnerability": 0.04,
}
assert set(CATEGORY_WEIGHTS) == set(CATEGORIES)
assert abs(sum(CATEGORY_WEIGHTS.values()) - 1.0) < 1e-9

ENVIRONMENTS = ["production", "staging", "development"]

VOCAB = {
    "authentication_access": {
        "subjects": ["SSO login", "OAuth token refresh", "password reset", "session cookie", "MFA challenge", "API key validation", "role permission check"],
        "symptoms": ["fails with a 401", "silently logs the user out", "loops without completing", "rejects valid credentials", "times out after 30s", "grants access it shouldn't"],
        "components": ["auth-service", "identity-provider", "session-manager", "rbac-gateway"],
    },
    "api_backend_error": {
        "subjects": ["order submission endpoint", "checkout API", "webhook handler", "background job worker", "GraphQL resolver", "batch export endpoint"],
        "symptoms": ["returns a 500", "throws an unhandled NullReferenceException", "crashes the worker process", "returns malformed JSON", "hangs indefinitely", "returns a 502 from the gateway"],
        "components": ["orders-service", "billing-api", "notification-worker", "gateway", "reporting-service"],
    },
    "ui_frontend": {
        "subjects": ["dashboard chart", "checkout form", "settings page", "navigation menu", "file upload widget", "notifications panel"],
        "symptoms": ["renders blank on load", "throws a console error and freezes", "loses state on refresh", "overlaps other elements on mobile", "doesn't update after saving", "is unresponsive to clicks"],
        "components": ["web-dashboard", "checkout-frontend", "admin-console", "mobile-web-app"],
    },
    "database_data_integrity": {
        "subjects": ["nightly ETL job", "user profile table", "inventory sync", "audit log write", "schema migration"],
        "symptoms": ["leaves duplicate rows", "silently drops records", "deadlocks under load", "corrupts a foreign key relationship", "rolls back partway through", "produces mismatched totals"],
        "components": ["primary-db", "analytics-warehouse", "inventory-db", "audit-store"],
    },
    "performance_latency": {
        "subjects": ["search endpoint", "homepage load", "report generation", "image thumbnail pipeline", "cache warmup job"],
        "symptoms": ["takes over 20 seconds to respond", "degrades sharply under concurrent load", "spikes CPU to 100%", "exhausts available memory", "queues requests for minutes", "times out intermittently"],
        "components": ["search-service", "cdn-edge", "reporting-service", "media-pipeline", "cache-cluster"],
    },
    "infrastructure_deployment": {
        "subjects": ["production deploy", "container rollout", "autoscaling policy", "DNS cutover", "TLS certificate renewal", "config rollout"],
        "symptoms": ["fails health checks and rolls back", "leaves half the pods on the old version", "is stuck in a crash loop", "misroutes traffic to the wrong region", "expires without renewing", "wasn't applied to all nodes"],
        "components": ["k8s-cluster", "ci-pipeline", "load-balancer", "dns-service", "cert-manager"],
    },
    "third_party_integration": {
        "subjects": ["payment provider webhook", "shipping-carrier API call", "email delivery integration", "analytics export", "SSO federation with partner IdP"],
        "symptoms": ["silently stops receiving events", "returns inconsistent status codes", "rejects previously valid requests", "duplicates outbound events", "fails signature verification", "times out against the vendor endpoint"],
        "components": ["payments-integration", "shipping-integration", "email-integration", "partner-sso-bridge"],
    },
    "security_vulnerability": {
        "subjects": ["file upload endpoint", "admin impersonation feature", "public API rate limiter", "password reset flow", "third-party dependency"],
        "symptoms": ["allows path traversal", "can be used to escalate privileges", "can be bypassed with a crafted request", "exposes internal stack traces", "has a known CVE with no patch applied", "leaks another user's data in the response"],
        "components": ["upload-service", "admin-console", "gateway", "auth-service", "dependency: libfoo"],
    },
}

TITLE_TEMPLATES = [
    "{subject} {symptom}",
    "{component}: {subject} {symptom}",
    "[{env}] {subject} {symptom}",
]

DESCRIPTION_TEMPLATES = [
    (
        "In {env}, the {subject} {symptom}. First observed by {reporter} on "
        "affected component `{component}`. Steps to reproduce: trigger the "
        "{subject} under normal load and observe the failure within "
        "{minutes} minutes. Error reference: {error_code}."
    ),
    (
        "Reported against `{component}` in {env}. The {subject} {symptom}, "
        "impacting downstream consumers. {reporter} noticed this after a "
        "recent change and could reproduce it consistently. Reference code: "
        "{error_code}."
    ),
    (
        "{component} ({env}) — {subject} {symptom}. Approximately "
        "{minutes} minutes elapsed before the issue was noticed. No known "
        "workaround yet. Logged by {reporter}, error code {error_code}."
    ),
]

SYNONYM_SWAPS = {
    "fails": "breaks",
    "returns": "responds with",
    "throws": "raises",
    "silently": "quietly",
    "intermittently": "sporadically",
}

# Deliberately overlapping category pairs. Without this, category vocabulary
# is disjoint enough that TF-IDF trivially separates every class (we saw a
# meaningless 1.0 macro F1 across the board before adding this) — real
# incident reports are ambiguous between related categories, and a
# synthetic benchmark that can't show that isn't demonstrating the
# evaluation methodology honestly. For CONFUSION_RATE of rows, the
# subject/symptom is borrowed from the paired category while the label
# stays the true one, so a classifier has to actually work for its score.
CONFUSABLE_PAIRS = {
    "api_backend_error": "third_party_integration",
    "third_party_integration": "api_backend_error",
    "performance_latency": "infrastructure_deployment",
    "infrastructure_deployment": "performance_latency",
    "database_data_integrity": "api_backend_error",
    "ui_frontend": "performance_latency",
    "authentication_access": "security_vulnerability",
    "security_vulnerability": "authentication_access",
}
CONFUSION_RATE = 0.18


@dataclass
class Row:
    incident_id: int
    dup_group_id: int
    reporter_id: str
    created_at: str
    title: str
    description: str
    category: str
    is_synthetic: bool = True


def _weighted_categories(rng: random.Random, n: int) -> list[str]:
    cats = list(CATEGORY_WEIGHTS.keys())
    weights = list(CATEGORY_WEIGHTS.values())
    return rng.choices(cats, weights=weights, k=n)


def _make_row(rng: random.Random, incident_id: int, category: str, reporters: list[str]) -> Row:
    vocab = VOCAB[category]
    source_vocab = vocab
    if category in CONFUSABLE_PAIRS and rng.random() < CONFUSION_RATE:
        source_vocab = VOCAB[CONFUSABLE_PAIRS[category]]

    subject = rng.choice(source_vocab["subjects"])
    symptom = rng.choice(source_vocab["symptoms"])
    component = rng.choice(vocab["components"])
    env = rng.choice(ENVIRONMENTS)
    reporter = rng.choice(reporters)

    title = rng.choice(TITLE_TEMPLATES).format(
        subject=subject, symptom=symptom, component=component, env=env
    )
    description = rng.choice(DESCRIPTION_TEMPLATES).format(
        subject=subject,
        symptom=symptom,
        component=component,
        env=env,
        reporter=reporter,
        minutes=rng.randint(1, 90),
        error_code=f"ERR-{rng.randint(1000, 9999)}",
    )
    offset_days = rng.uniform(0, SPAN_DAYS)
    created_at = (START_DATE + timedelta(days=offset_days)).isoformat()

    return Row(
        incident_id=incident_id,
        dup_group_id=incident_id,
        reporter_id=reporter,
        created_at=created_at,
        title=title[:1].upper() + title[1:],
        description=description,
        category=category,
    )


def _make_near_duplicate(rng: random.Random, source: Row, new_id: int, reporters: list[str]) -> Row:
    """Produce a near-duplicate of `source`: same underlying incident, minor
    wording changes, reported slightly later (mirrors a second user hitting
    the same bug and filing an independent report)."""
    title = source.title
    description = source.description
    for old, new in SYNONYM_SWAPS.items():
        if rng.random() < 0.5:
            title = title.replace(old, new)
            description = description.replace(old, new)
    if rng.random() < 0.5:
        title = "Re: " + title

    created = datetime.fromisoformat(source.created_at) + timedelta(
        hours=rng.uniform(1, 72)
    )
    return Row(
        incident_id=new_id,
        dup_group_id=source.dup_group_id,
        reporter_id=rng.choice(reporters),
        created_at=created.isoformat(),
        title=title,
        description=description,
        category=source.category,
    )


def generate() -> list[Row]:
    rng = random.Random(RANDOM_SEED)
    reporters = [f"user_{i:04d}" for i in range(N_REPORTERS)]
    categories = _weighted_categories(rng, N_BASE_ROWS)

    rows: list[Row] = []
    for i, category in enumerate(categories):
        rows.append(_make_row(rng, incident_id=i, category=category, reporters=reporters))

    n_dupes = int(len(rows) * NEAR_DUPLICATE_FRACTION)
    next_id = len(rows)
    for source in rng.sample(rows, n_dupes):
        rows.append(_make_near_duplicate(rng, source, next_id, reporters))
        next_id += 1

    rng.shuffle(rows)
    return rows


def main() -> None:
    rows = generate()
    RAW_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RAW_DATASET_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "incident_id",
                "dup_group_id",
                "reporter_id",
                "created_at",
                "title",
                "description",
                "category",
                "is_synthetic",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row.__dict__)

    n_dup_groups_with_dupes = sum(
        1 for r in rows if r.dup_group_id != r.incident_id
    )
    print(f"Wrote {len(rows)} rows to {RAW_DATASET_PATH}")
    print(f"  near-duplicate rows: {n_dup_groups_with_dupes}")
    print(f"  categories: {len(CATEGORIES)}")


if __name__ == "__main__":
    main()
