"""promptrecipe — compose prompts from path-addressed fragments.

Invariants enforced throughout this package:
- All I/O is confined to the `custody` subpackage. Everything else is pure.
- Fragment content is never evaluated. It is inert text.
- Assembly is deterministic: identical inputs yield byte-identical output.
- Dynamic execution never appears in this package (enforced by an AST test).
"""

from __future__ import annotations

from promptrecipe.assemble import Assembled, Params, assemble
from promptrecipe.errors import PromptRecipeError
from promptrecipe.identity import FragmentId
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

__version__ = "0.1.0"

__all__ = [
    "Assembled",
    "FragmentId",
    "FragmentPath",
    "Params",
    "PromptRecipeError",
    "Resolver",
    "get_prompt",
]


def get_prompt(recipe_path: str, params: Params, resolver: Resolver) -> Assembled:
    """Assemble the prompt a recipe describes.

    This is the product's entire public surface. The caller supplies a recipe
    path and parameters, and receives assembled text — with no need to know
    what a fragment, condition, or version is (FR-038).
    """
    path = FragmentPath.parse(recipe_path)
    source = resolver.read(path)
    return assemble(parse(source.text), params, resolver)
