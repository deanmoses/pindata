"""Tests for scripts/apply_description.py."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# Allow importing from scripts/ and lib/
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

from apply_description import apply_description, main, parse_frontmatter


# ---------------------------------------------------------------------------
# parse_frontmatter
# ---------------------------------------------------------------------------


class TestParseFrontmatter:
    def test_frontmatter_only(self):
        text = "---\nname: Foo\n---\n"
        fm, body = parse_frontmatter(text)
        assert fm == "---\nname: Foo\n---\n"
        assert body == ""

    def test_frontmatter_with_body(self):
        text = "---\nname: Foo\n---\n\nSome description here.\n"
        fm, body = parse_frontmatter(text)
        assert fm == "---\nname: Foo\n---\n"
        assert body == "Some description here."

    def test_multiline_body(self):
        text = "---\nname: Foo\n---\n\nParagraph one.\n\nParagraph two.\n"
        fm, body = parse_frontmatter(text)
        assert body == "Paragraph one.\n\nParagraph two."

    def test_no_frontmatter_delimiter(self):
        with pytest.raises(ValueError, match="does not start with frontmatter"):
            parse_frontmatter("name: Foo\n")

    def test_unclosed_frontmatter(self):
        with pytest.raises(ValueError, match="Unclosed frontmatter"):
            parse_frontmatter("---\nname: Foo\n")

    def test_preserves_complex_frontmatter(self):
        text = "---\nname: Foo\naliases:\n  - Bar\n  - Baz\n---\n"
        fm, body = parse_frontmatter(text)
        assert "aliases:" in fm
        assert "  - Bar" in fm
        assert body == ""


# ---------------------------------------------------------------------------
# apply_description
# ---------------------------------------------------------------------------


class TestApplyDescription:
    def test_adds_description_to_empty_body(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        apply_description(md, "A great manufacturer.")

        result = md.read_text()
        assert result == "---\nname: Genco\n---\n\nA great manufacturer.\n"

    def test_preserves_frontmatter(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\nopdb_manufacturer_id: 24\n---\n")

        apply_description(md, "A great manufacturer.")

        result = md.read_text()
        assert "name: Genco" in result
        assert "opdb_manufacturer_id: 24" in result
        assert result.endswith("A great manufacturer.\n")

    def test_refuses_overwrite_by_default(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Bally\n---\n\nExisting description.\n")

        with pytest.raises(RuntimeError, match="already has a description"):
            apply_description(md, "New description.")

    def test_existing_description_unchanged_on_refusal(self, tmp_path: Path):
        original = "---\nname: Bally\n---\n\nExisting description.\n"
        md = tmp_path / "test.md"
        md.write_text(original)

        with pytest.raises(RuntimeError):
            apply_description(md, "New description.")

        assert md.read_text() == original

    def test_overwrite_replaces_description(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Bally\n---\n\nOld description.\n")

        apply_description(md, "New description.", overwrite=True)

        result = md.read_text()
        assert "Old description" not in result
        assert result.endswith("New description.\n")

    def test_multiline_description(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        desc = "Paragraph one.\n\nParagraph two."
        apply_description(md, desc)

        result = md.read_text()
        assert "Paragraph one.\n\nParagraph two.\n" in result

    def test_strips_trailing_whitespace_from_description(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        apply_description(md, "A description.\n\n\n")

        result = md.read_text()
        assert result.endswith("A description.\n")

    def test_file_not_found(self, tmp_path: Path):
        md = tmp_path / "nonexistent.md"
        with pytest.raises(FileNotFoundError, match="not found"):
            apply_description(md, "Some text.")

    def test_empty_description_rejected(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        with pytest.raises(ValueError, match="empty"):
            apply_description(md, "")

    def test_whitespace_only_description_rejected(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        with pytest.raises(ValueError, match="empty"):
            apply_description(md, "   \n\n  ")


# ---------------------------------------------------------------------------
# CLI (main)
# ---------------------------------------------------------------------------


class TestCLI:
    def test_apply_from_file(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")
        desc_file = tmp_path / "desc.md"
        desc_file.write_text("A description from file.")

        rc = main([str(md), str(desc_file)])

        assert rc == 0
        assert "A description from file." in md.read_text()

    def test_apply_from_stdin(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        import io

        monkeypatch.setattr("sys.stdin", io.StringIO("A description from stdin."))

        rc = main([str(md), "-"])

        assert rc == 0
        assert "A description from stdin." in md.read_text()

    def test_refuses_overwrite_without_flag(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Bally\n---\n\nExisting.\n")
        desc_file = tmp_path / "desc.md"
        desc_file.write_text("New text.")

        rc = main([str(md), str(desc_file)])

        assert rc == 1
        assert "Existing." in md.read_text()

    def test_overwrite_flag_works(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Bally\n---\n\nExisting.\n")
        desc_file = tmp_path / "desc.md"
        desc_file.write_text("Replacement.")

        rc = main(["--overwrite", str(md), str(desc_file)])

        assert rc == 0
        assert "Replacement." in md.read_text()

    def test_missing_catalog_file(self, tmp_path: Path):
        desc_file = tmp_path / "desc.md"
        desc_file.write_text("Some text.")

        rc = main([str(tmp_path / "nope.md"), str(desc_file)])

        assert rc == 1

    def test_missing_description_file(self, tmp_path: Path):
        md = tmp_path / "test.md"
        md.write_text("---\nname: Genco\n---\n")

        rc = main([str(md), str(tmp_path / "nope.md")])

        assert rc == 1
