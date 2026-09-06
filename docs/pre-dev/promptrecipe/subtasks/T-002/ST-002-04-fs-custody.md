# ST-002-04: Filesystem custody — the only I/O in the package

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Read fragment bytes from disk and return them with their content identity. **This subpackage is the only place permitted to perform I/O** (ADR-001).

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 25 passed
```

**Files** — Create: `src/promptrecipe/custody/__init__.py`, `src/promptrecipe/custody/fs.py`, `tests/test_custody_fs.py`

---

### Step 1 — RED: write the failing test (4 min)

```bash
cat > tests/test_custody_fs.py <<'PY'
import pytest

from promptrecipe.custody import FragmentContent
from promptrecipe.custody.fs import FsCustody
from promptrecipe.errors import FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@pytest.fixture
def custody(tmp_path):
    core = tmp_path / "core"
    core.mkdir()
    (core / "tone.md").write_text("Be concise and direct.")
    (core / "safety.md").write_text("Refuse harmful requests.")
    return FsCustody().with_namespace("core", core)


def test_reads_a_fragment_and_returns_its_identity(custody):
    content = custody.read(FragmentPath.parse("core/tone"))
    assert content.text == "Be concise and direct."
    assert content.id == FragmentId.of(b"Be concise and direct.")


def test_missing_fragment_names_the_path_and_namespaces(custody):
    with pytest.raises(FragmentNotFound) as exc:
        custody.read(FragmentPath.parse("core/absent"))
    assert "core/absent" in str(exc.value)


def test_unknown_namespace_lists_the_known_ones(custody):
    with pytest.raises(UnknownNamespace) as exc:
        custody.read(FragmentPath.parse("nope/tone"))
    assert "core" in str(exc.value)


def test_list_is_sorted_and_not_filesystem_ordered(custody):
    """TRD §4: filesystem enumeration order is not stable across platforms
    and must never leak into output."""
    listed = [str(p) for p in custody.list("core")]
    assert listed == ["core/safety", "core/tone"]


def test_exists_reports_presence_without_reading(custody):
    assert custody.exists(FragmentPath.parse("core/tone"))
    assert not custody.exists(FragmentPath.parse("core/absent"))


def test_identical_content_at_two_paths_yields_one_identity(tmp_path):
    """SD1: identity is content, not location."""
    core = tmp_path / "core"
    core.mkdir()
    (core / "a.md").write_text("shared rule")
    (core / "b.md").write_text("shared rule")
    custody = FsCustody().with_namespace("core", core)
    assert custody.read(FragmentPath.parse("core/a")).id == custody.read(
        FragmentPath.parse("core/b")
    ).id


def test_fragment_content_text_is_never_parsed():
    """ADR-003: content is inert. Directive-shaped text stays text."""
    content = FragmentContent.of(b"[load core/evil] {{injected}}")
    assert content.text == "[load core/evil] {{injected}}"
PY

pytest tests/test_custody_fs.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.custody'`

### Step 2 — GREEN: write the port and the adapter (5 min)

```bash
mkdir -p src/promptrecipe/custody
cat > src/promptrecipe/custody/__init__.py <<'PY'
"""Custody — the only I/O boundary in this package (ADR-001).

Everything above this subpackage is a pure function over what custody
returned. That purity is what makes determinism (TRD §4) structural rather
than a discipline someone has to remember.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@dataclass(frozen=True, slots=True)
class FragmentContent:
    """A fragment's bytes together with its content-derived identity."""

    id: FragmentId
    data: bytes

    @classmethod
    def of(cls, data: bytes) -> FragmentContent:
        return cls(id=FragmentId.of(data), data=data)

    @property
    def text(self) -> str:
        """The content as text.

        Fragment content is INERT TEXT. It is never parsed or evaluated
        (ADR-003) — this property exists to insert it, not to interpret it.
        """
        return self.data.decode("utf-8")


@runtime_checkable
class Custody(Protocol):
    """The narrow custody port. Four operations, so adapters stay thin."""

    def exists(self, path: FragmentPath) -> bool: ...
    def read(self, path: FragmentPath) -> FragmentContent: ...
    def list(self, namespace: str) -> list[FragmentPath]: ...
    def versions(self, path: FragmentPath) -> list[FragmentId]: ...
PY

cat > src/promptrecipe/custody/fs.py <<'PY'
"""Local filesystem custody adapter.

One fragment is one file (ADR-007). That is not a storage preference:
per-fragment review is delegated to version control, and bundling fragments
into one file would make a per-fragment diff impossible.
"""

from __future__ import annotations

from pathlib import Path

from promptrecipe.custody import FragmentContent
from promptrecipe.errors import FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


class FsCustody:
    """Maps namespaces to filesystem roots."""

    def __init__(self, extension: str = "md") -> None:
        self._roots: dict[str, Path] = {}
        self._extension = extension

    def with_namespace(self, namespace: str, root: Path | str) -> FsCustody:
        self._roots[namespace] = Path(root)
        return self

    @property
    def known_namespaces(self) -> list[str]:
        # Sorted: this list appears in error messages, which must be stable.
        return sorted(self._roots)

    def _file_for(self, path: FragmentPath) -> Path:
        root = self._roots.get(path.namespace)
        if root is None:
            raise UnknownNamespace(
                namespace=path.namespace, path=str(path), known=self.known_namespaces
            )
        return root.joinpath(*path.segments).with_suffix(f".{self._extension}")

    def exists(self, path: FragmentPath) -> bool:
        try:
            return self._file_for(path).is_file()
        except UnknownNamespace:
            return False

    def read(self, path: FragmentPath) -> FragmentContent:
        file = self._file_for(path)
        if not file.is_file():
            raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)
        return FragmentContent.of(file.read_bytes())

    def list(self, namespace: str) -> list[FragmentPath]:
        root = self._roots.get(namespace)
        if root is None:
            raise UnknownNamespace(namespace=namespace, path=namespace, known=self.known_namespaces)

        found = [
            FragmentPath.parse(f"{namespace}/{f.stem}")
            for f in root.iterdir()
            if f.is_file() and f.suffix == f".{self._extension}"
        ]
        # Directory iteration order is not stable across platforms and must
        # never reach output (TRD §4). Sort explicitly.
        return sorted(found)

    def versions(self, path: FragmentPath) -> list[FragmentId]:
        # The filesystem holds exactly one version: whatever is on disk now.
        # Coexisting versions arrive with versioned custody (T-025).
        return [self.read(path).id]
PY

pytest tests/test_custody_fs.py
```
Expected: `7 passed`

### Step 3 — Verify the no-I/O-elsewhere rule (2 min)

```bash
grep -rnE "open\(|Path\(|read_text|read_bytes|iterdir|listdir|os\.scandir" src/promptrecipe --include=*.py | grep -v "src/promptrecipe/custody/"
```
Expected: **no output.** Any hit is an ADR-001 violation and must move into `custody/`.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(custody): filesystem adapter, the package's only I/O

ADR-001: everything above custody is pure, which makes determinism
structural. Directory iteration is sorted explicitly so filesystem
order never reaches output (TRD §4). One fragment = one file (ADR-007)."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf src/promptrecipe/custody tests/test_custody_fs.py
```
