# ST-002-05: Identity-keyed cache — a path-keyed cache would be a correctness bug

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Cache fragment content **by content identity, never by path**. This is not an optimization detail: a path-keyed cache serves stale content after an edit, silently breaking the product's central promise (FR-007, change once → propagates).

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 32 passed
```

**Files** — Create: `src/promptrecipe/custody/cache.py`, `tests/test_cache.py`

---

### Step 1 — RED: write the failing test (3 min)

The decisive test is `an_edited_fragment_never_hits_the_cache` — written to fail loudly if anyone ever re-keys this cache by path.

```bash
cat > tests/test_cache.py <<'PY'
from promptrecipe.custody import FragmentContent
from promptrecipe.custody.cache import ContentCache
from promptrecipe.identity import FragmentId


def test_caches_and_returns_content_by_identity():
    cache = ContentCache()
    content = FragmentContent.of(b"Be concise.")
    cache.put(content)
    assert cache.get(content.id).data == content.data
    assert cache.stats == (1, 0)


def test_an_edited_fragment_never_hits_the_cache():
    """THE load-bearing test of this module.

    A fragment at a fixed path is edited. With identity keying the new
    content has a new key, so the old entry cannot be returned. If someone
    re-keys this cache by path, this test fails — which is the point.
    """
    cache = ContentCache()
    before = FragmentContent.of(b"Be concise.")
    cache.put(before)

    after = FragmentContent.of(b"Be concise and cite sources.")
    assert before.id != after.id, "edited content must have a new identity"

    assert cache.get(after.id) is None, (
        "edited content must MISS the cache — a hit means the cache is keyed "
        "by something other than content, and stale text would be served "
        "after an edit, breaking FR-007 silently"
    )


def test_identical_content_at_two_paths_shares_one_entry():
    """Deduplication falls out of identity keying, and is what makes
    fragments shared across model variants cheap."""
    cache = ContentCache()
    cache.put(FragmentContent.of(b"shared safety rule"))
    cache.put(FragmentContent.of(b"shared safety rule"))
    assert len(cache) == 1


def test_a_miss_is_counted_and_returns_none():
    cache = ContentCache()
    assert cache.get(FragmentId.of(b"never inserted")) is None
    assert cache.stats == (0, 1)


def test_the_cache_is_keyed_by_fragment_id_not_by_path():
    """Structural guard: inspect the key type directly."""
    cache = ContentCache()
    content = FragmentContent.of(b"x")
    cache.put(content)
    assert all(isinstance(k, FragmentId) for k in cache.keys())
PY

pytest tests/test_cache.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.custody.cache'`

### Step 2 — GREEN: write the implementation (3 min)

```bash
cat > src/promptrecipe/custody/cache.py <<'PY'
"""Content-keyed cache.

The cache key is the CONTENT IDENTITY, never the path. A path-keyed cache
would return stale bytes after a fragment changed — silently breaking FR-007
(change once, propagates everywhere) with no error anywhere. Keying by
identity makes staleness structurally impossible: different content is a
different key.
"""

from __future__ import annotations

from collections.abc import Iterator

from promptrecipe.custody import FragmentContent
from promptrecipe.identity import FragmentId


class ContentCache:
    """Caches fragment content by identity."""

    def __init__(self) -> None:
        # Keyed by FragmentId. Never by FragmentPath. See the module docstring.
        self._entries: dict[FragmentId, bytes] = {}
        self._hits = 0
        self._misses = 0

    def get(self, fragment_id: FragmentId) -> FragmentContent | None:
        data = self._entries.get(fragment_id)
        if data is None:
            self._misses += 1
            return None
        self._hits += 1
        return FragmentContent(id=fragment_id, data=data)

    def put(self, content: FragmentContent) -> None:
        self._entries[content.id] = content.data

    def keys(self) -> Iterator[FragmentId]:
        return iter(self._entries)

    @property
    def stats(self) -> tuple[int, int]:
        """(hits, misses)."""
        return self._hits, self._misses

    def __len__(self) -> int:
        return len(self._entries)
PY

pytest tests/test_cache.py
```
Expected: `5 passed`

### Step 3 — Guard the invariant against future edits (1 min)

```bash
grep -n "FragmentPath" src/promptrecipe/custody/cache.py
```
Expected: **no output.** A hit means the cache was re-keyed by path — revert it.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(custody): content-keyed cache; never keyed by path

Keying by identity makes staleness structurally impossible: edited
content is a different key, so an edit can never be served from cache.
Dedup across paths falls out for free."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/custody/cache.py tests/test_cache.py
```

---

## T-002 Definition of Done

- [ ] `FragmentId` derives identity from content alone (ADR-002)
- [ ] Every error names what failed, expected, and supplied (TRD §7)
- [ ] Paths canonicalize lexically and cannot escape their namespace root
- [ ] **A test proves path parsing never touches the filesystem** (ADR-001)
- [ ] **`grep` confirms no I/O anywhere outside `custody/`**
- [ ] **Cache keyed by identity; the edited-content test proves staleness is impossible**
- [ ] Directory listing sorted explicitly, never filesystem-ordered (TRD §4)
