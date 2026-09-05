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
    precedence: int = 0


@dataclass(slots=True)
class ResolutionTrace:
    path: str
    entries: list[TraceEntry] = field(default_factory=list)
    winner: str | None = None

    def explain(self) -> str:
        """Why this reference resolved where it did (FR-030).

        Gate 0 found that mature precedence systems become confusing at scale
        precisely because they are not inspectable. This is the mitigation, so
        it is part of the type rather than a debugging afterthought.
        """
        lines = [f"resolving '{self.path}':"]
        for e in self.entries:
            mark = "found" if e.found else "     "
            won = "  <- winner" if e.found and e.source == self.winner else ""
            lines.append(f"  [{mark}] {e.source} (precedence {e.precedence}){won}")
        if self.winner is None:
            lines.append("  no source matched")
        return "\n".join(lines)


@dataclass(frozen=True, slots=True)
class Source:
    name: str
    custody: Custody
    precedence: int = 0
    """Higher wins. Layering is opt-in and DECLARED.

    ADR-004 forbids resolving a collision by registration order, because that
    makes shadowing invisible. A precedence difference is an explicit
    statement by the person configuring the resolver — so an override is a
    decision someone wrote down, not an accident of ordering. Equal
    precedence remains ambiguous and still errors.
    """


class Resolver:
    """Routes namespaces to custody sources."""

    def __init__(self) -> None:
        self._namespaces: dict[str, list[Source]] = {}

    def register(
        self, namespace: str, name: str, custody: Custody, precedence: int = 0
    ) -> Resolver:
        """Register a source under a namespace.

        `precedence` opts into layering: a higher value overrides a lower one
        for the same path, and the resolution trace explains why (FR-030).
        Sources left at the default share a precedence, so a collision between
        them is still ambiguous and still errors — an override has to be
        declared, never inferred from the order someone happened to register.
        """
        self._namespaces.setdefault(namespace, []).append(
            Source(name=name, custody=custody, precedence=precedence)
        )
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
        hits: list[Source] = []

        for source in sources:
            found = source.custody.exists(path)
            trace.entries.append(
                TraceEntry(
                    namespace=path.namespace,
                    source=source.name,
                    found=found,
                    precedence=source.precedence,
                )
            )
            if found:
                hits.append(source)

        if not hits:
            raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)

        top = max(h.precedence for h in hits)
        winners = [h for h in hits if h.precedence == top]
        if len(winners) > 1:
            # ADR-004 / FR-031: never pick. Two sources at the same declared
            # precedence means nobody said which should win.
            raise AmbiguousReference(
                path=str(path),
                candidates=[f"{w.name} (precedence {w.precedence})" for w in winners],
            )

        trace.winner = winners[0].name
        return winners[0].custody.read(path), trace

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
