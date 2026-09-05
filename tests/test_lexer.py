import pytest

from promptrecipe.errors import ParseError
from promptrecipe.parser.lexer import Kind, tokenize


def kinds(src: str) -> list[Kind]:
    return [t.kind for t in tokenize(src)]


def test_prose_outside_brackets_is_one_inert_text_token():
    toks = tokenize("You are helpful.")
    assert [t.kind for t in toks] == [Kind.TEXT]
    assert toks[0].value == "You are helpful."


def test_tokenizes_a_load_directive():
    assert kinds("[load core/tone]") == [Kind.LBRACKET, Kind.IDENT, Kind.IDENT, Kind.RBRACKET]


def test_tokenizes_a_condition_with_a_string_comparison():
    assert kinds('[if model == "claude"]') == [
        Kind.LBRACKET,
        Kind.IDENT,
        Kind.IDENT,
        Kind.EQ,
        Kind.STRING,
        Kind.RBRACKET,
    ]


def test_interleaves_prose_and_directives():
    toks = tokenize("Intro [load core/tone] outro")
    assert toks[0].kind is Kind.TEXT and toks[0].value == "Intro "
    assert toks[-1].kind is Kind.TEXT and toks[-1].value == " outro"


def test_unterminated_directive_reports_a_position():
    with pytest.raises(ParseError) as exc:
        tokenize("[load core/tone")
    assert "line 1" in str(exc.value)
    assert "end of input" in str(exc.value)


def test_position_tracks_across_newlines():
    toks = tokenize("first line\n[load core/tone]")
    bracket = next(t for t in toks if t.kind is Kind.LBRACKET)
    assert bracket.position.line == 2
    assert bracket.position.column == 1


def test_text_that_looks_like_a_placeholder_is_still_text():
    """Value placeholders are substituted much later (ADR-006), not lexed."""
    toks = tokenize("Hello {{name}}")
    assert [t.kind for t in toks] == [Kind.TEXT]
    assert toks[0].value == "Hello {{name}}"
