# ST-006-04: ⭐ Property P2 — order-aware structural identity

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Establish that permuting fragment order changes the structural identity.

**Why this needs a property test.** An order-blind identity is a **silent** failure. Nothing errors. Assembly succeeds, results look plausible, and two genuinely different prompts are grouped as one — quietly corrupting every comparison. Nobody who believes the code is correct writes the example that catches this.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 115 passed
```

**Files** — Create: `tests/test_property_order_identity.py`

---

### Step 1 — Write the property test (6 min)

```bash
cat > tests/test_property_order_identity.py <<'PY'
"""Property P2 — order-aware structural identity (SD13, ADR-005).

Two assemblies containing an identical fragment SET but a different ORDER are
different prompts and must have different structural identities.
"""

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)

SETTINGS = settings(max_examples=300, deadline=None)


def attestation(
    deps: list[tuple[str, str]], values: list[tuple[str, str]] | None = None
) -> Attestation:
    return Attestation(
        subject="00" * 32,
        resolved_dependencies=[ResolvedDependency(p, i) for p, i in deps],
        resolved_order=[p for p, _ in deps],
        value_bindings=values or [],
        producer=Producer(),
    )


def distinct_deps(n: int) -> list[tuple[str, str]]:
    return [(f"core/f{i}", f"{i + 1:064x}") for i in range(n)]


@SETTINGS
@given(count=st.integers(min_value=2, max_value=8), rotate_by=st.integers(1, 7))
def test_reordering_fragments_changes_the_structural_identity(count, rotate_by):
    deps = distinct_deps(count)
    shift = rotate_by % count
    rotated = deps[shift:] + deps[:shift]
    assume(rotated != deps)

    assert structural_identity(attestation(deps)) != structural_identity(attestation(rotated)), (
        "reordered fragments produced the SAME structural identity. This is "
        "the silent failure: two different prompts would be grouped as one and "
        "every comparison between them would be meaningless, with no error "
        "raised anywhere."
    )


@SETTINGS
@given(count=st.integers(min_value=1, max_value=8))
def test_identical_order_gives_identical_structural_identity(count):
    deps = distinct_deps(count)
    assert structural_identity(attestation(deps)) == structural_identity(attestation(deps))


@SETTINGS
@given(
    count=st.integers(min_value=1, max_value=6),
    left=st.text(min_size=1, max_size=10),
    right=st.text(min_size=1, max_size=10),
)
def test_value_bindings_move_instance_identity_only(count, left, right):
    """ADR-005: values change instance identity, never structural identity."""
    assume(left != right)
    deps = distinct_deps(count)

    a = attestation(deps, [("customer", left)])
    b = attestation(deps, [("customer", right)])

    assert structural_identity(a) == structural_identity(b), (
        "value bindings must NOT affect structural identity, or A/B grouping "
        "breaks and every single call stands alone"
    )
    assert instance_identity(a) != instance_identity(b), (
        "value bindings MUST affect instance identity, or byte-identical "
        "reproduction cannot tell two renderings apart"
    )


@SETTINGS
@given(count=st.integers(min_value=1, max_value=6))
def test_changed_fragment_content_changes_the_structural_identity(count):
    """Path and order unchanged, content different — still a different prompt."""
    deps = distinct_deps(count)
    edited = [(deps[0][0], f"{0xDEADBEEF:064x}"), *deps[1:]]
    assert structural_identity(attestation(deps)) != structural_identity(attestation(edited))
PY

pytest tests/test_property_order_identity.py
```
Expected: `4 passed`

> **If the first test fails, stop everything.** It means dependencies are being sorted, or collected into a set, before digesting. Check `canonical_structural_form`: dependency order must be **preserved** while binding-style collections are **sorted**. Getting that backwards is the single easiest way to corrupt every comparison the product will ever produce.

### Step 2 — Run the full suite (1 min)

```bash
pytest
```
Expected: all green — P1 and P2 both established.

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test: establish property P2 — order-aware structural identity

Reordering fragments changes the structural identity; value bindings
move only the instance identity (ADR-005, SD13). An order-blind
identity fails silently, which is why this is a property test."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_property_order_identity.py
```

---

## T-006 Definition of Done

- [ ] Every assembly returns an attestation — **a non-optional field, so SD5 cannot be bypassed**
- [ ] Canonical forms stable; **dependency order preserved, binding collections sorted**
- [ ] **Timestamps excluded from both digests** (TRD §4)
- [ ] **Property P2 green** — reordering changes structural identity
- [ ] **Value bindings change instance identity only** (ADR-005)
- [ ] Both identities are full 64-character digests
- [ ] P1 from T-005 still green
