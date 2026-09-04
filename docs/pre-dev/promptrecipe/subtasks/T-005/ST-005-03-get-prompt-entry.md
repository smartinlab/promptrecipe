# ST-005-03: The `get_prompt` entry point

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Expose the single public call the whole product is shaped around.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 90 passed
```

**Files** — Modify: `src/promptrecipe/__init__.py`. Create: `tests/test_get_prompt.py`

---

### Step 1 — RED: write the integration test (4 min)

```bash
cat > tests/test_get_prompt.py <<'PY'
import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.errors import FragmentNotFound
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/recipe.claude": "[load core/role]\n[load core/tone.claude]\n[load core/safety]",
    "core/recipe.gpt": "[load core/role]\n[load core/tone.gpt]\n[load core/safety]",
    "core/role": "You are an assistant.",
    "core/tone.claude": "Be concise.",
    "core/tone.gpt": "Be thorough.",
    "core/safety": "Refuse harmful requests.",
}


@pytest.fixture
def resolver():
    return Resolver().register("core", "mem", MemoryCustody(LIBRARY))


def test_assembles_a_prompt_from_a_recipe_path(resolver):
    out = get_prompt("core/recipe.claude", Params(), resolver)
    assert "You are an assistant." in out.text
    assert "Be concise." in out.text


def test_two_templates_share_a_fragment_by_reference_not_by_copy(resolver):
    """The driving use case (amendment 6): model portability.

    Both templates reference core/safety — the SAME fragment, proven by
    identity equality rather than by matching text.
    """
    a = get_prompt("core/recipe.claude", Params(), resolver)
    b = get_prompt("core/recipe.gpt", Params(), resolver)

    assert dict(a.fragments)["core/safety"] == dict(b.fragments)["core/safety"], (
        "the shared fragment must be one fragment, not two copies"
    )
    assert a.text != b.text, "the variants must still differ where they should"


def test_a_missing_recipe_fails_explicitly(resolver):
    with pytest.raises(FragmentNotFound) as exc:
        get_prompt("core/absent", Params(), resolver)
    assert "core/absent" in str(exc.value)


def test_control_variables_reach_conditions_through_the_entry_point():
    r = Resolver().register(
        "core", "mem", MemoryCustody({"core/r": "[if verbose] [load core/extra]",
                                      "core/extra": "EXTRA"})
    )
    on = get_prompt("core/r", Params(controls={"verbose": True}), r)
    off = get_prompt("core/r", Params(controls={"verbose": False}), r)
    assert "EXTRA" in on.text
    assert "EXTRA" not in off.text
PY

pytest tests/test_get_prompt.py
```
Expected: `ImportError: cannot import name 'get_prompt'`

### Step 2 — GREEN: add the entry point (3 min)

```bash
cat > src/promptrecipe/__init__.py <<'PY'
"""promptrecipe — compose prompts from path-addressed fragments.

Invariants enforced throughout this package:
- All I/O is confined to the `custody` subpackage. Everything else is pure.
- Fragment content is never evaluated. It is inert text.
- Assembly is deterministic: identical inputs yield byte-identical output.
- `eval`, `exec`, `compile`, and `__import__` never appear in this package.
"""

from __future__ import annotations

from promptrecipe.assemble import Assembled, Params, assemble
from promptrecipe.errors import PromptRecipeError
from promptrecipe.identity import FragmentId
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

__version__ = "0.1.0"

__all__ = [
    "Assembled",
    "FragmentId",
    "FragmentPath",
    "Params",
    "PromptRecipeError",
    "Resolver",
    "get_prompt",
]


def get_prompt(recipe_path: str, params: Params, resolver: Resolver) -> Assembled:
    """Assemble the prompt a recipe describes.

    This is the product's entire public surface. The caller supplies a recipe
    path and parameters, and receives assembled text — with no need to know
    what a fragment, condition, or version is (FR-038).
    """
    path = FragmentPath.parse(recipe_path)
    source = resolver.read(path)
    return assemble(parse(source.text), params, resolver)
PY

pytest tests/test_get_prompt.py && pytest
```
Expected: `4 passed`, then all suites green.

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "feat: get_prompt entry point

The product's entire public surface. Includes the model-portability
test: two templates sharing a fragment by reference, proven by identity
equality rather than by matching text."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_get_prompt.py
```
