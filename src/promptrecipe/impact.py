"""Which recipes depend on a fragment, and what a change to it would do.

Two questions with deliberately different costs (TRD C7):

- **Dependents** (T-021) must be CHEAP. It is the question you ask before
  every change, so it walks the reference graph and assembles NOTHING. That
  is the whole reason resolution is a separate layer from assembly (SD3).
- **Preview** (T-022) assembles on purpose, because showing how output would
  differ requires producing it. It is the slower question you ask once, about
  a change you are already considering.

Keeping them apart is what keeps the cheap one cheap.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from promptrecipe.custody import Custody
from promptrecipe.errors import PromptRecipeError
from promptrecipe.parser.nodes import If, Load, PathLiteral, Recipe, Stmt
from promptrecipe.parser.parse import parse
from promptrecipe.paths import FragmentPath
from promptrecipe.resolve import Resolver

# A fragment's reference to a sibling. Matches assemble.REFERENCE — fragments
# may name a sibling and nothing else, so the dependency graph sees the same
# edges assembly would.
_REFERENCE = re.compile(r"\[\s*load\s+([A-Za-z_][\w.-]*(?:/[\w.-]+)+)\s*\]")


@dataclass(frozen=True, slots=True)
class Edge:
    """One reference, and whether a condition guards it."""

    source: str
    target: str
    conditional: bool = False
    """A conditional edge MIGHT load. Dependents is deliberately pessimistic:
    it reports what COULD be affected, because the question is about risk."""


@dataclass(slots=True)
class Graph:
    edges: list[Edge] = field(default_factory=list)
    unresolvable: list[str] = field(default_factory=list)
    """References that name nothing. Reported, not raised: a dependency query
    on a library mid-edit should still answer, and say what it could not
    follow."""

    def dependents_of(self, path: str) -> list[str]:
        """Everything that reaches `path`, transitively."""
        reverse: dict[str, list[str]] = {}
        for edge in self.edges:
            reverse.setdefault(edge.target, []).append(edge.source)

        found: set[str] = set()
        frontier = [path]
        while frontier:
            current = frontier.pop()
            for parent in reverse.get(current, []):
                if parent not in found:
                    found.add(parent)
                    frontier.append(parent)
        return sorted(found)

    def direct_dependents_of(self, path: str) -> list[str]:
        return sorted({e.source for e in self.edges if e.target == path})


def _references(statements: list[Stmt], *, guarded: bool = False) -> list[tuple[str, bool]]:
    """Literal load targets in a recipe, with whether a condition guards them.

    Address variables are skipped: their target is only known at call time, so
    a static graph cannot follow them. That gap is reported by the caller
    rather than guessed at.
    """
    out: list[tuple[str, bool]] = []
    for stmt in statements:
        if isinstance(stmt, If):
            out.extend(_references([stmt.body], guarded=True))
        elif isinstance(stmt, Load) and isinstance(stmt.path, PathLiteral):
            out.append((stmt.path.value, guarded))
    return out


def build_graph(resolver: Resolver, namespaces: list[str] | None = None) -> Graph:
    """Walk the whole library and record every reference.

    Reads content — a reference lives inside text — but PARSES nothing beyond
    what it takes to find edges, and assembles nothing at all.
    """
    graph = Graph()
    wanted = namespaces or resolver.known_namespaces

    for namespace in wanted:
        for source in resolver.sources_for(namespace):
            custody: Custody = source.custody
            try:
                entries = custody.list(namespace)
            except PromptRecipeError:
                continue

            for path in entries:
                try:
                    text = custody.read(path).text
                except PromptRecipeError:
                    continue

                # A recipe's edges come from its directives; a fragment's from
                # its inline references. Try the recipe reading first and fall
                # back — a fragment is not a valid recipe and need not be.
                try:
                    recipe: Recipe = parse(text)
                    edges = _references(recipe.statements)
                except PromptRecipeError:
                    edges = [(m.group(1), False) for m in _REFERENCE.finditer(text)]

                for target, conditional in edges:
                    try:
                        resolved = str(FragmentPath.parse(target))
                    except PromptRecipeError:
                        graph.unresolvable.append(f"{path} -> {target}")
                        continue
                    graph.edges.append(
                        Edge(source=str(path), target=resolved, conditional=conditional)
                    )

    graph.edges.sort(key=lambda e: (e.source, e.target))
    return graph


def dependents(fragment_path: str, resolver: Resolver) -> list[str]:
    """Every recipe or fragment that could reach this one. Assembles nothing."""
    return build_graph(resolver).dependents_of(str(FragmentPath.parse(fragment_path)))


@dataclass(frozen=True, slots=True)
class PreviewedChange:
    """How one dependent's output would differ."""

    path: str
    before: str
    after: str
    error: str | None = None
    """Why this dependent could not be evaluated, if it could not be.

    Reported rather than swallowed: a dependent whose assembly fails is one
    the preview could NOT check, and silently dropping it understates the
    blast radius the caller asked about.
    """

    @property
    def changed(self) -> bool:
        return self.error is None and self.before != self.after

    def diff(self) -> str:
        import difflib

        return "\n".join(
            difflib.unified_diff(
                self.before.splitlines(),
                self.after.splitlines(),
                fromfile=f"{self.path} (current)",
                tofile=f"{self.path} (after)",
                lineterm="",
            )
        )


def preview_change(
    fragment_path: str,
    new_content: str,
    resolver: Resolver,
    params: object | None = None,
    recipes: list[str] | None = None,
) -> list[PreviewedChange]:
    """Show how a proposed fragment change would alter each dependent (T-022).

    This one DOES assemble — showing how output would differ requires
    producing it. It is scoped to the affected dependents rather than the
    whole library, so the cost stays proportional to the blast radius that
    `dependents()` already reported.

    The change is applied to an OVERLAY, never to custody: previewing must
    not mutate the library, and accepting a change is version control's job
    (amendment 7).
    """
    from promptrecipe import get_prompt
    from promptrecipe.assemble import Params

    params = params or Params()
    target = str(FragmentPath.parse(fragment_path))
    affected = recipes if recipes is not None else dependents(target, resolver)

    overlay = _OverlayCustody({target: new_content})
    with_change = Resolver()
    for namespace in resolver.known_namespaces:
        for source in resolver.sources_for(namespace):
            with_change = with_change.register(
                namespace, source.name, source.custody, source.precedence
            )
    with_change = with_change.register(
        FragmentPath.parse(target).namespace, "preview-overlay", overlay, precedence=10_000
    )

    previews: list[PreviewedChange] = []
    for path in affected:
        try:
            before = get_prompt(path, params, resolver).text
            after = get_prompt(path, params, with_change).text
        except PromptRecipeError as exc:
            # One dependent failing must not fail the whole preview — you ask
            # this question about a library you are in the middle of changing.
            previews.append(PreviewedChange(path=path, before="", after="", error=str(exc)))
            continue
        previews.append(PreviewedChange(path=path, before=before, after=after))

    return previews


class _OverlayCustody:
    """In-memory custody holding only the proposed content.

    Registered at a high precedence so it wins over the real fragment for the
    duration of the preview — using the declared-precedence mechanism rather
    than mutating anything (ADR-004).
    """

    def __init__(self, entries: dict[str, str]) -> None:
        self._entries = {k: v.encode("utf-8") for k, v in entries.items()}

    def exists(self, path: FragmentPath) -> bool:
        return str(path) in self._entries

    def read(self, path: FragmentPath):
        from promptrecipe.custody import FragmentContent
        from promptrecipe.errors import FragmentNotFound

        data = self._entries.get(str(path))
        if data is None:
            raise FragmentNotFound(path=str(path), namespaces=["preview-overlay"])
        return FragmentContent.of(data)

    def list(self, namespace: str) -> list[FragmentPath]:
        return sorted(
            FragmentPath.parse(k) for k in self._entries if k.startswith(f"{namespace}/")
        )

