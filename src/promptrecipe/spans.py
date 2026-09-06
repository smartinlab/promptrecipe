"""Which fragment produced which portion of the output (FR-004, T-019).

The attestation says WHICH fragments took part. This says WHERE each one
landed. That is the difference between "one of these eleven fragments is
wrong" and "line 34 came from policy/refusal.md" — the question you actually
have when a prompt misbehaves.

The hard part is not collecting the spans; it is keeping them true. Value
substitution runs LAST (ADR-006) and changes the length of the text, so every
offset collected during assembly is stale by the time assembly finishes.
Remapping through that final pass is what makes the map trustworthy rather
than approximately right.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass, replace


@dataclass(frozen=True, slots=True)
class Span:
    """A contiguous run of output, and where its characters came from."""

    path: str
    """The fragment that literally contains these characters. Empty for prose
    written in the recipe itself."""
    identity: str
    """The fragment's content identity. Empty for recipe prose."""
    start: int
    end: int

    @property
    def from_recipe(self) -> bool:
        return not self.path

    def slice(self, text: str) -> str:
        return text[self.start : self.end]


@dataclass(frozen=True, slots=True)
class SpanMap:
    """A partition of the assembled text — every character attributed once.

    Spans are contiguous, non-overlapping, and cover the whole output. A
    partition rather than a set of highlights: an offset that no span claims
    would be output nobody can account for, which is exactly the situation
    this map exists to make impossible.
    """

    spans: tuple[Span, ...] = ()

    def source_of(self, offset: int) -> Span | None:
        """Which fragment produced the character at `offset`."""
        starts = [s.start for s in self.spans]
        index = bisect.bisect_right(starts, offset) - 1
        if index < 0:
            return None
        span = self.spans[index]
        return span if span.start <= offset < span.end else None

    def spans_for(self, path: str) -> list[Span]:
        """Every place one fragment landed. A fragment loaded twice has two."""
        return [s for s in self.spans if s.path == path]

    def covers(self, text: str) -> bool:
        """Whether the map accounts for every character of `text`."""
        cursor = 0
        for span in self.spans:
            if span.start != cursor:
                return False
            cursor = span.end
        return cursor == len(text)

    def annotate(self, text: str) -> str:
        """A human view: each span prefixed by the fragment that produced it."""
        lines = []
        for span in self.spans:
            origin = span.path or "(recipe)"
            lines.append(f"--- {origin} [{span.start}:{span.end}]")
            lines.append(span.slice(text))
        return "\n".join(lines)


def coalesce(spans: list[Span]) -> tuple[Span, ...]:
    """Merge adjacent spans with the same origin.

    Expansion naturally splits a fragment at every reference it makes; once
    the children are attributed to themselves, the parent's remaining pieces
    are one continuous stretch again and should read as one.
    """
    merged: list[Span] = []
    for span in spans:
        if span.start == span.end:
            continue
        if merged and merged[-1].path == span.path and merged[-1].end == span.start:
            merged[-1] = replace(merged[-1], end=span.end)
        else:
            merged.append(span)
    return tuple(merged)


def remap(spans: tuple[Span, ...], edits: list[tuple[int, int, int]]) -> tuple[Span, ...]:
    """Shift span offsets through the final substitution pass.

    `edits` are `(start, end, new_length)` over the PRE-substitution text, in
    order and non-overlapping — exactly what one left-to-right pass produces.

    A boundary that falls INSIDE a replaced placeholder is clamped to that
    replacement's start. It can only happen when a placeholder straddles a
    fragment boundary (`{{na` in one fragment, `me}}` in the next), and in
    that case the substituted text genuinely belongs to neither fragment
    alone. Attributing it to the earlier one is arbitrary but stable, which
    is what an offset map needs to be.
    """
    if not edits:
        return spans

    starts = [e[0] for e in edits]
    shifts: list[int] = []
    running = 0
    for start, end, new_length in edits:
        running += new_length - (end - start)
        shifts.append(running)

    def move(offset: int) -> int:
        index = bisect.bisect_right(starts, offset) - 1
        if index < 0:
            return offset
        start, end, _ = edits[index]
        before = shifts[index - 1] if index else 0
        if offset < end:
            # Inside the replaced region — clamp to where it now begins.
            return start + before
        return offset + shifts[index]

    return coalesce([replace(s, start=move(s.start), end=move(s.end)) for s in spans])
