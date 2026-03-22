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

- Catalog data as Markdown files with YAML frontmatter (one file per entity)
- JSON schemas for validating frontmatter
- Python scripts for validation, JSON export, and R2 upload
- Documentation

**What does NOT live here:**

- Django, SvelteKit, or any web framework code
- Frontend or backend application code
- Database models or migrations

The exported JSON is published to Cloudflare R2, where downstream projects pull it.

**Downstream consumers:**

- [Pinexplore](https://github.com/deanmoses/pinexplore) — analyzes, validates, and explores pinball data
- [Pinbase](https://github.com/deanmoses/pinbase) — pinball catalog website (Django + SvelteKit)

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
make push         # Export + push JSON to Cloudflare R2
make clean        # Remove export/ directory
make agent-docs   # Regenerate CLAUDE.md and AGENTS.md
```

## Project Structure

```text
catalog/          Markdown entity files — one file per pinball entity
schema/           JSON Schema files for frontmatter validation
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
- Cross-references in prose use `[[entity-type:slug]]` wikilink syntax
- Schemas in `schema/` define valid frontmatter per entity type

**Entity types:** models, titles, manufacturers, corporate_entities, people, themes, franchises, systems, series, cabinets, credit_roles, display_types, display_subtypes, game_formats, gameplay_features, tags, technology_generations, technology_subgenerations

## Validation

```bash
make validate
# or directly:
python3 scripts/validate_catalog.py
```

Validates: YAML parsing, JSON schema conformance, slug/filename match, slug uniqueness, OPDB ID uniqueness, cross-entity reference integrity, and self-referential variant checks.

START_CLAUDE

## Tool Usage

Use Context7 (`mcp__context7__resolve-library-id` and `mcp__context7__query-docs`) to look up current documentation when needed.

GitHub access:

- Use the GitHub MCP server for read-only operations (listing/viewing issues, PRs, commits, files)
- Use the `gh` CLI for writes or auth-required actions (creating/updating/commenting/merging)

END_CLAUDE

START_AGENTS

## Environment Setup (Codex Cloud)

**Setup command**: `uv sync`

After setup, use the standard commands:

```bash
make validate     # Validate catalog records
make export       # Export to JSON
```

**Notes:**

- Internet is disabled during task execution — all dependencies must be installed during setup
- Use the `gh` CLI for GitHub operations

END_AGENTS

## Pre-commit Hooks

Pre-commit hooks auto-regenerate `CLAUDE.md` and `AGENTS.md` when `docs/AGENTS.src.md` changes, and block direct edits to those generated files. Hooks also run prettier and markdownlint on documentation, and validate catalog records when `catalog/` or `schema/` files change. Do not edit `CLAUDE.md` or `AGENTS.md` directly — edit `docs/AGENTS.src.md` instead.

## Testing

- For any change, run `make validate` to check catalog integrity.
- When adding or editing catalog records, validate cross-references resolve correctly.

## Test-Driven Development (TDD)

This project follows Test-Driven Development. When fixing a bug, you MUST write failing test(s) that exercise the bug **before** writing the fix. Confirm the test fails for the expected reason, then implement the fix and verify the test passes.

## Rules

- Don't silence linter warnings — fix the underlying issue
- Never hardcode secrets — use environment variables via `.env`
- Describe your approach before implementing non-trivial changes
