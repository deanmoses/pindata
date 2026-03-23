"""Tests for hierarchical location loading in catalog_loader."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from catalog_loader import (
    LocationStructureError,
    _iter_locations,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_country(catalog_dir: Path, slug: str, name: str, divisions: list[str]) -> None:
    divs = "\n".join(f"  - {d}" for d in divisions)
    _write(
        catalog_dir / "locations" / f"{slug}.md",
        f"---\nname: {name}\ndivisions:\n{divs}\n---\n",
    )


def _make_subdivision(
    catalog_dir: Path, path_parts: list[str], name: str, sub_type: str, code: str
) -> None:
    file_path = catalog_dir / "locations" / "/".join(path_parts[:-1]) / f"{path_parts[-1]}.md"
    _write(file_path, f"---\nname: {name}\ntype: {sub_type}\ncode: {code}\n---\n")


def _make_city(catalog_dir: Path, path_parts: list[str], name: str) -> None:
    file_path = catalog_dir / "locations" / "/".join(path_parts[:-1]) / f"{path_parts[-1]}.md"
    _write(file_path, f"---\nname: {name}\ntype: city\n---\n")


def _collect(catalog_dir: Path) -> list:
    return list(_iter_locations(catalog_dir=catalog_dir, validate=True))


def _by_type(records, type_value):
    return [r for r in records if r.frontmatter.get("type") == type_value]


# --- Basic hierarchy tests ---


def test_country_only(tmp_path):
    """Country with no subdirectory yields just the country record."""
    _make_country(tmp_path, "netherlands", "Netherlands", ["city"])
    records = _collect(tmp_path)
    assert len(records) == 1
    assert records[0].entity_type == "location"
    assert records[0].frontmatter["type"] == "country"
    assert records[0].frontmatter["location_path"] == "netherlands"


def test_two_level_hierarchy(tmp_path):
    """Country with divisions: [city] — cities directly under country dir."""
    _make_country(tmp_path, "netherlands", "Netherlands", ["city"])
    _make_city(tmp_path, ["netherlands", "amsterdam"], "Amsterdam")
    _make_city(tmp_path, ["netherlands", "rotterdam"], "Rotterdam")

    records = _collect(tmp_path)
    assert len(records) == 3

    countries = _by_type(records, "country")
    cities = _by_type(records, "city")
    assert len(countries) == 1
    assert len(cities) == 2

    amsterdam = next(r for r in cities if r.slug == "amsterdam")
    assert amsterdam.frontmatter["country_slug"] == "netherlands"
    assert amsterdam.frontmatter["location_path"] == "netherlands/amsterdam"


def test_three_level_hierarchy(tmp_path):
    """Country with divisions: [state, city]."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    _make_subdivision(tmp_path, ["usa", "ca"], "California", "state", "CA")
    _make_city(tmp_path, ["usa", "ca", "los-angeles"], "Los Angeles")
    _make_city(tmp_path, ["usa", "ca", "san-francisco"], "San Francisco")

    records = _collect(tmp_path)
    assert len(records) == 4

    subdivisions = _by_type(records, "state")
    assert len(subdivisions) == 1
    assert subdivisions[0].slug == "ca"
    assert subdivisions[0].frontmatter["country_slug"] == "usa"
    assert subdivisions[0].frontmatter["location_path"] == "usa/ca"

    cities = _by_type(records, "city")
    assert len(cities) == 2
    la = next(r for r in cities if r.slug == "los-angeles")
    assert la.frontmatter["country_slug"] == "usa"
    assert la.frontmatter["state_slug"] == "ca"
    assert la.frontmatter["location_path"] == "usa/ca/los-angeles"


def test_four_level_hierarchy(tmp_path):
    """Country with divisions: [region, department, city] like France."""
    _make_country(tmp_path, "france", "France", ["region", "department", "city"])
    _make_subdivision(tmp_path, ["france", "idf"], "Île-de-France", "region", "IDF")
    _make_subdivision(
        tmp_path, ["france", "idf", "paris-dept"], "Paris", "department", "75"
    )
    _make_city(tmp_path, ["france", "idf", "paris-dept", "paris"], "Paris")

    records = _collect(tmp_path)
    assert len(records) == 4

    paris = next(r for r in _by_type(records, "city") if r.slug == "paris")
    assert paris.frontmatter["country_slug"] == "france"
    assert paris.frontmatter["region_slug"] == "idf"
    assert paris.frontmatter["department_slug"] == "paris-dept"
    assert paris.frontmatter["location_path"] == "france/idf/paris-dept/paris"


def test_multiple_countries(tmp_path):
    """Multiple countries with different division structures."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    _make_country(tmp_path, "netherlands", "Netherlands", ["city"])

    _make_subdivision(tmp_path, ["usa", "il"], "Illinois", "state", "IL")
    _make_city(tmp_path, ["usa", "il", "chicago"], "Chicago")
    _make_city(tmp_path, ["netherlands", "amsterdam"], "Amsterdam")

    records = _collect(tmp_path)
    countries = _by_type(records, "country")
    cities = _by_type(records, "city")
    assert len(countries) == 2
    assert len(cities) == 2

    chicago = next(r for r in cities if r.slug == "chicago")
    assert chicago.frontmatter["state_slug"] == "il"
    assert chicago.frontmatter["country_slug"] == "usa"

    amsterdam = next(r for r in cities if r.slug == "amsterdam")
    assert amsterdam.frontmatter["country_slug"] == "netherlands"
    assert "state_slug" not in amsterdam.frontmatter


def test_all_records_have_entity_type_location(tmp_path):
    """Every record from _iter_locations has entity_type 'location'."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    _make_subdivision(tmp_path, ["usa", "ca"], "California", "state", "CA")
    _make_city(tmp_path, ["usa", "ca", "la"], "Los Angeles")

    records = _collect(tmp_path)
    assert all(r.entity_type == "location" for r in records)


# --- Structure error tests ---


def test_error_subdir_without_country_file(tmp_path):
    """Subdirectory with no matching country .md file."""
    (tmp_path / "locations" / "narnia").mkdir(parents=True)
    _write(tmp_path / "locations" / "narnia" / "tumnus-city.md", "---\nname: Tumnus\ntype: city\n---\n")

    with pytest.raises(LocationStructureError, match="no matching country file"):
        _collect(tmp_path)


def test_error_subdir_without_md_file(tmp_path):
    """Subdirectory under a country that has no matching .md sibling."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    # Create a subdirectory 'ghost/' with no ghost.md
    ghost_dir = tmp_path / "locations" / "usa" / "ghost"
    ghost_dir.mkdir(parents=True)
    _write(ghost_dir / "somecity.md", "---\nname: Some City\ntype: city\n---\n")

    with pytest.raises(LocationStructureError, match="no matching file"):
        _collect(tmp_path)


def test_error_nesting_beyond_divisions(tmp_path):
    """Files nested deeper than the divisions array allows."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    _make_subdivision(tmp_path, ["usa", "ca"], "California", "state", "CA")
    _make_city(tmp_path, ["usa", "ca", "la"], "Los Angeles")
    # Create a subdirectory under a city (leaf level).
    bad_dir = tmp_path / "locations" / "usa" / "ca" / "la"
    bad_dir.mkdir(parents=True)
    _write(bad_dir / "downtown.md", "---\nname: Downtown\ntype: city\n---\n")

    with pytest.raises(LocationStructureError, match="unexpected subdirectory at leaf level"):
        _collect(tmp_path)


def test_error_type_mismatch(tmp_path):
    """Record type field doesn't match expected division at that depth."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    # Put a file with type: city where a state is expected.
    _make_city(tmp_path, ["usa", "not-a-state"], "Not A State")

    with pytest.raises(LocationStructureError, match="not in allowed types"):
        _collect(tmp_path)


def test_error_missing_type_at_multi_type_level(tmp_path):
    """Record without type at a multi-type division level is an error."""
    _make_country(tmp_path, "usa", "United States of America", ["state,district", "city"])
    # Write a file without a type field at the state,district level.
    _write(
        tmp_path / "locations" / "usa" / "dc.md",
        "---\nname: District of Columbia\ncode: DC\n---\n",
    )

    with pytest.raises(LocationStructureError, match="missing 'type' field at a multi-type"):
        _collect(tmp_path)


# --- Edge cases ---


def test_country_with_no_subdir_and_divisions(tmp_path):
    """Country declares divisions but has no subdirectory yet — valid (empty)."""
    _make_country(tmp_path, "japan", "Japan", ["prefecture", "city"])
    records = _collect(tmp_path)
    assert len(records) == 1
    assert records[0].entity_type == "location"
    assert records[0].frontmatter["type"] == "country"


def test_error_frontmatter_conflicts_with_parent_slug(tmp_path):
    """Frontmatter containing a path-derived parent slug field is an error."""
    _make_country(tmp_path, "usa", "United States of America", ["state", "city"])
    # Write a state file that also has country_slug in its frontmatter.
    _write(
        tmp_path / "locations" / "usa" / "ca.md",
        "---\nname: California\ntype: state\ncode: CA\ncountry_slug: oops\n---\n",
    )

    with pytest.raises(LocationStructureError, match="conflict with path-derived"):
        _collect(tmp_path)
