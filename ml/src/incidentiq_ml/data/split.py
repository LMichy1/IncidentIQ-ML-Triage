"""Leakage-controlled train/val/test splitting.

Temporal (earliest incidents train, latest test — mirrors how the model will
actually be used: trained on the past, scored on the future) AND group-aware
(every row sharing a `dup_group_id` — an original report and its injected
near-duplicates — is kept in a single split, so a near-duplicate of a
training example can never leak into validation/test).
"""

from __future__ import annotations

import pandas as pd

from incidentiq_ml.config import TEST_FRACTION, TRAIN_FRACTION, VAL_FRACTION


def split_dataset(
    df: pd.DataFrame,
    train_frac: float = TRAIN_FRACTION,
    val_frac: float = VAL_FRACTION,
    test_frac: float = TEST_FRACTION,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if abs(train_frac + val_frac + test_frac - 1.0) > 1e-9:
        raise ValueError("split fractions must sum to 1.0")

    df = df.copy()
    df["created_at"] = pd.to_datetime(df["created_at"])

    group_order = (
        df.groupby("dup_group_id")["created_at"].min().sort_values().index.tolist()
    )
    group_sizes = df.groupby("dup_group_id").size()

    total = len(df)
    train_target = total * train_frac
    val_target = total * (train_frac + val_frac)

    train_ids: list = []
    val_ids: list = []
    test_ids: list = []
    cumulative = 0
    for group_id in group_order:
        if cumulative < train_target:
            train_ids.append(group_id)
        elif cumulative < val_target:
            val_ids.append(group_id)
        else:
            test_ids.append(group_id)
        cumulative += group_sizes[group_id]

    train_df = df[df["dup_group_id"].isin(train_ids)].reset_index(drop=True)
    val_df = df[df["dup_group_id"].isin(val_ids)].reset_index(drop=True)
    test_df = df[df["dup_group_id"].isin(test_ids)].reset_index(drop=True)
    return train_df, val_df, test_df
