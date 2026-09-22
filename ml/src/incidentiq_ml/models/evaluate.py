"""Evaluation helpers shared by training and tests."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)


def compute_metrics(y_true, y_pred, labels: list[str]) -> dict[str, Any]:
    macro_f1 = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, average=None, zero_division=0
    )
    per_class = {
        label: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i, label in enumerate(labels)
    }
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    return {
        "macro_f1": float(macro_f1),
        "per_class": per_class,
        "confusion_matrix": {
            "labels": labels,
            "matrix": cm.tolist(),
        },
        "n_examples": int(len(y_true)),
    }


def summarize_for_log(metrics: dict[str, Any]) -> str:
    lines = [f"macro_f1={metrics['macro_f1']:.4f} (n={metrics['n_examples']})"]
    for label, stats in metrics["per_class"].items():
        lines.append(
            f"  {label:28s} precision={stats['precision']:.3f} "
            f"recall={stats['recall']:.3f} f1={stats['f1']:.3f} "
            f"support={stats['support']}"
        )
    return "\n".join(lines)
