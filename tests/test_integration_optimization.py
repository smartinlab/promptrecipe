"""The optimization adapter, tested against the real library where installed.

Structure tests run everywhere. Tests that touch dspy skip when it is absent,
because the integration is an optional extra and the core must build and test
without it (Gate 0: both integration targets changed ownership within eight
months, so neither may become load-bearing).
"""

import pytest
from conftest import MemoryCustody

from promptrecipe.integrations.optimization import (
    Proposal,
    is_stale,
    proposal_from_state,
    seed_from_fragment,
)
from promptrecipe.resolve import Resolver

dspy = pytest.importorskip("dspy", reason="optional integration extra")

TONE = "Lead with the answer. Keep it short.\n"


def resolver(text: str = TONE):
    return Resolver().register("core", "mem", MemoryCustody({"core/tone": text}))


def state_with(instructions: str) -> dict:
    """A dspy state dict, built by dspy itself rather than hand-rolled."""
    sig = dspy.Signature("question -> answer", instructions)
    return dspy.Predict(sig).dump_state()


# --- the contract dspy actually offers -------------------------------------


def test_dspy_accepts_a_fragment_as_signature_instructions():
    seed = seed_from_fragment("core/tone", resolver())
    sig = dspy.Signature("question -> answer", seed.instructions)
    assert sig.instructions.strip() == seed.instructions.strip()


def test_the_state_shape_the_write_back_depends_on():
    """Pins what a version bump could break: instructions must stay a plain
    string at signature.instructions."""
    state = state_with("Be concise.")
    assert "signature" in state
    assert isinstance(state["signature"]["instructions"], str)


def test_dspy_strips_trailing_whitespace_and_that_is_idempotent():
    """The normalisation the adapter has to account for. If a dspy release
    ever changes this, this test says so before the adapter misbehaves."""
    once = dspy.Signature("question -> answer", TONE).instructions
    twice = dspy.Signature("question -> answer", once).instructions
    assert once == TONE.strip()
    assert twice == once


# --- the adapter -----------------------------------------------------------


def test_a_round_trip_with_no_optimization_reports_no_change():
    """The false positive this guards: dspy's own stripping is not an edit."""
    seed = seed_from_fragment("core/tone", resolver())
    proposal = proposal_from_state(seed, state_with(seed.instructions))
    assert not proposal.changed, "dspy's normalisation must not read as a change"


def test_a_real_optimization_reports_a_change():
    seed = seed_from_fragment("core/tone", resolver())
    proposal = proposal_from_state(seed, state_with("Answer in one sentence."))
    assert proposal.changed
    assert "Answer in one sentence." in proposal.diff()


def test_accepting_a_proposal_preserves_the_final_newline():
    """Applying the optimizer's text verbatim would delete the file's trailing
    newline — an edit nobody asked for that changes the fragment's identity
    and therefore every assembly using it."""
    seed = seed_from_fragment("core/tone", resolver())
    proposal = proposal_from_state(seed, state_with("Answer in one sentence."))
    assert proposal.to_apply().endswith("\n")
    assert proposal.to_apply() == "Answer in one sentence.\n"


def test_a_fragment_without_a_trailing_newline_does_not_gain_one():
    seed = seed_from_fragment("core/tone", resolver("No newline here"))
    proposal = proposal_from_state(seed, state_with("Rewritten"))
    assert proposal.to_apply() == "Rewritten"


def test_a_proposal_pins_the_version_it_was_seeded_from():
    r = resolver()
    seed = seed_from_fragment("core/tone", r)
    proposal = proposal_from_state(seed, state_with("Rewritten"))

    assert not is_stale(proposal, r)
    # The fragment moves on underneath the proposal.
    moved_on = resolver("Someone edited this in the meantime.\n")
    assert is_stale(proposal, moved_on), (
        "a reviewer must be told the fragment changed since the optimizer "
        "was seeded — accepting silently would discard that edit"
    )


def test_no_whole_recipe_seeding_is_offered():
    """SD11: an optimizer returns one result with no sub-prompt attribution,
    so offering a whole-recipe form would imply an attribution that does not
    exist."""
    from promptrecipe.integrations import optimization

    public = [n for n in dir(optimization) if not n.startswith("_")]
    assert not [n for n in public if "recipe" in n.lower()]


def test_the_proposal_is_never_written_to_custody():
    """Amendment 7: accepting a change is version control's job. A
    machine-authored change goes through the same review as any other."""
    import inspect

    from promptrecipe.integrations import optimization

    source = inspect.getsource(optimization)
    for forbidden in ("write_text", "write_bytes", "open("):
        assert forbidden not in source, "the adapter must not apply a proposal itself"


def test_the_core_does_not_import_the_integration():
    """The core must survive the integration target disappearing."""
    import subprocess
    import sys

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import promptrecipe, sys; print('dspy' in sys.modules)"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "False"


def test_a_proposal_is_a_plain_dataclass():
    p = Proposal(path="core/x", seeded_from="a" * 64, proposed="new", original="old")
    assert p.changed
