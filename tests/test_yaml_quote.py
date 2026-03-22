"""Tests for frontmatter.yaml_quote."""

from __future__ import annotations

import pytest
import yaml

from frontmatter import yaml_quote


@pytest.mark.parametrize(
    "value, expected",
    [
        # Plain values pass through unquoted
        ("hello", "hello"),
        ("simple value", "simple value"),
        # Colon triggers quoting
        ("Star Wars: Episode IV", '"Star Wars: Episode IV"'),
        # Hash triggers quoting
        ("C# programming", '"C# programming"'),
        # Brackets and braces
        ("list [1]", '"list [1]"'),
        ("map {a}", '"map {a}"'),
        # Ampersand
        ("Circus & Carnival", '"Circus & Carnival"'),
        # Leading quote
        ("'quoted'", "\"'quoted'\""),
        ('"double"', r'"\"double\""'),
        # YAML booleans (case-insensitive)
        ("true", '"true"'),
        ("False", '"False"'),
        ("YES", '"YES"'),
        ("no", '"no"'),
        # Null
        ("null", '"null"'),
        ("~", '"~"'),
        # Numeric-looking strings
        ("42", '"42"'),
        ("-3.14", '"-3.14"'),
        ("0", '"0"'),
        # Empty string
        ("", '""'),
        # Leading/trailing whitespace
        ("  padded  ", '"  padded  "'),
        # Newline — must be escaped so YAML round-trips correctly
        ("line1\nline2", '"line1\\nline2"'),
        # Backslash — safe as bare YAML scalar
        ("back\\slash", "back\\slash"),
    ],
)
def test_yaml_quote(value: str, expected: str) -> None:
    assert yaml_quote(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "hello",
        "Star Wars: Episode IV",
        "C# programming",
        "true",
        "42",
        "",
        "Circus & Carnival",
        "'quoted'",
        "back\\slash",
        "line1\nline2",
    ],
)
def test_yaml_quote_roundtrips(value: str) -> None:
    """Every quoted value should round-trip through PyYAML as the original string."""
    yaml_str = f"key: {yaml_quote(value)}\n"
    parsed = yaml.safe_load(yaml_str)
    assert parsed["key"] == value
