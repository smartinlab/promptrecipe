"""Rebuild an assembly from its provenance record (FR-003, T-018).

The point of recording provenance is that a result can be traced back to the
exact prompt that earned it, weeks later. That claim is only worth something
if the rebuild is verified rather than assumed — so this module reassembles
from the record and CHECKS the output against the recorded subject digest.

If anything the record depends on has moved — the recipe, a fragment — it
fails and says which. It never substitutes a different version to make the
rebuild succeed: a reproduction that quietly used newer content would be
worse than no reproduction at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from promptrecipe.assemble import Assembled, Params, assemble
from promptrecipe.errors import IdentityMismatch, PromptRecipeError
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.provenance import Attestation
from promptrecipe.resolve import Resolver


@dataclass(slots=True)
class IrreproducibleAssembly(PromptRecipeError):
    """The record cannot be rebuilt as it stands."""

    recipe_path: str
    reason: str
    drifted: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        moved = f" (changed since: {', '.join(self.drifted)})" if self.drifted else ""
        return f"cannot reproduce '{self.recipe_path}': {self.reason}{moved}"


def drift(attestation: Attestation, resolver: Resolver) -> list[str]:
    """Which recorded inputs no longer match what custody holds.

    Answers "can this still be reproduced?" without doing the work, and names
    what moved so a reader knows whether the difference matters.
    """
    moved: list[str] = []

    if attestation.recipe_path:
        try:
            current = resolver.read(FragmentPath.parse(attestation.recipe_path)).id.hex
            if current != attestation.recipe_identity:
                moved.append(attestation.recipe_path)
        except PromptRecipeError:
            moved.append(f"{attestation.recipe_path} (gone)")

    for dependency in attestation.resolved_dependencies:
        try:
            current = resolver.read(FragmentPath.parse(dependency.path)).id.hex
            if current != dependency.identity:
                moved.append(dependency.path)
        except PromptRecipeError:
            moved.append(f"{dependency.path} (gone)")

    return moved


def params_from(attestation: Attestation) -> Params:
    """Rebuild the exact inputs the assembly ran with."""
    return Params(
        controls=dict(attestation.control_bindings),
        addresses=dict(attestation.address_resolutions),
        values=dict(attestation.value_bindings),
    )


def reproduce(attestation: Attestation, resolver: Resolver) -> Assembled:
    """Reassemble from a record, byte-identically, or fail saying why.

    The output is verified against the recorded subject digest. A rebuild that
    differs is reported as a mismatch rather than returned — the caller asked
    for *that* prompt, not for whatever the library produces today.
    """
    if not attestation.recipe_path:
        raise IrreproducibleAssembly(
            recipe_path="<unrecorded>",
            reason="the record predates recipe tracking, so nothing names what to rebuild",
        )

    moved = drift(attestation, resolver)
    if moved:
        raise IrreproducibleAssembly(
            recipe_path=attestation.recipe_path,
            reason="inputs have changed since it was recorded",
            drifted=moved,
        )

    path = FragmentPath.parse(attestation.recipe_path)
    source = resolver.read(path)
    rebuilt = assemble(
        parse(source.text),
        params_from(attestation),
        resolver,
        recipe_path=str(path),
        recipe_identity=source.id.hex,
    )

    if rebuilt.attestation.subject != attestation.subject:
        # Every input matched but the output did not: the library itself
        # changed. Saying so is more useful than returning different text.
        raise IdentityMismatch(
            path=attestation.recipe_path,
            expected=attestation.subject,
            found=rebuilt.attestation.subject,
        )

    return rebuilt


def binds_to(attestation: Attestation, result_identity: str) -> bool:
    """Does an externally-produced result belong to this assembly? (T-020)

    Compare by STRUCTURAL identity: an evaluation result belongs to a prompt
    DESIGN, and two runs for two customers are the same design. Comparing by
    instance identity makes every call unique and groups nothing — the most
    likely misuse of the pair, so it gets a named function rather than being
    left to the caller to get right.
    """
    return attestation.structural_identity == result_identity
