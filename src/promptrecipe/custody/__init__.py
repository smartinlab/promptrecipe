"""Custody — the only I/O boundary in this package (ADR-001).

Everything above this subpackage is a pure function over what custody
returned. That purity is what makes determinism (TRD §4) structural rather
than a discipline someone has to remember.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

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
        """
        return self.data.decode("utf-8")


@runtime_checkable
class Custody(Protocol):
    """The narrow custody port. Four operations, so adapters stay thin."""

    def exists(self, path: FragmentPath) -> bool: ...
    def read(self, path: FragmentPath) -> FragmentContent: ...
    def list(self, namespace: str) -> list[FragmentPath]: ...
    def versions(self, path: FragmentPath) -> list[FragmentId]: ...
