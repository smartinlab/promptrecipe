"""Every failure path in the library (TRD §7).

Two rules hold everywhere:
1. A message names what failed, what was expected, and what was supplied.
2. No failure path emits partial output. There is no "warn and continue".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Position:
    """A position in recipe source text."""

    line: int
    column: int

    def __str__(self) -> str:
        return f"line {self.line}, column {self.column}"


class PromptRecipeError(Exception):
    """Base for every failure this library raises.

    Callers catch this one type rather than enumerating variants.
    """


@dataclass(slots=True)
class FragmentNotFound(PromptRecipeError):
    path: str
    namespaces: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        where = ", ".join(self.namespaces) or "<none registered>"
        return f"fragment not found at path '{self.path}' (searched namespaces: {where})"


@dataclass(slots=True)
class AmbiguousReference(PromptRecipeError):
    path: str
    candidates: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.candidates) or "<none>"
        return (
            f"reference '{self.path}' is ambiguous — {len(self.candidates)} candidates "
            f"matched: {listed}. Resolution never picks silently; disambiguate the reference."
        )


@dataclass(slots=True)
class PathEscapesNamespace(PromptRecipeError):
    path: str
    root: str

    def __str__(self) -> str:
        return f"path '{self.path}' escapes its namespace root '{self.root}'"


@dataclass(slots=True)
class UnknownNamespace(PromptRecipeError):
    namespace: str
    path: str
    known: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.known) or "<none registered>"
        return f"unknown namespace '{self.namespace}' in path '{self.path}' (known: {listed})"


@dataclass(slots=True)
class ExpectationFailed(PromptRecipeError):
    position: Position
    expected: str
    actual: str

    def __str__(self) -> str:
        return f"expectation failed at {self.position}: expected {self.expected}, but {self.actual}"


@dataclass(slots=True)
class CyclicInclusion(PromptRecipeError):
    cycle: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return f"cyclic fragment inclusion: {' -> '.join(self.cycle)}"


@dataclass(slots=True)
class DepthLimitExceeded(PromptRecipeError):
    limit: int
    path: str

    def __str__(self) -> str:
        return f"inclusion depth limit of {self.limit} exceeded at path '{self.path}'"


@dataclass(slots=True)
class ParseError(PromptRecipeError):
    position: Position
    expected: str
    found: str

    def __str__(self) -> str:
        return f"parse error at {self.position}: expected {self.expected}, found '{self.found}'"


@dataclass(slots=True)
class IdentityMismatch(PromptRecipeError):
    path: str
    expected: str
    found: str

    def __str__(self) -> str:
        return (
            f"content at '{self.path}' does not match its pinned identity "
            f"(expected {self.expected}, found {self.found}) — refusing to substitute"
        )


@dataclass(slots=True)
class UndefinedVariable(PromptRecipeError):
    name: str
    bound: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(sorted(self.bound)) or "<none>"
        return f"undefined variable '{self.name}' (bound variables: {listed})"


@dataclass(slots=True)
class AmbiguousOrder(PromptRecipeError):
    """More than one order declaration was reachable in one assembly."""

    declarations: list[list[str]] = field(default_factory=list)

    def __str__(self) -> str:
        listed = " | ".join(", ".join(d) for d in self.declarations)
        return (
            f"{len(self.declarations)} order declarations are active at once: {listed}. "
            "The recipe does not say what the order is; gate each declaration so "
            "exactly one applies."
        )


@dataclass(slots=True)
class UnknownOrderName(PromptRecipeError):
    """An order names a slot that no loaded fragment fills."""

    name: str
    available: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.available) or "<none loaded>"
        return (
            f"order names '{self.name}', but no loaded fragment fills that slot "
            f"(loaded slots: {listed}). A slot is a fragment's leaf name up to "
            "its first dot, so 'core/tone.claude' fills the slot 'tone'."
        )


@dataclass(slots=True)
class UnorderedFragment(PromptRecipeError):
    """A fragment loaded but the declared order never mentions its slot."""

    slots: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        listed = ", ".join(self.slots)
        return (
            f"these slots were loaded but the order does not mention them: {listed}. "
            "Once an order is declared it must account for every loaded fragment, "
            "or the unmentioned ones have no defined position."
        )


@dataclass(slots=True)
class UndecodableFragment(PromptRecipeError):
    """Fragment bytes are not valid UTF-8.

    Wrapped rather than allowed to surface as UnicodeDecodeError, so the
    documented `except PromptRecipeError` really does catch every failure.
    """

    identity: str
    reason: str

    def __str__(self) -> str:
        return f"fragment {self.identity} is not valid UTF-8: {self.reason}"


@dataclass(slots=True)
class FragmentDirectiveNotAllowed(PromptRecipeError):
    """Fragment text contains a directive other than a qualified reference.

    A fragment may name a sibling with `[load namespace/path]`. It may not
    branch, order, or assert — those decide STRUCTURE, and fragment content is
    untrusted (it may be optimizer-written or remotely fetched).

    Rejected rather than left literal: `[if x] [load y]` would otherwise load
    unconditionally while looking conditional, which is the silently-wrong
    output this library refuses everywhere else.
    """

    path: str
    directive: str
    excerpt: str = ""

    def __str__(self) -> str:
        return (
            f"fragment '{self.path}' contains a '[{self.directive} ...]' directive "
            f"near {self.excerpt!r}. A fragment may reference a sibling with "
            "[load namespace/path] and nothing else — conditions, ordering and "
            "expectations belong in the recipe, not in fragment content."
        )
