"""promptrecipe — compose prompts from path-addressed fragments.

Invariants enforced throughout this package:
- All I/O is confined to the `custody` subpackage. Everything else is pure.
- Fragment content is never evaluated. It is inert text.
- Assembly is deterministic: identical inputs yield byte-identical output.
- Dynamic execution never appears in this package (enforced by an AST test).
"""

from __future__ import annotations

from dataclasses import dataclass

from promptrecipe.assemble import Assembled, Params, assemble
from promptrecipe.config import LibraryConfig, load_config, resolver_from_config
from promptrecipe.errors import PromptRecipeError
from promptrecipe.identity import FragmentId
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.provenance import PRODUCER_VERSION
from promptrecipe.resolve import Resolver

# One source of truth: the attestation's producer version and the package
# version cannot drift apart across a release bump.
__version__ = PRODUCER_VERSION

__all__ = [
    "Assembled",
    "DecompositionResult",
    "LibraryConfig",
    "FragmentId",
    "FragmentPath",
    "Params",
    "PromptRecipeError",
    "Resolver",
    "get_prompt",
    "load_config",
    "resolver_from_config",
    "verify_decomposition",
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


@dataclass(frozen=True, slots=True)
class DecompositionResult:
    """Whether a decomposition reproduces the original prompt exactly."""

    identical: bool
    original_length: int
    assembled_length: int
    first_difference: int | None = None
    original_excerpt: str = ""
    assembled_excerpt: str = ""

    def __str__(self) -> str:
        if self.identical:
            return f"identical ({self.original_length} characters)"
        return (
            f"differs at character {self.first_difference}: "
            f"original {self.original_excerpt!r} vs assembled {self.assembled_excerpt!r} "
            f"(lengths {self.original_length} vs {self.assembled_length})"
        )


def verify_decomposition(
    original: str, recipe_path: str, params: Params, resolver: Resolver
) -> DecompositionResult:
    """Check that a decomposition assembles back to the original, byte for byte.

    The adoption path for an existing prompt (FR-035): extract one fragment,
    verify nothing changed, repeat. Byte-identity is unforgiving — prompt text
    is full of significant whitespace — which is exactly why the check has to
    be mechanical rather than eyeballed, and why any difference is reported
    with its position instead of a bare False.
    """
    assembled = get_prompt(recipe_path, params, resolver).text
    if assembled == original:
        return DecompositionResult(
            identical=True,
            original_length=len(original),
            assembled_length=len(assembled),
        )

    at = next(
        (i for i, (a, b) in enumerate(zip(original, assembled, strict=False)) if a != b),
        min(len(original), len(assembled)),
    )
    window = 20
    return DecompositionResult(
        identical=False,
        original_length=len(original),
        assembled_length=len(assembled),
        first_difference=at,
        original_excerpt=original[at : at + window],
        assembled_excerpt=assembled[at : at + window],
    )
