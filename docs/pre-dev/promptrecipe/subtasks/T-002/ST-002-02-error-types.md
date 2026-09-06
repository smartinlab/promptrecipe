# ST-002-02: Errors that name what failed and what was supplied

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Make TRD §7 enforceable rather than aspirational — every failure names what failed, what was expected, and what was actually supplied.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 10 passed
```

**Files** — Create: `src/promptrecipe/errors.py`, `tests/test_errors.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_errors.py <<'PY'
from promptrecipe.errors import (
    AmbiguousReference,
    CyclicInclusion,
    ExpectationFailed,
    FragmentNotFound,
    IdentityMismatch,
    Position,
    PromptRecipeError,
)


def test_not_found_names_the_path_and_where_it_looked():
    err = FragmentNotFound(path="core/tone", namespaces=["core", "shared"])
    msg = str(err)
    assert "core/tone" in msg
    assert "core" in msg and "shared" in msg


def test_ambiguity_names_every_candidate_and_refuses_to_pick():
    err = AmbiguousReference(path="tone", candidates=["core/tone", "shared/tone"])
    msg = str(err)
    assert "core/tone" in msg
    assert "shared/tone" in msg
    # ADR-004: the message must make clear that nothing was picked.
    assert "never picks silently" in msg


def test_expectation_failure_names_expected_and_actual():
    err = ExpectationFailed(
        position=Position(line=3, column=5),
        expected="language in ['pt', 'en']",
        actual="language was 'fr'",
    )
    msg = str(err)
    assert "line 3, column 5" in msg
    assert "language in ['pt', 'en']" in msg
    assert "'fr'" in msg


def test_cycle_reports_the_whole_path_not_just_its_existence():
    err = CyclicInclusion(cycle=["a", "b", "c", "a"])
    assert "a -> b -> c -> a" in str(err)


def test_identity_mismatch_refuses_substitution():
    err = IdentityMismatch(path="core/tone", expected="abc123", found="def456")
    assert "refusing to substitute" in str(err)


def test_every_error_is_catchable_as_one_base_type():
    """Callers must be able to catch the library's failures without
    enumerating every variant."""
    for err in [
        FragmentNotFound(path="p", namespaces=[]),
        AmbiguousReference(path="p", candidates=[]),
        CyclicInclusion(cycle=["a", "a"]),
    ]:
        assert isinstance(err, PromptRecipeError)
PY

pytest tests/test_errors.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.errors'`

### Step 2 — GREEN: write the implementation (4 min)

```bash
cat > src/promptrecipe/errors.py <<'PY'
"""Every failure path in the library (TRD §7).

Two rules hold everywhere:
1. A message names what failed, what was expected, and what was supplied.
2. No failure path emits partial output. There is no "warn and continue".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Position:
    """A position in recipe source text."""

    line: int
    column: int

    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"


class PromptRecipeError(Exception):
    """Base for every failure this library raises.

    Callers catch this one type rather than enumerating variants.
    """


@dataclass(slots=True)
class FragmentNotFound(PromptRecipeError):
    path: str
    namespaces: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        where = ", ".join(self.namespaces) or "<none registered>"
        return f"fragment not found at path '{self.path}' (searched namespaces: {where})"


@dataclass(slots=True)
class AmbiguousReference(PromptRecipeError):
    path: str
    candidates: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.candidates) or "<none>"
        return (
            f"reference '{self.path}' is ambiguous — {len(self.candidates)} candidates "
            f"matched: {listed}. Resolution never picks silently; disambiguate the reference."
        )


@dataclass(slots=True)
class PathEscapesNamespace(PromptRecipeError):
    path: str
    root: str

    def __str__(self) -> str:
        return f"path '{self.path}' escapes its namespace root '{self.root}'"


@dataclass(slots=True)
class UnknownNamespace(PromptRecipeError):
    namespace: str
    path: str
    known: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.known) or "<none registered>"
        return f"unknown namespace '{self.namespace}' in path '{self.path}' (known: {listed})"


@dataclass(slots=True)
class ExpectationFailed(PromptRecipeError):
    position: Position
    expected: str
    actual: str

    def __str__(self) -> str:
        return f"expectation failed at {self.position}: expected {self.expected}, but {self.actual}"


@dataclass(slots=True)
class CyclicInclusion(PromptRecipeError):
    cycle: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"cyclic fragment inclusion: {' -> '.join(self.cycle)}"


@dataclass(slots=True)
class DepthLimitExceeded(PromptRecipeError):
    limit: int
    path: str

    def __str__(self) -> str:
        return f"inclusion depth limit of {self.limit} exceeded at path '{self.path}'"


@dataclass(slots=True)
class ParseError(PromptRecipeError):
    position: Position
    expected: str
    found: str

    def __str__(self) -> str:
        return f"parse error at {self.position}: expected {self.expected}, found '{self.found}'"


@dataclass(slots=True)
class IdentityMismatch(PromptRecipeError):
    path: str
    expected: str
    found: str

    def __str__(self) -> str:
        return (
            f"content at '{self.path}' does not match its pinned identity "
            f"(expected {self.expected}, found {self.found}) — refusing to substitute"
        )


@dataclass(slots=True)
class UndefinedVariable(PromptRecipeError):
    name: str
    bound: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(sorted(self.bound)) or "<none>"
        return f"undefined variable '{self.name}' (bound variables: {listed})"
PY

pytest tests/test_errors.py
```
Expected: `6 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(errors): failure types that name expected and actual

TRD §7. Ambiguity carries every candidate and states that resolution
never picks silently (ADR-004); cycles carry the whole path. One base
type so callers catch failures without enumerating variants."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/errors.py tests/test_errors.py
```
