"""FR-038: an agent framework consumes the output with zero fragment awareness.

The fake agent is deliberately naive — it accepts a system prompt as a plain
string and nothing else. If the library ever requires a caller to understand
its internal types, these tests fail.
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
    """Stands in for a LangChain/Agno-style agent. It knows only strings."""

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
    result = get_prompt("core/recipe.claude", Params(), resolver())
    assert type(result.text) is str
    assert len(result.text) > 0


def test_switching_models_is_switching_a_recipe_path():
    """Amendment 6 from the consumer's side: the caller changes one string."""
    r = resolver()
    claude = FakeAgent(get_prompt("core/recipe.claude", Params(), r).text)
    gpt = FakeAgent(get_prompt("core/recipe.gpt", Params(), r).text)

    assert "Be concise." in claude.system_prompt
    assert "Be thorough." in gpt.system_prompt
    # The shared fragment is identical in both — one fix corrects both.
    assert "Never invent features." in claude.system_prompt
    assert "Never invent features." in gpt.system_prompt


def test_identity_is_available_but_never_required():
    result = get_prompt("core/recipe.claude", Params(), resolver())
    FakeAgent(result.text)  # basic use never touches the attestation
    assert len(result.attestation.structural_identity) == 64


# The primary path: what a caller needs to assemble a prompt and use it.
# FR-038 lives here — growth in THIS set is how "zero fragment awareness"
# erodes, so it is pinned exactly.
CONSUMPTION_SURFACE = {
    "Assembled",
    "Params",
    "PromptRecipeError",
    "Resolver",
    "get_prompt",
}

# Tooling: capabilities used to ADOPT or INSPECT a library, never needed to
# consume a prompt. Additions here are expected as later phases land, so this
# set is allowed to grow — but only deliberately, by editing this list.
TOOLING_SURFACE = {
    "DecompositionResult",
    "FragmentId",
    "FragmentPath",
    "verify_decomposition",
}


def test_the_consumption_surface_stays_exactly_this_small():
    """FR-038 guard, kept sharp.

    Widening this test whenever something is added would defeat it. The
    consumption set is pinned; new capability belongs in TOOLING_SURFACE and
    has to be added on purpose.
    """
    import promptrecipe

    exported = set(promptrecipe.__all__)
    assert exported & CONSUMPTION_SURFACE == CONSUMPTION_SURFACE
    unexpected = exported - CONSUMPTION_SURFACE - TOOLING_SURFACE
    assert not unexpected, (
        f"new public names {sorted(unexpected)} — if a caller needs them to "
        "assemble a prompt, FR-038 is eroding; if not, list them as tooling"
    )


def test_assembling_a_prompt_needs_only_the_consumption_surface():
    """The stronger form: the primary path must not reach for tooling."""
    result = get_prompt("core/recipe.claude", Params(values={"product": "Acme"}), resolver())
    assert isinstance(result.text, str)
