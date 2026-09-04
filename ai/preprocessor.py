"""Log preprocessing and TF-IDF feature extraction for failure classifier."""

from __future__ import annotations

import re
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer


class LogPreprocessor:
    """Cleans and normalizes log text strings for machine learning models."""

    # Regex patterns for cleaning log lines
    HEX_PATTERN = re.compile(r"0x[0-9a-fA-F]+")
    TIMESTAMP_PATTERN = re.compile(r"\[?\s*\d{1,4}[-/\.]\d{1,2}[-/\.]\d{1,2}[\sT]?\d{1,2}:\d{2}:\d{2}(?:\.\d+)?Z?\s*\]?")
    DMESG_TS_PATTERN = re.compile(r"\[\s*\d+\.\d+\s*\]")
    PID_PATTERN = re.compile(r"\[\d+\]|PID\s*\d+|pid\s*\d+")
    PATH_PATTERN = re.compile(r"/(?:[a-zA-Z0-9_\.\-]+/)+[a-zA-Z0-9_\.\-]*")

    @classmethod
    def clean_text(cls, text: str) -> str:
        """Strip variable entities (timestamps, PIDs, hex addresses, file paths) from log text."""
        if not isinstance(text, str):
            text = str(text)

        cleaned = cls.TIMESTAMP_PATTERN.sub(" ", text)
        cleaned = cls.DMESG_TS_PATTERN.sub(" ", cleaned)
        cleaned = cls.HEX_PATTERN.sub(" ", cleaned)
        cleaned = cls.PID_PATTERN.sub(" ", cleaned)
        cleaned = cls.PATH_PATTERN.sub(" ", cleaned)

        # Remove numbers and special punctuation, leaving text tokens
        cleaned = re.sub(r"[^a-zA-Z\s]", " ", cleaned)
        # Collapse multiple spaces
        cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()

        return cleaned if cleaned else "empty_log"

    @classmethod
    def build_vectorizer(
        cls,
        max_features: int = 500,
        ngram_range: tuple[int, int] = (1, 2),
    ) -> TfidfVectorizer:
        """Build configured TF-IDF vectorizer."""
        return TfidfVectorizer(
            preprocessor=cls.clean_text,
            max_features=max_features,
            ngram_range=ngram_range,
            sublinear_tf=True,
        )
