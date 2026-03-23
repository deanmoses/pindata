"""Shared loader for catalog/**/*.md Markdown records.

Parses YAML frontmatter and Markdown body from per-entity files.
Validates frontmatter against JSON schemas in schema/.
Exposes entity iterators for titles, models, people, manufacturers,
series, systems, franchises, themes, and taxonomy records.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from frontmatter import parse_markdown_file, validate_frontmatter

logger = logging.getLogger(__name__)

# Resolve paths relative to the repo root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_CATALOG_DIR = _REPO_ROOT / "catalog"


@dataclass(frozen=True)
class CatalogRecord:
    """A single parsed Markdown record."""

    entity_type: str
    slug: str
    frontmatter: dict
    description: str
    file_path: Path




# ---------------------------------------------------------------------------
# Directory → schema mapping
# ---------------------------------------------------------------------------

# Maps directory names under catalog/ to their schema file names.
DIR_SCHEMA_MAP: dict[str, str] = {
    "titles": "title",
    "models": "model",
    "people": "person",
    "manufacturers": "manufacturer",
    "series": "series",
    "systems": "system",
    "franchises": "franchise",
    "themes": "theme",
    "corporate_entities": "corporate_entity",
    # Taxonomy directories that share the generic taxonomy schema:
    "cabinets": "taxonomy",
    "credit_roles": "taxonomy",
    "display_types": "taxonomy",
    "game_formats": "taxonomy",
    "gameplay_features": "gameplay_feature",
    "reward_types": "taxonomy",
    "tags": "taxonomy",
    # Taxonomy directories with parent-child schemas:
    "display_subtypes": "display_subtype",
    "technology_generations": "technology_generation",
    "technology_subgenerations": "technology_subgeneration",
}

# The entity_type value for each directory.
_DIR_ENTITY_TYPE: dict[str, str] = {
    "titles": "title",
    "models": "model",
    "people": "person",
    "manufacturers": "manufacturer",
    "series": "series",
    "systems": "system",
    "franchises": "franchise",
    "themes": "theme",
    "corporate_entities": "corporate_entity",
    "cabinets": "cabinet",
    "credit_roles": "credit_role",
    "display_types": "display_type",
    "display_subtypes": "display_subtype",
    "game_formats": "game_format",
    "gameplay_features": "gameplay_feature",
    "reward_types": "reward_type",
    "tags": "tag",
    "technology_generations": "technology_generation",
    "technology_subgenerations": "technology_subgeneration",
}


# ---------------------------------------------------------------------------
# Entity iterators
# ---------------------------------------------------------------------------


def _iter_directory(
    dir_name: str,
    *,
    catalog_dir: Path | None = None,
    validate: bool = True,
) -> Iterator[CatalogRecord]:
    """Iterate over all .md files in a catalog subdirectory.

    Yields CatalogRecord instances. Logs warnings for parse/validation
    failures but does not raise.
    """
    base = catalog_dir or _CATALOG_DIR
    directory = base / dir_name
    if not directory.is_dir():
        return

    schema_name = DIR_SCHEMA_MAP.get(dir_name)
    entity_type = _DIR_ENTITY_TYPE.get(dir_name, dir_name)

    for md_file in sorted(directory.glob("*.md")):
        result = parse_markdown_file(md_file)
        if result is None:
            continue

        frontmatter, body = result

        # Validate slug matches filename.
        expected_slug = md_file.stem
        actual_slug = frontmatter.get("slug")
        if actual_slug and actual_slug != expected_slug:
            logger.warning(
                "%s: slug %r does not match filename %r",
                md_file,
                actual_slug,
                expected_slug,
            )

        if validate and schema_name:
            errors = validate_frontmatter(frontmatter, schema_name, md_file)
            for err in errors:
                logger.warning(err)

        yield CatalogRecord(
            entity_type=entity_type,
            slug=frontmatter.get("slug", expected_slug),
            frontmatter=frontmatter,
            description=body,
            file_path=md_file,
        )


def iter_titles(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all title records."""
    return _iter_directory("titles", catalog_dir=catalog_dir, validate=validate)


def iter_models(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all model records."""
    return _iter_directory("models", catalog_dir=catalog_dir, validate=validate)


def iter_people(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all person records."""
    return _iter_directory("people", catalog_dir=catalog_dir, validate=validate)


def iter_manufacturers(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all manufacturer records."""
    return _iter_directory("manufacturers", catalog_dir=catalog_dir, validate=validate)


def iter_corporate_entities(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all corporate entity records."""
    return _iter_directory(
        "corporate_entities", catalog_dir=catalog_dir, validate=validate
    )


def iter_series(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all series records."""
    return _iter_directory("series", catalog_dir=catalog_dir, validate=validate)


def iter_systems(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all system records."""
    return _iter_directory("systems", catalog_dir=catalog_dir, validate=validate)


def iter_franchises(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all franchise records."""
    return _iter_directory("franchises", catalog_dir=catalog_dir, validate=validate)


def iter_themes(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all theme records."""
    return _iter_directory("themes", catalog_dir=catalog_dir, validate=validate)


def iter_taxonomy(
    entity_dir: str,
    *,
    catalog_dir: Path | None = None,
    validate: bool = True,
) -> Iterator[CatalogRecord]:
    """Iterate over a specific taxonomy directory."""
    return _iter_directory(entity_dir, catalog_dir=catalog_dir, validate=validate)


# Convenience: all taxonomy directory names.
TAXONOMY_DIRS = [
    "cabinets",
    "credit_roles",
    "display_types",
    "display_subtypes",
    "game_formats",
    "gameplay_features",
    "tags",
    "technology_generations",
    "technology_subgenerations",
]


def iter_all_taxonomy(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all taxonomy records across all taxonomy directories."""
    for dir_name in TAXONOMY_DIRS:
        yield from _iter_directory(dir_name, catalog_dir=catalog_dir, validate=validate)


class LocationStructureError(Exception):
    """Raised when catalog/locations/ directory structure violates a country's divisions."""


def _iter_locations(
    *,
    catalog_dir: Path | None = None,
    validate: bool = True,
) -> Iterator[CatalogRecord]:
    """Iterate over the hierarchical locations directory.

    Phase 1: Read country files (top-level .md in locations/).
    Phase 2: Validate directory structure against each country's divisions.
    Phase 3: Walk subdirectories, yielding records with synthetic parent fields.

    Raises LocationStructureError if the directory tree doesn't match
    the declared divisions for any country.
    """
    base = catalog_dir or _CATALOG_DIR
    locations_dir = base / "locations"
    if not locations_dir.is_dir():
        return

    # Phase 1: Read country files.
    countries: dict[str, list[str]] = {}  # slug -> divisions list

    for md_file in sorted(locations_dir.glob("*.md")):
        result = parse_markdown_file(md_file)
        if result is None:
            continue

        frontmatter, body = result
        slug = md_file.stem
        divisions = frontmatter.get("divisions", [])
        countries[slug] = divisions

        if validate:
            errors = validate_frontmatter(frontmatter, "location_country", md_file)
            for err in errors:
                logger.warning(err)

        yield CatalogRecord(
            entity_type="location",
            slug=slug,
            frontmatter={**frontmatter, "location_path": slug, "type": "country"},
            description=body,
            file_path=md_file,
        )

    # Phase 2 & 3: Walk each country's subdirectory.
    for country_slug, divisions in countries.items():
        country_dir = locations_dir / country_slug
        if not country_dir.is_dir():
            continue

        yield from _walk_location_subtree(
            country_dir,
            divisions=divisions,
            depth=0,
            parent_slugs={"country_slug": country_slug},
            path_prefix=country_slug,
            country_slug=country_slug,
            validate=validate,
        )

    # Check for subdirectories that don't correspond to any country file.
    for entry in sorted(locations_dir.iterdir()):
        if entry.is_dir() and not entry.name.startswith((".", "__")):
            if entry.name not in countries:
                raise LocationStructureError(
                    f"{entry}: directory has no matching country file "
                    f"locations/{entry.name}.md"
                )


def _walk_location_subtree(
    directory: Path,
    *,
    divisions: list[str],
    depth: int,
    parent_slugs: dict[str, str],
    path_prefix: str,
    country_slug: str,
    validate: bool,
) -> Iterator[CatalogRecord]:
    """Recursively walk a location subtree, yielding records at each level."""
    if depth >= len(divisions):
        raise LocationStructureError(
            f"{directory}: unexpected nesting beyond declared divisions "
            f"for country '{country_slug}' (divisions: {divisions})"
        )

    allowed_types = set(divisions[depth].split(","))
    is_city = allowed_types == {"city"}
    is_leaf = depth == len(divisions) - 1
    schema_name = "location_city" if is_city else "location_subdivision"

    for md_file in sorted(directory.glob("*.md")):
        result = parse_markdown_file(md_file)
        if result is None:
            continue

        frontmatter, body = result
        slug = md_file.stem

        # Validate type field against the allowed set for this division level.
        record_type = frontmatter.get("type")
        if not record_type and len(allowed_types) > 1:
            raise LocationStructureError(
                f"{md_file}: missing 'type' field at a multi-type division "
                f"level {sorted(allowed_types)} for country '{country_slug}' "
                f"(divisions: {divisions})"
            )
        if record_type and record_type not in allowed_types:
            raise LocationStructureError(
                f"{md_file}: type '{record_type}' is not in allowed types "
                f"{sorted(allowed_types)} at depth {depth} for country "
                f"'{country_slug}' (divisions: {divisions})"
            )

        if validate:
            errors = validate_frontmatter(frontmatter, schema_name, md_file)
            for err in errors:
                logger.warning(err)

        # Build frontmatter with synthetic parent fields + location_path.
        # Parent slugs derived from the path are authoritative.
        location_path = f"{path_prefix}/{slug}"
        conflicts = set(parent_slugs) & set(frontmatter)
        if conflicts:
            raise LocationStructureError(
                f"{md_file}: frontmatter contains fields that conflict with "
                f"path-derived parent slugs: {conflicts}"
            )
        augmented = {**frontmatter, **parent_slugs, "location_path": location_path}

        yield CatalogRecord(
            entity_type="location",
            slug=slug,
            frontmatter=augmented,
            description=body,
            file_path=md_file,
        )

        # Recurse into matching subdirectory if not at leaf level.
        if not is_leaf:
            subdir = directory / slug
            if subdir.is_dir():
                yield from _walk_location_subtree(
                    subdir,
                    divisions=divisions,
                    depth=depth + 1,
                    parent_slugs={
                        **parent_slugs,
                        f"{record_type or sorted(allowed_types)[0]}_slug": slug,
                    },
                    path_prefix=location_path,
                    country_slug=country_slug,
                    validate=validate,
                )

    # Check for unexpected subdirectories.
    md_stems = {f.stem for f in directory.glob("*.md")}
    for entry in sorted(directory.iterdir()):
        if not entry.is_dir() or entry.name.startswith((".", "__")):
            continue
        if is_leaf:
            raise LocationStructureError(
                f"{entry}: unexpected subdirectory at leaf level "
                f"'{divisions[depth]}' for country '{country_slug}' "
                f"(divisions: {divisions})"
            )
        if entry.name not in md_stems:
            raise LocationStructureError(
                f"{entry}: subdirectory has no matching file "
                f"{entry.name}.md in {directory}"
            )


def iter_locations(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over all location records."""
    return _iter_locations(catalog_dir=catalog_dir, validate=validate)


def iter_all(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over every catalog record across all entity types."""
    for dir_name in _DIR_ENTITY_TYPE:
        yield from _iter_directory(dir_name, catalog_dir=catalog_dir, validate=validate)
    yield from _iter_locations(catalog_dir=catalog_dir, validate=validate)
