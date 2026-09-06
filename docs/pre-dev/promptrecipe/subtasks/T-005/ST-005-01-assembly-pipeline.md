# ST-005-01: Assembly pipeline — evaluate, load, order, concatenate

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Turn a parsed recipe plus parameters into assembled text, as a **pure function** over what custody returned. Purity is what makes determinism structural rather than a discipline (ADR-001).

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 78 passed
```

**Files** — Create: `src/promptrecipe/assemble.py`, `tests/test_assemble.py`

---

### Step 1 — RED: write the failing test (4 min)

```bash
cat > tests/test_assemble.py <<'PY'
import pytest
from conftest import MemoryCustody

from promptrecipe.assemble import Params, assemble
from promptrecipe.errors import ExpectationFailed
from promptrecipe.parser.parse import parse
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/role": "You are an assistant.",
    "core/tone.claude": "Be concise.",
    "core/tone.gpt": "Be thorough.",
}


def resolver() -> Resolver:
    return Resolver().register("core", "mem", MemoryCustody(LIBRARY))


def run(src: str, params: Params | None = None):
    return assemble(parse(src), params or Params(), resolver())


def test_loads_and_concatenates_in_declaration_order():
    out = run("[load core/role] [load core/tone.claude]")
    assert "You are an assistant." in out.text
    assert "Be concise." in out.text
    assert len(out.fragments) == 2


def test_a_false_condition_excludes_its_fragment():
    out = run("[load core/role][if use_tone] [load core/tone.claude]",
              Params(controls={"use_tone": False}))
    assert "Be concise." not in out.text
    assert len(out.fragments) == 1


def test_condition_outcomes_are_recorded_so_a_branch_can_be_replayed():
    """SD6: without the outcomes, the fragment list says WHAT loaded but not WHY."""
    out = run("[if use_tone] [load core/tone.claude]", Params(controls={"use_tone": True}))
    assert len(out.condition_outcomes) == 1
    assert out.condition_outcomes[0][1] is True


def test_a_violated_expectation_emits_no_partial_output():
    with pytest.raises(ExpectationFailed):
        run('[expect language in ["pt", "en"]] Some prose [load core/role]',
            Params(controls={"language": "fr"}))


def test_an_address_variable_selects_which_fragment_loads():
    out = run("[load tone]", Params(addresses={"tone": "core/tone.gpt"}))
    assert "Be thorough." in out.text


def test_string_equality_drives_model_selection():
    out = run('[if model == "claude"] [load core/tone.claude]',
              Params(controls={"model": "claude"}))
    assert "Be concise." in out.text
PY

pytest tests/test_assemble.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.assemble'`

### Step 2 — GREEN: write the pipeline (6 min)

```bash
cat > src/promptrecipe/assemble.py <<'PY'
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
    PathLiteral,
    PathVar,
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


def _path_for(path: PathLiteral | PathVar, params: Params) -> FragmentPath:
    if isinstance(path, PathLiteral):
        return FragmentPath.parse(path.value)
    if path.name not in params.addresses:
        raise UndefinedVariable(name=path.name, bound=list(params.addresses))
    return FragmentPath.parse(params.addresses[path.name])


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
            return
        if isinstance(stmt, Load):
            path = _path_for(stmt.path, params)
            fragment_id, _trace = resolver.resolve(path)
            parts.append(resolver.read(path).text)
            fragments.append((str(path), fragment_id))
            return
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
    # Added in ST-005-02.
    text = "".join(parts)

    return Assembled(text=text, fragments=fragments, condition_outcomes=condition_outcomes)


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
PY

pytest tests/test_assemble.py
```
Expected: `6 passed`

### Step 3 — Verify no ambient state reached the assembly path (2 min)

```bash
grep -nE "datetime|time\.|os\.environ|getenv|random|\.lower\(\)|\.upper\(\)|set\(" src/promptrecipe/assemble.py
```
Expected: **no output.** Any hit is a TRD §4 determinism hazard — clock, environment, randomness, locale-sensitive casing, or set iteration.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(assemble): pure deterministic assembly pipeline

Expectations run before any content exists, so a violation emits
nothing (TRD §7). Condition outcomes are recorded because the fragment
list says WHAT loaded but not WHY, and a branch cannot be replayed
without them (SD6)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/assemble.py tests/test_assemble.py
```
