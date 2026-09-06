"""T-018 / T-020 — reproduce from a record, and bind a result to an assembly.

The point of recording provenance is that a result can be traced back to the
exact prompt that earned it, weeks later. That is only worth something if the
rebuild is VERIFIED rather than assumed.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import Params, binds_to, drift, get_prompt, reproduce
from promptrecipe.errors import IdentityMismatch
from promptrecipe.provenance import Attestation, Producer
from promptrecipe.reproduce import IrreproducibleAssembly, params_from
from promptrecipe.resolve import Resolver

LIB = {
    "core/r": "Header\n[load core/role]\n[if premium][load core/extra]\nHello {{name}}",
    "core/role": "ROLE",
    "core/extra": "EXTRA",
}


def library(**overrides):
    return Resolver().register("core", "mem", MemoryCustody({**LIB, **overrides}))


def assemble_once(resolver=None, **controls):
    return get_prompt(
        "core/r",
        Params(controls={"premium": True, **controls}, values={"name": "Aria"}),
        resolver or library(),
    )


# --- reproduction ----------------------------------------------------------


def test_an_assembly_reproduces_byte_identically():
    resolver = library()
    original = assemble_once(resolver)
    rebuilt = reproduce(original.attestation, resolver)

    assert rebuilt.text == original.text
    assert rebuilt.attestation.subject == original.attestation.subject
    assert rebuilt.attestation.instance_identity == original.attestation.instance_identity


def test_reproduction_replays_the_branch_that_was_taken():
    """SD6: the fragment list says WHAT loaded, not WHY. Without the control
    bindings the branch cannot be replayed."""
    resolver = library()
    without_extra = assemble_once(resolver, premium=False)
    rebuilt = reproduce(without_extra.attestation, resolver)

    assert "EXTRA" not in rebuilt.text
    assert rebuilt.text == without_extra.text


def test_the_recorded_params_round_trip():
    original = assemble_once()
    params = params_from(original.attestation)
    assert params.controls == {"premium": True}
    assert params.values == {"name": "Aria"}


def test_a_changed_fragment_fails_and_never_substitutes():
    """A reproduction that quietly used newer content would be worse than no
    reproduction at all."""
    original = assemble_once()
    moved_on = library(**{"core/role": "ROLE, REWRITTEN"})

    with pytest.raises(IrreproducibleAssembly) as exc:
        reproduce(original.attestation, moved_on)
    assert "core/role" in str(exc.value)


def test_a_changed_recipe_is_detected_too():
    original = assemble_once()
    moved_on = library(**{"core/r": "Different header\n[load core/role]"})

    with pytest.raises(IrreproducibleAssembly) as exc:
        reproduce(original.attestation, moved_on)
    assert "core/r" in str(exc.value)


def test_a_deleted_fragment_says_it_is_gone():
    original = assemble_once()
    without = Resolver().register(
        "core", "mem", MemoryCustody({k: v for k, v in LIB.items() if k != "core/role"})
    )
    with pytest.raises(IrreproducibleAssembly) as exc:
        reproduce(original.attestation, without)
    assert "gone" in str(exc.value)


def test_a_record_with_no_recipe_path_says_what_is_missing():
    orphan = Attestation(subject="aa" * 32, producer=Producer())
    with pytest.raises(IrreproducibleAssembly) as exc:
        reproduce(orphan, library())
    assert "nothing names what to rebuild" in str(exc.value)


def test_a_library_change_that_alters_output_is_reported_as_a_mismatch(monkeypatch):
    """Every input matches but the output differs: the library itself changed.
    Saying so beats returning different text."""
    resolver = library()
    original = assemble_once(resolver)

    # `promptrecipe.assemble` is the FUNCTION, not the module — the package
    # re-exports it and shadows the submodule. Reach the module explicitly.
    import importlib

    module = importlib.import_module("promptrecipe.assemble")
    real = module._substitute
    def drifted(text, values):
        substituted, edits = real(text, values)
        return substituted + " DRIFT", edits

    monkeypatch.setattr(module, "_substitute", drifted)

    with pytest.raises(IdentityMismatch):
        reproduce(original.attestation, resolver)


# --- drift, without doing the work ----------------------------------------


def test_drift_is_empty_when_nothing_moved():
    resolver = library()
    assert drift(assemble_once(resolver).attestation, resolver) == []


def test_drift_names_every_input_that_moved():
    original = assemble_once()
    moved_on = library(**{"core/role": "CHANGED", "core/extra": "ALSO CHANGED"})
    assert set(drift(original.attestation, moved_on)) == {"core/role", "core/extra"}


# --- binding a result (T-020) ----------------------------------------------


def test_a_result_binds_by_structural_identity():
    original = assemble_once()
    assert binds_to(original.attestation, original.attestation.structural_identity)


def test_two_customers_share_the_binding():
    """An evaluation result belongs to a prompt DESIGN. Two runs for two
    customers are the same design, so a result groups across both."""
    resolver = library()

    def for_customer(name: str):
        return get_prompt(
            "core/r", Params(controls={"premium": True}, values={"name": name}), resolver
        )

    aria, nova = for_customer("Aria"), for_customer("Nova")

    assert aria.text != nova.text
    assert binds_to(nova.attestation, aria.attestation.structural_identity)


def test_binding_by_instance_identity_groups_nothing():
    """The most likely misuse of the pair, made explicit."""
    resolver = library()

    def for_customer(name: str):
        return get_prompt(
            "core/r", Params(controls={"premium": True}, values={"name": name}), resolver
        )

    aria, nova = for_customer("Aria"), for_customer("Nova")

    assert not binds_to(nova.attestation, aria.attestation.instance_identity)


def test_a_different_variant_does_not_bind():
    resolver = library()
    with_extra = assemble_once(resolver, premium=True)
    without = assemble_once(resolver, premium=False)
    assert not binds_to(without.attestation, with_extra.attestation.structural_identity)


# --- the collision this work uncovered -------------------------------------


def test_two_recipes_with_different_prose_do_not_collide():
    """Found while building reproduction: the canonical form omitted the
    recipe entirely, so two recipes loading the same fragments in the same
    order shared one structural identity — the same silent-collision class as
    an order-blind identity."""
    resolver = Resolver().register(
        "core",
        "mem",
        MemoryCustody(
            {
                "core/a": "PROSE A\n[load core/f]",
                "core/b": "COMPLETELY DIFFERENT PROSE\n[load core/f]",
                "core/f": "FRAGMENT",
            }
        ),
    )
    a = get_prompt("core/a", Params(), resolver)
    b = get_prompt("core/b", Params(), resolver)

    assert a.text != b.text
    assert a.attestation.structural_identity != b.attestation.structural_identity
    assert not binds_to(b.attestation, a.attestation.structural_identity)
