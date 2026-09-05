"""Assemble a fixed recipe once and print the digest of the result.

Used by the cross-process determinism test. Each run is a fresh process with
a fresh hash seed, so two runs printing the same digest is evidence that no
per-process state reached the output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from conftest import MemoryCustody  # noqa: E402

from promptrecipe import get_prompt  # noqa: E402
from promptrecipe.assemble import Params  # noqa: E402
from promptrecipe.identity import FragmentId  # noqa: E402
from promptrecipe.resolve import Resolver  # noqa: E402

# Many fragments and many bindings: the more there are, the more likely a
# hash-ordered iteration would show up as a different order.
COUNT = 24


def main() -> int:
    entries = {f"core/f{i}": f"FRAGMENT-{i}" for i in range(COUNT)}
    recipe = ["Header {{customer}}\n"]
    recipe += [f"[if flag{i}] [load core/f{i}]\n" for i in range(COUNT)]
    recipe.append("Footer {{customer}}\n")
    entries["core/recipe"] = "".join(recipe)

    resolver = Resolver().register("core", "mem", MemoryCustody(entries))
    params = Params(
        controls={f"flag{i}": (i % 3 != 0) for i in range(COUNT)},
        values={"customer": "Acme Corporation"},
    )

    out = get_prompt("core/recipe", params, resolver)
    print(FragmentId.of(out.text.encode("utf-8")).hex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
