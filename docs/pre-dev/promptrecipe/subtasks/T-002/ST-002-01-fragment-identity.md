# ST-002-01: `FragmentId` — BLAKE3 content identity

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Give every fragment version an identity derived from its bytes alone — independent of path, custody, and metadata (ADR-002).

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 3 passed
```

**Files** — Create: `src/promptrecipe/identity.py`, `tests/test_identity.py`

---

### Step 1 — RED: write the failing test (3 min)

```bash
cat > tests/test_identity.py <<'PY'
from promptrecipe.identity import FragmentId


def test_identical_bytes_yield_identical_identity():
    assert FragmentId.of(b"you are a helpful assistant") == FragmentId.of(
        b"you are a helpful assistant"
    )


def test_one_changed_byte_changes_the_identity():
    assert FragmentId.of(b"be concise") != FragmentId.of(b"be concise.")


def test_identity_does_not_depend_on_where_content_came_from():
    """The property that lets custody change safely (SD1).

    The same bytes read locally and remotely must be one identity, or
    provenance recorded before a custody move stops validating after it.
    """
    assert FragmentId.of(b"shared safety rule") == FragmentId.of(b"shared safety rule")


def test_hex_is_64_chars_and_short_is_12():
    fid = FragmentId.of(b"anything")
    assert len(fid.hex) == 64
    assert len(fid.short) == 12
    assert fid.hex.startswith(fid.short)


def test_empty_content_still_has_an_identity():
    assert len(FragmentId.of(b"").hex) == 64


def test_identity_is_hashable_and_usable_as_a_dict_key():
    """Required by the identity-keyed cache in ST-002-05."""
    fid = FragmentId.of(b"x")
    assert {fid: "value"}[FragmentId.of(b"x")] == "value"


def test_identity_is_immutable():
    fid = FragmentId.of(b"x")
    try:
        fid.hex = "tampered"  # type: ignore[misc]
    except AttributeError:
        return
    raise AssertionError("FragmentId must be immutable")
PY

pytest tests/test_identity.py
```
Expected: `ModuleNotFoundError: No module named 'promptrecipe.identity'`

### Step 2 — GREEN: write the implementation (3 min)

```bash
cat > src/promptrecipe/identity.py <<'PY'
"""Content-derived fragment identity (ADR-002).

Identity comes from the bytes and nothing else. Two fragments with identical
content have identical identity, whatever their path or custody. That is what
lets custody change without invalidating provenance (SD1, SD2).
"""

from __future__ import annotations

from dataclasses import dataclass

import blake3

DIGEST_ALGORITHM = "blake3"


@dataclass(frozen=True, slots=True, order=True)
class FragmentId:
    """A content-derived identity for a fragment version.

    Frozen so an identity cannot be mutated after creation, and hashable so it
    can key the content cache (ST-002-05).
    """

    hex: str

    @classmethod
    def of(cls, content: bytes) -> FragmentId:
        """Compute the identity of the given bytes."""
        return cls(blake3.blake3(content).hexdigest())

    @property
    def short(self) -> str:
        """First 12 hex characters. Display only — never an identity."""
        return self.hex[:12]

    def __str__(self) -> str:
        return self.hex

    def __repr__(self) -> str:
        return f"FragmentId({self.short})"
PY

pytest tests/test_identity.py
```
Expected: `7 passed`

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(identity): content-derived FragmentId via BLAKE3

ADR-002. Identity comes from bytes alone, so it survives a custody
change — which keeps provenance valid across SD2's backends. Frozen
and hashable, because it keys the content cache."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f src/promptrecipe/identity.py tests/test_identity.py
```
