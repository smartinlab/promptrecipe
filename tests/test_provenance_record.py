import json
from dataclasses import replace

from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    canonical_instance_form,
    canonical_structural_form,
)


def sample() -> Attestation:
    return Attestation(
        subject="aa" * 32,
        resolved_dependencies=[ResolvedDependency(path="core/tone", identity="bb" * 32)],
        condition_outcomes=[("(model == 'claude')", True)],
        resolved_order=["core/role", "core/tone"],
        address_resolutions=[("tone", "core/tone.claude")],
        value_bindings=[("customer", "Acme")],
        producer=Producer(),
        recorded_at="2026-09-05T12:00:00Z",
        structural_identity="cc" * 32,
        instance_identity="dd" * 32,
    )


def test_an_attestation_round_trips_through_json():
    a = sample()
    assert Attestation.from_json(json.loads(a.to_json())) == a


def test_dependencies_keep_their_assembly_order():
    """SD13: order is part of identity, so this must be a list, not a set."""
    a = replace(
        sample(),
        resolved_dependencies=[
            ResolvedDependency(path="b", identity="1"),
            ResolvedDependency(path="a", identity="2"),
        ],
    )
    back = Attestation.from_json(json.loads(a.to_json()))
    assert back.resolved_dependencies[0].path == "b"


def test_the_producer_records_the_digest_algorithm():
    assert Producer().digest_algorithm == "blake3"
    assert Producer().name == "promptrecipe"


def test_the_canonical_form_is_stable_across_calls():
    a = sample()
    assert canonical_structural_form(a) == canonical_structural_form(a)


def test_a_timestamp_never_reaches_the_canonical_form():
    """TRD §4: wall-clock must not leak into anything digested."""
    base = sample()
    assert canonical_structural_form(base) == canonical_structural_form(
        replace(base, recorded_at="2099-01-01T00:00:00Z")
    )
    assert canonical_structural_form(base) == canonical_structural_form(
        replace(base, recorded_at=None)
    )


def test_value_binding_order_does_not_change_the_canonical_form():
    forward = replace(sample(), value_bindings=[("a", "1"), ("b", "2")])
    backward = replace(sample(), value_bindings=[("b", "2"), ("a", "1")])
    assert canonical_instance_form(forward) == canonical_instance_form(backward)


def test_dependency_order_DOES_change_the_canonical_form():
    """The deliberate opposite of the previous test.

    Bindings are a SET of inputs, so their order is incidental. Dependency
    ORDER is part of what the prompt IS (SD13). Sorting dependencies here
    would destroy that and silently corrupt every comparison.
    """
    ab = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("a", "1"), ResolvedDependency("b", "2")],
    )
    ba = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("b", "2"), ResolvedDependency("a", "1")],
    )
    assert canonical_structural_form(ab) != canonical_structural_form(ba)


def test_the_structural_form_excludes_value_bindings():
    with_values = replace(sample(), value_bindings=[("customer", "Acme")])
    without = replace(sample(), value_bindings=[])
    assert canonical_structural_form(with_values) == canonical_structural_form(without)
