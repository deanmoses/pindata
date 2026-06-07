# Data Patches

A **data patch** is a small, source-attributed set of catalog claims, authored
as YAML, that corrects or extends catalog data in already-seeded downstream
databases **without a full re-ingest**. Patches are the schema-migration model,
applied to data: the catalog seed is an immutable baseline, and patches are an
append-only, numbered log replayed on top of it in every environment.

**This repo is only the transport.** Pindata is where patches are *authored*,
*validated* structurally, and *shipped* to R2 alongside the catalog export. The
authoritative apply model — attribution resolution, the assert/create/retract
operations, the per-database ledger, and immutability hashing — lives in the
consumer that applies them (flipcommons' `ingest_patches`), not here. This
document covers what you need to author a valid patch file in pindata.

## Location and naming

Patches live at the top level in `patches/`, named `NNNN-slug.yaml`:

- The four-digit `NNNN` prefix **orders application** and must be unique.
- The filename stem (e.g. `0001-prototype-tags`) is the **patch id**.

They ride the existing `make push` → R2 path, shipped **verbatim** (not exported
to JSON) under the `pindata/patches/` prefix.

## File format

Plain YAML with three top-level keys:

```yaml
attribution: flip-museum            # required — a Source slug; must already exist downstream
description: >                      # optional — the "why"; copied to the apply run's note
  Tag known unreleased prototypes that never reached commercial production.
claims:                            # required — an ordered list of single-key entries
  - model.mazatron:                # entity ref: <entity-type>.<public-id>
      expect: { year: 1990 }       # optional drift guard
      tag: [prototype]             # a field operation
```

- **`attribution`** — the source the fact came from (`flip-museum`,
  `flipcommons-catalog`, `ipdb`, `opdb`, …). One attribution per patch. A patch
  corrects or retracts *that source's own* claim; there is no "override tier."
- **`description`** — freeform rationale.
- **`claims`** — an ordered list. Each entry is a **single-key mapping**: the
  key is an entity reference, the value is the operations on it.

### Entity reference

The entry key is `<entity-type>.<public-id>`, split on the **first `.`**:

- `entity-type` — the canonical kebab-case singular type (`model`,
  `manufacturer`, `corporate-entity`, `tag`, …).
- `public-id` — the slug for most entities (`location_path` for Location).

A `.` is used (not the wikilink `:`) so the YAML key needs no quoting.

### Field operations

Non-reserved keys are claim fields, classified downstream by introspection:

- **scalar** (`year`, `year_start`) — value used as-is.
- **FK** (`manufacturer`, `title`) — value is the target entity's public-id.
- **relationship** (`tag`, `theme`) — key is the namespace, value is a list of
  member public-ids.

### Reserved keys

- **`create: true`** — opt in to creating a missing entity. The author writes
  only the authored fields (e.g. `name`); the adapter supplies the public-id
  (from the entry key) and `status`. An unresolved reference without `create` is
  an error (typo guard); `create: true` on an entity that already exists is also
  an error.
- **`expect:`** — a drift guard: a map of currently-resolved scalar/FK values
  the target must already have, checked before any write. A mismatch is a hard
  error. Use it to ensure a hand-authored public-id lands on the row you mean
  (e.g. the unreleased original, not a same-named remake).
- **`retract:`** — a list of scalar/FK field names whose claim **from this
  patch's source** should be removed. Not valid together with `create` on the
  same entry.

### Strict parsing

Patch YAML is parsed strictly — `make validate` mirrors the same rules the
downstream loader enforces:

- **Duplicate mapping keys are an error** (not last-wins).
- **Values must be JSON-shaped.** YAML 1.1 implicit coercion is disabled, so a
  bare `1996-01-01` stays a string and `no` stays `"no"` — no need to quote, but
  no surprises either. Non-JSON explicit tags (`!!timestamp`, `!!set`,
  `!!binary`, non-finite `!!float .nan`/`.inf`) are rejected.

## Examples

**Edit + relationship** (`0001-prototype-tags.yaml`, attribution `flip-museum`):

```yaml
attribution: flip-museum
claims:
  - model.mazatron:
      expect: { year: 1990 }
      tag: [prototype]
```

**Create + supersede** (`0002-stern-catalog.yaml`, attribution
`flipcommons-catalog` — the new manufacturer's slug *is* the entry key, and the
corporate entity's FK supersedes the source's prior claim):

```yaml
attribution: flipcommons-catalog
claims:
  - manufacturer.western-products:
      name: Western Products
      create: true
  - corporate-entity.western-products-incorporated:
      manufacturer: western-products
```

**Retract** (`0003-stern-ipdb.yaml`, attribution `ipdb` — removes that source's
fabricated claim):

```yaml
attribution: ipdb
claims:
  - corporate-entity.western-products-incorporated:
      retract: [manufacturer]
```

## Validating locally

```bash
make validate
# or directly:
uv run python3 scripts/validate_patches.py
```

`scripts/validate_patches.py` is a fast **structural** gate so a typo is caught
before publishing: filename format, unique numeric prefixes, strict
JSON-shaped YAML, and conformance to `schema/patch.schema.json`. Authoritative
validation — entity resolution, the `expect` drift guard, field classification,
attribution existence — happens downstream when the patch is applied.

## What pindata does *not* do

Applying patches, resolving attribution priority, the per-database applied-once
ledger, and immutability checks are all the consumer's responsibility
(flipcommons' `ingest_patches`). Pindata validates and ships; it never applies.
