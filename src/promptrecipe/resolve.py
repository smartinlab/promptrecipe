"""Resolution — path plus selection context to exactly one fragment identity.

Two rules define this module (ADR-004):

1. **Namespace isolation, not ordered search.** A path's leading segment
   routes to exactly one namespace. Collisions are structurally impossible
   rather than silently shadowed.
2. **Ambiguity is an error.** Where layering is configured, more than one
   candidate is a failure naming all of them — never a silent pick.

Resolution performs NO assembly and reads no content beyond what identity
requires. That separation is what makes dependency queries cheap (FR-011).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from promptrecipe.custody import Custody, FragmentContent
from promptrecipe.errors import AmbiguousReference, FragmentNotFound, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


@dataclass(frozen=True, slots=True)
class TraceEntry:
    """One step of how a reference was resolved. Makes precedence inspectable
    (FR-030) — you can always explain why a fragment won."""

    namespace: str
    source: str
    found: bool


@dataclass(slots=True)
class ResolutionTrace:
    path: str
    entries: list[TraceEntry] = field(default_factory=list)
    winner: str | None = None


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    custody: Custody


class Resolver:
    """Routes namespaces to custody sources."""

    def __init__(self) -> None:
        self._namespaces: dict[str, list[Source]] = {}

    def register(self, namespace: str, name: str, custody: Custody) -> Resolver:
        self._namespaces.setdefault(namespace, []).append(Source(name=name, custody=custody))
        return self

    @property
    def known_namespaces(self) -> list[str]:
        # Sorted: this list reaches error messages, which must be stable
        # across runs (TRD §4).
        return sorted(self._namespaces)

    def sources_for(self, namespace: str) -> list[Source]:
        return list(self._namespaces.get(namespace, []))

    def _sources_or_raise(self, path: FragmentPath) -> list[Source]:
        sources = self._namespaces.get(path.namespace)
        if sources is None:
            raise UnknownNamespace(
                namespace=path.namespace, path=str(path), known=self.known_namespaces
            )
        return sources

    def fetch(self, path: FragmentPath) -> tuple[FragmentContent, ResolutionTrace]:
        """Resolve a path to exactly one fragment and return its content.

        THE single lookup path. Every source registered for the namespace is
        consulted — deliberately NOT short-circuited on the first hit, because
        short-circuiting makes ambiguity undetectable, which is the
        silent-shadowing failure ADR-004 exists to prevent.

        Content is read once here and returned, rather than read to compute an
        identity and then re-read by the caller. Two lookup paths is how the
        original `read()` came to bypass the ambiguity check entirely.
        """
        sources = self._sources_or_raise(path)
        trace = ResolutionTrace(path=str(path))
        hits: list[tuple[str, FragmentContent]] = []

        for source in sources:
            found = source.custody.exists(path)
            trace.entries.append(
                TraceEntry(namespace=path.namespace, source=source.name, found=found)
            )
            if found:
                hits.append((source.name, source.custody.read(path)))

        if not hits:
            raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)
        if len(hits) > 1:
            # ADR-004 / FR-031: never pick. Name every candidate.
            raise AmbiguousReference(path=str(path), candidates=[name for name, _ in hits])

        trace.winner = hits[0][0]
        return hits[0][1], trace

    def resolve(self, path: FragmentPath) -> tuple[FragmentId, ResolutionTrace]:
        """Resolve a path to exactly one fragment identity."""
        content, trace = self.fetch(path)
        return content.id, trace

    def read(self, path: FragmentPath) -> FragmentContent:
        """Read the content a path resolves to.

        Goes through `fetch`, so an ambiguous reference raises here exactly as
        it does in `resolve`. It previously scanned for the first match, which
        let `get_prompt` fetch the RECIPE itself without an ambiguity check —
        silently picking a winner in the one place ADR-004 most needed to hold.
        """
        return self.fetch(path)[0]
