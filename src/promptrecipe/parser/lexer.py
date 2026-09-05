"""Tokenizer. Every token carries the position where it started."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from promptrecipe.errors import ParseError, Position


class Kind(Enum):
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    COLON = auto()
    EQ = auto()
    NEQ = auto()
    IDENT = auto()
    STRING = auto()
    NUMBER = auto()
    TEXT = auto()


@dataclass(frozen=True, slots=True)
class Token:
    kind: Kind
    value: str
    position: Position


_IDENT_EXTRA = "_/.-"
_PUNCT = {
    "(": Kind.LPAREN,
    ")": Kind.RPAREN,
    "[": Kind.LBRACKET,
    ",": Kind.COMMA,
    ":": Kind.COLON,
}


def tokenize(source: str) -> list[Token]:
    """Tokenize a recipe.

    Anything outside a `[ ... ]` directive is literal prose and becomes a
    single TEXT token. Prose is never interpreted — it is inert content.
    """
    tokens: list[Token] = []
    i = 0
    line = 1
    column = 1
    n = len(source)

    def here() -> Position:
        return Position(line=line, column=column)

    def advance() -> None:
        nonlocal i, line, column
        if source[i] == "\n":
            line += 1
            column = 1
        else:
            column += 1
        i += 1

    while i < n:
        if source[i] != "[":
            start = here()
            begin = i
            while i < n and source[i] != "[":
                advance()
            tokens.append(Token(Kind.TEXT, source[begin:i], start))
            continue

        tokens.append(Token(Kind.LBRACKET, "[", here()))
        advance()

        # Bracket depth INSIDE the directive. A membership list is written
        # `in ["pt", "en"]`, so a directive can legitimately contain nested
        # brackets — the directive closes only when depth returns to zero.
        depth = 0
        closed = False
        while i < n:
            while i < n and source[i] in " \t\r\n":
                advance()
            if i >= n:
                break

            start = here()
            ch = source[i]

            if ch == "]":
                tokens.append(Token(Kind.RBRACKET, "]", start))
                advance()
                if depth == 0:
                    closed = True
                    break
                depth -= 1
                continue
            if ch in _PUNCT:
                if ch == "[":
                    depth += 1
                tokens.append(Token(_PUNCT[ch], ch, start))
                advance()
                continue
            if ch == "=":
                advance()
                if i < n and source[i] == "=":
                    advance()
                    tokens.append(Token(Kind.EQ, "==", start))
                    continue
                raise ParseError(position=start, expected="'=='", found="=")
            if ch == "!":
                advance()
                if i < n and source[i] == "=":
                    advance()
                    tokens.append(Token(Kind.NEQ, "!=", start))
                    continue
                raise ParseError(position=start, expected="'!='", found="!")
            if ch == '"':
                advance()
                begin = i
                while i < n and source[i] != '"':
                    advance()
                if i >= n:
                    raise ParseError(
                        position=start, expected="closing double quote", found="end of input"
                    )
                text = source[begin:i]
                advance()
                tokens.append(Token(Kind.STRING, text, start))
                continue
            if ch.isdigit():
                begin = i
                while i < n and source[i].isdigit():
                    advance()
                tokens.append(Token(Kind.NUMBER, source[begin:i], start))
                continue
            if ch.isalpha() or ch == "_":
                begin = i
                while i < n and (source[i].isalnum() or source[i] in _IDENT_EXTRA):
                    advance()
                tokens.append(Token(Kind.IDENT, source[begin:i], start))
                continue

            raise ParseError(
                position=start,
                expected="a directive keyword, operator, or value",
                found=ch,
            )

        if not closed:
            raise ParseError(
                position=here(),
                expected="']' to close the directive",
                found="end of input",
            )

    return tokens
