"""Fragment paths: canonicalization and namespace confinement.

A path is a hierarchical address: `namespace/segment/segment`.
Canonicalization is purely LEXICAL — it never touches the filesystem, which
keeps this module inside the "no I/O outside custody" rule (ADR-001).
"""

from __future__ import annotations

from dataclasses import dataclass

from promptrecipe.errors import PathEscapesNamespace, UnknownNamespace


@dataclass(frozen=True, slots=True, order=True)
class FragmentPath:
    """A canonical fragment path.

    Frozen and ordered: hashable for caches, sortable so any listing that
    reaches output has a deterministic order (TRD §4).
    """

    namespace: str
    segments: tuple[str, ...]

    @classmethod
    def parse(cls, raw: str) -> FragmentPath:
        """Parse and canonicalize a raw path reference.

        Resolves `.` and `..` lexically and rejects any path whose `..`
        segments would climb above the namespace root.
        """
        parts = [p for p in raw.strip().lstrip("/").split("/") if p]
        if not parts:
            raise UnknownNamespace(namespace="", path=raw, known=[])

        namespace, *rest = parts
        segments: list[str] = []
        for part in rest:
            if part == ".":
                continue
            if part == "..":
                if not segments:
                    raise PathEscapesNamespace(path=raw, root=namespace)
                segments.pop()
                continue
            segments.append(part)

        return cls(namespace=namespace, segments=tuple(segments))

    def __str__(self) -> str:
        return "/".join((self.namespace, *self.segments))
