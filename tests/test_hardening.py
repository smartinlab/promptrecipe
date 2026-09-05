"""Hardening for the defects the code review found.

Each test names the guarantee it protects and what breaking it would mean.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import MAX_EXPRESSION_DEPTH, Params, assemble
from promptrecipe.custody import FragmentContent
from promptrecipe.custody.fs import FsCustody
from promptrecipe.errors import (
    DepthLimitExceeded,
    OrderNotImplemented,
    PathEscapesNamespace,
    PromptRecipeError,
    UndecodableFragment,
)
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def resolver(entries=None):
    return Resolver().register("core", "mem", MemoryCustody(entries or {"core/x": "body"}))


# --- depth ceilings: a bare RecursionError escapes `except PromptRecipeError` ---


def test_deeply_nested_parentheses_raise_a_library_error_not_recursionerror():
    src = "[if " + "(" * 500 + "true" + ")" * 500 + "] body"
    with pytest.raises(PromptRecipeError) as exc:
        parse(src)
    assert isinstance(exc.value, DepthLimitExceeded)


def test_deeply_nested_not_raises_a_library_error():
    src = "[if " + "not " * 500 + "true] body"
    with pytest.raises(PromptRecipeError):
        parse(src)


def test_a_deep_tree_reaching_the_evaluator_directly_is_also_bounded():
    """The parser bounds what it builds, but an AST can arrive by other routes."""
    from promptrecipe.parser.nodes import Literal, Not

    expr = Literal(True)
    for _ in range(MAX_EXPRESSION_DEPTH + 10):
        expr = Not(expr)

    from promptrecipe.assemble import _truth

    with pytest.raises(DepthLimitExceeded):
        _truth(expr, Params())


def test_a_legible_condition_is_well_within_the_ceiling():
    """The ceiling must not reject anything a person would actually write."""
    out = assemble(
        parse('[if ((model == "claude") and (not verbose)) or always] [load core/x]'),
        Params(controls={"model": "claude", "verbose": False, "always": False}),
        resolver(),
    )
    assert "body" in out.text


# --- nested If was silently dropped: fail-closed, but silently wrong ---


def test_a_nested_condition_is_evaluated_not_dropped():
    r = resolver({"core/r": "[if a][if b] [load core/x]", "core/x": "BODY"})
    both = get_prompt("core/r", Params(controls={"a": True, "b": True}), r)
    assert "BODY" in both.text

    inner_false = get_prompt("core/r", Params(controls={"a": True, "b": False}), r)
    assert "BODY" not in inner_false.text

    outer_false = get_prompt("core/r", Params(controls={"a": False, "b": True}), r)
    assert "BODY" not in outer_false.text


def test_both_conditions_are_recorded_in_provenance():
    """SD6: a branch cannot be replayed if only the outer condition was kept."""
    r = resolver({"core/r": "[if a][if b] [load core/x]", "core/x": "BODY"})
    out = get_prompt("core/r", Params(controls={"a": True, "b": True}), r)
    assert len(out.attestation.condition_outcomes) == 2


# --- [order] parsed but never applied ---


def test_an_order_directive_fails_loudly_instead_of_being_ignored():
    """Silently dropping it would produce a prompt whose sequence contradicts
    the recipe — and order is part of identity (SD13)."""
    with pytest.raises(OrderNotImplemented) as exc:
        assemble(parse("[order: role, tone]"), Params(), resolver())
    assert "T-011" in str(exc.value)


# --- symlink escape: lexical canonicalization cannot see a symlink ---


def test_a_symlink_cannot_read_outside_the_namespace_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("OUTSIDE SECRET")

    root = tmp_path / "ns"
    root.mkdir()
    (root / "leak.md").symlink_to(outside / "secret.md")

    custody = FsCustody().with_namespace("core", root)
    with pytest.raises(PathEscapesNamespace):
        custody.read(FragmentPath.parse("core/leak"))


def test_a_symlink_inside_the_root_is_still_allowed(tmp_path):
    """Confinement, not a blanket symlink ban — a link within the namespace is
    a legitimate way to alias a fragment."""
    root = tmp_path / "ns"
    (root / "real").mkdir(parents=True)
    (root / "real" / "tone.md").write_text("INSIDE")
    (root / "alias.md").symlink_to(root / "real" / "tone.md")

    custody = FsCustody().with_namespace("core", root)
    assert custody.read(FragmentPath.parse("core/alias")).text == "INSIDE"


# --- every failure is catchable as one type ---


def test_invalid_utf8_raises_a_library_error_not_unicodedecodeerror():
    content = FragmentContent.of(b"\xff\xfe\x00bad")
    with pytest.raises(UndecodableFragment) as exc:
        _ = content.text
    assert isinstance(exc.value, PromptRecipeError)
