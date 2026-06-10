"""Tests for scripts/validate_patches.py.

Covers the structural patch gate run by ``make validate``: the strict YAML
loader (JSON-shaped values only) and the JSON-schema structural checks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

import validate_patches as vp


def _load(doc: str):
    return yaml.load(doc, Loader=vp._StrictLoader)


# --- Strict loader: JSON-shaped implicit coercion ---------------------------


@pytest.mark.parametrize(
    "doc, key, expected",
    [
        ("a: 1990", "a", 1990),  # int stays int
        ("a: 3.14", "a", 3.14),  # finite float stays float
        ("a: true", "a", True),  # JSON bool
        ("a: null", "a", None),  # JSON null
        ("a: no", "a", "no"),  # YAML 1.1 bool -> string (JSON has no `no`)
        ("a: yes", "a", "yes"),
        ("a: 1996-01-01", "a", "1996-01-01"),  # bare date -> string
    ],
)
def test_implicit_coercion_is_json_shaped(doc, key, expected):
    assert _load(doc)[key] == expected


# --- Strict loader: explicit non-JSON tags are rejected ---------------------


@pytest.mark.parametrize(
    "doc",
    [
        "a: !!timestamp 2020-01-01",
        "a: !!float .nan",
        "a: !!float .inf",
        "a: !!float -.inf",
        "a: !!set {x, y}",
        "a: !!binary aGk=",
        "a: !!omap [{x: 1}]",
        "a: !!pairs [{x: 1}]",
    ],
)
def test_explicit_non_json_tags_rejected(doc):
    with pytest.raises(yaml.YAMLError):
        _load(doc)


def test_duplicate_keys_rejected():
    with pytest.raises(yaml.YAMLError):
        _load("a: 1\na: 2")


# --- Schema: create + retract are mutually exclusive ------------------------


@pytest.fixture(scope="module")
def schema_validator():
    schema = json.loads(vp.SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft7Validator(schema)


def _has_error(validator, data) -> bool:
    return bool(list(validator.iter_errors(data)))


def test_create_and_retract_together_rejected(schema_validator):
    data = {
        "attribution": "ipdb",
        "claims": [
            {"manufacturer.foo": {"create": True, "retract": ["manufacturer"]}}
        ],
    }
    assert _has_error(schema_validator, data)


def test_create_only_is_valid(schema_validator):
    data = {
        "attribution": "flipcommons-catalog",
        "claims": [{"manufacturer.foo": {"name": "Foo", "create": True}}],
    }
    assert not _has_error(schema_validator, data)


def test_retract_only_is_valid(schema_validator):
    data = {
        "attribution": "ipdb",
        "claims": [{"corporate-entity.foo": {"retract": ["manufacturer"]}}],
    }
    assert not _has_error(schema_validator, data)


# --- Schema: entity-reference key pattern -----------------------------------


@pytest.mark.parametrize(
    "ref",
    [
        "model.mazatron",  # slug
        "corporate-entity.western-products-incorporated",  # hyphenated type + slug
        "location.usa/il/chicago",  # location_path public-id
    ],
)
def test_valid_entity_refs_accepted(schema_validator, ref):
    data = {"attribution": "ipdb", "claims": [{ref: {"year": 1990}}]}
    assert not _has_error(schema_validator, data)


@pytest.mark.parametrize(
    "ref",
    [
        "model.foo bar",  # space in public-id
        "manufacturer.Foo",  # uppercase in public-id
        "Model.foo",  # uppercase in type
        "model.",  # empty public-id
        "model.foo.bar",  # stray dot in public-id
        "modelfoo",  # no dot at all
    ],
)
def test_malformed_entity_refs_rejected(schema_validator, ref):
    data = {"attribution": "ipdb", "claims": [{ref: {"year": 1990}}]}
    assert _has_error(schema_validator, data)


# --- Schema: cite accepts scheme:identifier and http(s) URL -----------------


@pytest.mark.parametrize(
    "cite",
    [
        "ipdb:4443",
        "opdb:GRhX5",
        "https://en.wikipedia.org/wiki/Bally_Manufacturing",
        "http://example.com/a",
    ],
)
def test_cite_forms_accepted(schema_validator, cite):
    data = {
        "attribution": "flipcommons-catalog",
        "claims": [{"corporate-entity.foo": {"year_start": 1990, "cite": cite}}],
    }
    assert not _has_error(schema_validator, data)


@pytest.mark.parametrize(
    "cite",
    [
        "ipdb",  # scheme without identifier
        "bogus:4443",  # unknown scheme
        "ftp://example.com",  # non-http(s) URL
        "just some text",  # neither form
    ],
)
def test_malformed_cite_rejected(schema_validator, cite):
    data = {
        "attribution": "flipcommons-catalog",
        "claims": [{"corporate-entity.foo": {"year_start": 1990, "cite": cite}}],
    }
    assert _has_error(schema_validator, data)


# --- Schema: the sources: block ---------------------------------------------


def test_sources_only_patch_is_valid(schema_validator):
    data = {
        "attribution": "flipcommons-catalog",
        "sources": [
            {
                "name": "Wikipedia",
                "source_type": "web",
                "description": "Free encyclopedia.",
                "links": [
                    {"url": "https://en.wikipedia.org/", "link_type": "homepage"}
                ],
            }
        ],
    }
    assert not _has_error(schema_validator, data)


def test_patch_without_claims_or_sources_rejected(schema_validator):
    # Neither block, and an empty sources block, are both rejected.
    assert _has_error(schema_validator, {"attribution": "ipdb"})
    assert _has_error(schema_validator, {"attribution": "ipdb", "sources": []})


@pytest.mark.parametrize(
    "source",
    [
        {"source_type": "web"},  # missing name
        {"name": "X"},  # missing source_type
        {"name": "X", "source_type": "blog"},  # source_type not in enum
        {"name": "X", "source_type": "web", "bogus": 1},  # unknown key
        {  # nested children unsupported (v1 sources are flat)
            "name": "X",
            "source_type": "web",
            "children": [{"name": "Y", "source_type": "web"}],
        },
        {  # link_type not in enum
            "name": "X",
            "source_type": "web",
            "links": [{"url": "https://x/", "link_type": "bogus"}],
        },
        {  # link missing url
            "name": "X",
            "source_type": "web",
            "links": [{"link_type": "homepage"}],
        },
    ],
)
def test_malformed_source_rejected(schema_validator, source):
    data = {"attribution": "flipcommons-catalog", "sources": [source]}
    assert _has_error(schema_validator, data)


# --- Schema: delete / remove directives -------------------------------------


def test_delete_and_remove_directives_valid(schema_validator):
    data = {
        "attribution": "flip-museum",
        "claims": [
            {"model.foo": {"delete": True}},
            {"corporate-entity.bar": {"remove": {"location": ["germany"]}}},
        ],
    }
    assert not _has_error(schema_validator, data)


# --- The shipped patches validate cleanly ----------------------------------


def test_shipped_patches_pass(schema_validator):
    for path in sorted(vp.PATCHES_DIR.glob("*.yaml")):
        data = yaml.load(path.read_text(encoding="utf-8"), Loader=vp._StrictLoader)
        errors = list(schema_validator.iter_errors(data))
        assert not errors, f"{path.name}: {[e.message for e in errors]}"
