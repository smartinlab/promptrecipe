"""The gap that let a real defect ship green.

`tests/test_resolution_never_shadows.py` exercises `Resolver.resolve()`
exclusively. Nothing exercised `Resolver.read()` or `get_prompt()` under an
ambiguous multi-source configuration — so a first-match-wins `read()` passed
a suite whose name promised the opposite.

The recipe path is fetched by `get_prompt` and is exactly the kind of layered
reference (base library + project override) ADR-004 was written to protect.
"""

import pytest
from conftest import MemoryCustody

from promptrecipe import get_prompt
from promptrecipe.assemble import Params
from promptrecipe.errors import AmbiguousReference
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


def two_sources_for_the_same_recipe() -> Resolver:
    return (
        Resolver()
        .register("core", "alpha", MemoryCustody({"core/recipe": "ALPHA VERSION"}))
        .register("core", "beta", MemoryCustody({"core/recipe": "BETA VERSION"}))
    )


def test_get_prompt_refuses_an_ambiguous_recipe_path():
    with pytest.raises(AmbiguousReference) as exc:
        get_prompt("core/recipe", Params(), two_sources_for_the_same_recipe())
    msg = str(exc.value)
    assert "alpha" in msg and "beta" in msg


def test_resolver_read_refuses_an_ambiguous_path():
    with pytest.raises(AmbiguousReference):
        two_sources_for_the_same_recipe().read(FragmentPath.parse("core/recipe"))


def test_an_ambiguous_fragment_inside_a_recipe_also_refuses():
    r = (
        Resolver()
        .register("core", "only", MemoryCustody({"core/recipe": "[load core/tone]"}))
        .register("core", "alpha", MemoryCustody({"core/tone": "A"}))
        .register("core", "beta", MemoryCustody({"core/tone": "B"}))
    )
    with pytest.raises(AmbiguousReference):
        get_prompt("core/recipe", Params(), r)


def test_a_single_source_still_works():
    r = Resolver().register("core", "only", MemoryCustody({"core/recipe": "FINE"}))
    assert get_prompt("core/recipe", Params(), r).text == "FINE"
