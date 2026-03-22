"""Shared frontmatter parsing and validation utilities for catalog markdown files."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = _REPO_ROOT / "schema"

# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

_schema_cache: dict[str, dict] = {}


def _load_schema(schema_name: str) -> dict | None:
    """Load and cache a JSON schema by name."""
    if schema_name in _schema_cache:
        return _schema_cache[schema_name]
    schema_path = SCHEMA_DIR / f"{schema_name}.schema.json"
    if not schema_path.exists():
        return None
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _schema_cache[schema_name] = schema
    return schema


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

# Characters/patterns that require quoting in YAML scalar values.
_YAML_NEEDS_QUOTING = re.compile(
    r"""[:#{}\[\]&*?|>!%@`]"""  # special YAML indicators
    r"""|^['"]"""  # leading quote
    r"""|^\s|\s$"""  # leading/trailing whitespace
    r"""|^(true|false|yes|no|null|~)$"""  # YAML booleans / null (case-insensitive)
    r"""|^-?\d"""  # starts like a number
    r"""|\n""",  # contains newline
    re.IGNORECASE,
)


def yaml_quote(value: str) -> str:
    """Return *value* quoted for use as a YAML scalar if necessary.

    Uses double-quotes so that values containing single quotes are
    handled correctly.  Values that are safe as bare scalars are
    returned unchanged.  Empty strings are always quoted.
    """
    if not value or _YAML_NEEDS_QUOTING.search(value):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return value


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


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


def parse_markdown_file(file_path: Path) -> tuple[dict, str] | None:
    """Parse a Markdown file with YAML frontmatter.

    Returns (frontmatter_dict, body_text) or None on parse failure.
    Logs warnings instead of raising on malformed files.
    """
    text = file_path.read_text(encoding="utf-8")

    try:
        frontmatter_block, body = parse_frontmatter(text)
    except ValueError as exc:
        logger.warning("%s: %s", file_path, exc)
        return None

    frontmatter_text = frontmatter_block.strip().removeprefix("---").removesuffix("---").strip()

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as exc:
        logger.warning("YAML parse error in %s: %s", file_path, exc)
        return None

    if not isinstance(frontmatter, dict):
        logger.warning("Frontmatter is not a mapping in %s", file_path)
        return None

    return frontmatter, body


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Optional dependency: jsonschema is used if installed but not required
# at import time so the module can be loaded in lightweight contexts.
try:
    import jsonschema

    _HAS_JSONSCHEMA = True
except ModuleNotFoundError:  # pragma: no cover
    _HAS_JSONSCHEMA = False


def validate_frontmatter(
    frontmatter: dict, schema_name: str, file_path: Path
) -> list[str]:
    """Validate frontmatter against a JSON schema.

    Returns a list of error messages (empty if valid).
    """
    if not _HAS_JSONSCHEMA:
        return []

    schema = _load_schema(schema_name)
    if schema is None:
        return [f"No schema found: {schema_name}.schema.json"]

    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in sorted(validator.iter_errors(frontmatter), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"{file_path}: {path}: {error.message}")
    return errors
