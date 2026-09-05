import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.errors import FragmentNotFound
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/recipe.claude": "[load core/role]\n[load core/tone.claude]\n[load core/safety]",
    "core/recipe.gpt": "[load core/role]\n[load core/tone.gpt]\n[load core/safety]",
    "core/role": "You are an assistant.",
    "core/tone.claude": "Be concise.",
    "core/tone.gpt": "Be thorough.",
    "core/safety": "Refuse harmful requests.",
}


@pytest.fixture
def resolver():
    return Resolver().register("core", "mem", MemoryCustody(LIBRARY))


def test_assembles_a_prompt_from_a_recipe_path(resolver):
    out = get_prompt("core/recipe.claude", Params(), resolver)
    assert "You are an assistant." in out.text
    assert "Be concise." in out.text


def test_two_templates_share_a_fragment_by_reference_not_by_copy(resolver):
    """The driving use case (amendment 6): model portability.

    Proven by identity equality rather than by matching text.
    """
    a = get_prompt("core/recipe.claude", Params(), resolver)
    b = get_prompt("core/recipe.gpt", Params(), resolver)

    assert dict(a.fragments)["core/safety"] == dict(b.fragments)["core/safety"], (
        "the shared fragment must be one fragment, not two copies"
    )
    assert a.text != b.text, "the variants must still differ where they should"


def test_a_missing_recipe_fails_explicitly(resolver):
    with pytest.raises(FragmentNotFound) as exc:
        get_prompt("core/absent", Params(), resolver)
    assert "core/absent" in str(exc.value)


def test_control_variables_reach_conditions_through_the_entry_point():
    r = Resolver().register(
        "core",
        "mem",
        MemoryCustody({"core/r": "[if verbose] [load core/extra]", "core/extra": "EXTRA"}),
    )
    on = get_prompt("core/r", Params(controls={"verbose": True}), r)
    off = get_prompt("core/r", Params(controls={"verbose": False}), r)
    assert "EXTRA" in on.text
    assert "EXTRA" not in off.text
