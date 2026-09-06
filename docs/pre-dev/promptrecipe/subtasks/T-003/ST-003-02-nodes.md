# ST-003-02: Grammar nodes — the closed grammar, and the security boundary

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Define the complete grammar as types. **This file *is* the security boundary** (ADR-003): if the grammar cannot express a call, a loop, or I/O, then no recipe can contain one, and evaluation is total by construction.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 44 passed
```

**Files** — Create: `src/promptrecipe/parser/nodes.py`, `tests/test_nodes.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_nodes.py <<'PY'
import inspect

from promptrecipe.errors import Position
from promptrecipe.parser import nodes
from promptrecipe.parser.nodes import (
    And,
    Equals,
    Expect,
    In,
    Literal,
    Load,
    Order,
    PathLiteral,
    PathVar,
    Recipe,
    Text,
    Var,
)

POS = Position(line=1, column=1)


def test_a_recipe_holds_prose_and_directives():
    r = Recipe([Text("You are helpful.\n"), Load(PathLiteral("core/tone"), POS)])
    assert len(r.statements) == 2


def test_expectations_are_reachable_before_assembly():
    r = Recipe([Expect(Var("language", POS), POS), Text("prose")])
    assert len(r.expectations) == 1


def test_declared_order_is_readable():
    r = Recipe([Order(["role", "tone", "rules"], POS)])
    assert r.declared_order == ["role", "tone", "rules"]


def test_an_address_variable_names_a_path_not_text():
    """Amendment 9: an address variable resolves to a fragment path.
    Substituting it IS path resolution."""
    load = Load(PathVar("tone_fragment", POS), POS)
    assert isinstance(load.path, PathVar)


def test_membership_and_boolean_expressions_compose():
    expr = And(
        In(Var("language", POS), [Literal("pt"), Literal("en")]),
        Equals(Var("model", POS), Literal("claude")),
    )
    assert isinstance(expr, And)


def test_the_grammar_contains_no_dangerous_production():
    """THE structural guard on ADR-003.

    If no node type can express a call, loop, or I/O, no recipe can contain
    one — and evaluation is total by construction rather than by sandbox.
    """
    forbidden = {"Call", "Invoke", "Apply", "Loop", "While", "For", "Exec", "Eval", "Import"}
    defined = {
        name
        for name, obj in inspect.getmembers(nodes, inspect.isclass)
        if obj.__module__ == nodes.__name__
    }
    assert not (defined & forbidden), f"dangerous grammar production added: {defined & forbidden}"


def test_the_grammar_module_uses_no_dynamic_execution():
    """PROJECT_RULES: eval/exec/compile/__import__ never appear in the library."""
    source = inspect.getsource(nodes)
    for banned in ("eval(", "exec(", "compile(", "__import__"):
        assert banned not in source, f"'{banned}' must never appear in the library"
PY

pytest tests/test_nodes.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.parser.nodes'`

### Step 2 — GREEN: write the grammar (4 min)

```bash
cat > src/promptrecipe/parser/nodes.py <<'PY'
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

    Its value is a fragment PATH, not text. This is why variable substitution
    for an address variable IS path resolution.
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
PY

pytest tests/test_nodes.py
```
Expected: `7 passed`

### Step 3 — Verify the grammar is closed, from the shell too (1 min)

```bash
grep -rnE "\beval\(|\bexec\(|\bcompile\(|__import__" src/promptrecipe/
```
Expected: **no output.** This must hold for the whole package, forever.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(parser): closed grammar — the security boundary

ADR-003. No call, loop, or I/O node exists, so evaluation is total by
construction (E3). Two tests enforce it structurally: one asserts no
dangerous node type was added, one asserts no dynamic execution."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/parser/nodes.py tests/test_nodes.py
```
