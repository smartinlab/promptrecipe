# ST-004-03: Ambiguity is an error naming every candidate

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Prove at integration level that **no configuration can produce a silent shadow.** First-match-wins is the exact silent-failure class this product exists to remove: it resolves successfully, produces a plausible prompt, and gives no signal that a different fragment was shadowed.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 74 passed
```

**Files** — Create: `tests/test_resolution_never_shadows.py`

---

### Step 1 — Write the guard suite (4 min)

These tests fail if anyone ever adds a fallback for convenience.

```bash
cat > tests/test_resolution_never_shadows.py <<'PY'
"""ADR-004 / FR-031: resolution must never silently pick between candidates."""

import pytest
from conftest import MemoryCustody

from promptrecipe.errors import AmbiguousReference
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def test_two_candidates_produce_an_error_not_a_winner():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "from alpha"}))
        .register("core", "beta", MemoryCustody({"core/tone": "from beta"}))
    )
    with pytest.raises(AmbiguousReference):
        r.resolve(FragmentPath.parse("core/tone"))


def test_the_ambiguity_error_names_every_candidate():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "a"}))
        .register("core", "beta", MemoryCustody({"core/tone": "b"}))
        .register("core", "gamma", MemoryCustody({"core/tone": "c"}))
    )
    with pytest.raises(AmbiguousReference) as exc:
        r.resolve(FragmentPath.parse("core/tone"))
    msg = str(exc.value)
    for candidate in ("alpha", "beta", "gamma"):
        assert candidate in msg
    assert "3 candidates" in msg


def test_identical_content_in_two_sources_is_still_ambiguous():
    """Even when both candidates would produce identical bytes, the
    CONFIGURATION is ambiguous and the author should be told. Resolving
    quietly here means the next edit to one source silently changes
    behaviour with no signal."""
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/tone": "same"}))
        .register("core", "beta", MemoryCustody({"core/tone": "same"}))
    )
    with pytest.raises(AmbiguousReference):
        r.resolve(FragmentPath.parse("core/tone"))


def test_a_single_candidate_across_several_sources_resolves_cleanly():
    r = (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/other": "x"}))
        .register("core", "beta", MemoryCustody({"core/tone": "the only one"}))
    )
    fid, trace = r.resolve(FragmentPath.parse("core/tone"))
    assert fid == FragmentId.of(b"the only one")
    assert trace.winner == "beta"
    assert len(trace.entries) == 2, "both sources are consulted"
PY

pytest tests/test_resolution_never_shadows.py
```
Expected: `4 passed`

### Step 2 — Run the whole suite (1 min)

```bash
pytest
```
Expected: all green.

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test(resolve): prove no configuration can silently shadow

Includes the subtle case: identical content in two sources is still an
ambiguous configuration, because the next edit to one of them would
change behaviour with no signal."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_resolution_never_shadows.py
```

---

## T-004 Definition of Done

- [ ] A path resolves to exactly one `FragmentId`
- [ ] **Every candidate is evaluated — never short-circuited**
- [ ] **Ambiguity errors, naming every candidate and the count**
- [ ] Unknown namespace errors listing the known ones; missing fragment errors without falling back
- [ ] A resolution trace explains every outcome (FR-030)
- [ ] **A test asserts resolution performs no assembly** (FR-011 depends on it)
