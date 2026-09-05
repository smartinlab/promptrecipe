import pytest

from promptrecipe.errors import ParseError
from promptrecipe.parser.nodes import If, Load, PathVar, Text
from promptrecipe.parser.parse import parse

REALISTIC = """[expect language in ["pt", "en"]]
You are a technical assistant.

[load core/role]
[if model == "claude"] [load core/tone.claude]
[if model == "gpt"] [load core/tone.gpt]
[load core/safety]

[order: role, tone, safety]
"""


def test_a_realistic_recipe_parses_completely():
    assert parse(REALISTIC).statements


def test_expectations_are_reachable_before_any_assembly():
    assert len(parse(REALISTIC).expectations) == 1


def test_the_declared_order_is_read_not_inferred():
    """TRD §4: ordering must never derive from declaration sequence."""
    assert parse(REALISTIC).declared_order == ["role", "tone", "safety"]


def test_prose_is_preserved_verbatim_as_inert_text():
    recipe = parse("Hello [load core/x] world")
    texts = [s.value for s in recipe.statements if isinstance(s, Text)]
    assert texts == ["Hello ", " world"]


def test_text_that_looks_like_a_directive_is_still_just_text():
    """The load-bearing safety case at parse level (ADR-003)."""
    recipe = parse("The word load and the word if are ordinary words here.")
    assert len(recipe.statements) == 1
    assert isinstance(recipe.statements[0], Text)


def test_conditional_loads_carry_their_condition():
    stmt = parse('[if model == "claude"] [load core/tone.claude]').statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.body, Load)


def test_an_address_variable_load_is_distinguished_from_a_literal_path():
    """Amendment 9: an address variable's value is a path, not text."""
    stmt = parse("[load tone_choice]").statements[0]
    assert isinstance(stmt, Load)
    assert isinstance(stmt.path, PathVar)
    assert stmt.path.name == "tone_choice"


def test_an_unknown_directive_fails_naming_the_valid_ones():
    with pytest.raises(ParseError) as exc:
        parse("[render core/x]")
    msg = str(exc.value)
    assert "load" in msg
    assert "render" in msg


def test_a_membership_list_inside_a_directive_does_not_close_it_early():
    """Regression: the lexer must track bracket depth inside a directive.

    Found by execution, not by inspection — the first `]` of a membership
    list was closing the whole directive and the second became prose.
    """
    recipe = parse('[expect language in ["pt", "en"]]rest')
    assert len(recipe.expectations) == 1
    texts = [s.value for s in recipe.statements if isinstance(s, Text)]
    assert texts == ["rest"]


def test_whitespace_between_condition_and_body_does_not_break_the_association():
    """Regression: `[if x] [load y]` must guard the load, not the space.

    Found by execution. The If body was capturing the whitespace token and
    the load escaped to top level — meaning it would have loaded
    unconditionally, silently ignoring the condition.
    """
    recipe = parse('[if model == "claude"] [load core/tone.claude]')
    assert len(recipe.statements) == 1, "the load must not escape to top level"
    stmt = recipe.statements[0]
    assert isinstance(stmt, If)
    assert isinstance(stmt.body, Load)


def test_a_condition_with_no_body_fails_explicitly():
    with pytest.raises(ParseError) as exc:
        parse("[if model]   ")
    assert "after [if ...]" in str(exc.value)
