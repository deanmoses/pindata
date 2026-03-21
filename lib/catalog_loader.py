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
    "gameplay_features": "taxonomy",
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


def iter_all(
    *, catalog_dir: Path | None = None, validate: bool = True
) -> Iterator[CatalogRecord]:
    """Iterate over every catalog record across all entity types."""
    for dir_name in _DIR_ENTITY_TYPE:
        yield from _iter_directory(dir_name, catalog_dir=catalog_dir, validate=validate)
