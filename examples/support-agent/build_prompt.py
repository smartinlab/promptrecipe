"""End-to-end SDK walkthrough: a real fragment library on disk.

Three namespaces, ten fragments, two model recipes sharing what does not
differ, value variables, control variables driving `[if ...]`, and a nested
reference (core/safety pulls in policy/refusal).

    python examples/support-agent/build_prompt.py
"""

from pathlib import Path

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

PROMPTS = Path(__file__).parent / "prompts"


def build() -> Resolver:
    """One custody per namespace root — how a real library is laid out."""
    return (
        Resolver()
        .register("core", "fs", FsCustody().with_namespace("core", PROMPTS / "core"))
        .register("policy", "fs", FsCustody().with_namespace("policy", PROMPTS / "policy"))
        .register("tools", "fs", FsCustody().with_namespace("tools", PROMPTS / "tools"))
    )


def show(title: str, recipe: str, params: Params, resolver: Resolver) -> None:
    result = promptrecipe.get_prompt(recipe, params, resolver)

    print("=" * 78)
    print(title)
    print("=" * 78)
    print(result.text.rstrip())
    print("-" * 78)
    print(f"{len(result.fragments)} fragments, {len(result.text)} characters")
    for path, fid in result.fragments:
        print(f"    {path:<24} {fid.short}")
    outcomes = result.attestation.condition_outcomes
    print(f"  conditions: {sum(1 for _, o in outcomes if o)}/{len(outcomes)} taken")
    for expr, taken in outcomes:
        print(f"    {'✓' if taken else '✗'} {expr}")
    print(f"  structural {result.attestation.structural_identity[:16]}…  (compare A/B by this)")
    print(f"  instance   {result.attestation.instance_identity[:16]}…  (reproduce from this)")
    print()


def main() -> None:
    resolver = build()

    base = {"agent_name": "Aria", "product": "Acme Cloud"}

    show(
        "1. Free tier, English, no tools — Claude",
        "core/agent.claude",
        Params(
            controls={"tier": "free", "language": "en", "tools_enabled": False},
            values={**base, "tier": "free"},
        ),
        resolver,
    )

    show(
        "2. Enterprise, Portuguese, tools on — Claude",
        "core/agent.claude",
        Params(
            controls={"tier": "enterprise", "language": "pt-br", "tools_enabled": True},
            values={**base, "tier": "enterprise"},
        ),
        resolver,
    )

    show(
        "3. Same context, different model — GPT recipe",
        "core/agent.gpt",
        Params(
            controls={"tier": "enterprise", "language": "pt-br", "tools_enabled": True},
            values={**base, "tier": "enterprise"},
        ),
        resolver,
    )

    # --- what the identities are for -------------------------------------
    ctx = Params(
        controls={"tier": "pro", "language": "en", "tools_enabled": True},
        values={**base, "tier": "pro"},
    )
    other_customer = Params(
        controls=ctx.controls,
        values={**base, "product": "Acme Cloud", "agent_name": "Nova", "tier": "pro"},
    )

    a = promptrecipe.get_prompt("core/agent.claude", ctx, resolver)
    b = promptrecipe.get_prompt("core/agent.claude", other_customer, resolver)
    c = promptrecipe.get_prompt("core/agent.gpt", ctx, resolver)

    print("=" * 78)
    print("What the two identities are for")
    print("=" * 78)
    same_design = a.attestation.structural_identity == b.attestation.structural_identity
    different_text = a.attestation.instance_identity != b.attestation.instance_identity
    different_design = a.attestation.structural_identity != c.attestation.structural_identity

    print("Same recipe, different agent_name (a value variable):")
    print(f"  text differs .............. {a.text != b.text}")
    print(f"  structural identity SAME .. {same_design}   <- comparable as one variant")
    print(f"  instance identity DIFFERS . {different_text}   <- reproducible separately")
    print()
    print("Different recipe (a structural change):")
    print(f"  structural identity DIFFERS {different_design}   <- a different prompt design")
    print()
    shared = set(dict(a.fragments)) & set(dict(c.fragments))
    print(f"Fragments shared by both model recipes: {len(shared)}")
    for path in sorted(shared):
        same = dict(a.fragments)[path] == dict(c.fragments)[path]
        print(f"    {path:<24} same fragment: {same}")
    print()
    print("Fix core/safety once and BOTH model recipes change — it is one")
    print("fragment referenced twice, not two copies.")


if __name__ == "__main__":
    main()
