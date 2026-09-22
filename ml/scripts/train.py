#!/usr/bin/env python3
"""Explicit training entry point. Never invoked implicitly by the backend.

Usage:
    uv run python scripts/train.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from incidentiq_ml.models.train import main  # noqa: E402

if __name__ == "__main__":
    main()
