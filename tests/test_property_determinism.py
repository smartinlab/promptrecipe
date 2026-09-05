"""Property P1 — determinism (TRD §4, SD7).

Assembly must be a pure function: the same inputs always produce the same
bytes. TRD §4 names the hazards — hash/dict-order iteration, wall-clock and
environment leakage, locale-sensitive comparison, filesystem enumeration.
"""

from conftest import MemoryCustody
from hypothesis import given, settings
from hypothesis import strategies as st

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.resolve import Resolver

SETTINGS = settings(max_examples=200, deadline=None)


def library(count: int) -> Resolver:
    """A recipe loading `count` fragments, each gated by a control variable,
    with value placeholders in the prose."""
    entries = {f"core/f{i}": f"FRAGMENT-{i}-BODY" for i in range(count)}
    recipe = ["Header {{customer}}\n"]
    recipe += [f"[if flag{i}] [load core/f{i}]\n" for i in range(count)]
    recipe.append("Footer {{customer}}\n")
    entries["core/recipe"] = "".join(recipe)
    return Resolver().register("core", "mem", MemoryCustody(entries))


@SETTINGS
@given(
    flags=st.lists(st.booleans(), min_size=1, max_size=12),
    customer=st.text(max_size=24),
)
def test_assembly_is_byte_identical_for_identical_inputs(flags, customer):
    resolver = library(len(flags))
    params = Params(
        controls={f"flag{i}": on for i, on in enumerate(flags)},
        values={"customer": customer},
    )

    first = get_prompt("core/recipe", params, resolver)
    second = get_prompt("core/recipe", params, resolver)

    assert first.text == second.text
    assert first.fragments == second.fragments
    assert first.condition_outcomes == second.condition_outcomes


@SETTINGS
@given(flags=st.lists(st.booleans(), min_size=1, max_size=8))
def test_repeated_assembly_never_drifts(flags):
    resolver = library(len(flags))
    params = Params(controls={f"flag{i}": on for i, on in enumerate(flags)})

    baseline = get_prompt("core/recipe", params, resolver).text
    for round_number in range(10):
        assert baseline == get_prompt("core/recipe", params, resolver).text, (
            f"drift appeared at round {round_number}"
        )


@SETTINGS
@given(flags=st.lists(st.booleans(), min_size=2, max_size=8))
def test_binding_insertion_order_does_not_affect_output(flags):
    """The direct guard against dict-insertion order reaching the result."""
    resolver = library(len(flags))

    forward = Params(controls={f"flag{i}": on for i, on in enumerate(flags)})
    backward = Params(controls={f"flag{i}": on for i, on in reversed(list(enumerate(flags)))})

    assert (
        get_prompt("core/recipe", forward, resolver).text
        == get_prompt("core/recipe", backward, resolver).text
    ), "binding insertion order leaked into output"


@SETTINGS
@given(value=st.text(max_size=40))
def test_arbitrary_value_text_never_changes_which_fragments_load(value):
    """ADR-006 as a property: no caller-supplied text, however hostile,
    can influence structure."""
    resolver = library(3)
    params = Params(
        controls={f"flag{i}": True for i in range(3)},
        values={"customer": value},
    )
    out = get_prompt("core/recipe", params, resolver)
    assert len(out.fragments) == 3, "value text must never add or remove a fragment"
