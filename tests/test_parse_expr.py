import pytest

from promptrecipe.errors import ParseError
from promptrecipe.parser.nodes import And, Equals, If, In, Or
from promptrecipe.parser.parse import parse


def condition(src: str):
    stmt = parse(f"[if {src}] [load core/x]").statements[0]
    assert isinstance(stmt, If)
    return stmt.condition


def test_parses_string_equality():
    assert isinstance(condition('model == "claude"'), Equals)


def test_and_binds_tighter_than_or():
    """`a or b and c` must parse as `a or (b and c)`."""
    expr = condition("a or b and c")
    assert isinstance(expr, Or)
    assert isinstance(expr.right, And)


def test_parses_membership():
    expr = condition('language in ["pt", "en"]')
    assert isinstance(expr, In)
    assert len(expr.haystack) == 2


def test_parentheses_override_precedence():
    expr = condition("(a or b) and c")
    assert isinstance(expr, And)
    assert isinstance(expr.left, Or)


def test_parse_errors_carry_a_position():
    with pytest.raises(ParseError) as exc:
        parse("[if model ==]")
    assert "line 1" in str(exc.value)
