# ST-003-03: Expression parser — comparisons, booleans, membership

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Parse the expression half of the grammar by recursive descent, with correct precedence and position-carrying errors.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 51 passed
```

**Files** — Create: `src/promptrecipe/parser/parse.py`, `tests/test_parse_expr.py`

---

### Step 1 — RED: write the failing test (3 min)

Precedence, lowest binding first: `or` → `and` → comparison (`==`, `!=`, `in`) → primary.

```bash
cat > tests/test_parse_expr.py <<'PY'
import pytest

from promptrecipe.errors import ParseError
from promptrecipe.parser.nodes import And, Equals, If, In, Or
from promptrecipe.parser.parse import parse


def condition(src: str):
    recipe = parse(f"[if {src}] [load core/x]")
    stmt = recipe.statements[0]
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
PY

pytest tests/test_parse_expr.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.parser.parse'`

### Step 2 — GREEN: write the parser (6 min)

```bash
cat > src/promptrecipe/parser/parse.py <<'PY'
"""Recursive-descent parser.

Hand-written: for a grammar this small it gives better error positions than a
generator, and adds no dependency (E7).
"""

from __future__ import annotations

from promptrecipe.errors import ParseError, Position
from promptrecipe.parser.lexer import Kind, Token, tokenize
from promptrecipe.parser.nodes import (
    And,
    Equals,
    Expect,
    Expr,
    If,
    In,
    Literal,
    Load,
    Not,
    NotEquals,
    Or,
    Order,
    PathExpr,
    PathLiteral,
    PathVar,
    Recipe,
    Stmt,
    Text,
    Var,
)

_DIRECTIVES = ("load", "if", "order", "expect")
_NOWHERE = Position(line=0, column=0)


class _Parser:
    def __init__(self, source: str) -> None:
        self._tokens = tokenize(source)
        self._i = 0

    # --- helpers ------------------------------------------------------------

    def _peek(self) -> Token | None:
        return self._tokens[self._i] if self._i < len(self._tokens) else None

    def _position(self) -> Position:
        tok = self._peek()
        return tok.position if tok else _NOWHERE

    def _next(self) -> Token | None:
        tok = self._peek()
        if tok is not None:
            self._i += 1
        return tok

    def _expect(self, kind: Kind, what: str) -> Token:
        tok = self._peek()
        if tok is None:
            raise ParseError(position=self._position(), expected=what, found="end of input")
        if tok.kind is not kind:
            raise ParseError(position=tok.position, expected=what, found=tok.value)
        self._i += 1
        return tok

    def _eat_keyword(self, word: str) -> bool:
        tok = self._peek()
        if tok is not None and tok.kind is Kind.IDENT and tok.value == word:
            self._i += 1
            return True
        return False

    # --- expressions --------------------------------------------------------

    def expression(self) -> Expr:
        return self._or()

    def _or(self) -> Expr:
        left = self._and()
        while self._eat_keyword("or"):
            left = Or(left, self._and())
        return left

    def _and(self) -> Expr:
        left = self._comparison()
        while self._eat_keyword("and"):
            left = And(left, self._comparison())
        return left

    def _comparison(self) -> Expr:
        left = self._primary()
        tok = self._peek()
        if tok is None:
            return left
        if tok.kind is Kind.EQ:
            self._i += 1
            return Equals(left, self._primary())
        if tok.kind is Kind.NEQ:
            self._i += 1
            return NotEquals(left, self._primary())
        if tok.kind is Kind.IDENT and tok.value == "in":
            self._i += 1
            self._expect(Kind.LBRACKET, "'[' to start a membership list")
            items: list[Expr] = []
            while True:
                nxt = self._peek()
                if nxt is None:
                    raise ParseError(
                        position=self._position(),
                        expected="']' to close the membership list",
                        found="end of input",
                    )
                if nxt.kind is Kind.RBRACKET:
                    self._i += 1
                    break
                if nxt.kind is Kind.COMMA:
                    self._i += 1
                    continue
                items.append(self._primary())
            return In(left, items)
        return left

    def _primary(self) -> Expr:
        tok = self._next()
        if tok is None:
            raise ParseError(
                position=self._position(),
                expected="a value, variable, or '('",
                found="end of input",
            )
        if tok.kind is Kind.STRING:
            return Literal(tok.value)
        if tok.kind is Kind.NUMBER:
            return Literal(int(tok.value))
        if tok.kind is Kind.LPAREN:
            inner = self.expression()
            self._expect(Kind.RPAREN, "')' to close the group")
            return inner
        if tok.kind is Kind.IDENT:
            if tok.value == "true":
                return Literal(True)
            if tok.value == "false":
                return Literal(False)
            if tok.value == "not":
                return Not(self._primary())
            return Var(tok.value, tok.position)
        raise ParseError(
            position=tok.position, expected="a value, variable, or '('", found=tok.value
        )

    # --- statements ---------------------------------------------------------

    def recipe(self) -> Recipe:
        statements: list[Stmt] = []
        while self._peek() is not None:
            statements.append(self.statement())
        return Recipe(statements)

    def statement(self) -> Stmt:
        tok = self._peek()
        if tok is None:
            raise ParseError(
                position=self._position(), expected="a statement", found="end of input"
            )
        if tok.kind is Kind.TEXT:
            self._i += 1
            return Text(tok.value)
        if tok.kind is Kind.LBRACKET:
            self._i += 1
            return self._directive(tok.position)
        raise ParseError(
            position=tok.position, expected="prose or a '[' directive", found=tok.value
        )

    def _directive(self, position: Position) -> Stmt:
        keyword = self._next()
        if keyword is None or keyword.kind is not Kind.IDENT:
            found = keyword.value if keyword else "end of input"
            raise ParseError(
                position=position, expected=f"one of: {', '.join(_DIRECTIVES)}", found=found
            )

        if keyword.value == "load":
            return Load(self._path(position), position)
        if keyword.value == "expect":
            condition = self.expression()
            self._expect(Kind.RBRACKET, "']' to close [expect ...]")
            return Expect(condition, position)
        if keyword.value == "if":
            condition = self.expression()
            self._expect(Kind.RBRACKET, "']' to close [if ...]")
            return If(condition, self.statement(), position)
        if keyword.value == "order":
            return Order(self._order_names(position), position)

        raise ParseError(
            position=position,
            expected=f"one of: {', '.join(_DIRECTIVES)}",
            found=keyword.value,
        )

    def _path(self, position: Position) -> PathExpr:
        tok = self._next()
        if tok is None:
            raise ParseError(
                position=position,
                expected="a fragment path or an address variable",
                found="end of input",
            )
        if tok.kind is Kind.STRING:
            path: PathExpr = PathLiteral(tok.value)
        elif tok.kind is Kind.IDENT:
            # A bare identifier with no separator is an ADDRESS VARIABLE;
            # anything containing '/' or '.' is a literal path (amendment 9).
            path = (
                PathLiteral(tok.value)
                if ("/" in tok.value or "." in tok.value)
                else PathVar(tok.value, tok.position)
            )
        else:
            raise ParseError(
                position=position,
                expected="a fragment path or an address variable",
                found=tok.value,
            )
        self._expect(Kind.RBRACKET, "']' to close [load ...]")
        return path

    def _order_names(self, position: Position) -> list[str]:
        names: list[str] = []
        while True:
            tok = self._next()
            if tok is None:
                raise ParseError(
                    position=position, expected="']' to close [order ...]", found="end of input"
                )
            if tok.kind is Kind.RBRACKET:
                if names or self._peek() is None:
                    return names
                continue
            if tok.kind in (Kind.IDENT, Kind.STRING):
                names.append(tok.value)
                continue
            if tok.kind in (Kind.COMMA, Kind.COLON, Kind.LBRACKET):
                continue
            raise ParseError(
                position=position, expected="a fragment name, ',' or ']'", found=tok.value
            )


def parse(source: str) -> Recipe:
    """Parse recipe source into a Recipe."""
    return _Parser(source).recipe()
PY

pytest tests/test_parse_expr.py
```
Expected: `5 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(parser): recursive-descent expression parser

Precedence or < and < comparison < primary. Hand-written rather than
generated: better error positions for a grammar this small, and no
dependency (E7). A bare identifier in [load] is an address variable;
anything with a separator is a literal path (amendment 9)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/parser/parse.py tests/test_parse_expr.py
```
