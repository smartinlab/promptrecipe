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
