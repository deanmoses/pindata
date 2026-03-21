#!/usr/bin/env python3
"""Set YAML frontmatter fields on a catalog markdown file.

Reads a catalog markdown file, inserts or updates one or more frontmatter
fields in canonical schema order, and writes the result back. Validates
the updated frontmatter against the entity's JSON schema.

By default, refuses to overwrite an existing field value. Use --overwrite
to replace existing values.

When using from Python, it will be simpler to import apply_fields() and
call it directly.

Usage:
    uv run python scripts/apply_fields.py catalog/titles/alien.md franchise_slug=alien
    uv run python scripts/apply_fields.py catalog/titles/foo.md franchise_slug=alien series_slug=bar
    uv run python scripts/apply_fields.py --overwrite catalog/titles/alien.md franchise_slug=new
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import yaml  # noqa: E402
from catalog_loader import _DIR_SCHEMA_MAP  # noqa: E402
from frontmatter import _SCHEMA_DIR, parse_frontmatter, validate_frontmatter  # noqa: E402

__all__ = ["apply_fields"]


def _load_schema_properties(schema_name: str) -> list[str]:
    """Load a JSON schema and return its property names in order."""
    schema_path = _SCHEMA_DIR / f"{schema_name}.schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return list(schema.get("properties", {}).keys())


def _resolve_schema_name(catalog_path: Path) -> str:
    """Determine the schema name from a catalog file path."""
    dir_name = catalog_path.resolve().parent.name
    schema_name = _DIR_SCHEMA_MAP.get(dir_name)
    if schema_name is None:
        raise ValueError(
            f"Cannot determine schema for directory '{dir_name}'. "
            f"Known directories: {', '.join(sorted(_DIR_SCHEMA_MAP))}"
        )
    return schema_name


def _insert_field(frontmatter_lines: list[str], key: str, value: str, property_order: list[str]) -> list[str]:
    """Insert a key: value line at the correct position in frontmatter lines.

    frontmatter_lines[0] is '---' and frontmatter_lines[-1] is '---'.
    Fields are inserted according to the canonical property_order from
    the JSON schema.
    """
    target_idx = property_order.index(key) if key in property_order else len(property_order)

    # Find the best insertion point: after the last existing field that
    # comes before this field in schema order.
    insert_after = 0  # after opening '---'
    for i, line in enumerate(frontmatter_lines):
        if i == 0 or i == len(frontmatter_lines) - 1:
            continue
        # Extract the field name from lines like "key: value" or "key:"
        # Skip continuation lines (indented, like list items under abbreviations)
        if line.startswith(" ") or line.startswith("-"):
            continue
        field_name = line.split(":")[0].strip()
        if field_name in property_order:
            field_idx = property_order.index(field_name)
            if field_idx < target_idx:
                # Move past this field and any continuation lines
                insert_after = i
                for j in range(i + 1, len(frontmatter_lines) - 1):
                    if frontmatter_lines[j].startswith(" ") or frontmatter_lines[j].startswith("-"):
                        insert_after = j
                    else:
                        break

    new_line = f"{key}: {value}"
    result = frontmatter_lines.copy()
    result.insert(insert_after + 1, new_line)
    return result


def apply_fields(
    catalog_path: Path,
    fields: dict[str, str],
    *,
    overwrite: bool = False,
) -> None:
    """Set frontmatter fields on *catalog_path*.

    Preserves existing frontmatter and body. Inserts fields in canonical
    schema order. Validates the result against the JSON schema.

    Raises ``FileNotFoundError`` if the file or schema doesn't exist,
    ``ValueError`` if a field isn't in the schema or frontmatter is invalid,
    and ``RuntimeError`` if a field already has a value and *overwrite* is False.
    """
    if not catalog_path.is_file():
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    schema_name = _resolve_schema_name(catalog_path)
    property_order = _load_schema_properties(schema_name)

    # Validate field names against schema
    for key in fields:
        if key not in property_order:
            raise ValueError(
                f"Field '{key}' is not in the {schema_name} schema. "
                f"Valid fields: {', '.join(property_order)}"
            )

    original = catalog_path.read_text(encoding="utf-8")
    frontmatter_block, body = parse_frontmatter(original)

    # Parse existing frontmatter to check for conflicts
    fm_text = frontmatter_block.strip().removeprefix("---").removesuffix("---").strip()
    existing_fm = yaml.safe_load(fm_text) or {}

    for key, value in fields.items():
        if key in existing_fm and existing_fm[key] is not None and str(existing_fm[key]) != "":
            if not overwrite:
                raise RuntimeError(
                    f"{catalog_path}: field '{key}' already has value "
                    f"'{existing_fm[key]}'. Use overwrite=True to replace it."
                )

    # Build the new frontmatter by string manipulation
    lines = frontmatter_block.rstrip("\n").split("\n")
    # lines[0] = '---', lines[-1] = '---'

    for key, value in fields.items():
        if key in existing_fm and existing_fm[key] is not None and str(existing_fm[key]) != "":
            # Overwrite: find and replace the line
            for i, line in enumerate(lines):
                if line.startswith(f"{key}:"):
                    lines[i] = f"{key}: {value}"
                    break
        else:
            lines = _insert_field(lines, key, value, property_order)

    new_frontmatter = "\n".join(lines) + "\n"

    # Reassemble
    if body:
        new_content = new_frontmatter + "\n" + body + "\n"
    else:
        new_content = new_frontmatter

    # Validate before writing
    new_fm_text = new_frontmatter.strip().removeprefix("---").removesuffix("---").strip()
    new_fm = yaml.safe_load(new_fm_text) or {}
    errors = validate_frontmatter(new_fm, schema_name, catalog_path)
    if errors:
        raise ValueError(
            f"Validation failed after applying fields:\n" + "\n".join(errors)
        )

    catalog_path.write_text(new_content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Set YAML frontmatter fields on a catalog markdown file.",
    )
    parser.add_argument(
        "catalog_file",
        type=Path,
        help="Path to the catalog markdown file to update",
    )
    parser.add_argument(
        "fields",
        nargs="+",
        help="Fields to set as key=value pairs (e.g., franchise_slug=alien)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting existing field values",
    )
    args = parser.parse_args(argv)

    # Parse key=value pairs
    field_dict: dict[str, str] = {}
    for field_spec in args.fields:
        if "=" not in field_spec:
            print(f"Error: invalid field spec '{field_spec}' (expected key=value)", file=sys.stderr)
            return 1
        key, value = field_spec.split("=", 1)
        field_dict[key] = value

    try:
        apply_fields(args.catalog_file, field_dict, overwrite=args.overwrite)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    field_summary = ", ".join(f"{k}={v}" for k, v in field_dict.items())
    print(f"Applied {field_summary} to {args.catalog_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
