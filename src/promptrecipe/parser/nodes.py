"""The recipe grammar — a CLOSED list (ADR-003).

## Why this file is the security boundary

Fragments may be written by an optimizer or fetched from remote custody,
which makes them untrusted input. The guarantee that keeps that safe is that
fragment content is never evaluated — and the guarantee that keeps
*conditions* safe is that this grammar cannot express anything dangerous.

There is deliberately NO node for:
  - a function or method call
  - a loop or unbounded recursion
  - file, network, clock, or environment access

Evaluation is therefore TOTAL: it terminates on every input (E3).
Adding a node here is a security decision, not a convenience.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from promptrecipe.errors import Position

# --- expressions ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Literal:
    value: str | int | bool


@dataclass(frozen=True, slots=True)
class Var:
    """A CONTROL variable reference — feeds conditions (amendment 9)."""

    name: str
    position: Position


@dataclass(frozen=True, slots=True)
class Equals:
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class NotEquals:
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class And:
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class Or:
    left: Expr
    right: Expr


@dataclass(frozen=True, slots=True)
class Not:
    operand: Expr


@dataclass(frozen=True, slots=True)
class In:
    needle: Expr
    haystack: list[Expr]


Expr = Literal | Var | Equals | NotEquals | And | Or | Not | In

# --- path expressions -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PathLiteral:
    """A literal fragment path, e.g. `core/tone`."""

    value: str


@dataclass(frozen=True, slots=True)
class PathVar:
    """An ADDRESS variable (amendment 9).

    Its value is a fragment PATH, not text. This is why substituting an
    address variable IS path resolution.
    """

    name: str
    position: Position


PathExpr = PathLiteral | PathVar

# --- statements -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Text:
    """Inert prose. Never interpreted."""

    value: str


@dataclass(frozen=True, slots=True)
class Load:
    path: PathExpr
    position: Position


@dataclass(frozen=True, slots=True)
class If:
    condition: Expr
    body: Stmt
    position: Position


@dataclass(frozen=True, slots=True)
class Order:
    names: list[str]
    position: Position


@dataclass(frozen=True, slots=True)
class Expect:
    """Evaluated before any content is produced (TRD §7)."""

    condition: Expr
    position: Position


Stmt = Text | Load | If | Order | Expect


@dataclass(frozen=True, slots=True)
class Recipe:
    statements: list[Stmt] = field(default_factory=list)

    @property
    def expectations(self) -> list[Expect]:
        """Every expectation. Evaluated first, before any content exists, so a
        violation emits no partial output (TRD §7)."""
        return [s for s in self.statements if isinstance(s, Expect)]

    @property
    def declared_order(self) -> list[str] | None:
        for s in self.statements:
            if isinstance(s, Order):
                return s.names
        return None
