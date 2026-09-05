"""Assembly — pure, deterministic, ordered (TRD §3, §4).

Pipeline order is fixed, and is itself a security property:
  1. evaluate expectations   (fail before any content exists)
  2. evaluate conditions     (decide what loads, in what order)
  3. resolve paths           (reference -> exactly one identity)
  4. fetch fragments         (the only I/O, delegated to custody)
  5. concatenate in declared order
  6. substitute value variables  <- LAST, never re-parsed (ADR-006)

Step 6 runs last so a caller-supplied value can never influence which
fragments load, their order, or their version.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from promptrecipe.custody import FragmentContent
from promptrecipe.errors import (
    AmbiguousOrder,
    CyclicInclusion,
    DepthLimitExceeded,
    ExpectationFailed,
    FragmentDirectiveNotAllowed,
    UndefinedVariable,
    UnknownOrderName,
    UnorderedFragment,
)
from promptrecipe.identity import FragmentId
from promptrecipe.parser.nodes import (
    And,
    Equals,
    Expr,
    If,
    In,
    Literal,
    Load,
    Not,
    NotEquals,
    Or,
    Order,
    PathExpr,
    PathLiteral,
    Recipe,
    Stmt,
    Text,
    Var,
)
from promptrecipe.paths import FragmentPath
from promptrecipe.provenance import (
    Attestation,
    Producer,
    ResolvedDependency,
    instance_identity,
    structural_identity,
)
from promptrecipe.resolve import Resolver

Value = str | int | bool

MAX_INCLUSION_DEPTH = 32
"""Ceiling on nested fragment inclusion.

Cycle detection catches a fragment that comes back to itself; this catches a
chain that is merely absurdly long. Both fail loudly rather than exhausting
the stack.
"""

MAX_EXPRESSION_DEPTH = 64
"""Ceiling on expression-tree depth during evaluation.

The parser bounds what it will build, but an AST can reach the evaluator by
other routes. Bounding here too means a deep tree raises DepthLimitExceeded —
a PromptRecipeError the documented `except` clause catches — rather than a
bare RecursionError that escapes it.
"""


@dataclass(slots=True)
class Params:
    """The inputs to one assembly (amendment 9 — three distinct roles).

    Dicts are iterated in SORTED order wherever their order can reach output
    or a digest; insertion order must never leak (TRD §4).
    """

    controls: dict[str, Value] = field(default_factory=dict)
    """Feed conditions. Affect STRUCTURE."""
    addresses: dict[str, str] = field(default_factory=dict)
    """Resolve to fragment paths. Affect STRUCTURE."""
    values: dict[str, str] = field(default_factory=dict)
    """Substituted as literal text. Affect CONTENT only."""


@dataclass(slots=True)
class Assembled:
    text: str
    attestation: Attestation
    """Emitted here, at assembly time — never reconstructed (SD5)."""
    fragments: list[tuple[str, FragmentId]] = field(default_factory=list)
    """Fragments in assembly ORDER. A list, never a set — order is identity (SD13)."""
    condition_outcomes: list[tuple[str, bool]] = field(default_factory=list)
    """Every condition and its outcome, so a branch can be replayed (SD6)."""


def _value_of(expr: Expr, params: Params, depth: int = 0) -> Value:
    if depth > MAX_EXPRESSION_DEPTH:
        raise DepthLimitExceeded(limit=MAX_EXPRESSION_DEPTH, path="condition expression")
    if isinstance(expr, Literal):
        return expr.value
    if isinstance(expr, Var):
        if expr.name not in params.controls:
            raise UndefinedVariable(name=expr.name, bound=list(params.controls))
        return params.controls[expr.name]
    return _truth(expr, params, depth + 1)


def _truth(expr: Expr, params: Params, depth: int = 0) -> bool:
    """Evaluate an expression to a boolean.

    Total by construction: the grammar has no call, loop, or I/O node, so
    every recursion is structural and terminates (E3, ADR-003).
    """
    if depth > MAX_EXPRESSION_DEPTH:
        raise DepthLimitExceeded(limit=MAX_EXPRESSION_DEPTH, path="condition expression")
    if isinstance(expr, Literal):
        return bool(expr.value)
    if isinstance(expr, Var):
        if expr.name not in params.controls:
            raise UndefinedVariable(name=expr.name, bound=list(params.controls))
        return bool(params.controls[expr.name])
    if isinstance(expr, Not):
        return not _truth(expr.operand, params, depth + 1)
    if isinstance(expr, And):
        return _truth(expr.left, params, depth + 1) and _truth(expr.right, params, depth + 1)
    if isinstance(expr, Or):
        return _truth(expr.left, params, depth + 1) or _truth(expr.right, params, depth + 1)
    if isinstance(expr, Equals):
        return _value_of(expr.left, params, depth + 1) == _value_of(expr.right, params, depth + 1)
    if isinstance(expr, NotEquals):
        return _value_of(expr.left, params, depth + 1) != _value_of(expr.right, params, depth + 1)
    if isinstance(expr, In):
        needle = _value_of(expr.needle, params, depth + 1)
        return any(_value_of(item, params, depth + 1) == needle for item in expr.haystack)
    raise AssertionError(f"unreachable: unknown expression node {type(expr).__name__}")


def _describe(expr: Expr, depth: int = 0) -> str:
    """A stable textual form of a condition, for provenance and messages.

    Must be deterministic: it reaches the provenance digest (SD6).
    """
    if depth > MAX_EXPRESSION_DEPTH:
        raise DepthLimitExceeded(limit=MAX_EXPRESSION_DEPTH, path="condition expression")
    if isinstance(expr, Literal):
        return repr(expr.value)
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Not):
        return f"not {_describe(expr.operand, depth + 1)}"
    if isinstance(expr, And):
        return f"({_describe(expr.left, depth + 1)} and {_describe(expr.right, depth + 1)})"
    if isinstance(expr, Or):
        return f"({_describe(expr.left, depth + 1)} or {_describe(expr.right, depth + 1)})"
    if isinstance(expr, Equals):
        return f"({_describe(expr.left, depth + 1)} == {_describe(expr.right, depth + 1)})"
    if isinstance(expr, NotEquals):
        return f"({_describe(expr.left, depth + 1)} != {_describe(expr.right, depth + 1)})"
    if isinstance(expr, In):
        items = ", ".join(_describe(i, depth + 1) for i in expr.haystack)
        return f"({_describe(expr.needle, depth + 1)} in [{items}])"
    raise AssertionError(f"unreachable: unknown expression node {type(expr).__name__}")


REFERENCE = re.compile(r"\[\s*load\s+([A-Za-z_][\w.-]*(?:/[\w.-]+)+)\s*\]")
"""A fragment's reference to a sibling: `[load namespace/path]`.

The path must be QUALIFIED — it must contain a separator. A bare identifier
would be an address variable, and honouring one inside fragment text would
let untrusted content read from the caller's address space.

Recognising this one fixed form is not evaluating the fragment: there is no
expression to evaluate and no branch to take. The fragment can name a
sibling and nothing else (ADR-003, E1).
"""

DIRECTIVE_IN_FRAGMENT = re.compile(r"\[\s*(load|if|order|expect)\b")
"""Any directive keyword appearing in fragment text.

A fragment may reference; it may not branch, order, or assert. Text like
`[if x] [load y]` is rejected rather than treated as literal-prose-plus-load:
the load would happen unconditionally while looking conditional, which is
precisely the silently-wrong output this codebase refuses everywhere else.

Ordinary bracketed prose — `[1]`, `[TODO]`, `[see appendix]` — is untouched,
because only these four keywords are directives.
"""


def slot_of(path: FragmentPath) -> str:
    """The ORDER SLOT a fragment fills.

    A slot is the leaf name up to its first dot, so `core/tone.claude` and
    `core/tone.gpt` both fill the slot `tone`. That is what lets an order
    declaration describe STRUCTURE while a condition chooses the VARIANT —
    the split amendment 6's model-portability use case depends on.
    """
    leaf = path.segments[-1] if path.segments else path.namespace
    return leaf.split(".", 1)[0]


def _path_for(path: PathExpr, params: Params) -> FragmentPath:
    if isinstance(path, PathLiteral):
        return FragmentPath.parse(path.value)
    if path.name not in params.addresses:
        raise UndefinedVariable(name=path.name, bound=list(params.addresses))
    return FragmentPath.parse(params.addresses[path.name])


def _substitute(text: str, values: dict[str, str]) -> str:
    """Replace `{{name}}` with its bound value.

    ONE pass over the input. The output is never re-scanned, so a substituted
    value containing `{{...}}` or `[load ...]` stays literal (ADR-006).
    Unbound placeholders are left untouched: values are content, not
    structure, so an unknown one is not a structural failure.
    """
    out: list[str] = []
    i = 0
    n = len(text)

    while i < n:
        start = text.find("{{", i)
        if start == -1:
            out.append(text[i:])
            break
        end = text.find("}}", start + 2)
        if end == -1:
            out.append(text[i:])
            break

        out.append(text[i:start])
        name = text[start + 2 : end].strip()
        if name in values:
            # Appended directly to the output; `i` jumps past it, so this
            # loop never re-examines the substituted text.
            out.append(values[name])
        else:
            out.append(text[start : end + 2])
        i = end + 2

    return "".join(out)


def _expand(
    path: FragmentPath,
    content: FragmentContent,
    resolver: Resolver,
    stack: list[str],
    seen: list[tuple[str, FragmentId]],
) -> str:
    """Inline a fragment, resolving any references it makes to other fragments.

    Depth-first over an explicit stack so a cycle can be reported as the
    ACTUAL PATH that closed it — `a -> b -> c -> a` — rather than merely
    "a cycle exists". Gate 0 found build systems that only report the latter,
    and one that silently drops the cycle and continues; the second is the
    behaviour this product exists to make impossible.
    """
    if len(stack) > MAX_INCLUSION_DEPTH:
        raise DepthLimitExceeded(limit=MAX_INCLUSION_DEPTH, path=str(path))

    out: list[str] = []
    cursor = 0
    text = content.text

    # Reject directive-shaped text that is not a plain qualified reference,
    # before inlining anything.
    references = list(REFERENCE.finditer(text))
    allowed = {(m.start(), m.end()) for m in references}
    for found in DIRECTIVE_IN_FRAGMENT.finditer(text):
        if not any(start <= found.start() < end for start, end in allowed):
            raise FragmentDirectiveNotAllowed(
                path=str(path),
                directive=found.group(1),
                excerpt=text[found.start() : found.start() + 40],
            )

    for match in references:
        out.append(text[cursor : match.start()])
        child_path = FragmentPath.parse(match.group(1))
        key = str(child_path)

        if key in stack:
            # The cycle is the portion of the stack from the first visit
            # onward, closed by the repeat.
            start = stack.index(key)
            raise CyclicInclusion(cycle=[*stack[start:], key])

        child_content, _trace = resolver.fetch(child_path)
        seen.append((key, child_content.id))
        stack.append(key)
        try:
            out.append(_expand(child_path, child_content, resolver, stack, seen))
        finally:
            stack.pop()
        cursor = match.end()

    out.append(text[cursor:])
    return "".join(out)


def _apply_order(
    segments: list[tuple[str, object]], declared: list[Order]
) -> list[tuple[str, object]]:
    """Permute fragment segments into a declared slot order.

    Prose keeps its position; only the fragment contents move between the
    positions where loads occurred. That keeps a reordering predictable — the
    shape of the recipe is unchanged, the sequence of its parts is not.
    """
    if not declared:
        return segments
    if len(declared) > 1:
        # Two reachable order declarations mean the recipe does not say what
        # the order is. Picking one would be the silent-shadowing failure in
        # a different costume.
        raise AmbiguousOrder(declarations=[list(d.names) for d in declared])

    wanted = declared[0].names
    positions = [i for i, (kind, _) in enumerate(segments) if kind == "frag"]
    loaded = [segments[i][1] for i in positions]

    by_slot: dict[str, list[object]] = {}
    for item in loaded:
        by_slot.setdefault(slot_of(item[0]), []).append(item)

    ordered: list[object] = []
    for name in wanted:
        if name not in by_slot:
            raise UnknownOrderName(name=name, available=sorted(by_slot))
        ordered.extend(by_slot.pop(name))

    if by_slot:
        # A loaded fragment the order never mentions has no defined position.
        raise UnorderedFragment(slots=sorted(by_slot))

    reordered = list(segments)
    for position, item in zip(positions, ordered, strict=True):
        reordered[position] = ("frag", item)
    return reordered


def assemble(recipe: Recipe, params: Params, resolver: Resolver) -> Assembled:
    """Assemble a recipe. Pure over what the resolver returns."""
    # --- 1. expectations, before any content exists (TRD §7) ---------------
    for expectation in recipe.expectations:
        if not _truth(expectation.condition, params):
            raise ExpectationFailed(
                position=expectation.position,
                expected=_describe(expectation.condition),
                actual=f"controls were {dict(sorted(params.controls.items()))}",
            )

    # Segments are (kind, payload). Fragment segments stay addressable so a
    # declared order can permute them while prose keeps its position.
    segments: list[tuple[str, object]] = []
    condition_outcomes: list[tuple[str, bool]] = []
    declared_orders: list[Order] = []

    def emit(stmt: Stmt) -> bool:
        """Append a statement's output. Returns True if it produced nothing
        because a condition was not taken — the caller uses that to suppress
        the rest of the line."""
        if isinstance(stmt, If):
            # A nested `[if a][if b] x` used to fall through here and vanish
            # with no error — silent wrong output, which PROJECT_RULES forbids.
            outcome = _truth(stmt.condition, params)
            condition_outcomes.append((_describe(stmt.condition), outcome))
            if outcome:
                emit(stmt.body)
                return False
            return True
        elif isinstance(stmt, Order):
            # Collected, not applied here: an order declaration inside a
            # satisfied condition is how ordering becomes parameterizable,
            # reusing the condition mechanism rather than inventing a second
            # one (the same reasoning as amendment 3 for version selection).
            declared_orders.append(stmt)
        elif isinstance(stmt, Text):
            segments.append(("text", stmt.value))
        elif isinstance(stmt, Load):
            path = _path_for(stmt.path, params)
            # One fetch: resolve and read were two independent lookups, which
            # meant two I/O round-trips per fragment and — worse — two code
            # paths that could disagree about ambiguity.
            content, _trace = resolver.fetch(path)
            segments.append(("frag", (path, content)))
        return False

    # A conditional that is not taken also swallows the remainder of its line.
    #
    # Without this, `[if x][load y]` on its own line still emits the newline
    # that followed it, so a recipe with three unmet conditions produces three
    # stray blank lines. Found by assembling a realistic library rather than a
    # unit fixture — the recipes in tests are single-line and never showed it.
    #
    # The rule is deliberately narrow: only whitespace up to and including the
    # FIRST newline is dropped, and only directly after an untaken condition.
    # A blank line the author wrote as spacing between other statements is
    # untouched.
    suppress_line = False
    for stmt in recipe.statements:
        if suppress_line and isinstance(stmt, Text):
            newline = stmt.value.find("\n")
            head = stmt.value[: newline + 1] if newline != -1 else stmt.value
            if head.strip():
                # Real content on the line — the author meant it to stay.
                suppress_line = False
            else:
                remainder = stmt.value[newline + 1 :] if newline != -1 else ""
                suppress_line = False
                if remainder:
                    segments.append(("text", remainder))
                continue
        suppress_line = emit(stmt)

    segments = _apply_order(segments, declared_orders)

    parts: list[str] = []
    fragments: list[tuple[str, FragmentId]] = []
    for kind, payload in segments:
        if kind == "text":
            parts.append(payload)
        else:
            path, content = payload
            nested: list[tuple[str, FragmentId]] = []
            parts.append(_expand(path, content, resolver, [str(path)], nested))
            fragments.append((str(path), content.id))
            # Nested fragments are dependencies too: provenance must name every
            # fragment that reached the output, not only the ones the recipe
            # mentioned directly (SD13, FR-002).
            fragments.extend(nested)

    # --- 6. value substitution — LAST, single pass, never re-parsed --------
    #
    # Running last IS the security property (ADR-006): every structural
    # decision above is already final, so a caller-supplied value cannot
    # influence which fragments loaded, their order, or their version.
    text = _substitute("".join(parts), params.values)

    # --- provenance: produced HERE, as a return value, so it cannot be
    # reconstructed after the fact when inputs may have changed (SD5).
    attestation = Attestation(
        subject=FragmentId.of(text.encode("utf-8")).hex,
        resolved_dependencies=[
            ResolvedDependency(path=path, identity=fid.hex) for path, fid in fragments
        ],
        condition_outcomes=list(condition_outcomes),
        resolved_order=[path for path, _ in fragments],
        address_resolutions=sorted(params.addresses.items()),
        value_bindings=sorted(params.values.items()),
        producer=Producer(),
        recorded_at=None,
    )
    attestation = replace(attestation, structural_identity=structural_identity(attestation))
    attestation = replace(attestation, instance_identity=instance_identity(attestation))

    return Assembled(
        text=text,
        attestation=attestation,
        fragments=fragments,
        condition_outcomes=condition_outcomes,
    )
