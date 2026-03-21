#!/usr/bin/env python3
"""Regenerate theme markdown files from the theme vocabulary JSON.

Deletes all existing theme files and generates new ones from
the theme_cleanup.json vocabulary. Each theme becomes a markdown
file with YAML frontmatter containing name, aliases, and parents.

Usage:
    uv run python scripts/generate_themes.py <json_path> [--dry-run]

Example:
    uv run python scripts/generate_themes.py ../pinexplore/local_sources/themes.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from slugify import slugify

REPO_ROOT = Path(__file__).resolve().parent.parent
THEME_DIR = REPO_ROOT / "catalog" / "themes"


def theme_to_yaml(theme: dict) -> str:
    """Render a theme dict as YAML frontmatter markdown."""
    lines = ["---"]
    lines.append(f"name: {theme['name']}")

    aliases = theme.get("aliases")
    if aliases:
        lines.append("aliases:")
        for a in aliases:
            lines.append(f"  - {a}")

    parents = theme.get("parents")
    if parents:
        lines.append("parents:")
        for p in parents:
            lines.append(f"  - {p}")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="Path to themes JSON file")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print what would be done"
    )
    args = parser.parse_args()

    with open(args.json_path) as f:
        data = json.load(f)

    themes = data["themes"]

    # Check for slug collisions
    slugs: dict[str, str] = {}
    for theme in themes:
        slug = slugify(theme["name"])
        if slug in slugs:
            print(
                f"ERROR: slug collision: {theme['name']!r} and "
                f"{slugs[slug]!r} both slugify to {slug!r}",
                file=sys.stderr,
            )
            sys.exit(1)
        slugs[slug] = theme["name"]

    if args.dry_run:
        print(f"Would delete {THEME_DIR}/ and recreate with {len(themes)} files")
        for theme in themes[:5]:
            slug = slugify(theme["name"])
            print(f"\n--- {slug}.md ---")
            print(theme_to_yaml(theme), end="")
        print(f"\n... and {len(themes) - 5} more")
        return

    # Delete existing theme files
    if THEME_DIR.exists():
        existing = list(THEME_DIR.glob("*.md"))
        for f in existing:
            f.unlink()
        print(f"Deleted {len(existing)} existing theme files")

    # Generate new files
    THEME_DIR.mkdir(parents=True, exist_ok=True)
    for theme in themes:
        slug = slugify(theme["name"])
        path = THEME_DIR / f"{slug}.md"
        path.write_text(theme_to_yaml(theme))

    print(f"Generated {len(themes)} theme files in {THEME_DIR}/")


if __name__ == "__main__":
    main()
