# ST-006-02: Canonical ordering before digesting; timestamps excluded

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Compute digests over **canonically ordered** fields. A serialization-order-dependent digest would silently break determinism — the same assembly would get different identities on different runs.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 104 passed
```

**Files** — Modify: `src/promptrecipe/provenance.py`. Create: `tests/test_canonical_form.py`

---

### Step 1 — RED: write the failing test (4 min)

The pair of tests in steps below encode a distinction that is easy to get backwards, and getting it backwards corrupts every comparison.

```bash
cat > tests/test_canonical_form.py <<'PY'
from dataclasses import replace

from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    canonical_instance_form,
    canonical_structural_form,
)


def sample() -> Attestation:
    return Attestation(
        subject="aa" * 32,
        resolved_dependencies=[ResolvedDependency(path="core/tone", identity="bb" * 32)],
        condition_outcomes=[("(model == 'claude')", True)],
        resolved_order=["core/role", "core/tone"],
        address_resolutions=[("tone", "core/tone.claude")],
        value_bindings=[("customer", "Acme")],
        producer=Producer(),
        recorded_at="2026-08-31T12:00:00Z",
    )


def test_the_canonical_form_is_stable_across_calls():
    a = sample()
    assert canonical_structural_form(a) == canonical_structural_form(a)


def test_a_timestamp_never_reaches_the_canonical_form():
    """TRD §4: wall-clock must not leak into anything digested, or the same
    assembly would get a new identity every time it ran."""
    base = sample()
    later = replace(base, recorded_at="2099-01-01T00:00:00Z")
    absent = replace(base, recorded_at=None)

    assert canonical_structural_form(base) == canonical_structural_form(later)
    assert canonical_structural_form(base) == canonical_structural_form(absent)


def test_value_binding_order_does_not_change_the_canonical_form():
    """Bindings are sorted before digesting: the order a caller supplied them
    in must not change an identity."""
    forward = replace(sample(), value_bindings=[("a", "1"), ("b", "2")])
    backward = replace(sample(), value_bindings=[("b", "2"), ("a", "1")])
    assert canonical_instance_form(forward) == canonical_instance_form(backward)


def test_dependency_order_DOES_change_the_canonical_form():
    """The deliberate opposite of the previous test.

    Bindings are a SET of inputs, so their order is incidental. Dependency
    ORDER is part of what the prompt IS (SD13). Sorting dependencies here
    would destroy that distinction and silently corrupt every comparison.
    """
    ab = replace(
        sample(),
        resolved_dependencies=[
            ResolvedDependency("a", "1"),
            ResolvedDependency("b", "2"),
        ],
    )
    ba = replace(
        sample(),
        resolved_dependencies=[
            ResolvedDependency("b", "2"),
            ResolvedDependency("a", "1"),
        ],
    )
    assert canonical_structural_form(ab) != canonical_structural_form(ba)


def test_the_structural_form_excludes_value_bindings():
    with_values = replace(sample(), value_bindings=[("customer", "Acme")])
    without = replace(sample(), value_bindings=[])
    assert canonical_structural_form(with_values) == canonical_structural_form(without)
PY

pytest tests/test_canonical_form.py
```
Expected: `ImportError: cannot import name 'canonical_structural_form'`

### Step 2 — GREEN: add the canonical forms (4 min)

```bash
python3 - <<'PY'
import io
p = "src/promptrecipe/provenance.py"
s = io.open(p, encoding="utf-8").read()
s += '''

def canonical_structural_form(a: Attestation) -> str:
    """Canonical text for the STRUCTURAL identity.

    Excludes value bindings (ADR-005) and the timestamp (TRD §4).

    Dependency ORDER is preserved because order is part of what the prompt is
    (SD13). Binding-style collections are SORTED because their order is
    incidental. Getting that distinction backwards is the easiest way to
    corrupt every comparison the product will ever produce.
    """
    lines: list[str] = ["deps"]
    # NOT sorted: assembly order is meaningful.
    lines += [f"{d.path}\\t{d.identity}" for d in a.resolved_dependencies]

    lines.append("order")
    lines += list(a.resolved_order)

    lines.append("conditions")
    lines += [f"{expr}\\t{outcome}" for expr, outcome in sorted(a.condition_outcomes)]

    lines.append("addresses")
    lines += [f"{name}\\t{path}" for name, path in sorted(a.address_resolutions)]

    lines.append("producer")
    lines.append(f"{a.producer.name}\\t{a.producer.version}\\t{a.producer.digest_algorithm}")

    return "\\n".join(lines) + "\\n"


def canonical_instance_form(a: Attestation) -> str:
    """Canonical text for the INSTANCE identity: the structural form plus the
    value bindings, sorted."""
    lines = [canonical_structural_form(a).rstrip("\\n"), "values"]
    lines += [f"{name}\\t{value}" for name, value in sorted(a.value_bindings)]
    return "\\n".join(lines) + "\\n"
'''
io.open(p, "w", encoding="utf-8").write(s)
PY

pytest tests/test_canonical_form.py
```
Expected: `5 passed`

### Step 3 — Confirm the timestamp exclusion holds (1 min)

```bash
awk '/def canonical_structural_form/,/^def canonical_instance_form/' src/promptrecipe/provenance.py | grep -n "recorded_at"
```
Expected: **no output.**

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(provenance): canonical forms; timestamps excluded from digests

Dependency order is preserved (SD13: order is part of what the prompt
is); binding-style collections are sorted because their order is
incidental. Two tests encode that distinction explicitly, because
getting it backwards corrupts every comparison silently."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_canonical_form.py
```
