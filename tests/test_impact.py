"""T-021 / T-022 — blast radius before a change, and what it would do.

Two questions with deliberately different costs. Dependents is the one you
ask before EVERY change, so it must assemble nothing; preview assembles on
purpose, because showing how output differs requires producing it. Keeping
them apart is what keeps the cheap one cheap.
"""

from conftest import MemoryCustody

from promptrecipe import Params, dependents, preview_change
from promptrecipe.impact import build_graph
from promptrecipe.resolve import Resolver

LIB = {
    "core/agent.claude": "[load core/role]\n[if premium][load core/extra]\n[load core/safety]",
    "core/agent.gpt": "[load core/role]\n[load core/safety]",
    "core/role": "ROLE",
    "core/extra": "EXTRA",
    "core/safety": "SAFE\n[load core/refusal]",
    "core/refusal": "REFUSE",
    "core/orphan": "NOBODY USES ME",
}


def library(**overrides):
    return Resolver().register("core", "mem", MemoryCustody({**LIB, **overrides}))


# --- T-021: dependents, without assembling ---------------------------------


def test_direct_dependents_are_found():
    assert dependents("core/role", library()) == ["core/agent.claude", "core/agent.gpt"]


def test_dependents_are_transitive():
    """core/refusal is reached only THROUGH core/safety — the recipes never
    name it, and it must still show up."""
    assert dependents("core/refusal", library()) == [
        "core/agent.claude",
        "core/agent.gpt",
        "core/safety",
    ]


def test_a_conditional_reference_still_counts_as_a_dependent():
    """Deliberately pessimistic: the question is about RISK, so a fragment
    that MIGHT load is a fragment that might be affected."""
    assert "core/agent.claude" in dependents("core/extra", library())


def test_a_conditional_edge_is_marked_as_such():
    graph = build_graph(library())
    extra = next(e for e in graph.edges if e.target == "core/extra")
    role = next(e for e in graph.edges if e.target == "core/role")
    assert extra.conditional
    assert not role.conditional


def test_a_fragment_nobody_references_has_no_dependents():
    assert dependents("core/orphan", library()) == []


def test_dependents_assembles_nothing(monkeypatch):
    """FR-011, the load-bearing property: this is the question asked before
    EVERY change, so it must stay cheap. Asserted by making assembly explode
    — a structural check on the source would pass on a docstring."""
    import sys

    import promptrecipe

    def explode(*_args, **_kwargs):
        raise AssertionError("dependents() must not assemble")

    monkeypatch.setattr(promptrecipe, "get_prompt", explode)
    monkeypatch.setattr(promptrecipe, "assemble", explode)
    monkeypatch.setattr(sys.modules["promptrecipe.assemble"], "assemble", explode)

    assert dependents("core/role", library()) == ["core/agent.claude", "core/agent.gpt"]


def test_an_address_variable_reference_is_not_guessed_at():
    """A variable target is only known at call time, so a static graph cannot
    follow it. Skipped rather than guessed."""
    graph = build_graph(library(**{"core/agent.claude": "[load tone_slot]"}))
    assert not [e for e in graph.edges if e.source == "core/agent.claude"]


def test_a_library_mid_edit_still_answers():
    """A broken recipe must not stop a dependency query — you ask this
    question precisely when things are in flux."""
    broken = library(**{"core/agent.gpt": "[load core/role"})  # unterminated
    assert "core/agent.claude" in dependents("core/role", broken)


# --- T-022: preview -------------------------------------------------------


BOUND = Params(controls={"premium": True})


def test_a_preview_shows_how_each_dependent_would_differ():
    previews = preview_change("core/role", "ROLE, REWRITTEN", library(), BOUND)
    changed = {p.path for p in previews if p.changed}
    assert changed == {"core/agent.claude", "core/agent.gpt"}
    assert all("ROLE, REWRITTEN" in p.after for p in previews if p.changed)


def test_a_preview_reaches_transitive_dependents():
    """core/safety is a dependent too — it is a fragment that loads another
    one. Being reachable through it is what makes the query transitive."""
    previews = preview_change("core/refusal", "REFUSE, FIRMLY", library(), BOUND)
    assert {p.path for p in previews if p.changed} == {
        "core/agent.claude",
        "core/agent.gpt",
        "core/safety",
    }


def test_a_dependent_that_cannot_be_assembled_is_reported_not_dropped():
    """Leaving it out would understate the blast radius — the caller asked
    what a change would affect, and this is one the preview could not check."""
    previews = preview_change("core/role", "ROLE, REWRITTEN", library())  # premium unbound
    failed = next(p for p in previews if p.path == "core/agent.claude")
    assert failed.error is not None
    assert not failed.changed


def test_a_preview_does_not_touch_custody():
    """Previewing must not mutate the library — accepting a change is version
    control's job (amendment 7)."""
    resolver = library()
    preview_change("core/role", "MUTATED", resolver, BOUND)
    from promptrecipe.paths import FragmentPath

    assert resolver.read(FragmentPath.parse("core/role")).text == "ROLE"


def test_a_preview_diff_reads_as_a_diff():
    previews = preview_change("core/role", "ROLE, REWRITTEN", library(), BOUND)
    diff = next(p for p in previews if p.changed).diff()
    assert "-ROLE" in diff
    assert "+ROLE, REWRITTEN" in diff


def test_an_unchanged_proposal_reports_no_change():
    previews = preview_change("core/role", "ROLE", library(), BOUND)
    assert previews
    assert not any(p.changed for p in previews)


def test_a_preview_respects_the_conditions_it_is_given():
    off = preview_change("core/extra", "EXTRA, NEW", library(), Params(controls={"premium": False}))
    on = preview_change("core/extra", "EXTRA, NEW", library(), Params(controls={"premium": True}))

    # A fragment behind a false condition cannot change the output.
    assert not any(p.changed for p in off)
    assert any(p.changed for p in on)


def test_a_preview_can_be_scoped_to_named_recipes():
    previews = preview_change(
        "core/role", "ROLE, REWRITTEN", library(), BOUND, recipes=["core/agent.gpt"]
    )
    assert [p.path for p in previews] == ["core/agent.gpt"]


def test_previewing_a_fragment_nobody_uses_returns_nothing():
    assert preview_change("core/orphan", "CHANGED", library()) == []
