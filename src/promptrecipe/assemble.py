"""Assembly — pure, deterministic, ordered (TRD §3, §4).

Pipeline order is fixed, and is itself a security property:
  1. evaluate expectations   (fail before any content exists)
  2. evaluate conditions     (decide what loads, in what order)
  3. resolve paths           (reference -> exactly one identity)
  4. fetch fragments         (the only I/O, delegated to custody)
  5. concatenate in declared order
  6. substitute value variables  <- LAST, never re-parsed (ADR-006)

Step 6 runs last so a caller-supplied value can never influence which
fragments load, their order, or their version.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from promptrecipe.errors import ExpectationFailed, UndefinedVariable
from promptrecipe.identity import FragmentId
from promptrecipe.parser.nodes import (
    And,
    Equals,
    Expr,
    If,
    In,
    Literal,
    Load,
    Not,
    NotEquals,
    Or,
    PathExpr,
    PathLiteral,
    Recipe,
    Stmt,
    Text,
    Var,
)
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

Value = str | int | bool


@dataclass(slots=True)
class Params:
    """The inputs to one assembly (amendment 9 — three distinct roles).

    Dicts are iterated in SORTED order wherever their order can reach output
    or a digest; insertion order must never leak (TRD §4).
    """

    controls: dict[str, Value] = field(default_factory=dict)
    """Feed conditions. Affect STRUCTURE."""
    addresses: dict[str, str] = field(default_factory=dict)
    """Resolve to fragment paths. Affect STRUCTURE."""
    values: dict[str, str] = field(default_factory=dict)
    """Substituted as literal text. Affect CONTENT only."""


@dataclass(slots=True)
class Assembled:
    text: str
    fragments: list[tuple[str, FragmentId]] = field(default_factory=list)
    """Fragments in assembly ORDER. A list, never a set — order is identity (SD13)."""
    condition_outcomes: list[tuple[str, bool]] = field(default_factory=list)
    """Every condition and its outcome, so a branch can be replayed (SD6)."""


def _value_of(expr: Expr, params: Params) -> Value:
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Var):
        if expr.name not in params.controls:
            raise UndefinedVariable(name=expr.name, bound=list(params.controls))
        return params.controls[expr.name]
    return _truth(expr, params)


def _truth(expr: Expr, params: Params) -> bool:
    """Evaluate an expression to a boolean.

    Total by construction: the grammar has no call, loop, or I/O node, so
    every recursion is structural and terminates (E3, ADR-003).
    """
    if isinstance(expr, Literal):
        return bool(expr.value)
    if isinstance(expr, Var):
        if expr.name not in params.controls:
            raise UndefinedVariable(name=expr.name, bound=list(params.controls))
        return bool(params.controls[expr.name])
    if isinstance(expr, Not):
        return not _truth(expr.operand, params)
    if isinstance(expr, And):
        return _truth(expr.left, params) and _truth(expr.right, params)
    if isinstance(expr, Or):
        return _truth(expr.left, params) or _truth(expr.right, params)
    if isinstance(expr, Equals):
        return _value_of(expr.left, params) == _value_of(expr.right, params)
    if isinstance(expr, NotEquals):
        return _value_of(expr.left, params) != _value_of(expr.right, params)
    if isinstance(expr, In):
        needle = _value_of(expr.needle, params)
        return any(_value_of(item, params) == needle for item in expr.haystack)
    raise AssertionError(f"unreachable: unknown expression node {type(expr).__name__}")


def _describe(expr: Expr) -> str:
    """A stable textual form of a condition, for provenance and messages.

    Must be deterministic: it reaches the provenance digest (SD6).
    """
    if isinstance(expr, Literal):
        return repr(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Not):
        return f"not {_describe(expr.operand)}"
    if isinstance(expr, And):
        return f"({_describe(expr.left)} and {_describe(expr.right)})"
    if isinstance(expr, Or):
        return f"({_describe(expr.left)} or {_describe(expr.right)})"
    if isinstance(expr, Equals):
        return f"({_describe(expr.left)} == {_describe(expr.right)})"
    if isinstance(expr, NotEquals):
        return f"({_describe(expr.left)} != {_describe(expr.right)})"
    if isinstance(expr, In):
        items = ", ".join(_describe(i) for i in expr.haystack)
        return f"({_describe(expr.needle)} in [{items}])"
    raise AssertionError(f"unreachable: unknown expression node {type(expr).__name__}")


def _path_for(path: PathExpr, params: Params) -> FragmentPath:
    if isinstance(path, PathLiteral):
        return FragmentPath.parse(path.value)
    if path.name not in params.addresses:
        raise UndefinedVariable(name=path.name, bound=list(params.addresses))
    return FragmentPath.parse(params.addresses[path.name])


def _substitute(text: str, values: dict[str, str]) -> str:
    """Replace `{{name}}` with its bound value.

    ONE pass over the input. The output is never re-scanned, so a substituted
    value containing `{{...}}` or `[load ...]` stays literal (ADR-006).
    Unbound placeholders are left untouched: values are content, not
    structure, so an unknown one is not a structural failure.
    """
    out: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        start = text.find("{{", i)
        if start == -1:
            out.append(text[i:])
            break
        end = text.find("}}", start + 2)
        if end == -1:
            out.append(text[i:])
            break

        out.append(text[i:start])
        name = text[start + 2 : end].strip()
        if name in values:
            # Appended directly to the output; `i` jumps past it, so this
            # loop never re-examines the substituted text.
            out.append(values[name])
        else:
            out.append(text[start : end + 2])
        i = end + 2

    return "".join(out)


def assemble(recipe: Recipe, params: Params, resolver: Resolver) -> Assembled:
    """Assemble a recipe. Pure over what the resolver returns."""
    # --- 1. expectations, before any content exists (TRD §7) ---------------
    for expectation in recipe.expectations:
        if not _truth(expectation.condition, params):
            raise ExpectationFailed(
                position=expectation.position,
                expected=_describe(expectation.condition),
                actual=f"controls were {dict(sorted(params.controls.items()))}",
            )

    parts: list[str] = []
    fragments: list[tuple[str, FragmentId]] = []
    condition_outcomes: list[tuple[str, bool]] = []

    def emit(stmt: Stmt) -> None:
        if isinstance(stmt, Text):
            parts.append(stmt.value)
        elif isinstance(stmt, Load):
            path = _path_for(stmt.path, params)
            fragment_id, _trace = resolver.resolve(path)
            parts.append(resolver.read(path).text)
            fragments.append((str(path), fragment_id))
        # Order and Expect produce no content here.

    for stmt in recipe.statements:
        if isinstance(stmt, If):
            outcome = _truth(stmt.condition, params)
            condition_outcomes.append((_describe(stmt.condition), outcome))
            if outcome:
                emit(stmt.body)
        else:
            emit(stmt)

    # --- 6. value substitution — LAST, single pass, never re-parsed --------
    #
    # Running last IS the security property (ADR-006): every structural
    # decision above is already final, so a caller-supplied value cannot
    # influence which fragments loaded, their order, or their version.
    text = _substitute("".join(parts), params.values)

    return Assembled(text=text, fragments=fragments, condition_outcomes=condition_outcomes)
