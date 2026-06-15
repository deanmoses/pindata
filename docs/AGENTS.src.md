# Development Guide

START_IGNORE

This is the source file for generating [`CLAUDE.md`](../CLAUDE.md) and [`AGENTS.md`](../AGENTS.md).
Do not edit those files directly - edit this file instead.

Regenerate with: make agent-docs

Markers:

- START_CLAUDE / END_CLAUDE - content appears only in [`CLAUDE.md`](../CLAUDE.md)
- START_AGENTS / END_AGENTS - content appears only in [`AGENTS.md`](../AGENTS.md)
- START_IGNORE / END_IGNORE - content stripped from both (like this block)

END_IGNORE

This file provides guidance to AI programming agents when working with code in this repository.

## Project Overview

Pindata is a standalone data catalog for pinball machines. It contains **only data and tooling** — no web framework, no frontend, no backend.

**What lives here:**

- **Baseline seed catalog data**: the giant corpus of data that was synthesized from IPDB, OPDB, web scrapes and other sources. This forms the foundation of the catalog, and is ingested once on a fresh database and then never ingested again. It lives at `catalog/<entity_type_plural>/<slug>.md`, e.g. `catalog/gameplay_features/multiball.md`). Format: Markdown files with YAML frontmatter, one file per entity.

**Data patches** — the source-attributed corrections layered on top of this seed after a database is created — are authored, validated, and published from a **separate repo, `flippatch`** (`../flippatch`), not here. pindata is the immutable baseline they target. See [Data Patches](#data-patches) below.

Supporting stuff:

- JSON schemas for validating the catalog
- Python scripts for catalog validation, export, and upload to Cloudflare R2, from which downstream projects pull it.

**Downstream consumers:**

- [Pinexplore](https://github.com/deanmoses/pinexplore) — analyzes, validates, and explores pinball data
- [Flipcommons](https://github.com/The-Flip/flipcommons) — collaborative pinball catalog encyclopedia wiki website + production DB, in Django + SvelteKit; applies data patches via `ingest_patches`

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Getting Started

```bash
cp .env.example .env
uv sync
```

## Development Commands

```bash
make validate     # Validate catalog records against schemas
make export       # Export catalog to JSON in export/
make push         # Export + push catalog JSON to Cloudflare R2
make clean        # Remove export/ directory
make agent-docs   # Regenerate CLAUDE.md and AGENTS.md
```

## Project Structure

```text
catalog/          Markdown entity files — one file per pinball entity
schema/           JSON Schema files for catalog frontmatter validation
scripts/          Python tooling (loader, validator, exporter, R2 push)
docs/             Documentation source files
export/           (gitignored) JSON build artifacts from `make export`
```

## Catalog Data

See [docs/Catalog.md](Catalog.md) for full details on the catalog format.

**Key points:**

- Each entity is a Markdown file in `catalog/<entity_type>/<slug>.md`
- YAML frontmatter holds structured fields; optional Markdown body for prose
- Filename = slug (no `slug` field in frontmatter)
- Omit optional fields — don't set them to null
- Cross-references in prose use `[[<entity-type>:<public-id>]]` wikilink syntax — `<entity-type>` is the **kebab-case singular** form (e.g. `[[manufacturer:bally]]`, `[[gameplay-feature:multiball]]`, `[[display-type:dot-matrix]]`)
- Schemas in `schema/` define valid frontmatter per entity type

**Entity types** (the form to use as a wikilink prefix — kebab-case singular): cabinet, corporate-entity, credit-role, display-subtype, display-type, franchise, game-format, gameplay-feature, location, manufacturer, model, person, reward-type, series, system, tag, technology-generation, technology-subgeneration, theme, title

The `catalog/` filesystem uses the snake_case plural form as the directory name (`catalog/gameplay_features/`); the wikilink prefix is always the kebab-case singular form (`[[gameplay-feature:...]]`).

Validate catalog records with `make validate` — see [Validation](#validation).

## Data Patches

Data patches — the small, source-attributed YAML files that correct or extend the catalog after a database is seeded — are **no longer authored here.** They live in the sibling **flippatch** repo (`../flippatch`), which owns the patch format, the `patchkit` generator, structural validation, and the R2 publish step. The canonical patch documentation lives in `../flipcommons/docs/` (DataPatches.md, DataPatchAuthoring.md, DataPatchKit.md); flippatch's own docs point there.

pindata is the immutable baseline these patches target. It neither authors patches nor applies them — applying is the job of flipcommons' `ingest_patches`.

## Validation

`make validate` validates the catalog with `scripts/validate_catalog.py`: YAML parsing, JSON schema conformance, slug/filename match, slug uniqueness, OPDB ID uniqueness, cross-entity reference integrity, wikilink prefix canonicalization, and self-referential variant checks.

To run it on its own while iterating:

```bash
python3 scripts/validate_catalog.py
```

START_CLAUDE

## Tool Usage

Use Context7 (`mcp__context7__resolve-library-id` and `mcp__context7__query-docs`) to look up current documentation when needed.

GitHub access:

- Use the GitHub MCP server for read-only operations (listing/viewing issues, PRs, commits, files)
- Use the `gh` CLI for writes or auth-required actions (creating/updating/commenting/merging)

END_CLAUDE

START_AGENTS

## Codex Cloud Environment Setup

**Setup command**: `uv sync`

After setup, use the standard commands:

```bash
make validate     # Validate catalog records
make export       # Export to JSON
```

**Notes:**

- Use the `gh` CLI for GitHub operations
- Data patch authoring lives in the sibling `flippatch` repo, not here — see [Data Patches](#data-patches). Only catalog work and `make validate`/`make export` are relevant in Codex Cloud.

END_AGENTS

## Generated Agent Docs

`CLAUDE.md` and `AGENTS.md` are generated from `docs/AGENTS.src.md`. Do not edit them directly — edit the source file and run `make agent-docs` to regenerate.

## Testing

- For any change, run `make validate` to check catalog integrity.
- When adding or editing catalog records, validate cross-references resolve correctly.

## Test-Driven Development (TDD)

This project follows Test-Driven Development. When fixing a bug, you MUST write failing test(s) that exercise the bug **before** writing the fix. Confirm the test fails for the expected reason, then implement the fix and verify the test passes.

## Rules

- Don't silence linter warnings — fix the underlying issue
- Never hardcode secrets — use environment variables via `.env`
- Describe your approach before implementing non-trivial changes
- When writing or editing Markdown, never hard-wrap prose. Write each paragraph and list item as a single long line and let the viewer soft-wrap it. Hard line breaks inserted to fit ~80 columns produce choppy short lines in a narrow viewport. (Tables, code blocks and the existing line structure of generated files are exempt.)
