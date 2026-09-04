# ST-004-01: Namespace registry — prefix-routed dispatch

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Route a path's leading segment to the custody source that owns it — the mature prior art Gate 0 identified for path-addressed content with namespacing.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 64 passed
```

**Files** — Create: `src/promptrecipe/resolve.py`, `tests/conftest.py`, `tests/test_resolve_registry.py`

---

### Step 1 — Create a shared in-memory custody for tests (2 min)

Keeps resolution tests free of I/O, which is the point of ADR-001.

```bash
cat > tests/conftest.py <<'PY'
"""Shared test helpers."""

from __future__ import annotations

from promptrecipe.custody import FragmentContent
from promptrecipe.errors import FragmentNotFound
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


class MemoryCustody:
    """In-memory custody. Lets resolution and assembly be tested without I/O."""

    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self._entries = {k: v.encode("utf-8") for k, v in (entries or {}).items()}

    def exists(self, path: FragmentPath) -> bool:
        return str(path) in self._entries

    def read(self, path: FragmentPath) -> FragmentContent:
        data = self._entries.get(str(path))
        if data is None:
            raise FragmentNotFound(path=str(path), namespaces=["memory"])
        return FragmentContent.of(data)

    def list(self, namespace: str) -> list[FragmentPath]:
        return sorted(
            FragmentPath.parse(k) for k in self._entries if k.startswith(f"{namespace}/")
        )

    def versions(self, path: FragmentPath) -> list[FragmentId]:
        return [self.read(path).id]
PY
```

### Step 2 — RED: write the failing test (3 min)

```bash
cat > tests/test_resolve_registry.py <<'PY'
from conftest import MemoryCustody

from promptrecipe.resolve import Resolver


def test_a_namespace_routes_to_its_source():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    assert r.known_namespaces == ["core"]
    assert len(r.sources_for("core")) == 1


def test_namespaces_are_isolated_from_one_another():
    """ADR-004: the same leaf name in two namespaces cannot collide, because
    the leading segment routes deterministically."""
    r = (
        Resolver()
        .register("core", "a", MemoryCustody({"core/tone": "core version"}))
        .register("team", "b", MemoryCustody({"team/tone": "team version"}))
    )
    assert r.known_namespaces == ["core", "team"]
    assert len(r.sources_for("core")) == 1
    assert len(r.sources_for("team")) == 1


def test_namespace_ordering_is_deterministic():
    """TRD §4: anything that can reach output or an error message must have a
    stable order, never dict-insertion or hash order."""

    def build():
        return (
            Resolver()
            .register("zeta", "z", MemoryCustody())
            .register("alpha", "a", MemoryCustody())
            .known_namespaces
        )

    assert build() == build() == ["alpha", "zeta"]


def test_an_unregistered_namespace_has_no_sources():
    assert Resolver().sources_for("core") == []
PY

pytest tests/test_resolve_registry.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.resolve'`

### Step 3 — GREEN: write the registry (3 min)

```bash
cat > src/promptrecipe/resolve.py <<'PY'
"""Resolution — path plus selection context to exactly one fragment identity.

Two rules define this module (ADR-004):

1. **Namespace isolation, not ordered search.** A path's leading segment
   routes to exactly one namespace. Collisions are structurally impossible
   rather than silently shadowed.
2. **Ambiguity is an error.** Where layering is configured, more than one
   candidate is a failure naming all of them — never a silent pick.

Resolution performs NO assembly and reads no content beyond what identity
requires. That separation is what makes dependency queries cheap (FR-011).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from promptrecipe.custody import Custody, FragmentContent
from promptrecipe.errors import AmbiguousReference, FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@dataclass(frozen=True, slots=True)
class TraceEntry:
    """One step of how a reference was resolved. Makes precedence
    inspectable (FR-030) — you can always explain why a fragment won."""

    namespace: str
    source: str
    found: bool


@dataclass(slots=True)
class ResolutionTrace:
    path: str
    entries: list[TraceEntry] = field(default_factory=list)
    winner: str | None = None


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    custody: Custody


class Resolver:
    """Routes namespaces to custody sources."""

    def __init__(self) -> None:
        self._namespaces: dict[str, list[Source]] = {}

    def register(self, namespace: str, name: str, custody: Custody) -> Resolver:
        self._namespaces.setdefault(namespace, []).append(Source(name=name, custody=custody))
        return self

    @property
    def known_namespaces(self) -> list[str]:
        # Sorted: this list reaches error messages, which must be stable
        # across runs (TRD §4).
        return sorted(self._namespaces)

    def sources_for(self, namespace: str) -> list[Source]:
        return list(self._namespaces.get(namespace, []))
PY

pytest tests/test_resolve_registry.py
```
Expected: `4 passed`

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(resolve): namespace registry with prefix-routed dispatch

ADR-004: namespace isolation makes collisions structurally impossible
rather than silently shadowed. Namespace listings are sorted so error
messages are stable across runs (TRD §4)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/resolve.py tests/conftest.py tests/test_resolve_registry.py
```
