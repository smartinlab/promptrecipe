"""T-017 — layering by DECLARED precedence, with an inspectable trace.

ADR-004 forbids resolving a collision by registration order, because that
makes shadowing invisible. Layering is therefore opt-in: a source overrides
another only when someone assigned it a higher precedence on purpose. Equal
precedence stays ambiguous and still errors.

Gate 0 found that mature precedence systems become confusing at scale
precisely because they are not inspectable — so `explain()` is part of the
type, not a debugging afterthought.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.errors import AmbiguousReference
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

BASE = {"core/tone": "BASE TONE"}
OVERRIDE = {"core/tone": "PROJECT TONE"}


def test_a_higher_precedence_source_overrides_a_lower_one():
    r = (
        Resolver()
        .register("core", "base", MemoryCustody(BASE), precedence=0)
        .register("core", "project", MemoryCustody(OVERRIDE), precedence=10)
    )
    content, trace = r.fetch(FragmentPath.parse("core/tone"))
    assert content.text == "PROJECT TONE"
    assert trace.winner == "project"


def test_precedence_wins_regardless_of_registration_order():
    """The whole point: the override is declared, not positional."""
    forward = (
        Resolver()
        .register("core", "base", MemoryCustody(BASE), precedence=0)
        .register("core", "project", MemoryCustody(OVERRIDE), precedence=10)
    )
    backward = (
        Resolver()
        .register("core", "project", MemoryCustody(OVERRIDE), precedence=10)
        .register("core", "base", MemoryCustody(BASE), precedence=0)
    )
    assert forward.read(FragmentPath.parse("core/tone")).text == "PROJECT TONE"
    assert backward.read(FragmentPath.parse("core/tone")).text == "PROJECT TONE"


def test_equal_precedence_is_still_ambiguous_and_still_errors():
    """Layering does not weaken ADR-004 — it only honours a DECLARED
    difference. Two sources nobody ranked remain a collision."""
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody(BASE))
        .register("core", "beta", MemoryCustody(OVERRIDE))
    )
    with pytest.raises(AmbiguousReference) as exc:
        r.fetch(FragmentPath.parse("core/tone"))
    assert "precedence" in str(exc.value)


def test_the_default_is_no_layering():
    """A resolver built without thinking about precedence behaves exactly as
    before: collisions error."""
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody(BASE))
        .register("core", "beta", MemoryCustody(OVERRIDE))
    )
    with pytest.raises(AmbiguousReference):
        get_prompt("core/tone", Params(), r)


def test_a_lower_precedence_source_still_supplies_what_the_override_lacks():
    """Layering, not replacement: the override only shadows what it defines."""
    r = (
        Resolver()
        .register("core", "base", MemoryCustody({"core/tone": "BASE", "core/role": "ROLE"}))
        .register("core", "project", MemoryCustody({"core/tone": "OVERRIDE"}), precedence=10)
    )
    assert r.read(FragmentPath.parse("core/tone")).text == "OVERRIDE"
    assert r.read(FragmentPath.parse("core/role")).text == "ROLE"


def test_the_trace_explains_why_a_fragment_won():
    r = (
        Resolver()
        .register("core", "base", MemoryCustody(BASE), precedence=0)
        .register("core", "project", MemoryCustody(OVERRIDE), precedence=10)
    )
    _, trace = r.fetch(FragmentPath.parse("core/tone"))
    explanation = trace.explain()

    assert "core/tone" in explanation
    assert "base" in explanation and "project" in explanation
    assert "precedence 10" in explanation
    assert "<- winner" in explanation


def test_the_trace_names_sources_that_did_not_match():
    """Every candidate is consulted, so the trace can say who was asked and
    came back empty — not only who won."""
    r = (
        Resolver()
        .register("core", "empty", MemoryCustody({}))
        .register("core", "has_it", MemoryCustody(BASE), precedence=5)
    )
    _, trace = r.fetch(FragmentPath.parse("core/tone"))
    assert len(trace.entries) == 2
    assert [e.found for e in trace.entries] == [False, True]
    assert "empty" in trace.explain()


def test_an_override_reaches_assembly_end_to_end():
    r = (
        Resolver()
        .register(
            "core",
            "base",
            MemoryCustody({"core/r": "[load core/tone]", "core/tone": "BASE"}),
        )
        .register("core", "project", MemoryCustody({"core/tone": "OVERRIDE"}), precedence=10)
    )
    assert get_prompt("core/r", Params(), r).text == "OVERRIDE"
