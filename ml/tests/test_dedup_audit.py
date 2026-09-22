import pandas as pd
import pytest

from incidentiq_ml.data.dedup_audit import (
    MAX_ROWS_FOR_PAIRWISE_SCAN,
    find_exact_duplicates,
    find_near_duplicate_pairs,
)


def _df():
    return pd.DataFrame(
        {
            "incident_id": [1, 2, 3, 4, 5, 6],
            "combined_text": [
                "login fails with a 401 error on the auth service",
                "login fails with a 401 error on the auth service",
                "login breaks with a 401 error on the auth service",
                "checkout page renders blank after payment",
                "database migration deadlocks under load",
                "totally unrelated report about a slow report export",
            ],
        }
    )


def test_find_exact_duplicates_catches_identical_text():
    df = _df()
    dupes = find_exact_duplicates(df)
    assert set(dupes["incident_id"]) == {1, 2}


def test_find_near_duplicate_pairs_catches_reworded_text():
    df = _df()
    pairs = find_near_duplicate_pairs(df, threshold=0.8)
    pair_ids = {frozenset((a, b)) for a, b, _ in pairs}
    assert frozenset((1, 3)) in pair_ids or frozenset((2, 3)) in pair_ids


def test_find_near_duplicate_pairs_does_not_flag_unrelated_reports():
    df = _df()
    pairs = find_near_duplicate_pairs(df, threshold=0.8)
    pair_ids = {frozenset((a, b)) for a, b, _ in pairs}
    assert frozenset((4, 6)) not in pair_ids
    assert frozenset((5, 6)) not in pair_ids


def test_refuses_to_scan_too_many_rows():
    big_df = pd.DataFrame(
        {
            "incident_id": range(MAX_ROWS_FOR_PAIRWISE_SCAN + 1),
            "combined_text": ["x"] * (MAX_ROWS_FOR_PAIRWISE_SCAN + 1),
        }
    )
    with pytest.raises(ValueError):
        find_near_duplicate_pairs(big_df)
