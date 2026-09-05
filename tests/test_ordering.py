"""T-011 — declared ordering.

A slot is a fragment's leaf name up to its first dot, so `core/tone.claude`
and `core/tone.gpt` both fill the slot `tone`. That split is what lets an
order describe STRUCTURE while a condition chooses the VARIANT — the
separation amendment 6's model-portability use case rests on.

Ordering is parameterized by gating the declaration itself with a condition,
reusing the existing mechanism instead of inventing a second one (SD4).
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params, slot_of
from promptrecipe.errors import AmbiguousOrder, UnknownOrderName, UnorderedFragment
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/role": "ROLE",
    "core/tone.claude": "TONE-CLAUDE",
    "core/tone.gpt": "TONE-GPT",
    "core/safety": "SAFETY",
}


def run(recipe: str, params: Params | None = None):
    entries = {**LIBRARY, "core/r": recipe}
    r = Resolver().register("core", "mem", MemoryCustody(entries))
    return get_prompt("core/r", params or Params(), r)


def test_a_slot_is_the_leaf_name_up_to_the_first_dot():
    assert slot_of(FragmentPath.parse("core/tone.claude")) == "tone"
    assert slot_of(FragmentPath.parse("core/tone.gpt")) == "tone"
    assert slot_of(FragmentPath.parse("core/role")) == "role"
    assert slot_of(FragmentPath.parse("core/a/b/deep.variant")) == "deep"


def test_a_declared_order_permutes_the_fragments():
    out = run("[load core/role][load core/safety][order: safety, role]")
    assert out.text == "SAFETYROLE"


def test_document_order_applies_when_nothing_is_declared():
    assert run("[load core/role][load core/safety]").text == "ROLESAFETY"


def test_prose_keeps_its_position_while_fragments_move():
    """Reordering must stay predictable: the shape of the recipe is unchanged,
    only which fragment sits in which load position."""
    out = run("A[load core/role]B[load core/safety]C[order: safety, role]")
    assert out.text == "ASAFETYBROLEC"


def test_a_variant_fills_the_slot_its_base_name_names():
    """The point of slots: the order says `tone`, the condition picks which."""
    recipe = (
        "[load core/role]"
        '[if model == "claude"][load core/tone.claude]'
        '[if model == "gpt"][load core/tone.gpt]'
        "[order: tone, role]"
    )
    claude = run(recipe, Params(controls={"model": "claude"}))
    gpt = run(recipe, Params(controls={"model": "gpt"}))

    assert claude.text == "TONE-CLAUDEROLE"
    assert gpt.text == "TONE-GPTROLE"


def test_ordering_is_parameterized_by_gating_the_declaration():
    """SD4: no separate ordering subsystem — a condition gates the order
    declaration exactly as it gates a load."""
    recipe = (
        "[load core/role][load core/safety]"
        "[if reversed][order: safety, role]"
        "[if not reversed][order: role, safety]"
    )
    assert run(recipe, Params(controls={"reversed": True})).text == "SAFETYROLE"
    assert run(recipe, Params(controls={"reversed": False})).text == "ROLESAFETY"


def test_reordering_changes_the_structural_identity():
    """SD13, end to end: the same fragments in a different order are a
    different prompt, and the identity must say so."""
    recipe = "[load core/role][load core/safety][if reversed][order: safety, role]"
    a = run(recipe, Params(controls={"reversed": True}))
    b = run(recipe, Params(controls={"reversed": False}))

    assert {p for p, _ in a.fragments} == {p for p, _ in b.fragments}, "same fragment SET"
    assert a.text != b.text
    assert a.attestation.structural_identity != b.attestation.structural_identity


def test_two_active_order_declarations_fail_rather_than_one_winning():
    with pytest.raises(AmbiguousOrder) as exc:
        run("[load core/role][load core/safety][order: role, safety][order: safety, role]")
    assert "does not say what the order is" in str(exc.value)


def test_an_order_naming_an_unloaded_slot_fails():
    with pytest.raises(UnknownOrderName) as exc:
        run("[load core/role][order: role, absent]")
    assert "absent" in str(exc.value)


def test_a_loaded_fragment_the_order_ignores_fails():
    """Once an order is declared it must account for every loaded fragment,
    or the unmentioned ones have no defined position."""
    with pytest.raises(UnorderedFragment) as exc:
        run("[load core/role][load core/safety][order: role]")
    assert "safety" in str(exc.value)


def test_an_order_that_is_not_reached_does_not_apply():
    out = run(
        "[load core/role][load core/safety][if never][order: safety, role]",
        Params(controls={"never": False}),
    )
    assert out.text == "ROLESAFETY"
