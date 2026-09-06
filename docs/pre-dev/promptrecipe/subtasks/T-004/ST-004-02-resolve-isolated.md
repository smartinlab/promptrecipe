# ST-004-02: Resolve under namespace isolation, never first-match-wins

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Turn a path into exactly one `FragmentId`, evaluating **every** candidate rather than short-circuiting — so a trace can explain the outcome (FR-030), and so ambiguity is detectable at all.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 68 passed
```

**Files** — Modify: `src/promptrecipe/resolve.py`. Create: `tests/test_resolve.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_resolve.py <<'PY'
import pytest
from conftest import MemoryCustody

from promptrecipe.errors import FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def test_resolves_a_single_candidate_and_records_a_trace():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    fid, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert fid == FragmentId.of(b"Be concise.")
    assert trace.winner == "local"
    assert len(trace.entries) == 1


def test_every_candidate_is_evaluated_not_short_circuited():
    """Short-circuiting on the first hit would make ambiguity invisible."""
    r = (
        Resolver()
        .register("core", "first", MemoryCustody())
        .register("core", "second", MemoryCustody({"core/tone": "from second"}))
    )
    _, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert len(trace.entries) == 2, "all sources must be consulted"
    assert trace.winner == "second"


def test_unknown_namespace_fails_naming_the_known_ones():
    r = Resolver().register("core", "local", MemoryCustody())
    with pytest.raises(UnknownNamespace) as exc:
        r.resolve(FragmentPath.parse("nope/x"))
    assert "core" in str(exc.value)


def test_a_missing_fragment_fails_and_never_falls_back():
    r = Resolver().register("core", "local", MemoryCustody({"core/other": "x"}))
    with pytest.raises(FragmentNotFound):
        r.resolve(FragmentPath.parse("core/tone"))


def test_read_by_path_returns_content():
    r = Resolver().register("core", "local", MemoryCustody({"core/tone": "Be concise."}))
    assert r.read(FragmentPath.parse("core/tone")).text == "Be concise."


def test_resolution_performs_no_assembly():
    """FR-011 depends on resolution being cheap: no assembly, no substitution."""
    import inspect

    from promptrecipe import resolve

    source = inspect.getsource(resolve)
    for forbidden in ("assemble", "substitute"):
        assert forbidden not in source, f"resolution must not reference '{forbidden}'"
PY

pytest tests/test_resolve.py
```
Expected: `AttributeError: 'Resolver' object has no attribute 'resolve'`

### Step 2 — GREEN: add resolution (4 min)

```bash
python3 - <<'PY'
import io
p = "src/promptrecipe/resolve.py"
s = io.open(p, encoding="utf-8").read()
s += '''
    def resolve(self, path: FragmentPath) -> tuple[FragmentId, ResolutionTrace]:
        """Resolve a path to exactly one fragment identity.

        Every source registered for the namespace is consulted — deliberately
        NOT short-circuited on the first hit. Short-circuiting would make
        ambiguity undetectable, which is the silent-shadowing failure that
        ADR-004 exists to prevent.
        """
        sources = self._namespaces.get(path.namespace)
        if sources is None:
            raise UnknownNamespace(
                namespace=path.namespace, path=str(path), known=self.known_namespaces
            )

        trace = ResolutionTrace(path=str(path))
        hits: list[tuple[str, FragmentId]] = []

        for source in sources:
            found = source.custody.exists(path)
            trace.entries.append(
                TraceEntry(namespace=path.namespace, source=source.name, found=found)
            )
            if found:
                hits.append((source.name, source.custody.read(path).id))

        if not hits:
            raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)
        if len(hits) > 1:
            # ADR-004 / FR-031: never pick. Name every candidate.
            raise AmbiguousReference(path=str(path), candidates=[name for name, _ in hits])

        trace.winner = hits[0][0]
        return hits[0][1], trace

    def read(self, path: FragmentPath) -> FragmentContent:
        """Read the content a path resolves to. Delegates the only I/O to custody."""
        sources = self._namespaces.get(path.namespace)
        if sources is None:
            raise UnknownNamespace(
                namespace=path.namespace, path=str(path), known=self.known_namespaces
            )
        for source in sources:
            if source.custody.exists(path):
                return source.custody.read(path)
        raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)
'''
io.open(p, "w", encoding="utf-8").write(s)
PY

pytest tests/test_resolve.py
```
Expected: `6 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(resolve): resolve to exactly one identity, all candidates evaluated

Not short-circuited on first hit: short-circuiting makes ambiguity
undetectable, which is the silent shadowing ADR-004 forbids. A test
asserts resolution never references assembly, since FR-011 depends on
this staying cheap."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_resolve.py
```
