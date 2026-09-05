import pytest
from conftest import MemoryCustody

from promptrecipe.errors import FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def test_a_namespace_routes_to_its_source():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    assert r.known_namespaces == ["core"]
    assert len(r.sources_for("core")) == 1


def test_namespaces_are_isolated_from_one_another():
    """ADR-004: the same leaf name in two namespaces cannot collide."""
    r = (
        Resolver()
        .register("core", "a", MemoryCustody({"core/tone": "core version"}))
        .register("team", "b", MemoryCustody({"team/tone": "team version"}))
    )
    assert r.known_namespaces == ["core", "team"]


def test_namespace_ordering_is_deterministic():
    def build():
        return (
            Resolver()
            .register("zeta", "z", MemoryCustody())
            .register("alpha", "a", MemoryCustody())
            .known_namespaces
        )

    assert build() == build() == ["alpha", "zeta"]


def test_resolves_a_single_candidate_and_records_a_trace():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    fid, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert fid == FragmentId.of(b"Be concise.")
    assert trace.winner == "local"
    assert len(trace.entries) == 1


def test_every_candidate_is_evaluated_not_short_circuited():
    """Short-circuiting on the first hit would make ambiguity invisible."""
    r = (
        Resolver()
        .register("core", "first", MemoryCustody())
        .register("core", "second", MemoryCustody({"core/tone": "from second"}))
    )
    _, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert len(trace.entries) == 2
    assert trace.winner == "second"


def test_unknown_namespace_fails_naming_the_known_ones():
    r = Resolver().register("core", "local", MemoryCustody())
    with pytest.raises(UnknownNamespace) as exc:
        r.resolve(FragmentPath.parse("nope/x"))
    assert "core" in str(exc.value)


def test_a_missing_fragment_fails_and_never_falls_back():
    r = Resolver().register("core", "local", MemoryCustody({"core/other": "x"}))
    with pytest.raises(FragmentNotFound):
        r.resolve(FragmentPath.parse("core/tone"))


def test_read_returns_content():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    assert r.read(FragmentPath.parse("core/tone")).text == "Be concise."


def test_resolution_performs_no_assembly():
    """FR-011 depends on resolution staying cheap."""
    import inspect

    from promptrecipe import resolve

    source = inspect.getsource(resolve)
    for forbidden in ("assemble", "substitute"):
        assert forbidden not in source, f"resolution must not reference '{forbidden}'"
