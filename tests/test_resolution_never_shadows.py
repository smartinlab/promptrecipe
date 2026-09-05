"""ADR-004 / FR-031: resolution must never silently pick between candidates."""

import pytest
from conftest import MemoryCustody

from promptrecipe.errors import AmbiguousReference
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def test_two_candidates_produce_an_error_not_a_winner():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "from alpha"}))
        .register("core", "beta", MemoryCustody({"core/tone": "from beta"}))
    )
    with pytest.raises(AmbiguousReference):
        r.resolve(FragmentPath.parse("core/tone"))


def test_the_ambiguity_error_names_every_candidate():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "a"}))
        .register("core", "beta", MemoryCustody({"core/tone": "b"}))
        .register("core", "gamma", MemoryCustody({"core/tone": "c"}))
    )
    with pytest.raises(AmbiguousReference) as exc:
        r.resolve(FragmentPath.parse("core/tone"))
    msg = str(exc.value)
    for candidate in ("alpha", "beta", "gamma"):
        assert candidate in msg
    assert "3 candidates" in msg


def test_identical_content_in_two_sources_is_still_ambiguous():
    """Even when both would produce identical bytes, the CONFIGURATION is
    ambiguous: the next edit to one source would change behaviour silently."""
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "same"}))
        .register("core", "beta", MemoryCustody({"core/tone": "same"}))
    )
    with pytest.raises(AmbiguousReference):
        r.resolve(FragmentPath.parse("core/tone"))


def test_a_single_candidate_across_several_sources_resolves_cleanly():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/other": "x"}))
        .register("core", "beta", MemoryCustody({"core/tone": "the only one"}))
    )
    fid, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert fid == FragmentId.of(b"the only one")
    assert trace.winner == "beta"
    assert len(trace.entries) == 2
