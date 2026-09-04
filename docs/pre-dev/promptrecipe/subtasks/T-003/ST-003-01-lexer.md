# ST-003-01: Lexer with line/column positions

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Turn recipe text into tokens that each carry a position, so every parse error can name exactly where it happened (TRD §7, E7).

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 37 passed
```

**Files** — Create: `src/promptrecipe/parser/__init__.py`, `src/promptrecipe/parser/lexer.py`, `tests/test_lexer.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_lexer.py <<'PY'
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
PY

pytest tests/test_lexer.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.parser'`

### Step 2 — GREEN: write the lexer (5 min)

```bash
mkdir -p src/promptrecipe/parser
cat > src/promptrecipe/parser/__init__.py <<'PY'
"""Recipe parsing.

The grammar is a CLOSED LIST and is the package's security boundary
(ADR-003). It contains no function call, no loop, and no I/O production, so
evaluation is total by construction. Adding a production here is a security
decision, not a convenience — it must be justified against E1-E7.
"""
PY

cat > src/promptrecipe/parser/lexer.py <<'PY'
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

    def advance(count: int = 1) -> None:
        nonlocal i, line, column
        for _ in range(count):
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
                closed = True
                break
            if ch in "()[,:":
                mapping = {
                    "(": Kind.LPAREN,
                    ")": Kind.RPAREN,
                    "[": Kind.LBRACKET,
                    ",": Kind.COMMA,
                    ":": Kind.COLON,
                }
                tokens.append(Token(mapping[ch], ch, start))
                advance()
                continue
            if ch == "=":
                advance()
                if i < n and source[i] == "=":
                    advance()
                    tokens.append(Token(Kind.EQ, "==", start))
                    continue
                raise ParseError(position=start, expected="'=='", found="'='")
            if ch == "!":
                advance()
                if i < n and source[i] == "=":
                    advance()
                    tokens.append(Token(Kind.NEQ, "!=", start))
                    continue
                raise ParseError(position=start, expected="'!='", found="'!'")
            if ch == '"':
                advance()
                begin = i
                while i < n and source[i] != '"':
                    advance()
                if i >= n:
                    raise ParseError(position=start, expected="closing '\"'", found="end of input")
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
PY

pytest tests/test_lexer.py
```
Expected: `7 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(parser): lexer with line/column positions

Prose outside brackets becomes a single inert TEXT token; it is never
interpreted (ADR-003). Value placeholders are not lexed either — they
are substituted much later (ADR-006)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf src/promptrecipe/parser tests/test_lexer.py
```
