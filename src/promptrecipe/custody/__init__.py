"""Custody — the only I/O boundary in this package (ADR-001).

Everything above this subpackage is a pure function over what custody
returned. That purity is what makes determinism (TRD §4) structural rather
than a discipline someone has to remember.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from promptrecipe.errors import UndecodableFragment
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@dataclass(frozen=True, slots=True)
class FragmentContent:
    """A fragment's bytes together with its content-derived identity."""

    id: FragmentId
    data: bytes

    @classmethod
    def of(cls, data: bytes) -> FragmentContent:
        return cls(id=FragmentId.of(data), data=data)

    @property
    def text(self) -> str:
        """The content as text.

        Fragment content is INERT TEXT. It is never parsed or evaluated
        (ADR-003) — this property exists to insert it, not to interpret it.

        A decode failure is wrapped: errors.py promises callers catch one
        type, and a bare UnicodeDecodeError escapes that contract.
        """
        try:
            return self.data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise UndecodableFragment(identity=self.id.short, reason=str(exc)) from exc


@runtime_checkable
class Custody(Protocol):
    """The narrow custody port. Three operations, so adapters stay thin.

    There is no `versions()`. Custody is the consuming project's repository
    and nothing else, so a path holds exactly one fragment and history is that
    repository's `git log` — an operation every adapter answered identically
    was a seam reserved for a backend that no longer exists.
    """

    def exists(self, path: FragmentPath) -> bool: ...
    def read(self, path: FragmentPath) -> FragmentContent: ...
    def list(self, namespace: str) -> list[FragmentPath]: ...
