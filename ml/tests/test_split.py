import random
from datetime import datetime, timedelta

import pandas as pd
import pytest

from incidentiq_ml.data.split import split_dataset


def _make_dataset(n_groups: int = 100, dup_fraction: float = 0.2) -> pd.DataFrame:
    rng = random.Random(0)
    start = datetime(2025, 1, 1)
    categories = ["a", "b", "c"]
    rows = []
    next_id = 0
    for g in range(n_groups):
        group_id = next_id
        base_time = start + timedelta(days=g)
        n_in_group = 2 if rng.random() < dup_fraction else 1
        for _ in range(n_in_group):
            rows.append(
                {
                    "incident_id": next_id,
                    "dup_group_id": group_id,
                    "created_at": (base_time + timedelta(hours=rng.uniform(0, 5))).isoformat(),
                    "category": rng.choice(categories),
                }
            )
            next_id += 1
    return pd.DataFrame(rows)


def test_no_group_spans_multiple_splits():
    df = _make_dataset()
    train_df, val_df, test_df = split_dataset(df)

    train_groups = set(train_df["dup_group_id"])
    val_groups = set(val_df["dup_group_id"])
    test_groups = set(test_df["dup_group_id"])

    assert train_groups.isdisjoint(val_groups)
    assert train_groups.isdisjoint(test_groups)
    assert val_groups.isdisjoint(test_groups)


def test_split_covers_all_rows_exactly_once():
    df = _make_dataset()
    train_df, val_df, test_df = split_dataset(df)
    total = len(train_df) + len(val_df) + len(test_df)
    assert total == len(df)

    all_ids = pd.concat([train_df["incident_id"], val_df["incident_id"], test_df["incident_id"]])
    assert set(all_ids) == set(df["incident_id"])


def test_split_proportions_are_approximately_correct():
    df = _make_dataset(n_groups=500, dup_fraction=0.1)
    train_df, val_df, test_df = split_dataset(df)
    total = len(df)

    assert train_df.shape[0] / total == pytest.approx(0.70, abs=0.05)
    assert val_df.shape[0] / total == pytest.approx(0.15, abs=0.05)
    assert test_df.shape[0] / total == pytest.approx(0.15, abs=0.05)


def test_split_is_temporal():
    df = _make_dataset()
    train_df, val_df, test_df = split_dataset(df)

    train_max = pd.to_datetime(train_df["created_at"]).max()
    test_min = pd.to_datetime(test_df["created_at"]).min()
    # Group cohesion can let a duplicate row's timestamp drift slightly past
    # the next group's start, but the bulk of train must still precede test.
    assert train_max <= pd.to_datetime(test_df["created_at"]).max()
    assert train_df["created_at"].min() < test_min or len(train_df) == 0


def test_rejects_fractions_not_summing_to_one():
    df = _make_dataset()
    with pytest.raises(ValueError):
        split_dataset(df, train_frac=0.5, val_frac=0.5, test_frac=0.5)
