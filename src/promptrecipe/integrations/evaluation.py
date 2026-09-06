"""Expose recipes and fragments to an evaluation tool.

Gate 0 verified the two seams this needs:

- A **prompt function**: the tool calls a Python callable with `{vars, ...}`
  and takes back a string. That is the native, lowest-friction way to make a
  recipe an evaluable unit.
- **Assertions receive the rendered prompt**, so a recipe or a single
  fragment can be asserted on as TEXT, with no model call at all when paired
  with a pass-through provider.

Both are exposed here as plain callables, so this module works whether or not
the evaluation tool is installed — and the core never imports it either way.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from promptrecipe import get_prompt
from promptrecipe.assemble import Params, Value
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

# Variables arrive from an evaluation harness as one flat dict. These prefixes
# say which of the three roles each belongs to (amendment 9), because the
# distinction is not cosmetic: controls and addresses decide STRUCTURE while
# values only fill CONTENT, and a harness that conflated them could let test
# data change which fragments load.
CONTROL_PREFIX = "c_"
ADDRESS_PREFIX = "a_"


def params_from_vars(variables: dict[str, Any]) -> Params:
    """Split a harness's flat variable dict into the three roles."""
    controls: dict[str, Value] = {}
    addresses: dict[str, str] = {}
    values: dict[str, str] = {}

    for key, raw in variables.items():
        if key.startswith(CONTROL_PREFIX):
            controls[key[len(CONTROL_PREFIX) :]] = raw
        elif key.startswith(ADDRESS_PREFIX):
            addresses[key[len(ADDRESS_PREFIX) :]] = str(raw)
        else:
            values[key] = str(raw)

    return Params(controls=controls, addresses=addresses, values=values)


def recipe_prompt_function(recipe_path: str, resolver: Resolver) -> Callable[..., str]:
    """A prompt function that renders a whole recipe (FR-024).

    Returns a plain string, which is what an evaluation harness expects. The
    assembly identity is available to the caller through `get_prompt` — it is
    deliberately not smuggled into the prompt text, which would change what
    is being evaluated.
    """

    def render(context: dict[str, Any] | None = None, **_: Any) -> str:
        variables = (context or {}).get("vars", {})
        return get_prompt(recipe_path, params_from_vars(variables), resolver).text

    return render


def fragment_prompt_function(fragment_path: str, resolver: Resolver) -> Callable[..., str]:
    """A prompt function that renders ONE fragment (FR-025, SD14).

    A fragment and a whole recipe are distinct evaluation targets: fragment
    level catches a bad primitive, recipe level catches bad composition, and
    neither substitutes for the other.

    Value substitution still applies, because a fragment's placeholders are
    content. Nothing else in the fragment is interpreted.
    """
    path = FragmentPath.parse(fragment_path)

    def render(context: dict[str, Any] | None = None, **_: Any) -> str:
        from promptrecipe.assemble import _substitute

        variables = (context or {}).get("vars", {})
        params = params_from_vars(variables)
        text, _edits = _substitute(resolver.read(path).text, params.values)
        return text

    return render


def passthrough_provider(prompt: str, *_: Any, **__: Any) -> dict[str, str]:
    """A provider that returns the prompt instead of calling a model.

    This is what makes fragment-level and recipe-level text assertions cost
    ZERO model execution (FR-025). It is also the honest boundary: SD10 says
    this library produces prompts and never executes them, so the only
    "provider" it ships is one that executes nothing.
    """
    return {"output": prompt}
