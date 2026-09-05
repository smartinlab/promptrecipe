"""Recursive-descent parser.

Hand-written: for a grammar this small it gives better error positions than a
generator, and adds no dependency (E7).
"""

from __future__ import annotations

from promptrecipe.errors import DepthLimitExceeded, ParseError, Position
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

_DIRECTIVES = "load, if, order, expect"
_NOWHERE = Position(line=0, column=0)

MAX_EXPRESSION_DEPTH = 64
"""Ceiling on nested expression depth.

Recursive descent uses one Python frame per nesting level, so without a
ceiling roughly 200 nested parentheses exhaust the interpreter stack and
raise a bare RecursionError — not a PromptRecipeError, so a caller following
the documented `except PromptRecipeError` cannot catch it. 64 is far beyond
any legible condition and far below the stack limit.
"""


class _Parser:
    def __init__(self, source: str) -> None:
        self._tokens = tokenize(source)
        self._i = 0
        self._depth = 0

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
        self._depth += 1
        if self._depth > MAX_EXPRESSION_DEPTH:
            raise DepthLimitExceeded(limit=MAX_EXPRESSION_DEPTH, path="condition expression")
        try:
            return self._or()
        finally:
            self._depth -= 1

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
            return In(left, self._membership_list())
        return left

    def _membership_list(self) -> list[Expr]:
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
                return items
            if nxt.kind is Kind.COMMA:
                self._i += 1
                continue
            items.append(self._primary())

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
                self._depth += 1
                if self._depth > MAX_EXPRESSION_DEPTH:
                    raise DepthLimitExceeded(
                        limit=MAX_EXPRESSION_DEPTH, path="condition expression"
                    )
                try:
                    return Not(self._primary())
                finally:
                    self._depth -= 1
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
            raise ParseError(position=position, expected=f"one of: {_DIRECTIVES}", found=found)

        if keyword.value == "load":
            return Load(self._path(position), position)
        if keyword.value == "expect":
            condition = self.expression()
            self._expect(Kind.RBRACKET, "']' to close [expect ...]")
            return Expect(condition, position)
        if keyword.value == "if":
            condition = self.expression()
            self._expect(Kind.RBRACKET, "']' to close [if ...]")
            return If(condition, self._conditional_body(position), position)
        if keyword.value == "order":
            return Order(self._order_names(position), position)

        raise ParseError(position=position, expected=f"one of: {_DIRECTIVES}", found=keyword.value)

    def _conditional_body(self, position: Position) -> Stmt:
        """The statement an `[if ...]` guards.

        Whitespace between the condition and its body is formatting, not
        content: `[if x] [load y]` and `[if x][load y]` mean the same thing.
        Skipping it is what makes the documented style work — without this,
        the body would be the space and the load would escape the condition
        entirely, loading unconditionally.

        The skipped whitespace is not emitted, so a false condition suppresses
        the body and its leading gap together.
        """
        while True:
            tok = self._peek()
            if tok is None:
                raise ParseError(
                    position=position,
                    expected="a statement after [if ...]",
                    found="end of input",
                )
            if tok.kind is Kind.TEXT and not tok.value.strip():
                self._i += 1
                continue
            return self.statement()

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
        depth = 0
        while True:
            tok = self._next()
            if tok is None:
                raise ParseError(
                    position=position, expected="']' to close [order ...]", found="end of input"
                )
            if tok.kind is Kind.LBRACKET:
                depth += 1
                continue
            if tok.kind is Kind.RBRACKET:
                if depth:
                    depth -= 1
                    continue
                return names
            if tok.kind in (Kind.IDENT, Kind.STRING):
                names.append(tok.value)
                continue
            if tok.kind in (Kind.COMMA, Kind.COLON):
                continue
            raise ParseError(
                position=position, expected="a fragment name, ',' or ']'", found=tok.value
            )


def parse(source: str) -> Recipe:
    """Parse recipe source into a Recipe."""
    return _Parser(source).recipe()
