"""Execute QUICKSTART.md end to end from an empty directory, and time it.

Enforces metric M11 (FR-028): a new user must reach a working assembled
prompt in under 30 minutes. Scripted time is a floor, not a simulation of a
human — but if the SCRIPTED path exceeds the budget, the human path has no
chance. Exits non-zero over budget so CI fails.

Requires no remote custody, no evaluation tooling, no optimization tooling.
"""

from __future__ import annotations

import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

BUDGET_SECONDS = 30 * 60


def main() -> int:
    print("Quickstart walkthrough — budget 30 minutes\n")
    overall = time.monotonic()

    def step(name: str, fn: Callable[[], None]) -> None:
        start = time.monotonic()
        fn()
        print(f"  [{time.monotonic() - start:6.2f}s] {name}")

    workdir = Path(tempfile.mkdtemp(prefix="promptrecipe-quickstart-"))
    prompts = workdir / "prompts"
    captured: dict[str, object] = {}

    def write_fragments() -> None:
        prompts.mkdir(parents=True)
        (prompts / "role.md").write_text("You are a technical support assistant for {{product}}.\n")
        (prompts / "tone.md").write_text("Be concise. Lead with the answer.\n")

    step("write two fragments", write_fragments)

    def write_recipe() -> None:
        (prompts / "recipe.md").write_text("[load core/role]\n[load core/tone]\n")

    step("write a recipe", write_recipe)

    def assemble() -> None:
        import promptrecipe
        from promptrecipe.assemble import Params
        from promptrecipe.custody.fs import FsCustody
        from promptrecipe.resolve import Resolver

        resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", prompts))
        captured["result"] = promptrecipe.get_prompt(
            "core/recipe", Params(values={"product": "Acme Cloud"}), resolver
        )

    step("assemble the prompt", assemble)

    result = captured["result"]
    assert "Acme Cloud" in result.text, "the value variable must be substituted"
    assert "Be concise." in result.text, "the second fragment must be present"
    assert len(result.fragments) == 2, f"expected 2 fragments, got {len(result.fragments)}"
    assert len(result.attestation.structural_identity) == 64

    def change_once() -> None:
        import promptrecipe
        from promptrecipe.assemble import Params
        from promptrecipe.custody.fs import FsCustody
        from promptrecipe.resolve import Resolver

        (prompts / "tone.md").write_text("Be thorough. Show your reasoning.\n")
        resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", prompts))
        again = promptrecipe.get_prompt(
            "core/recipe", Params(values={"product": "Acme Cloud"}), resolver
        )
        assert "Show your reasoning." in again.text, "the edit must propagate"
        assert again.attestation.structural_identity != result.attestation.structural_identity

    step("change one fragment and see it propagate", change_once)

    total = time.monotonic() - overall
    print(f"\nTotal scripted time: {total:.2f}s  (budget {BUDGET_SECONDS}s)")

    if total > BUDGET_SECONDS:
        print(
            f"\nFAIL: the quickstart took {total:.0f}s, over the {BUDGET_SECONDS}s budget.\n"
            "Metric M11 is a survival metric: the real competitor is copy-paste at\n"
            "zero switching cost, and nobody arrives holding 200 prompts. A product\n"
            "that only wins at scale never reaches scale. Do not raise the budget —\n"
            "shorten the path.",
            file=sys.stderr,
        )
        return 1

    print("PASS: first value is reachable within budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
