# Pindata

A curated catalog of pinball machines, manufacturers, designers, and related entities.

## Overview

Pindata is the canonical data source for the pinball catalog ecosystem.

Each entity (machine, manufacturer, person, etc.) is a single Markdown file with structured YAML frontmatter and optional prose.

The data is validated against JSON schemas, exported to JSON, and published to Cloudflare R2 for downstream consumers.

**Downstream projects:**

- [Pinexplore](https://github.com/deanmoses/pinexplore) — analyzes, validates, and explores pinball data
- [Pinbase](https://github.com/deanmoses/pinbase) — pinball catalog website

## Why Markdown?

- Ergonomic for both humans and AI agents to read and write
- One file per entity keeps diffs small and reviewable
- YAML frontmatter for structured data, Markdown body for prose
- Git-native versioning with human-readable diffs

## Entity types

| Directory | Count | Description |
|---|---|---|
| `models/` | ~7k | Individual pinball machines |
| `titles/` | ~6k | Title groupings (e.g. all versions of "Medieval Madness") |
| `corporate_entities/` | ~800 | Legal entities behind the brands |
| `manufacturers/` | ~700 | Brand names (Williams, Bally, Stern, etc.) |
| `people/` | ~600 | Designers, artists, programmers |
| `themes/` | ~600 | Thematic categories |
| `franchises/` | ~130 | IP franchises (Star Wars, Indiana Jones, etc.) |
| `systems/` | ~70 | Hardware platforms (WPC-95, System 11, etc.) |
| `series/` | ~10 | Curated series (Eight Ball trilogy, etc.) |
| `cabinets/` | ~10 | Standard, widebody, countertop, mini |
| + 8 more taxonomy types | | Display types, credit roles, tags, etc. |

## File format

```markdown
---
name: Medieval Madness
year: 1997
technology_generation_slug: solid-state
---

Medieval Madness is widely regarded as one of the defining
[[manufacturer:williams]] games of the late [[system:wpc-95]] era.
```

- **Filename = slug** — `models/medieval-madness.md` has slug `medieval-madness`
- **Omit empty fields** — don't set them to null
- **Wikilinks** for cross-references — `[[<entity-type>:<public-id>]]`

See [docs/Catalog.md](docs/Catalog.md) for full details.

## Getting started

### Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
cp .env.example .env
uv sync
```

### Commands

```bash
make validate     # Validate catalog records against schemas
make export       # Export catalog to JSON in export/
make push         # Export + push JSON to Cloudflare R2
make clean        # Remove export/ directory
```

## Project structure

```
catalog/          Markdown entity files — one file per pinball entity
schema/           JSON Schema files for frontmatter validation
scripts/          Python tooling (loader, validator, exporter, R2 push)
docs/             Documentation source files
export/           (gitignored) JSON build artifacts
```

## Validation

```bash
make validate
```

Checks YAML parsing, JSON schema conformance, slug/filename consistency, uniqueness constraints, cross-entity reference integrity, and self-referential variant detection.
