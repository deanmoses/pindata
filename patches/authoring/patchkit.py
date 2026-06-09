"""patchkit - shared helpers for authoring Flipcommons data patches.

Pure Python (NO Django import) so it imports anywhere and is unit-testable. The
one Django-dependent step - reading live catalog values for `expect:` guards -
stays a one-liner in each generator (see docs/DataPatchAuthoring.md in
flipcommons and the worked example beside this file).

Why this exists: four prior patch-authoring sessions each re-derived YAML
escaping, the expect-guard chooser, the missing-ref assert and the review-doc
scaffolding - each slightly differently, some subtly wrong. This centralizes the
parts that kept getting reinvented so a new session writes classification data,
not scaffolding.

See DataPatches.md for the patch file format this emits.
"""

from __future__ import annotations

import re
import textwrap
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

# --------------------------------------------------------------------------- #
# text / escaping                                                             #
# --------------------------------------------------------------------------- #

_SMART = {
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...",
}


def ascii_clean(s: str) -> str:
    """Smart quotes/dashes -> ASCII; drop any remaining non-ASCII (mojibake).

    Patch notes must be plain ASCII (DataPatches.md). IPDB/OPDB free text is full
    of curly quotes and the U+FFFD replacement character.
    """
    for k, v in _SMART.items():
        s = s.replace(k, v)
    return s.encode("ascii", "ignore").decode("ascii")


def yamlq(s: str) -> str:
    """Render `s` as a single-quoted YAML scalar (the only note escaping needed).

    A single-quoted YAML scalar is literal except `'`, which is doubled. This
    safely carries both the double quotes in `... says "<verbatim>"` and the
    apostrophes in the verbatim text - no backslashes, unlike json.dumps. Always
    pass ascii_clean()ed text.
    """
    return "'" + s.replace("'", "''") + "'"


def source_note(source: str, verbatim: str, tail: str = "") -> str:
    """The canonical evidence note: `<Source> says "<verbatim>"<tail>`.

    Quote the source verbatim; mark your own omissions inside `verbatim` with
    ` [...] `. Output is ASCII. Feed the return value straight to entry(note=...).
    """
    return ascii_clean(f'{source} says "{verbatim.strip()}"{tail}')


_SAFE_SCALAR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _./()&'-]*$")
# A string value that would be read back as a JSON number/bool/null and so must be
# quoted to stay a string (e.g. a slug "404", or the literal "null").
_JSON_LITERAL = re.compile(r"^(true|false|null|-?\d+(\.\d+)?([eE][+-]?\d+)?)$")


def _scalar(v: object) -> str:
    """JSON-shaped scalar for a claim value (YAML coercion is off in the loader)."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    if _SAFE_SCALAR.match(s) and not _JSON_LITERAL.match(s):
        return s
    return yamlq(s)


def _fold(text: str, width: int = 92) -> list[str]:
    """Collapse whitespace and word-wrap, for `>` folded block bodies."""
    return textwrap.wrap(
        " ".join(text.split()), width=width,
        break_on_hyphens=False, break_long_words=False,
    ) or [""]


# --------------------------------------------------------------------------- #
# source-text extraction (classify.py side)                                   #
# --------------------------------------------------------------------------- #
#
# These run on the pinexplore side, against DuckDB free text - patchkit is pure
# stdlib, so a classify.py can `import patchkit` too (add the authoring dir to
# sys.path, as gen.py does). They were re-derived in every classify.py; pull the
# next one's from here instead.

_IPD_HEADER = re.compile(r"^\s*\d+\s*/[^.]*?\bPlayers?\b\s*")


def sentences(text: str) -> list[str]:
    """Split free text into sentences, normalizing CR/LF and runs of whitespace."""
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return [p.strip() for p in re.split(r"(?<=[.!?])\s+", text) if p.strip()]


def sentence_with(blob: str, needle: str) -> str:
    """The first sentence in `blob` containing `needle` (case-insensitive), or ''.

    The needle pattern that pins a quote: freeze a unique substring of the evidence
    sentence in your classify map, re-extract the live sentence here so the quote
    stays faithful to the current source text. Assert the result still contains the
    keyword you classified on (see DataPatchAuthoring.md's faithfulness-guard gotcha).
    """
    for s in sentences(blob):
        if needle.lower() in s.lower():
            return s
    return ""


_QUOTE_INTRO = re.compile(r'^.*?:\s*"(.+?)"?$')


def clean_ipdb_quote(text: str, limit: int = 240) -> str:
    """ASCII-clean an IPDB sentence, strip its framing and bound its length.

    IPDB glues a punctuation-less header ('6022 / 1946 / 1 Player') onto the first
    sentence, so the splitter keeps it; this drops it. It also frames quoted passages
    with an introducer ('... translates as follows: "<text>'); this keeps the inner
    passage and drops the framing, so we quote the evidence itself rather than a
    dangling open-quote that reads as complete. Over-long run-ons are cut at a word
    boundary with a marked ` [...]` omission (DataPatches.md requires marking
    omissions). Idempotent on already-clean text.
    """
    text = _IPD_HEADER.sub("", ascii_clean(text)).strip()
    intro = _QUOTE_INTRO.match(text)
    if intro:
        text = intro.group(1).strip()
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + " [...]"
    return text


# --------------------------------------------------------------------------- #
# guards / resolution                                                         #
# --------------------------------------------------------------------------- #

_GUARD_ALIASES = {
    "corporate_entity": ("corporate_entity", "corporate_entity__slug", "corporate_entity_slug"),
}


def guard(
    row: Mapping[str, object],
    prefer: Sequence[str] = ("ipdb_id", "year", "corporate_entity"),
) -> dict[str, object]:
    """Pick the most specific available `expect:` guard from a live-catalog row.

    `row` is a plain dict of resolved values (e.g. from
    `.values('year', 'corporate_entity__slug', 'ipdb_id')`). Returns {} when none
    are present - author should then guard on something else or accept the risk.

    Default order follows DataPatches.md: when the patch is keyed on the IPDB
    record, `ipdb_id` is the most specific guard (present even when year and
    corporate_entity are null); else `year`; else `corporate_entity`. Pass a
    different `prefer` (e.g. `("year", "corporate_entity")`) when not IPDB-keyed.
    """
    for key in prefer:
        for cand in _GUARD_ALIASES.get(key, (key,)):
            v = row.get(cand)
            if v is not None and v != "":
                return {key: v}
    return {}


def check_resolved(requested: Iterable[object], found: Iterable[object]) -> None:
    """Raise if any requested ref didn't resolve in the live DB (typo or drift)."""
    have = set(found)
    missing = [r for r in requested if r not in have]
    if missing:
        raise SystemExit(f"UNRESOLVED refs ({len(missing)}): {missing}")


# --------------------------------------------------------------------------- #
# YAML entry / patch emission                                                 #
# --------------------------------------------------------------------------- #


def entry(
    ref: str,
    *,
    create: bool = False,
    expect: Mapping[str, object] | None = None,
    note: str | None = None,
    cite: str | None = None,
    fields: Mapping[str, object] | None = None,
    description: str | None = None,
    tags: Sequence[str] | None = None,
    retract: Sequence[str] | None = None,
    comment: str | None = None,
    commented: bool = False,
) -> str:
    """Emit one YAML `claims:` entry block, correctly indented and escaped.

    ref:    '<entity_type>.<public_id>'  e.g. 'model.mazatron', 'game-format.slot-machine'.
    create: emit `create: true` (new entity; omit expect).
    expect: dict -> flow map `expect: { k: v }` (drift guard).
    note:   free text -> single-quoted scalar (use source_note() to build it).
    cite:   'scheme:id' e.g. 'ipdb:4443'.
    fields: scalar/FK claims; value used as-is for scalars, target public_id for FKs.
    description: folded `>` block (for vocab creation).
    tags / retract: lists -> `tag: [...]` / `retract: [...]`.
    commented: prefix every line with '# ' (FLAGGED rows kept in-file for a human call).
    comment: trailing `# ...` on the ref line.
    """
    if create and expect:
        raise ValueError(f"{ref}: create + expect are contradictory (create is for a new entity)")
    if create and retract:
        raise ValueError(f"{ref}: create + retract are invalid (nothing to retract on a new entity)")
    pre = "  # " if commented else "  "
    sub = "  #     " if commented else "      "
    head = f"{pre}- {ref}:"
    if comment:
        head += f"  # {comment}"
    lines = [head]
    if create:
        lines.append(f"{sub}create: true")
    if expect:
        inner = ", ".join(f"{k}: {_scalar(v)}" for k, v in expect.items())
        lines.append(f"{sub}expect: {{ {inner} }}")
    if note is not None:
        lines.append(f"{sub}note: {yamlq(ascii_clean(note))}")
    if cite:
        lines.append(f"{sub}cite: {cite}")
    for k, v in (fields or {}).items():
        lines.append(f"{sub}{k}: {_scalar(v)}")
    if description is not None:
        lines.append(f"{sub}description: >")
        for line in _fold(ascii_clean(description)):
            lines.append(f"{sub}  {line}")
    if tags:
        lines.append(f"{sub}tag: [{', '.join(tags)}]")
    if retract:
        lines.append(f"{sub}retract: [{', '.join(retract)}]")
    return "\n".join(lines)


def write_patch(
    path: str | Path,
    *,
    attribution: str,
    description: str,
    entries: Sequence[str],
) -> Path:
    """Write a complete patch file (header + folded description + claims)."""
    out = [f"attribution: {attribution}", "description: >"]
    out += [f"  {line}" for line in _fold(description)]
    out.append("claims:")
    out += list(entries)
    p = Path(path)
    p.write_text("\n".join(out) + "\n")
    return p


# --------------------------------------------------------------------------- #
# self-test                                                                   #
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    # smoke test - run `python patchkit.py`
    assert yamlq("a'b") == "'a''b'"
    assert ascii_clean("“flasher” — ok") == '"flasher" - ok'
    # source-text extraction
    assert sentences("One. Two? Three!") == ["One.", "Two?", "Three!"]
    assert sentence_with("Foo bar. Baz qux.", "baz") == "Baz qux."
    assert sentence_with("Foo bar.", "nope") == ""
    assert clean_ipdb_quote("6022 / 1946 / 1 Player This is a bagatelle.") == "This is a bagatelle."
    assert clean_ipdb_quote("“Plain” quote.") == '"Plain" quote.'  # also ascii-cleans
    # drops the framing introducer, keeps the quoted passage itself
    assert clean_ipdb_quote('The backglass translates as follows: "Win a prize."') == "Win a prize."
    assert clean_ipdb_quote("a " * 200, limit=20).endswith("[...]")  # marks truncation
    assert guard({"year": None, "ipdb_id": 42}) == {"ipdb_id": 42}
    assert guard({"year": 1990, "ipdb_id": None}) == {"year": 1990}
    assert guard({"corporate_entity__slug": "bally", "year": None, "ipdb_id": None}) == {
        "corporate_entity": "bally"
    }
    e = entry(
        "model.mazatron",
        expect={"ipdb_id": 4443},
        note=source_note("IPDB", 'exists only as a "prototype" machine'),
        cite="ipdb:4443",
        fields={"production_status": "unreleased"},
        tags=["prototype"],
    )
    assert "expect: { ipdb_id: 4443 }" in e
    assert '''note: 'IPDB says "exists only as a "prototype" machine"\'''' in e
    assert "production_status: unreleased" in e
    assert "tag: [prototype]" in e
    v = entry("game-format.slot-machine", create=True, fields={"name": "Slot Machine", "display_order": 5},
              description="Coin-operated   gambling machines.")
    assert "create: true" in v
    assert "description: >" in v
    # string values that look like JSON literals stay quoted (strings, not coerced)
    assert "game_format: '404'" in entry("model.x", fields={"game_format": "404"})
    assert "v: 'true'" in entry("model.x", fields={"v": "true"})
    # contradictory kwargs raise
    for make in (
        lambda: entry("model.x", create=True, expect={"year": 1}),
        lambda: entry("model.x", create=True, retract=["x"]),
    ):
        try:
            make()
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    print("patchkit self-test OK")
    print(e)
    print(v)
