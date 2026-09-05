"""Identity forgery: two different assemblies must never share an identity.

The canonical form separates fields with TAB and records with NEWLINE. Before
escaping, any caller-supplied string carrying a literal tab or newline could
inject a fake record and reproduce a different attestation's canonical text
byte-for-byte — a silent collision in the exact field A/B comparison depends
on.
"""

from conftest import MemoryCustody
from hypothesis import given, settings
from hypothesis import strategies as st

from promptrecipe.assemble import Params, assemble
from promptrecipe.parser.parse import parse
from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)
from promptrecipe.resolve import Resolver


def assemble_with(params: Params):
    resolver = Resolver().register("core", "mem", MemoryCustody({"core/x": "body"}))
    return assemble(parse("[load core/x]"), params, resolver)


def test_a_tab_and_newline_in_an_address_cannot_forge_an_identity():
    """The reported exploit, end to end through the public API."""
    honest = assemble_with(Params(addresses={"alpha": "core/a", "beta": "core/b"}))
    forged = assemble_with(Params(addresses={"alpha\tcore/a\nbeta": "core/b"}))

    assert honest.attestation.address_resolutions != forged.attestation.address_resolutions, (
        "the inputs must genuinely differ, or this test proves nothing"
    )
    assert honest.attestation.structural_identity != forged.attestation.structural_identity, (
        "different data produced the same structural identity — collision"
    )


def test_a_newline_in_a_value_cannot_forge_an_instance_identity():
    honest = assemble_with(Params(values={"a": "1", "b": "2"}))
    forged = assemble_with(Params(values={"a\t1\nb": "2"}))
    assert honest.attestation.instance_identity != forged.attestation.instance_identity


def test_a_backslash_is_escaped_so_the_mapping_stays_injective():
    """Escaping tab as `\\t` would itself collide with a literal `\\t` unless
    backslash is escaped first."""
    a = assemble_with(Params(values={"k": "x\ty"}))
    b = assemble_with(Params(values={"k": "x\\ty"}))
    assert a.attestation.instance_identity != b.attestation.instance_identity


def _attestation(deps, values=None):
    return Attestation(
        subject="00" * 32,
        resolved_dependencies=[ResolvedDependency(p, i) for p, i in deps],
        resolved_order=[p for p, _ in deps],
        value_bindings=values or [],
        producer=Producer(),
    )


@settings(max_examples=300, deadline=None)
@given(
    left=st.text(max_size=20),
    right=st.text(max_size=20),
)
def test_distinct_dependency_paths_never_share_a_structural_identity(left, right):
    """Property form: no pair of distinct strings — including any mix of tabs,
    newlines and backslashes hypothesis generates — may collide."""
    if left == right:
        return
    a = _attestation([(left, "aa" * 32)])
    b = _attestation([(right, "aa" * 32)])
    assert structural_identity(a) != structural_identity(b)


@settings(max_examples=300, deadline=None)
@given(left=st.text(max_size=20), right=st.text(max_size=20))
def test_distinct_value_bindings_never_share_an_instance_identity(left, right):
    if left == right:
        return
    a = _attestation([("core/x", "aa" * 32)], [("k", left)])
    b = _attestation([("core/x", "aa" * 32)], [("k", right)])
    assert instance_identity(a) != instance_identity(b)


def test_the_producer_version_tracks_the_package_version():
    import promptrecipe

    assert Producer().version == promptrecipe.__version__
