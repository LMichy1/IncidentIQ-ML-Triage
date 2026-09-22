"""Deterministic text preprocessing shared by training and inference.

Kept intentionally minimal: TfidfVectorizer already handles lowercasing and
tokenization. What we own here is the part a vectorizer can't do for us —
combining the two input fields the same way every time.
"""

from __future__ import annotations

import re

_WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Normalize whitespace. Deliberately not stripping punctuation/case —
    TF-IDF's tokenizer + lowercasing already does that, and doing it twice
    would just be redundant surface area for training/inference to drift."""
    return _WHITESPACE_RE.sub(" ", text or "").strip()


def combine_title_description(title: str, description: str) -> str:
    """The single feature TfidfVectorizer sees. Title is repeated to weight
    it relative to the (usually longer) description, since the title tends
    to carry the strongest category signal."""
    return f"{clean_text(title)} {clean_text(title)} {clean_text(description)}"
