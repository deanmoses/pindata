#!/usr/bin/env python3
"""Apply a description to a catalog markdown file.

Reads a description from a file or stdin and writes it as the body of a
catalog markdown file, preserving existing YAML frontmatter.

By default, refuses to overwrite an existing description.  Use --overwrite
to replace one.

Usage:
    uv run python scripts/apply_description.py catalog/manufacturers/genco.md desc.md
    echo "Some description." | uv run python scripts/apply_description.py catalog/manufacturers/genco.md -
    uv run python scripts/apply_description.py --overwrite catalog/manufacturers/bally.md new_desc.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_frontmatter(text: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter_block, body).

    The frontmatter_block includes the opening and closing ``---``
    delimiters and the trailing newline.  The body is everything after.

    Raises ValueError if the file has no valid frontmatter.
    """
    if not text.startswith("---"):
        raise ValueError("File does not start with frontmatter delimiter (---)")

    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("Unclosed frontmatter (missing closing ---)")

    # Include through the closing "---\n"
    frontmatter_end = end + 4  # len("\n---")
    frontmatter_block = text[:frontmatter_end]

    # Ensure frontmatter block ends with exactly one newline
    if not frontmatter_block.endswith("\n"):
        frontmatter_block += "\n"

    body = text[frontmatter_end:].strip()
    return frontmatter_block, body


def apply_description(
    catalog_path: Path,
    description: str,
    *,
    overwrite: bool = False,
) -> None:
    """Write *description* as the body of *catalog_path*.

    Preserves existing frontmatter.  Raises ``FileNotFoundError`` if the
    catalog file does not exist, ``ValueError`` if the file has no valid
    frontmatter, and ``RuntimeError`` if the file already has a
    description and *overwrite* is False.
    """
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    original = catalog_path.read_text(encoding="utf-8")
    frontmatter_block, existing_body = parse_frontmatter(original)

    if existing_body and not overwrite:
        raise RuntimeError(
            f"{catalog_path} already has a description. "
            "Use --overwrite to replace it."
        )

    description = description.strip()
    if not description:
        raise ValueError("Description is empty")

    new_content = frontmatter_block + "\n" + description + "\n"
    catalog_path.write_text(new_content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply a description to a catalog markdown file.",
    )
    parser.add_argument(
        "catalog_file",
        type=Path,
        help="Path to the catalog markdown file to update",
    )
    parser.add_argument(
        "description_file",
        type=Path,
        nargs="?",
        default=None,
        help="Path to the description file (use - for stdin). "
        "If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing description",
    )
    args = parser.parse_args(argv)

    # Read description
    if args.description_file is None or str(args.description_file) == "-":
        description = sys.stdin.read()
    else:
        if not args.description_file.is_file():
            print(f"Error: description file not found: {args.description_file}", file=sys.stderr)
            return 1
        description = args.description_file.read_text(encoding="utf-8")

    try:
        apply_description(args.catalog_file, description, overwrite=args.overwrite)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Applied description to {args.catalog_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
