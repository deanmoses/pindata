"""Tests for scripts/apply_fields.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from apply_fields import apply_fields, main

# All tests use a fake "titles" directory so apply_fields resolves the
# title schema.  The schema file must exist at the expected path relative
# to the catalog directory.
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"


@pytest.fixture()
def title_file(tmp_path: Path) -> Path:
    """Create a minimal title markdown file inside a titles/ subdirectory."""
    titles_dir = tmp_path / "catalog" / "titles"
    titles_dir.mkdir(parents=True)
    md = titles_dir / "alien.md"
    md.write_text("---\nname: Alien\n---\n")

    # Symlink schema dir so validation can find it
    schema_link = tmp_path / "schema"
    schema_link.symlink_to(SCHEMA_DIR)

    return md


@pytest.fixture()
def title_file_with_opdb(tmp_path: Path) -> Path:
    """Title file with name and opdb_group_id already set."""
    titles_dir = tmp_path / "catalog" / "titles"
    titles_dir.mkdir(parents=True)
    md = titles_dir / "batman.md"
    md.write_text("---\nname: Batman\nopdb_group_id: G4yVw\n---\n")

    schema_link = tmp_path / "schema"
    schema_link.symlink_to(SCHEMA_DIR)

    return md


@pytest.fixture()
def title_file_with_body(tmp_path: Path) -> Path:
    """Title file with a description body."""
    titles_dir = tmp_path / "catalog" / "titles"
    titles_dir.mkdir(parents=True)
    md = titles_dir / "star-wars.md"
    md.write_text("---\nname: Star Wars\n---\n\nA classic franchise.\n")

    schema_link = tmp_path / "schema"
    schema_link.symlink_to(SCHEMA_DIR)

    return md


# ---------------------------------------------------------------------------
# apply_fields — basic functionality
# ---------------------------------------------------------------------------


class TestApplyFields:
    def test_add_field_to_minimal_frontmatter(self, title_file: Path):
        apply_fields(title_file, {"franchise_slug": "alien"})

        result = title_file.read_text()
        assert "franchise_slug: alien" in result
        assert result.index("name:") < result.index("franchise_slug:")

    def test_add_field_after_opdb_group_id(self, title_file_with_opdb: Path):
        apply_fields(title_file_with_opdb, {"franchise_slug": "batman"})

        result = title_file_with_opdb.read_text()
        assert "franchise_slug: batman" in result
        # franchise_slug should come after opdb_group_id
        assert result.index("opdb_group_id:") < result.index("franchise_slug:")

    def test_add_field_before_existing_later_field(self, tmp_path: Path):
        """franchise_slug should be inserted before abbreviations."""
        titles_dir = tmp_path / "catalog" / "titles"
        titles_dir.mkdir(parents=True)
        md = titles_dir / "test.md"
        md.write_text("---\nname: Test\nabbreviations:\n- TST\n---\n")
        (tmp_path / "schema").symlink_to(SCHEMA_DIR)

        apply_fields(md, {"franchise_slug": "test-franchise"})

        result = md.read_text()
        assert result.index("franchise_slug:") < result.index("abbreviations:")

    def test_multiple_fields_at_once(self, title_file: Path):
        apply_fields(title_file, {"franchise_slug": "alien", "series_slug": "alien-series"})

        result = title_file.read_text()
        assert "franchise_slug: alien" in result
        assert "series_slug: alien-series" in result
        assert result.index("franchise_slug:") < result.index("series_slug:")

    def test_preserves_body(self, title_file_with_body: Path):
        apply_fields(title_file_with_body, {"franchise_slug": "star-wars"})

        result = title_file_with_body.read_text()
        assert "franchise_slug: star-wars" in result
        assert "A classic franchise." in result


# ---------------------------------------------------------------------------
# apply_fields — overwrite behavior
# ---------------------------------------------------------------------------


class TestOverwrite:
    def test_refuses_overwrite_by_default(self, title_file_with_opdb: Path):
        with pytest.raises(RuntimeError, match="already has value"):
            apply_fields(title_file_with_opdb, {"opdb_group_id": "NEW"})

    def test_existing_unchanged_on_refusal(self, title_file_with_opdb: Path):
        original = title_file_with_opdb.read_text()
        with pytest.raises(RuntimeError):
            apply_fields(title_file_with_opdb, {"opdb_group_id": "NEW"})
        assert title_file_with_opdb.read_text() == original

    def test_overwrite_replaces_value(self, title_file_with_opdb: Path):
        apply_fields(title_file_with_opdb, {"opdb_group_id": "GNEW"}, overwrite=True)

        result = title_file_with_opdb.read_text()
        assert "opdb_group_id: GNEW" in result
        assert "G4yVw" not in result


# ---------------------------------------------------------------------------
# apply_fields — delete fields
# ---------------------------------------------------------------------------


class TestDeleteFields:
    def test_delete_existing_scalar_field(self, title_file_with_opdb: Path):
        apply_fields(title_file_with_opdb, delete_fields=["opdb_group_id"])

        result = title_file_with_opdb.read_text()
        assert "opdb_group_id" not in result
        assert "name: Batman" in result

    def test_delete_nonexistent_field_is_noop(self, title_file: Path):
        original = title_file.read_text()
        apply_fields(title_file, delete_fields=["franchise_slug"])
        assert title_file.read_text() == original

    def test_delete_list_field(self, model_file_with_themes: Path):
        apply_fields(model_file_with_themes, delete_fields=["theme_slugs"])

        result = model_file_with_themes.read_text()
        assert "theme_slugs" not in result
        assert "  - fantasy" not in result
        assert "  - medieval" not in result

    def test_delete_preserves_other_fields(self, title_file_with_opdb: Path):
        apply_fields(title_file_with_opdb, delete_fields=["opdb_group_id"])

        result = title_file_with_opdb.read_text()
        assert "name: Batman" in result

    def test_delete_preserves_body(self, title_file_with_body: Path):
        apply_fields(title_file_with_body, {"opdb_group_id": "G1234"})
        apply_fields(title_file_with_body, delete_fields=["opdb_group_id"])

        result = title_file_with_body.read_text()
        assert "opdb_group_id" not in result
        assert "A classic franchise." in result

    def test_delete_and_add_in_one_call(self, title_file_with_opdb: Path):
        apply_fields(
            title_file_with_opdb,
            {"franchise_slug": "batman"},
            delete_fields=["opdb_group_id"],
        )

        result = title_file_with_opdb.read_text()
        assert "franchise_slug: batman" in result
        assert "opdb_group_id" not in result


# ---------------------------------------------------------------------------
# apply_fields — error handling
# ---------------------------------------------------------------------------


class TestErrors:
    def test_invalid_field_name(self, title_file: Path):
        with pytest.raises(ValueError, match="not in the title schema"):
            apply_fields(title_file, {"bogus_field": "value"})

    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            apply_fields(tmp_path / "nope.md", {"franchise_slug": "x"})

    def test_unknown_directory(self, tmp_path: Path):
        weird_dir = tmp_path / "catalog" / "widgets"
        weird_dir.mkdir(parents=True)
        md = weird_dir / "test.md"
        md.write_text("---\nname: Test\n---\n")

        with pytest.raises(ValueError, match="Cannot determine schema"):
            apply_fields(md, {"name": "New"})


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_set_field_via_cli(self, title_file: Path):
        rc = main([str(title_file), "franchise_slug=alien"])

        assert rc == 0
        assert "franchise_slug: alien" in title_file.read_text()

    def test_multiple_fields_via_cli(self, title_file: Path):
        rc = main([str(title_file), "franchise_slug=alien", "series_slug=alien-series"])

        assert rc == 0
        result = title_file.read_text()
        assert "franchise_slug: alien" in result
        assert "series_slug: alien-series" in result

    def test_invalid_field_spec(self, title_file: Path, capsys: pytest.CaptureFixture[str]):
        rc = main([str(title_file), "no_equals_sign"])

        assert rc == 1
        assert "expected key=value" in capsys.readouterr().err

    def test_refuses_overwrite_without_flag(self, title_file_with_opdb: Path):
        rc = main([str(title_file_with_opdb), "opdb_group_id=NEW"])

        assert rc == 1
        assert "G4yVw" in title_file_with_opdb.read_text()

    def test_overwrite_flag_works(self, title_file_with_opdb: Path):
        rc = main(["--overwrite", str(title_file_with_opdb), "opdb_group_id=GNEW"])

        assert rc == 0
        assert "opdb_group_id: GNEW" in title_file_with_opdb.read_text()

    def test_delete_field_via_cli(self, title_file_with_opdb: Path):
        rc = main([str(title_file_with_opdb), "--delete", "opdb_group_id"])

        assert rc == 0
        assert "opdb_group_id" not in title_file_with_opdb.read_text()


# ---------------------------------------------------------------------------
# List fields
# ---------------------------------------------------------------------------


@pytest.fixture()
def model_file(tmp_path: Path) -> Path:
    """Create a minimal model markdown file."""
    models_dir = tmp_path / "catalog" / "models"
    models_dir.mkdir(parents=True)
    md = models_dir / "medieval-madness.md"
    md.write_text("---\nname: Medieval Madness\ntitle_slug: medieval-madness\n---\n")

    schema_link = tmp_path / "schema"
    schema_link.symlink_to(SCHEMA_DIR)

    return md


@pytest.fixture()
def model_file_with_themes(tmp_path: Path) -> Path:
    """Model file with theme_slugs already set."""
    models_dir = tmp_path / "catalog" / "models"
    models_dir.mkdir(parents=True)
    md = models_dir / "medieval-madness.md"
    md.write_text(
        "---\nname: Medieval Madness\ntitle_slug: medieval-madness\n"
        "theme_slugs:\n  - fantasy\n  - medieval\n---\n"
    )

    schema_link = tmp_path / "schema"
    schema_link.symlink_to(SCHEMA_DIR)

    return md


class TestListFields:
    def test_add_list_field(self, model_file: Path):
        apply_fields(model_file, {"theme_slugs": ["fantasy", "medieval"]})

        result = model_file.read_text()
        assert "theme_slugs:" in result
        assert "  - fantasy" in result
        assert "  - medieval" in result

    def test_list_field_ordering(self, model_file: Path):
        """theme_slugs should appear after tag_slugs in schema order."""
        apply_fields(model_file, {
            "tag_slugs": ["widebody"],
            "theme_slugs": ["fantasy"],
        })

        result = model_file.read_text()
        assert result.index("tag_slugs:") < result.index("theme_slugs:")

    def test_list_field_before_credit_refs(self, tmp_path: Path):
        """theme_slugs should appear before credit_refs."""
        models_dir = tmp_path / "catalog" / "models"
        models_dir.mkdir(parents=True)
        md = models_dir / "test.md"
        md.write_text(
            "---\nname: Test\ntitle_slug: test\ncredit_refs:\n"
            "- person_slug: john\n  role: Design\n---\n"
        )
        (tmp_path / "schema").symlink_to(SCHEMA_DIR)

        apply_fields(md, {"theme_slugs": ["horror"]})

        result = md.read_text()
        assert result.index("theme_slugs:") < result.index("credit_refs:")

    def test_empty_list(self, model_file: Path):
        apply_fields(model_file, {"theme_slugs": []})

        result = model_file.read_text()
        assert "theme_slugs: []" in result

    def test_overwrite_list_field(self, model_file_with_themes: Path):
        apply_fields(
            model_file_with_themes,
            {"theme_slugs": ["horror", "zombies"]},
            overwrite=True,
        )

        result = model_file_with_themes.read_text()
        assert "  - horror" in result
        assert "  - zombies" in result
        assert "  - fantasy" not in result
        assert "  - medieval" not in result

    def test_refuses_overwrite_list_by_default(self, model_file_with_themes: Path):
        with pytest.raises(RuntimeError, match="already has value"):
            apply_fields(model_file_with_themes, {"theme_slugs": ["horror"]})

    def test_list_field_via_cli(self, model_file: Path):
        rc = main([str(model_file), "theme_slugs=fantasy,medieval"])

        assert rc == 0
        result = model_file.read_text()
        assert "theme_slugs:" in result
        assert "  - fantasy" in result
        assert "  - medieval" in result

    def test_preserves_body_with_list_field(self, tmp_path: Path):
        models_dir = tmp_path / "catalog" / "models"
        models_dir.mkdir(parents=True)
        md = models_dir / "test.md"
        md.write_text("---\nname: Test\ntitle_slug: test\n---\n\nA great machine.\n")
        (tmp_path / "schema").symlink_to(SCHEMA_DIR)

        apply_fields(md, {"theme_slugs": ["fantasy"]})

        result = md.read_text()
        assert "  - fantasy" in result
        assert "A great machine." in result
