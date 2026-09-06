# ST-007-02: Zero fragment awareness — agent-framework consumption proof

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Prove FR-038: a caller drops `get_prompt` into an agent **without knowing what a fragment, recipe, condition, or version is**.

**Why this is a real task and not a formality.** FR-038 is the requirement most easily eroded by convenience — exposing an internal object "just for debugging" quietly starts requiring callers to understand fragments. This test makes that erosion fail the build.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 123 passed
```

**Files** — Create: `tests/test_agent_consumption.py`

---

### Step 1 — Write the consumption proof (5 min)

```bash
cat > tests/test_agent_consumption.py <<'PY'
"""FR-038: an agent framework consumes the output with zero fragment awareness.

The fake agent below is deliberately naive — it accepts a system prompt as a
plain string and nothing else. If the library ever requires a caller to
understand its internal types, this stops compiling conceptually and these
tests fail.
"""

from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/recipe.claude": "[load core/role]\n[load core/tone.claude]\n[load core/safety]",
    "core/recipe.gpt": "[load core/role]\n[load core/tone.gpt]\n[load core/safety]",
    "core/role": "You are a support assistant for {{product}}.",
    "core/tone.claude": "Be concise.",
    "core/tone.gpt": "Be thorough.",
    "core/safety": "Never invent features.",
}


class FakeAgent:
    """Stands in for a LangChain/Agno-style agent.

    It knows only about strings. It has no idea fragments exist.
    """

    def __init__(self, system_prompt: str) -> None:
        if not isinstance(system_prompt, str):
            raise TypeError("an agent framework accepts a plain string")
        self.system_prompt = system_prompt

    def run(self, user_message: str) -> str:
        return f"[system: {len(self.system_prompt)} chars] {user_message}"


def resolver() -> Resolver:
    return Resolver().register("core", "mem", MemoryCustody(LIBRARY))


def test_an_agent_accepts_the_output_as_a_plain_string():
    result = get_prompt("core/recipe.claude", Params(values={"product": "Acme"}), resolver())
    agent = FakeAgent(result.text)
    assert "Acme" in agent.system_prompt
    assert agent.run("hello").startswith("[system:")


def test_the_caller_needs_no_library_type_to_use_the_output():
    """The primary path must be reachable with builtins only."""
    result = get_prompt("core/recipe.claude", Params(), resolver())
    assert type(result.text) is str
    assert isinstance(result.text, str) and len(result.text) > 0


def test_switching_models_is_switching_a_recipe_path():
    """Amendment 6, from the consumer's side: the caller changes one string."""
    r = resolver()
    claude_agent = FakeAgent(get_prompt("core/recipe.claude", Params(), r).text)
    gpt_agent = FakeAgent(get_prompt("core/recipe.gpt", Params(), r).text)

    assert "Be concise." in claude_agent.system_prompt
    assert "Be thorough." in gpt_agent.system_prompt
    # The shared fragment is identical in both — one fix corrects both.
    assert "Never invent features." in claude_agent.system_prompt
    assert "Never invent features." in gpt_agent.system_prompt


def test_identity_is_available_but_never_required():
    """Provenance travels alongside the prompt; basic use ignores it entirely."""
    result = get_prompt("core/recipe.claude", Params(), resolver())

    FakeAgent(result.text)  # basic use: never touches the attestation

    assert len(result.attestation.structural_identity) == 64
    assert len(result.attestation.instance_identity) == 64


def test_the_public_surface_stays_small():
    """FR-038 guard: the top-level namespace must not sprawl.

    Growth here is how 'zero fragment awareness' quietly becomes 'read the
    internals first'.
    """
    import promptrecipe

    assert set(promptrecipe.__all__) == {
        "Assembled",
        "FragmentId",
        "FragmentPath",
        "Params",
        "PromptRecipeError",
        "Resolver",
        "get_prompt",
    }
PY

pytest tests/test_agent_consumption.py
```
Expected: `5 passed`

### Step 2 — Run the full suite (1 min)

```bash
pytest
```
Expected: all green.

### Step 3 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test: agent-framework consumption with zero fragment awareness

FR-038. A deliberately naive fake agent accepts only a string, so any
future requirement that callers understand internal types fails this
suite. Includes a guard on the size of the public surface — growth
there is how zero-awareness quietly erodes."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_agent_consumption.py
```

---

## T-007 Definition of Done

- [ ] A `py3-none-any` wheel builds — **one artefact, every platform, no compiler**
- [ ] Wheel declares **exactly one runtime dependency** and the 3.11 floor, both asserted
- [ ] Tests and scripts stay out of the artefact
- [ ] CI installs the wheel into a clean environment and imports **from outside the source tree**
- [ ] **An agent framework consumes the output knowing only about strings** (FR-038)
- [ ] The public surface is asserted small
