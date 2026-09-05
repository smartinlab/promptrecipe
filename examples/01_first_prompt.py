"""Example 1 — your first assembled prompt.

python examples/01_first_prompt.py
"""

from pathlib import Path

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

FRAGMENTS = Path(__file__).parent / "fragments"

resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", FRAGMENTS))
result = promptrecipe.get_prompt(
    "core/recipe.claude", Params(values={"product": "Acme Cloud"}), resolver
)

print("--- assembled prompt ---")
print(result.text)
print("--- what produced it ---")
for path, fragment_id in result.fragments:
    print(f"  {path:<24} {fragment_id.short}")

att = result.attestation
print(f"\nstructural identity: {att.structural_identity[:16]}…  (compare A/B by this)")
print(f"instance identity:   {att.instance_identity[:16]}…  (reproduce exact text from this)")
