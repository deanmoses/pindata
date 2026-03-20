#!/usr/bin/env python3
"""Export catalog/**/*.md to JSON files for R2 upload.

Reads all Markdown records via the catalog loader and writes normalized
JSON arrays to an output directory. These files serve two consumers:

- Django ingest_pinbase command (pinbase pulls from R2)
- DuckDB tables in pinexplore (also pulls from R2)

Usage:
    python scripts/export_catalog_json.py [--output-dir DIR]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from catalog_loader import iter_all

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = REPO_ROOT / "export"


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Export catalog to JSON.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Group records by entity type.
    by_type: dict[str, list[dict]] = {}
    for r in iter_all(validate=False):
        entry = {"slug": r.slug, **r.frontmatter}
        if r.description:
            entry["description"] = r.description
        by_type.setdefault(r.entity_type, []).append(entry)

    for entity_type, records in sorted(by_type.items()):
        out_path = output_dir / f"{entity_type}.json"
        out_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"  {entity_type}: {len(records)} records -> {out_path.name}")

    total = sum(len(r) for r in by_type.values())
    print(f"\nExported {total} records across {len(by_type)} entity types.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
