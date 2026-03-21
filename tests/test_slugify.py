"""Tests for lib/slugify.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from slugify import slugify


@pytest.mark.parametrize(
    "input_name, expected_slug",
    [
        # Basic lowercasing and spacing
        ("Baseball", "baseball"),
        ("Auto Racing", "auto-racing"),
        ("World War II", "world-war-ii"),
        # Apostrophes stripped
        ("1980's Party Theme", "1980s-party-theme"),
        # Ampersands stripped, words joined
        ("Circus & Carnival", "circus-carnival"),
        ("Magic & Wizards", "magic-wizards"),
        # Hyphens preserved
        ("Tic-tac-toe", "tic-tac-toe"),
        ("Sci-fi Movies", "sci-fi-movies"),
        # Numbers
        ("21 Or Bust", "21-or-bust"),
        # All caps
        ("UFO", "ufo"),
        # Accented characters transliterated
        ("Café", "cafe"),
        ("naïve", "naive"),
        # Consecutive spaces/hyphens collapsed
        ("Deep  Sea   Fishing", "deep-sea-fishing"),
        ("Cops - And - Robbers", "cops-and-robbers"),
        # Leading/trailing whitespace stripped
        ("  Baseball  ", "baseball"),
        # Empty string fallback
        ("", "item"),
        # Only special characters
        ("&!@#", "item"),
    ],
)
def test_slugify(input_name: str, expected_slug: str) -> None:
    assert slugify(input_name) == expected_slug
