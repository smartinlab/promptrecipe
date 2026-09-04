# ST-005-04: ⭐ Property P1 — determinism

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Establish the property everything trustworthy rests on: **identical inputs yield byte-identical output**. Without it, a provenance record describes what happened once rather than what will happen again, and both reproduction (FR-003) and comparison (FR-005) become unsound.

**Why a property test:** nondeterminism surfaces on inputs nobody thought to write by hand. Someone who believes the code is correct will not write the failing example.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 94 passed
```

**Files** — Create: `tests/test_property_determinism.py`

---

### Step 1 — Write the property test (6 min)

```bash
cat > tests/test_property_determinism.py <<'PY'
"""Property P1 — determinism (TRD §4, SD7).

Assembly must be a pure function: the same inputs always produce the same
bytes. TRD §4 names the hazards — hash/dict-order iteration, wall-clock and
environment leakage, locale-sensitive comparison, filesystem enumeration.
"""

from conftest import MemoryCustody
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.resolve import Resolver

SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


def library(count: int) -> Resolver:
    """A recipe loading `count` fragments, each gated by a control variable,
    with value placeholders in the prose."""
    entries = {f"core/f{i}": f"FRAGMENT-{i}-BODY" for i in range(count)}
    recipe = ["Header {{customer}}\n"]
    recipe += [f"[if flag{i}] [load core/f{i}]\n" for i in range(count)]
    recipe.append("Footer {{customer}}\n")
    entries["core/recipe"] = "".join(recipe)
    return Resolver().register("core", "mem", MemoryCustody(entries))


@SETTINGS
@given(
    flags=st.lists(st.booleans(), min_size=1, max_size=12),
    customer=st.text(alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Zs")), max_size=24),
)
def test_assembly_is_byte_identical_for_identical_inputs(flags, customer):
    resolver = library(len(flags))
    params = Params(
        controls={f"flag{i}": on for i, on in enumerate(flags)},
        values={"customer": customer},
    )

    first = get_prompt("core/recipe", params, resolver)
    second = get_prompt("core/recipe", params, resolver)

    assert first.text == second.text, "assembly must be byte-identical"
    assert first.fragments == second.fragments, "fragment list and order must match"
    assert first.condition_outcomes == second.condition_outcomes


@SETTINGS
@given(flags=st.lists(st.booleans(), min_size=1, max_size=8))
def test_repeated_assembly_never_drifts(flags):
    resolver = library(len(flags))
    params = Params(controls={f"flag{i}": on for i, on in enumerate(flags)})

    baseline = get_prompt("core/recipe", params, resolver).text
    for round_number in range(10):
        again = get_prompt("core/recipe", params, resolver).text
        assert baseline == again, f"drift appeared at round {round_number}"


@SETTINGS
@given(flags=st.lists(st.booleans(), min_size=2, max_size=8))
def test_binding_insertion_order_does_not_affect_output(flags):
    """The direct guard against dict-insertion order reaching the result:
    the same bindings supplied in a different sequence must assemble
    identically."""
    resolver = library(len(flags))

    forward = Params(controls={f"flag{i}": on for i, on in enumerate(flags)})
    backward = Params(
        controls={f"flag{i}": on for i, on in reversed(list(enumerate(flags)))}
    )

    a = get_prompt("core/recipe", forward, resolver)
    b = get_prompt("core/recipe", backward, resolver)
    assert a.text == b.text, "binding insertion order leaked into output"


@SETTINGS
@given(value=st.text(max_size=40))
def test_arbitrary_value_text_never_changes_which_fragments_load(value):
    """ADR-006 as a property: no caller-supplied text, however hostile,
    can influence structure."""
    resolver = library(3)
    params = Params(
        controls={f"flag{i}": True for i in range(3)},
        values={"customer": value},
    )
    out = get_prompt("core/recipe", params, resolver)
    assert len(out.fragments) == 3, "value text must never add or remove a fragment"
PY

pytest tests/test_property_determinism.py
```
Expected:
```
4 passed
```

> **If any fails, do not weaken the test.** Hypothesis writes the minimal failing case to `.hypothesis/`. That case is the bug. Likely causes in order: a `set` or unsorted dict reached output ordering, a locale-sensitive string operation, or an environment read.

### Step 2 — Commit the hypothesis example database if one appeared (1 min)

```bash
ls .hypothesis/examples 2>/dev/null && echo "failing cases were found" || echo "none — property held"
```

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test: establish property P1 — determinism

Byte-identical for identical inputs, no drift across repeats, and
unaffected by binding insertion order — the direct guard against
dict-order iteration reaching output (TRD §4, SD7). Plus a property
form of ADR-006: no caller-supplied text can change structure."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_property_determinism.py
```
