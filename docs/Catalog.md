# Catalog Data

This project has a catalog of pinball machines, manufacturers, and pinball-related people.

The catalog is authored as one Markdown file per entity in `catalog/`. Each file has YAML frontmatter for structured fields and an optional Markdown
body for prose descriptions. This is the canonical source for all data authored and synthesized by this project (as opposed to data coming from external third party sources).

## Directory structure

```text
catalog/
  models/                 #  ~7k files — individual pinball machines
  titles/                 #  ~6k files — title groupings (e.g. all versions of "Medieval Madness")
  manufacturers/          # ~700 files — brand names (Williams, Bally, Stern, etc.)
  corporate_entities/     # ~800 files — legal entities behind the brands
  people/                 # ~600 files — designers, artists, programmers
  themes/                 # ~450 files — thematic categories
  franchises/             # ~130 files — IP franchises (Star Wars, Indiana Jones, etc.)
  systems/                #  ~70 files — hardware platforms (WPC-95, System 11, etc.)
  gameplay_features/      #  ~20 files — multiball, ramps, etc.
  credit_roles/           #  ~10 files — Design, Art, Music, etc.
  display_types/          #  ~10 files — DMD, LCD, alphanumeric, etc.
  display_subtypes/       #  ~10 files — specific display hardware
  tags/                   #  ~10 files — home-use, widebody, etc.
  series/                 #  ~10 files — curated series (Eight Ball trilogy, etc.)
  cabinets/               #  ~10 files — standard, widebody, countertop, mini
  game_formats/           #  ~10 files — pinball machine, bagatelle, etc.
  technology_generations/ #  ~10 files — electromechanical, solid-state, pure-mechanical
  technology_subgenerations/ # ~10 files — era subdivisions
```

## File format

Every file follows the same pattern: YAML frontmatter between `---` fences,
optional Markdown body below.

Example:

```md
---
name: Medieval Madness
year: 1997
technology_generation_slug: solid-state
---

Medieval Madness is widely regarded as one of the defining
[[manufacturer:williams]] games of the late [[system:wpc-95]] era.
```

Syntax notes:

- **Filename = slug.** The file `models/medieval-madness.md` has the slug
  `medieval-madness`. There is no `slug` field in frontmatter — the filename is
  the slug.
- **Optional fields are omitted.** If a field is null, empty, or false, it simply
  doesn't appear in frontmatter.
- **Prose uses wikilinks.** Cross-references in the Markdown body use
  `[[<entity-type>:<public-id>]]` syntax, e.g. `[[manufacturer:bally]]`,
  `[[person:steve-ritchie]]`, `[[title:attack-from-mars]]`. For most
  entity types the public-id is a slug; Location uses a multi-segment
  path (e.g. `[[location:usa/il/chicago]]`).

## Schemas

JSON Schema files in `schema/` define the valid frontmatter for
each entity type. The validator (`scripts/validate_catalog.py`)
validates every record against its schema.

## Validation

```bash
make validate
```

## Editing records

1. Edit the markdown file directly in `catalog/<entity_type>/<slug>.md`.
2. To create a new record, create a new `.md` file. The filename is the slug.
3. Omit optional fields that don't have values — don't set them to null.
4. Run validation: `make validate`

## How the data flows

1. **Authoring**: Records are edited in `catalog/` as markdown files.
2. **Export**: `make export` converts markdown to JSON in `export/`.
3. **Push**: `make push` uploads the JSON to Cloudflare R2.
4. **Downstream**: Consumer projects ([Pinexplore](https://github.com/deanmoses/pinexplore), [Pinbase](https://github.com/deanmoses/pinbase)) pull the JSON from R2.

## Rationale

### Why Markdown files with frontmatter?

The reason this project stores its catalog data in markdown files with YAML frontmatter for structured data:

- We wanted a format that is ergonomic for both AIs and humans to read and write:
  - AIs (and humans) handle filesystem writes much better than SQL insert statements.
  - AIs (and humans) handle records in individual files much better than one giant file; they don't blow out their context window.
  - AIs (and humans) handle writing YAML + markdown better than JSON.
- We wanted a format that can be versioned (such as via git):
  - This lets us make small updates, validate them in various ways, then commit.
- We wanted a format where the diffs are human-verifiable
  - With YAML frontmatter + markdown, native git diffs are very understandable

While there are a few 3rd party systems that provide versioned databases, we didn't want to be locked into a proprietary system, especially one that AIs don't know enough about to use well, and where the diffing wasn't readable by humans.
