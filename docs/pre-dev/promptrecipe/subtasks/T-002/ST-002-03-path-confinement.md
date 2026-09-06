# ST-002-03: Path canonicalization with namespace-root confinement

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Make a fragment path a safe canonical address that cannot escape its namespace root (TRD §6.2).

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 16 passed
```

**Files** — Create: `src/promptrecipe/paths.py`, `tests/test_paths.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_paths.py <<'PY'
import pytest

from promptrecipe.errors import PathEscapesNamespace, PromptRecipeError
from promptrecipe.paths import FragmentPath


def test_splits_namespace_from_segments():
    p = FragmentPath.parse("core/tone/formal")
    assert p.namespace == "core"
    assert p.segments == ("tone", "formal")
    assert str(p) == "core/tone/formal"


def test_canonicalization_is_idempotent():
    """Determinism (TRD §4): canonicalizing a canonical form returns itself."""
    once = FragmentPath.parse("core//tone/./formal")
    twice = FragmentPath.parse(str(once))
    assert once == twice
    assert str(once) == "core/tone/formal"


def test_dot_dot_resolves_lexically_within_the_namespace():
    assert str(FragmentPath.parse("core/tone/../safety")) == "core/safety"


def test_escaping_the_namespace_root_is_rejected():
    with pytest.raises(PathEscapesNamespace):
        FragmentPath.parse("core/../../etc/passwd")


def test_leading_slashes_are_stripped_not_treated_as_absolute():
    assert str(FragmentPath.parse("/core/tone")) == "core/tone"


def test_empty_path_is_rejected():
    with pytest.raises(PromptRecipeError):
        FragmentPath.parse("   ")


def test_a_namespace_alone_is_a_valid_path():
    p = FragmentPath.parse("core")
    assert p.namespace == "core"
    assert p.segments == ()


def test_paths_are_hashable_and_sortable():
    """Sortable because listing output must be deterministically ordered."""
    a = FragmentPath.parse("core/a")
    b = FragmentPath.parse("core/b")
    assert sorted([b, a]) == [a, b]
    assert len({a, FragmentPath.parse("core/a")}) == 1


def test_canonicalization_never_touches_the_filesystem(monkeypatch):
    """ADR-001: only the custody layer performs I/O.

    Path parsing is purely lexical, so it must work for paths that do not
    exist and must never call into the filesystem.
    """
    import os

    def explode(*args, **kwargs):
        raise AssertionError("path parsing must not touch the filesystem")

    monkeypatch.setattr(os.path, "realpath", explode)
    monkeypatch.setattr(os.path, "exists", explode)
    assert str(FragmentPath.parse("core/does/not/exist")) == "core/does/not/exist"
PY

pytest tests/test_paths.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.paths'`

### Step 2 — GREEN: write the implementation (3 min)

```bash
cat > src/promptrecipe/paths.py <<'PY'
"""Fragment paths: canonicalization and namespace confinement.

A path is a hierarchical address: `namespace/segment/segment`.
Canonicalization is purely LEXICAL — it never touches the filesystem, which
keeps this module inside the "no I/O outside custody" rule (ADR-001).
"""

from __future__ import annotations

from dataclasses import dataclass

from promptrecipe.errors import PathEscapesNamespace, UnknownNamespace


@dataclass(frozen=True, slots=True, order=True)
class FragmentPath:
    """A canonical fragment path.

    Frozen and ordered: hashable for caches, sortable so any listing that
    reaches output has a deterministic order (TRD §4).
    """

    namespace: str
    segments: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> FragmentPath:
        """Parse and canonicalize a raw path reference.

        Resolves `.` and `..` lexically and rejects any path whose `..`
        segments would climb above the namespace root.
        """
        parts = [p for p in raw.strip().lstrip("/").split("/") if p]
        if not parts:
            raise UnknownNamespace(namespace="", path=raw, known=[])

        namespace, *rest = parts
        segments: list[str] = []
        for part in rest:
            if part == ".":
                continue
            if part == "..":
                if not segments:
                    raise PathEscapesNamespace(path=raw, root=namespace)
                segments.pop()
                continue
            segments.append(part)

        return cls(namespace=namespace, segments=tuple(segments))

    def __str__(self) -> str:
        return "/".join((self.namespace, *self.segments))
PY

pytest tests/test_paths.py
```
Expected: `9 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(paths): canonical fragment paths confined to their namespace

Canonicalization is lexical and touches no filesystem, keeping this
module inside the no-I/O-outside-custody rule (ADR-001) — asserted by
a test that makes filesystem calls explode."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/paths.py tests/test_paths.py
```
