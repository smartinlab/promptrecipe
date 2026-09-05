"""Example 2 — the promise: fix one fragment, every recipe using it updates.

python examples/02_change_once.py
"""

from pathlib import Path

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

FRAGMENTS = Path(__file__).parent / "fragments"
SAFETY = FRAGMENTS / "safety.md"


def assemble(recipe: str):
    resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", FRAGMENTS))
    return promptrecipe.get_prompt(recipe, Params(values={"product": "Acme Cloud"}), resolver)


original = SAFETY.read_text()
try:
    before_claude = assemble("core/recipe.claude")
    before_gpt = assemble("core/recipe.gpt")

    shared_before = dict(before_claude.fragments)["core/safety"]
    assert shared_before == dict(before_gpt.fragments)["core/safety"]
    print(f"Both variants share core/safety at {shared_before.short}")

    SAFETY.write_text("Never invent features. Always cite the documentation page.\n")

    after_claude = assemble("core/recipe.claude")
    after_gpt = assemble("core/recipe.gpt")
    shared_after = dict(after_claude.fragments)["core/safety"]
    print(f"After one edit, both share      {shared_after.short}")

    assert "cite the documentation page" in after_claude.text
    assert "cite the documentation page" in after_gpt.text
    assert shared_after != shared_before

    print("\nOne edit. Both model variants updated. No copies to hunt down.")
finally:
    SAFETY.write_text(original)
