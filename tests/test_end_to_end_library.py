"""End-to-end against a real fragment library on disk.

Three namespaces, ten files, two model recipes, value variables, control
variables driving conditions, and a nested reference (core/safety pulls in
policy/refusal). Everything the unit tests exercise in isolation, assembled
together the way a caller actually uses it.

This is what surfaced the stray-blank-line problem that single-line unit
fixtures could not: a realistic multi-line recipe behaves differently from a
one-liner.
"""

from pathlib import Path

import pytest

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.errors import ExpectationFailed
from promptrecipe.resolve import Resolver

PROMPTS = Path(__file__).resolve().parents[1] / "examples" / "support-agent" / "prompts"


@pytest.fixture
def resolver():
    return (
        Resolver()
        .register("core", "fs", FsCustody().with_namespace("core", PROMPTS / "core"))
        .register("policy", "fs", FsCustody().with_namespace("policy", PROMPTS / "policy"))
        .register("tools", "fs", FsCustody().with_namespace("tools", PROMPTS / "tools"))
    )


def context(**overrides):
    controls = {"tier": "free", "language": "en", "tools_enabled": False, **overrides}
    return Params(
        controls=controls,
        values={"agent_name": "Aria", "product": "Acme Cloud", "tier": controls["tier"]},
    )


def test_the_minimal_context_loads_only_the_unconditional_fragments(resolver):
    out = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    paths = [p for p, _ in out.fragments]
    assert paths == ["core/identity", "core/tone.claude", "core/safety", "policy/refusal"]


def test_every_condition_adds_exactly_its_fragment(resolver):
    out = promptrecipe.get_prompt(
        "core/agent.claude",
        context(tier="enterprise", language="pt-br", tools_enabled=True),
        resolver,
    )
    paths = [p for p, _ in out.fragments]
    assert "policy/pt-br" in paths
    assert "policy/escalation" in paths
    assert "tools/search" in paths
    assert len(out.attestation.condition_outcomes) == 3
    assert all(taken for _, taken in out.attestation.condition_outcomes)


def test_value_variables_reach_fragments_across_namespaces(resolver):
    """`{{product}}` is used in core/identity, core/safety AND policy/refusal —
    a fragment reached only through a nested reference."""
    out = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    assert out.text.count("Acme Cloud") == 3
    assert "{{" not in out.text, "no placeholder may survive substitution"


def test_a_nested_reference_is_followed_and_recorded(resolver):
    """core/safety references policy/refusal; the recipe never mentions it."""
    out = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    assert "refuse plainly" in out.text
    assert "policy/refusal" in [p for p, _ in out.fragments]


def test_an_untaken_condition_leaves_no_blank_line(resolver):
    """The regression the end-to-end run found.

    Checked on the BODY, not the whole string: fragment files each end with a
    newline, so trailing blank lines at the very end are the files' own and
    are harmless. The defect was blank lines appearing mid-prompt where a
    condition had been skipped.
    """
    out = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    assert "\n\n\n" not in out.text.strip(), f"stray blank lines mid-prompt:\n{out.text!r}"


def test_the_two_model_recipes_share_every_fragment_that_does_not_differ(resolver):
    ctx = context(tier="enterprise", language="pt-br", tools_enabled=True)
    claude = promptrecipe.get_prompt("core/agent.claude", ctx, resolver)
    gpt = promptrecipe.get_prompt("core/agent.gpt", ctx, resolver)

    shared = set(dict(claude.fragments)) & set(dict(gpt.fragments))
    assert shared == {
        "core/identity",
        "core/safety",
        "policy/refusal",
        "policy/escalation",
        "policy/pt-br",
        "tools/search",
    }, "everything except the tone fragment is shared between the two models"
    for path in shared:
        assert dict(claude.fragments)[path] == dict(gpt.fragments)[path], (
            f"{path} must be ONE fragment, not a copy per model"
        )
    assert dict(claude.fragments)["core/tone.claude"] != dict(gpt.fragments)["core/tone.gpt"]


def test_a_value_change_keeps_the_structural_identity(resolver):
    """Two customers, same prompt design: comparable as one variant."""
    a = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    b_ctx = context()
    b_ctx.values["agent_name"] = "Nova"
    b = promptrecipe.get_prompt("core/agent.claude", b_ctx, resolver)

    assert a.text != b.text
    assert a.attestation.structural_identity == b.attestation.structural_identity
    assert a.attestation.instance_identity != b.attestation.instance_identity


def test_a_condition_change_changes_the_structural_identity(resolver):
    """A structural change must be visible in the identity used for A/B."""
    free = promptrecipe.get_prompt("core/agent.claude", context(), resolver)
    paid = promptrecipe.get_prompt("core/agent.claude", context(tier="pro"), resolver)
    assert free.attestation.structural_identity != paid.attestation.structural_identity


def test_a_violated_expectation_fails_before_any_output(resolver):
    with pytest.raises(ExpectationFailed) as exc:
        promptrecipe.get_prompt("core/agent.claude", context(tier="platinum"), resolver)
    assert "tier" in str(exc.value)


def test_assembly_is_deterministic_against_the_real_filesystem(resolver):
    """P1 where it matters: real files, real directory iteration."""
    ctx = context(tier="enterprise", language="pt-br", tools_enabled=True)
    first = promptrecipe.get_prompt("core/agent.claude", ctx, resolver)
    second = promptrecipe.get_prompt("core/agent.claude", ctx, resolver)
    assert first.text == second.text
    assert first.attestation.instance_identity == second.attestation.instance_identity


def test_the_walkthrough_script_runs(resolver):
    """The example a reader will actually run must keep working."""
    import subprocess
    import sys

    script = PROMPTS.parent / "build_prompt.py"
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
    assert "structural" in result.stdout
