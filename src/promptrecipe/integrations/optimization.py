"""Seed a prompt optimizer from a fragment, and take its output back as a proposal.

Gate 0 verified the shape this has to take, and its limit:

- A fragment's text can seed a signature's `instructions` — a plain string in,
  a plain string out of the optimizer's saved state. Friction-free.
- An optimizer returns ONE result with no sub-prompt attribution. Seeding from
  a whole assembled recipe therefore yields text that CANNOT be split back
  across the fragments that composed it (SD11).

So this module offers per-fragment seeding only. The API does not expose a
whole-recipe form, because offering one would imply an attribution that does
not exist.

The returned text is a PROPOSAL. It is never written to custody here — under
the delegation in amendment 7, accepting a change is version control's job,
and a machine-authored change goes through the same review as any other.
"""

from __future__ import annotations

from dataclasses import dataclass

from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver


@dataclass(frozen=True, slots=True)
class Seed:
    """A fragment's text, ready to become a signature's instructions."""

    path: str
    identity: str
    instructions: str


@dataclass(frozen=True, slots=True)
class Proposal:
    """Optimizer output, scoped to the fragment it came from.

    `seeded_from` pins the exact fragment version the optimizer started at, so
    a proposal cannot be silently applied to a fragment that has since moved
    on — the reviewer sees what it was based on.

    ## Why trailing whitespace is handled explicitly

    Verified against dspy 3.3.1: a signature STRIPS trailing whitespace from
    its instructions. Two consequences, both of which would be wrong to
    ignore:

    1. A round trip that changed nothing would still report `changed`, because
       the fragment's own trailing newline came back missing. Reviewers would
       be shown a diff with no content in it.
    2. Accepting such a proposal verbatim would delete the file's final
       newline — a real edit nobody asked for, and one that changes the
       fragment's identity and therefore every assembly using it.

    So `changed` compares content ignoring trailing whitespace, and
    `to_apply()` restores the original's trailing whitespace. The optimizer's
    normalisation is treated as what it is: an artefact of the round trip,
    not an authored change.
    """

    path: str
    seeded_from: str
    proposed: str
    original: str

    @property
    def changed(self) -> bool:
        """Did the optimizer actually change the text?

        Compares with trailing whitespace ignored, so the round trip's own
        normalisation is not mistaken for an edit.
        """
        return self.proposed.rstrip() != self.original.rstrip()

    def to_apply(self) -> str:
        """The text to write if this proposal is accepted.

        The optimizer's content, carrying the ORIGINAL's trailing whitespace,
        so accepting never silently deletes a file's final newline.
        """
        trailing = self.original[len(self.original.rstrip()) :]
        return self.proposed.rstrip() + trailing

    def diff(self) -> str:
        import difflib

        return "\n".join(
            difflib.unified_diff(
                self.original.splitlines(),
                self.to_apply().splitlines(),
                fromfile=f"{self.path} (current)",
                tofile=f"{self.path} (proposed)",
                lineterm="",
            )
        )


def seed_from_fragment(path: str, resolver: Resolver) -> Seed:
    """Read one fragment and present it as optimizer instructions."""
    fragment_path = FragmentPath.parse(path)
    content = resolver.read(fragment_path)
    return Seed(path=str(fragment_path), identity=content.id.hex, instructions=content.text)


def proposal_from_state(seed: Seed, state: dict, predictor: str | None = None) -> Proposal:
    """Extract optimized instruction text from an optimizer's saved state.

    Accepts the state dict a compiled program serialises to. The instructions
    live at `signature.instructions`, either at the top level (a single
    predictor) or nested under a named predictor.
    """
    node = state
    if predictor is not None:
        node = state[predictor]
    elif "signature" not in node:
        # A module's state maps predictor name -> predictor state.
        named = [v for v in state.values() if isinstance(v, dict) and "signature" in v]
        if len(named) != 1:
            raise ValueError(f"state holds {len(named)} predictors; name one with predictor=...")
        node = named[0]

    proposed = node["signature"]["instructions"]
    return Proposal(
        path=seed.path,
        seeded_from=seed.identity,
        proposed=proposed,
        original=seed.instructions,
    )


def is_stale(proposal: Proposal, resolver: Resolver) -> bool:
    """Has the fragment changed since the optimizer was seeded?

    A proposal built on a version that has since moved on is not necessarily
    wrong, but a reviewer must be told — accepting it would silently discard
    whatever changed in between.
    """
    current = resolver.read(FragmentPath.parse(proposal.path)).id
    return current != FragmentId(proposal.seeded_from)
