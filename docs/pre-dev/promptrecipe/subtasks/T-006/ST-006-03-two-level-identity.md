# ST-006-03: Structural vs instance identity (ADR-005)

> **You are here because a single identity cannot serve both comparison and reproduction.** Include value bindings and every call becomes unique, so nothing groups for A/B. Exclude them and byte-identical reproduction becomes impossible.

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Compute both identities and attach a complete attestation to every assembly.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 109 passed
```

**Files** — Modify: `src/promptrecipe/provenance.py`, `src/promptrecipe/assemble.py`. Create: `tests/test_two_level_identity.py`

---

### Step 1 — RED: write the failing test (4 min)

```bash
cat > tests/test_two_level_identity.py <<'PY'
from dataclasses import replace

from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)
from promptrecipe.resolve import Resolver


def sample() -> Attestation:
    return Attestation(
        subject="aa" * 32,
        resolved_dependencies=[ResolvedDependency("core/tone", "bb" * 32)],
        resolved_order=["core/tone"],
        producer=Producer(),
    )


def test_different_values_keep_structural_identity_and_change_instance_identity():
    """THE defining property of ADR-005.

    Two runs of the same prompt design for two different customers are the
    SAME variant (comparable) and DIFFERENT renderings (each reproducible).
    """
    acme = replace(sample(), value_bindings=[("customer", "Acme")])
    globex = replace(sample(), value_bindings=[("customer", "Globex")])

    assert structural_identity(acme) == structural_identity(globex), (
        "same prompt design must share a structural identity, or A/B grouping "
        "breaks and every run stands alone"
    )
    assert instance_identity(acme) != instance_identity(globex), (
        "different rendered text must have different instance identities, or "
        "reproduction cannot tell two renderings apart"
    )


def test_different_fragment_order_changes_the_structural_identity():
    """SD13, and the seed of property P2."""
    ab = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("a", "1"), ResolvedDependency("b", "2")],
    )
    ba = replace(
        sample(),
        resolved_dependencies=[ResolvedDependency("b", "2"), ResolvedDependency("a", "1")],
    )
    assert structural_identity(ab) != structural_identity(ba)


def test_identities_are_full_length_digests():
    a = sample()
    assert len(structural_identity(a)) == 64
    assert len(instance_identity(a)) == 64


def test_a_timestamp_change_leaves_both_identities_untouched():
    a = sample()
    b = replace(sample(), recorded_at="2099-01-01T00:00:00Z")
    assert structural_identity(a) == structural_identity(b)
    assert instance_identity(a) == instance_identity(b)


def test_every_assembly_carries_an_attestation():
    """SD5: the record is a return value, so it cannot be skipped."""
    resolver = Resolver().register(
        "core", "mem", MemoryCustody({"core/r": "[load core/f]", "core/f": "body"})
    )
    out = get_prompt("core/r", Params(), resolver)
    assert out.attestation is not None
    assert len(out.attestation.structural_identity) == 64
    assert len(out.attestation.instance_identity) == 64
    assert out.attestation.resolved_dependencies[0].path == "core/f"


def test_values_move_instance_identity_only_end_to_end():
    resolver = Resolver().register(
        "core", "mem", MemoryCustody({"core/r": "Hello {{customer}} [load core/f]",
                                      "core/f": "body"})
    )
    a = get_prompt("core/r", Params(values={"customer": "Acme"}), resolver)
    b = get_prompt("core/r", Params(values={"customer": "Globex"}), resolver)

    assert a.text != b.text
    assert a.attestation.structural_identity == b.attestation.structural_identity
    assert a.attestation.instance_identity != b.attestation.instance_identity
PY

pytest tests/test_two_level_identity.py
```
Expected: `ImportError: cannot import name 'structural_identity'`

### Step 2 — GREEN: add both identities (2 min)

```bash
python3 - <<'PY'
import io
p = "src/promptrecipe/provenance.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace("from promptrecipe.identity import DIGEST_ALGORITHM",
              "from promptrecipe.identity import DIGEST_ALGORITHM, FragmentId")
s += '''

def structural_identity(a: Attestation) -> str:
    """The identity to COMPARE by. Excludes value bindings (ADR-005).

    Two assemblies share this when they are the same prompt design. Group A/B
    results by this one.
    """
    return FragmentId.of(canonical_structural_form(a).encode("utf-8")).hex


def instance_identity(a: Attestation) -> str:
    """The identity to REPRODUCE from. Includes value bindings (ADR-005).

    Two assemblies share this only when they are the same rendered text.
    Comparing by this one makes every call unique and groups nothing.
    """
    return FragmentId.of(canonical_instance_form(a).encode("utf-8")).hex
'''
io.open(p, "w", encoding="utf-8").write(s)
PY
```

### Step 3 — GREEN: attach an attestation to every assembly (4 min)

```bash
python3 - <<'PY'
import io
p = "src/promptrecipe/assemble.py"
s = io.open(p, encoding="utf-8").read()

s = s.replace("from promptrecipe.paths import FragmentPath",
"""from promptrecipe.paths import FragmentPath
from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)""")

s = s.replace('''@dataclass(slots=True)
class Assembled:
    text: str''',
'''@dataclass(slots=True)
class Assembled:
    text: str
    attestation: Attestation
    """Emitted here, at assembly time — never reconstructed (SD5)."""''')

s = s.replace('''    return Assembled(text=text, fragments=fragments, condition_outcomes=condition_outcomes)''',
'''    # --- provenance: produced HERE, as a return value, so it cannot be
    # reconstructed after the fact when inputs may have changed (SD5).
    attestation = Attestation(
        subject=FragmentId.of(text.encode("utf-8")).hex,
        resolved_dependencies=[
            ResolvedDependency(path=path, identity=fid.hex) for path, fid in fragments
        ],
        condition_outcomes=list(condition_outcomes),
        resolved_order=[path for path, _ in fragments],
        address_resolutions=sorted(params.addresses.items()),
        value_bindings=sorted(params.values.items()),
        producer=Producer(),
        recorded_at=None,
    )
    attestation = replace(
        attestation,
        structural_identity=structural_identity(attestation),
    )
    attestation = replace(
        attestation,
        instance_identity=instance_identity(attestation),
    )

    return Assembled(
        text=text,
        attestation=attestation,
        fragments=fragments,
        condition_outcomes=condition_outcomes,
    )''')

s = s.replace("from dataclasses import dataclass, field",
              "from dataclasses import dataclass, field, replace")
io.open(p, "w", encoding="utf-8").write(s)
PY

pytest tests/test_two_level_identity.py && pytest
```
Expected: `6 passed`, then all suites green — including P1 from T-005.
> The P1 tests compare `text`, `fragments`, and `condition_outcomes`, all still deterministic. If they now fail, an identity is picking up per-run state.

### Step 4 — Verify the record cannot be skipped (1 min)

```bash
grep -n "attestation: Attestation" src/promptrecipe/assemble.py
```
Expected: a **non-optional field** of `Assembled` — no assembly can exist without one (SD5).

### Step 5 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat(provenance): two-level identity attached to every assembly

ADR-005. Structural identity groups A/B results; instance identity
reproduces exact text. One identity cannot serve both: including values
makes every call unique, excluding them makes reproduction impossible.
The attestation is a non-optional field, so SD5 cannot be bypassed."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_two_level_identity.py
```
