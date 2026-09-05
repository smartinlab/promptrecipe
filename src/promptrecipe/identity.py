"""Content-derived fragment identity (ADR-002).

Identity comes from the bytes and nothing else. Two fragments with identical
content have identical identity, whatever their path or custody. That is what
lets custody change without invalidating provenance (SD1, SD2).
"""

from __future__ import annotations

from dataclasses import dataclass

import blake3

DIGEST_ALGORITHM = "blake3"


@dataclass(frozen=True, slots=True, order=True)
class FragmentId:
    """A content-derived identity for a fragment version.

    Frozen so an identity cannot be mutated after creation, and hashable so it
    can key the content cache.
    """

    hex: str

    @classmethod
    def of(cls, content: bytes) -> FragmentId:
        """Compute the identity of the given bytes."""
        return cls(blake3.blake3(content).hexdigest())

    @property
    def short(self) -> str:
        """First 12 hex characters. Display only — never an identity."""
        return self.hex[:12]

    def __str__(self) -> str:
        return self.hex

    def __repr__(self) -> str:
        return f"FragmentId({self.short})"
