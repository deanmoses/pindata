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
- **Data patches**: change sets applied on top of the baseline seed catalog data. They live at `patches/NNNN-slug.yaml` (numbered, e.g. `patches/0042-japanese-maker-years.yaml`). Format: YAML files, one source-attributed set of catalog claims per file.

Supporting stuff:

- JSON schemas for validating the above
- Python scripts for validation, export, and upload to Cloudflare R2, from which downstream projects pull it.

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
make validate     # Validate catalog records and data patches against schemas
make export       # Export catalog to JSON in export/
make push         # Export + push JSON (and data patches) to Cloudflare R2
make clean        # Remove export/ directory
make agent-docs   # Regenerate CLAUDE.md and AGENTS.md
```

## Project Structure

```text
catalog/          Markdown entity files — one file per pinball entity
patches/          Data patches — NNNN-slug.yaml claim corrections for downstream
  authoring/      patchkit generator + one dir per generated patch set (audit trail)
schema/           JSON Schema files for frontmatter and patch validation
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

`patches/` holds **data patches** — small, source-attributed YAML files named `NNNN-slug.yaml` that correct or extend catalog data in already-seeded downstream databases **without a full re-ingest**. The catalog seed is an immutable baseline; patches are an append-only, numbered log replayed on top of it in every environment.

**Pindata is the authoring home and the transport — not the apply engine.** Patches are authored here, their generator artifacts live in `patches/authoring/`, they are validated _structurally_ here, and `make push` ships them verbatim to R2 under the `pindata/patches/` prefix. The authoritative apply model — attribution resolution, the assert/create/retract/remove/delete operations, citation sources, the per-database ledger, and immutability hashing — lives in the consumer that applies them (flipcommons' `ingest_patches`), not here. `scripts/validate_patches.py` (run by `make validate`) is a fast **structural** gate only — see [Validation](#validation).

The thin local reference is [docs/Patches.md](Patches.md); the authoritative format and authoring guidance live in flipcommons (below). **Do not author a patch from pindata's docs alone.**

### The three-repo topology

Real patch authoring spans three repos, checked out as siblings of pindata (`../flipcommons`, `../pinexplore`):

- **pindata** (here) — where patches and their `patches/authoring/` generators live, and where you run `make validate` and `make push`.
- **flipcommons** (`../flipcommons`) — the live catalog (Django + the SQLite dev DB at `backend/db.sqlite3`), the `ingest_patches` apply engine, the live `expect:` guard values you must read against, and the **canonical patch documentation**.
- **pinexplore** (`../pinexplore`) — where you research the verbatim source text behind a `note:`/`cite:`. Two evidence stores: the **web scrape cache** (a searchable, durable cache of fetched web pages — now the primary evidence source, since most new catalog data comes from the web rather than IPDB/OPDB) and the **DuckDB analysis DB** (IPDB/OPDB/Fandom dumps, cross-source checks). See `../pinexplore/docs/WebCache.md` for the cache and `../pinexplore/CLAUDE.md` for the rest.

### Canonical documentation — read before authoring

The authoritative, current patch docs live in flipcommons. pindata's local docs are thin pointers. Read, in `../flipcommons/docs/`:

- **Data.md** — the index for working with catalog data (seed vs patches, explore vs correct); start here to orient.
- **DataPatches.md** — the patch file format and the full apply model: every operation (assert/create/retract/remove/delete), reserved keys (`expect:`/`note:`/`cite:`), citation `sources:`, the ledger, and limitations. The source of truth for what a patch _is_.
- **DataPatchAuthoring.md** — how to author a _good_ patch: attribution, `expect:` guards, verbatim `note:`, record descriptions, and the localhost snapshot-validate loop.
- **DataPatchKit.md** — when and how to generate large curated patches with the shared `patchkit` helper (which lives here at `patches/authoring/patchkit.py`).
- **DataPatchReviewing.md** — the patch review checklist.
- **DomainModel.md** — the catalog entity hierarchy the claims target.

For the concepts a patch rests on, read these two when a claim or citation question gets subtle:

- **Provenance.md** — claims, source-priority resolution, and superseding: the model behind `attribution:`, `expect:`, and `retract:`. Explains _who asserted_ a value and how a new claim supersedes an old one.
- **Citations.md** — the evidence system behind `cite:` and the `sources:` block: why a URL cite needs its website root seeded first (domain match keys off the root's `homepage` link), and why citation sources carry no provenance. Note this is distinct from pinexplore's web scrape cache — Citations.md is the in-app evidence model; the cache is the authoring-side research tool.

### The authoring loop

1. **Read** the canonical docs above for the operation you need.
2. **Research the evidence** in pinexplore — the source text for the `note:` quote and the `cite:`. Usually the web scrape cache (per `WebCache.md`): `web_fetch.py <url> --query "..."` fetches a page once into the cache, then `web_cache.search()` / `web_cache.quote()` find pages and pull the verbatim quote; the `cite:` is the page URL (its website root must be seeded in an earlier patch). For IPDB/OPDB-keyed claims, the DuckDB analysis DB instead, citing `scheme:identifier`. Web-sourced claims usually have no `ipdb_id`, so `expect:` guards fall back to `year`/`corporate_entity`.
3. **Author** the patch: hand-write native YAML for a handful of targeted corrections, or generate with `patchkit` for a classified population (`patches/authoring/<patch>/gen.py`) — copy the shape of an existing `patches/authoring/` dir.
4. **Read live `expect:` values** from the flipcommons DB so guards match the serving catalog; generators do this in `gen.py`.
5. **Validate against flipcommons** behind a SQLite snapshot — apply from an isolated dir, inspect the result, roll back. The snapshot/rollback loop and the misleading-dry-run trap for vocab+assignment pairs are in DataPatchAuthoring.md.
6. **`make validate`** here (the [structural gate](#validation)). Stop there and hand off: **both the commit and `make push` are the user's call — never do either yourself.** Tell the user the patch is validated and ready; they decide when to commit, then run `make push` to ship to R2 and `make pull-ingest && make ingest-patches` on a target DB.

## Validation

`make validate` validates both the catalog and the patches in one pass:

- **Catalog** (`scripts/validate_catalog.py`): YAML parsing, JSON schema conformance, slug/filename match, slug uniqueness, OPDB ID uniqueness, cross-entity reference integrity, wikilink prefix canonicalization, and self-referential variant checks.
- **Patches** (`scripts/validate_patches.py`): a fast **structural** gate only — filename format, unique numeric prefixes, strict JSON-shaped YAML, and conformance to `schema/patch.schema.json`. It does not check apply-time semantics; those live in flipcommons' `ingest_patches` (see [Data Patches](#data-patches)).

To run one validator on its own while iterating:

```bash
python3 scripts/validate_catalog.py
python3 scripts/validate_patches.py
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
- The cross-repo patch authoring loop (Data Patches, above) assumes local sibling checkouts of `flipcommons` and `pinexplore`; in Codex Cloud those aren't present, so only the structural `make validate` is available — not the snapshot-validate or `patchkit` generation steps.

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
