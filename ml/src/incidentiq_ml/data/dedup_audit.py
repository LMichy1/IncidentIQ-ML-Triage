"""Exact and near-duplicate auditing.

This does NOT rely on the synthetic dataset's ground-truth `dup_group_id` —
that field only exists because we generated the data ourselves and wouldn't
be available for a real incident corpus. Instead it detects duplicates the
way we'd have to on real data: exact text match, and TF-IDF cosine-similarity
for near-duplicates. `dup_group_id` is used only in tests, to sanity-check
that this detector actually finds the near-duplicates we injected.
"""

from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

MAX_ROWS_FOR_PAIRWISE_SCAN = 5000


def find_exact_duplicates(df: pd.DataFrame, text_col: str = "combined_text") -> pd.DataFrame:
    mask = df.duplicated(subset=[text_col], keep=False)
    return df[mask]


def find_near_duplicate_pairs(
    df: pd.DataFrame,
    text_col: str = "combined_text",
    id_col: str = "incident_id",
    threshold: float = 0.95,
) -> list[tuple[int, int, float]]:
    """O(n^2) pairwise cosine-similarity scan. Fine for a few thousand rows
    (our synthetic dataset); refuses to run past MAX_ROWS_FOR_PAIRWISE_SCAN
    since it would not scale to a real production-sized corpus without a
    blocking/ANN step first.

    threshold=0.95 was chosen empirically against this dataset's known
    injected duplicates (see docs/dataset_decision.md): 0.85 produced ~5,100
    pairs at ~3% precision because the heavily templated text makes
    unrelated same-category reports look similar too; 0.95 gets to ~98%
    precision at ~85% recall of the known duplicates. This is a real
    threshold-tuning tradeoff, not a solved problem — a real corpus would
    need its own calibration against a labeled duplicate sample."""
    if len(df) > MAX_ROWS_FOR_PAIRWISE_SCAN:
        raise ValueError(
            f"find_near_duplicate_pairs is O(n^2); refusing to run on "
            f"{len(df)} rows (max {MAX_ROWS_FOR_PAIRWISE_SCAN})."
        )

    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(df[text_col])
    similarity = cosine_similarity(matrix)
    ids = df[id_col].to_numpy()

    pairs: list[tuple[int, int, float]] = []
    n = similarity.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            score = similarity[i, j]
            if score >= threshold:
                pairs.append((int(ids[i]), int(ids[j]), float(score)))
    return pairs
