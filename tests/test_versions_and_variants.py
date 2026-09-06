"""T-013/T-014/T-015 — coexisting versions, selected by condition.

Amendment 3 settled this: version and variant selection is ORDINARY
CONDITIONAL LOADING, not a separate subsystem (SD4). These tests hold that
claim to account — if a dedicated experimentation mechanism ever appears,
they are what says it was not needed.

`Custody.versions()` deliberately stays unused here. Under filesystem custody
a version is a distinct PATH, which is what makes coexistence work without any
new machinery; historical versions of one path belong to the consuming
project's git, not to this library. The port keeps the operation for a backend
that genuinely holds several versions at one address, such as an object store
with versioning turned on.
"""

from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params, slot_of
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

LIBRARY = {
    "core/role": "ROLE",
    "core/safety": "SAFETY",
    "core/tone.v1": "TONE-ONE",
    "core/tone.v2": "TONE-TWO",
    "core/tone.claude": "TONE-CLAUDE",
    "core/tone.gpt": "TONE-GPT",
}

VERSIONED = (
    "[load core/role]"
    '[if version == "v1"][load core/tone.v1]'
    '[if version == "v2"][load core/tone.v2]'
    "[load core/safety]"
)


def run(recipe: str, **controls):
    entries = {**LIBRARY, "core/r": recipe}
    r = Resolver().register("core", "mem", MemoryCustody(entries))
    return get_prompt("core/r", Params(controls=controls), r)


# --- T-013: versions coexist -----------------------------------------------


def test_two_versions_are_both_addressable_at_the_same_time():
    """Coexistence, not replacement: adding v2 does not remove v1."""
    assert run(VERSIONED, version="v1").text == "ROLETONE-ONESAFETY"
    assert run(VERSIONED, version="v2").text == "ROLETONE-TWOSAFETY"


def test_both_versions_fill_the_same_slot():
    assert slot_of(FragmentPath.parse("core/tone.v1")) == "tone"
    assert slot_of(FragmentPath.parse("core/tone.v2")) == "tone"


def test_changing_a_shared_fragment_reaches_every_version():
    """FR-007 across versions: the shared parts are shared, not copied."""
    a = run(VERSIONED, version="v1")
    b = run(VERSIONED, version="v2")
    shared_a = dict(a.fragments)["core/role"]
    shared_b = dict(b.fragments)["core/role"]
    assert shared_a == shared_b, "role must be ONE fragment across both versions"


# --- T-014: selection is ordinary conditional loading -----------------------


def test_selection_needs_no_dedicated_mechanism():
    """SD4: the same [if ...] that gates any load gates a version."""
    import inspect

    from promptrecipe import assemble

    source = inspect.getsource(assemble)
    for invented in ("class Experiment", "def select_version", "def choose_variant"):
        assert invented not in source, (
            f"'{invented}' suggests a parallel selection subsystem; amendment 3 "
            "says version selection is conditional loading and nothing more"
        )


def test_the_selected_version_appears_in_provenance():
    out = run(VERSIONED, version="v2")
    paths = [p for p, _ in out.fragments]
    assert "core/tone.v2" in paths
    assert "core/tone.v1" not in paths


def test_two_versions_have_different_structural_identities():
    """M12: an A/B result must attribute to exactly one version."""
    a = run(VERSIONED, version="v1")
    b = run(VERSIONED, version="v2")
    assert a.attestation.structural_identity != b.attestation.structural_identity


def test_selecting_no_version_loads_neither():
    out = run(VERSIONED, version="v3")
    assert out.text == "ROLESAFETY"


# --- T-015: model variants share fragments by reference ---------------------


def test_two_model_recipes_share_the_fragments_that_do_not_differ():
    """The driving use case, at library level rather than through examples."""
    entries = {
        **LIBRARY,
        "core/r.claude": "[load core/role][load core/tone.claude][load core/safety]",
        "core/r.gpt": "[load core/role][load core/tone.gpt][load core/safety]",
    }
    r = Resolver().register("core", "mem", MemoryCustody(entries))

    claude = get_prompt("core/r.claude", Params(), r)
    gpt = get_prompt("core/r.gpt", Params(), r)

    for shared in ("core/role", "core/safety"):
        assert dict(claude.fragments)[shared] == dict(gpt.fragments)[shared], (
            f"{shared} must be one fragment, not a copy per model"
        )

    assert dict(claude.fragments)["core/tone.claude"] != dict(gpt.fragments)["core/tone.gpt"]
    assert claude.text != gpt.text


def test_one_recipe_can_also_cover_both_models_by_condition():
    """Amendment 8 privileges separate templates, but does not forbid the
    conditional form — FR-037 says neither is privileged in the API."""
    recipe = (
        "[load core/role]"
        '[if model == "claude"][load core/tone.claude]'
        '[if model == "gpt"][load core/tone.gpt]'
    )
    assert run(recipe, model="claude").text == "ROLETONE-CLAUDE"
    assert run(recipe, model="gpt").text == "ROLETONE-GPT"
