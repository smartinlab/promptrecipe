import pytest
from conftest import MemoryCustody

from promptrecipe.assemble import Params, assemble
from promptrecipe.errors import ExpectationFailed
from promptrecipe.parser.parse import parse
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/role": "You are an assistant.",
    "core/tone.claude": "Be concise.",
    "core/tone.gpt": "Be thorough.",
}


def run(src: str, params: Params | None = None):
    resolver = Resolver().register("core", "mem", MemoryCustody(LIBRARY))
    return assemble(parse(src), params or Params(), resolver)


def test_loads_and_concatenates_in_declaration_order():
    out = run("[load core/role] [load core/tone.claude]")
    assert "You are an assistant." in out.text
    assert "Be concise." in out.text
    assert len(out.fragments) == 2


def test_a_false_condition_excludes_its_fragment():
    out = run(
        "[load core/role][if use_tone] [load core/tone.claude]",
        Params(controls={"use_tone": False}),
    )
    assert "Be concise." not in out.text
    assert len(out.fragments) == 1


def test_condition_outcomes_are_recorded_so_a_branch_can_be_replayed():
    """SD6: the fragment list says WHAT loaded but not WHY."""
    out = run("[if use_tone] [load core/tone.claude]", Params(controls={"use_tone": True}))
    assert len(out.condition_outcomes) == 1
    assert out.condition_outcomes[0][1] is True


def test_a_violated_expectation_emits_no_partial_output():
    with pytest.raises(ExpectationFailed):
        run(
            '[expect language in ["pt", "en"]] Some prose [load core/role]',
            Params(controls={"language": "fr"}),
        )


def test_an_address_variable_selects_which_fragment_loads():
    out = run("[load tone]", Params(addresses={"tone": "core/tone.gpt"}))
    assert "Be thorough." in out.text


def test_string_equality_drives_model_selection():
    out = run(
        '[if model == "claude"] [load core/tone.claude]', Params(controls={"model": "claude"})
    )
    assert "Be concise." in out.text
