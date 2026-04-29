#!/usr/bin/env python3
"""Validate catalog/**/*.md records against JSON schemas.

Checks:
- YAML frontmatter parses correctly
- Frontmatter validates against the entity's JSON schema
- Slug in frontmatter matches the filename
- Cross-entity reference integrity (model->title, title->model, etc.)
- Wikilink prefixes in prose use the canonical kebab-case entity_type form

Usage:
    python scripts/validate_catalog.py
    python scripts/validate_catalog.py --quiet
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from catalog_loader import (  # noqa: E402
    _DIR_ENTITY_TYPE,
    CatalogRecord,
    LocationStructureError,
    iter_all,
)


def _collect_records(catalog_dir: Path | None) -> list[CatalogRecord]:
    """Collect all records, printing parse/validation warnings to stderr."""
    return list(iter_all(catalog_dir=catalog_dir, validate=True))


def _check_slug_filename_match(records: list[CatalogRecord]) -> list[str]:
    """Check that each record's slug matches its filename."""
    errors = []
    for r in records:
        expected = r.file_path.stem
        if r.slug != expected:
            errors.append(
                f"{r.file_path}: slug '{r.slug}' does not match filename '{expected}'"
            )
    return errors


def _check_uniqueness(records: list[CatalogRecord]) -> list[str]:
    """Check slug uniqueness within each entity type.

    For location records, uniqueness is scoped to the parent directory
    (e.g. two cities named 'portland' are fine if they sit under
    different subdivisions).
    """
    errors = []
    by_type: dict[str, dict[str, Path]] = {}
    for r in records:
        bucket = by_type.setdefault(r.entity_type, {})
        if r.entity_type == "location":
            # Use the parent directory path + slug as the uniqueness key.
            key = f"{r.file_path.parent}:{r.slug}"
        else:
            key = r.slug
        if key in bucket:
            errors.append(
                f"Duplicate {r.entity_type} slug '{r.slug}': "
                f"{bucket[key]} and {r.file_path}"
            )
        else:
            bucket[key] = r.file_path
    return errors


def _check_opdb_id_uniqueness(records: list[CatalogRecord]) -> list[str]:
    """Check OPDB IDs are unique across model files."""
    errors = []
    seen: dict[str, Path] = {}
    for r in records:
        if r.entity_type != "model":
            continue
        opdb_id = r.frontmatter.get("opdb_id")
        if opdb_id is None:
            continue
        if opdb_id in seen:
            errors.append(
                f"Duplicate opdb_id '{opdb_id}': {seen[opdb_id]} and {r.file_path}"
            )
        else:
            seen[opdb_id] = r.file_path
    return errors


def _check_cross_references(records: list[CatalogRecord]) -> list[str]:
    """Check that slug references resolve to existing records."""
    errors = []

    # Build lookup sets.
    slugs_by_type: dict[str, set[str]] = {}
    for r in records:
        slugs_by_type.setdefault(r.entity_type, set()).add(r.slug)

    # Reference checks.
    ref_checks: list[tuple[str, str, str]] = [
        # (source_entity_type, frontmatter_field, target_entity_type)
        ("model", "title_slug", "title"),
        ("model", "corporate_entity_slug", "corporate_entity"),
        ("model", "variant_of", "model"),
        ("model", "converted_from", "model"),
        ("model", "remake_of", "model"),
        ("model", "display_type_slug", "display_type"),
        ("model", "display_subtype_slug", "display_subtype"),
        ("model", "technology_generation_slug", "technology_generation"),
        ("model", "technology_subgeneration_slug", "technology_subgeneration"),
        ("model", "system_slug", "system"),
        ("model", "cabinet_slug", "cabinet"),
        ("model", "game_format_slug", "game_format"),
        ("title", "franchise_slug", "franchise"),
        ("title", "series_slug", "series"),
        ("system", "manufacturer_slug", "manufacturer"),
        ("system", "technology_subgeneration_slug", "technology_subgeneration"),
        ("corporate_entity", "manufacturer_slug", "manufacturer"),
        ("display_subtype", "display_type_slug", "display_type"),
        ("technology_subgeneration", "technology_generation_slug", "technology_generation"),
    ]

    for src_type, field, target_type in ref_checks:
        target_slugs = slugs_by_type.get(target_type, set())
        for r in records:
            if r.entity_type != src_type:
                continue
            value = r.frontmatter.get(field)
            if value is None:
                continue
            if value not in target_slugs:
                errors.append(
                    f"{r.file_path}: {field} '{value}' not found in {target_type}/"
                )

    # Check model tag_slugs -> tag.
    tag_slugs = slugs_by_type.get("tag", set())
    for r in records:
        if r.entity_type != "model":
            continue
        for ts in r.frontmatter.get("tag_slugs", []):
            if ts not in tag_slugs:
                errors.append(f"{r.file_path}: tag_slug '{ts}' not found in tags/")

    # Check model reward_type_slugs -> reward_type.
    reward_type_slugs = slugs_by_type.get("reward_type", set())
    for r in records:
        if r.entity_type != "model":
            continue
        for rs in r.frontmatter.get("reward_type_slugs", []):
            if rs not in reward_type_slugs:
                errors.append(f"{r.file_path}: reward_type_slug '{rs}' not found in reward_types/")

    # Check credit_refs person_slug -> person.
    person_slugs = slugs_by_type.get("person", set())
    for r in records:
        if r.entity_type not in ("model", "series"):
            continue
        for cr in r.frontmatter.get("credit_refs", []):
            ps = cr.get("person_slug")
            if ps and ps not in person_slugs:
                errors.append(
                    f"{r.file_path}: credit person_slug '{ps}' not found in people/"
                )

    return errors


_WIKILINK_RE = re.compile(r"\[\[([a-z][a-z0-9_-]*):")


def _canonical_link_prefixes() -> set[str]:
    """Canonical wikilink prefixes — kebab-case form of every entity_type."""
    return {etype.replace("_", "-") for etype in _DIR_ENTITY_TYPE.values()}


def _check_wikilink_prefixes(records: list[CatalogRecord]) -> list[str]:
    """Check that every [[prefix:id]] in record bodies uses a canonical entity_type.

    The wikilink prefix on the left of the colon must be the kebab-case singular
    form of an entity_type (e.g. `[[gameplay-feature:multiball]]`). The pinbase
    renderer keys on entity_type; un-hyphenated forms like `gameplayfeature` or
    snake_case forms like `gameplay_feature` will silently fail to resolve.
    """
    errors = []
    canonical = _canonical_link_prefixes()
    canonical_by_normalized = {
        c.replace("-", ""): c for c in canonical
    }
    for r in records:
        seen: set[str] = set()
        for match in _WIKILINK_RE.finditer(r.description):
            prefix = match.group(1)
            if prefix in canonical or prefix in seen:
                continue
            seen.add(prefix)
            suggestion = canonical_by_normalized.get(
                prefix.replace("-", "").replace("_", "")
            )
            if suggestion:
                errors.append(
                    f"{r.file_path}: unknown wikilink prefix '[[{prefix}:...]]' "
                    f"(use '[[{suggestion}:...]]')"
                )
            else:
                errors.append(
                    f"{r.file_path}: unknown wikilink prefix '[[{prefix}:...]]'"
                )
    return errors


def _check_self_referential(records: list[CatalogRecord]) -> list[str]:
    """Check for self-referential or chained variant_of relationships."""
    errors = []

    model_variant: dict[str, str | None] = {}
    for r in records:
        if r.entity_type != "model":
            continue
        model_variant[r.slug] = r.frontmatter.get("variant_of")

    for slug, variant_of in model_variant.items():
        if variant_of is None:
            continue
        if variant_of == slug:
            errors.append(f"models/{slug}.md: self-referential variant_of")
            continue
        # Check for chains (variant_of pointing to another variant).
        parent_variant = model_variant.get(variant_of)
        if parent_variant is not None:
            errors.append(
                f"models/{slug}.md: chained variant_of "
                f"('{slug}' -> '{variant_of}' -> '{parent_variant}')"
            )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate catalog Markdown records")
    parser.add_argument(
        "--catalog-dir",
        type=Path,
        default=None,
        help="Override the catalog/ directory path",
    )
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    args = parser.parse_args()

    try:
        records = _collect_records(args.catalog_dir)
    except LocationStructureError as exc:
        print(f"Location structure error: {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        # Summary by type.
        counts: dict[str, int] = {}
        for r in records:
            counts[r.entity_type] = counts.get(r.entity_type, 0) + 1
        print(f"Loaded {len(records)} records:")
        for etype, count in sorted(counts.items()):
            print(f"  {etype}: {count}")

    all_errors: list[str] = []
    all_errors.extend(_check_slug_filename_match(records))
    all_errors.extend(_check_uniqueness(records))
    all_errors.extend(_check_opdb_id_uniqueness(records))
    all_errors.extend(_check_cross_references(records))
    all_errors.extend(_check_wikilink_prefixes(records))
    all_errors.extend(_check_self_referential(records))

    if all_errors:
        print(f"\n{len(all_errors)} error(s):", file=sys.stderr)
        for err in all_errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    if not args.quiet:
        print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
