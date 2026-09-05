from dataclasses import replace

from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)
from promptrecipe.resolve import Resolver


def sample() -> Attestation:
    return Attestation(
        subject="aa" * 32,
        resolved_dependencies=[ResolvedDependency("core/tone", "bb" * 32)],
        resolved_order=["core/tone"],
        producer=Producer(),
    )


def test_different_values_keep_structural_identity_and_change_instance_identity():
    """THE defining property of ADR-005.

    Two runs of the same prompt design for two different customers are the
    SAME variant (comparable) and DIFFERENT renderings (each reproducible).
    """
    acme = replace(sample(), value_bindings=[("customer", "Acme")])
    globex = replace(sample(), value_bindings=[("customer", "Globex")])

    assert structural_identity(acme) == structural_identity(globex), (
        "same prompt design must share a structural identity, or A/B grouping "
        "breaks and every run stands alone"
    )
    assert instance_identity(acme) != instance_identity(globex), (
        "different rendered text must have different instance identities, or "
        "reproduction cannot tell two renderings apart"
    )


def test_different_fragment_order_changes_the_structural_identity():
    ab = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("a", "1"), ResolvedDependency("b", "2")],
    )
    ba = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("b", "2"), ResolvedDependency("a", "1")],
    )
    assert structural_identity(ab) != structural_identity(ba)


def test_identities_are_full_length_digests():
    a = sample()
    assert len(structural_identity(a)) == 64
    assert len(instance_identity(a)) == 64


def test_a_timestamp_change_leaves_both_identities_untouched():
    a = sample()
    b = replace(sample(), recorded_at="2099-01-01T00:00:00Z")
    assert structural_identity(a) == structural_identity(b)
    assert instance_identity(a) == instance_identity(b)


def test_every_assembly_carries_an_attestation():
    """SD5: the record is a return value, so it cannot be skipped."""
    resolver = Resolver().register(
        "core", "mem", MemoryCustody({"core/r": "[load core/f]", "core/f": "body"})
    )
    out = get_prompt("core/r", Params(), resolver)
    assert len(out.attestation.structural_identity) == 64
    assert len(out.attestation.instance_identity) == 64
    assert out.attestation.resolved_dependencies[0].path == "core/f"


def test_values_move_instance_identity_only_end_to_end():
    resolver = Resolver().register(
        "core",
        "mem",
        MemoryCustody({"core/r": "Hello {{customer}} [load core/f]", "core/f": "body"}),
    )
    a = get_prompt("core/r", Params(values={"customer": "Acme"}), resolver)
    b = get_prompt("core/r", Params(values={"customer": "Globex"}), resolver)

    assert a.text != b.text
    assert a.attestation.structural_identity == b.attestation.structural_identity
    assert a.attestation.instance_identity != b.attestation.instance_identity
