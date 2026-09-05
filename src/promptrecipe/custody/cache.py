"""Content-keyed cache.

The cache key is the CONTENT IDENTITY, never the path. A path-keyed cache
would return stale bytes after a fragment changed — silently breaking FR-007
(change once, propagates everywhere) with no error anywhere. Keying by
identity makes staleness structurally impossible: different content is a
different key.
"""

from __future__ import annotations

from collections.abc import Iterator

from promptrecipe.custody import FragmentContent
from promptrecipe.identity import FragmentId


class ContentCache:
    """Caches fragment content by identity."""

    def __init__(self) -> None:
        # Keyed by FragmentId. Never by FragmentPath. See the module docstring.
        self._entries: dict[FragmentId, bytes] = {}
        self._hits = 0
        self._misses = 0

    def get(self, fragment_id: FragmentId) -> FragmentContent | None:
        data = self._entries.get(fragment_id)
        if data is None:
            self._misses += 1
            return None
        self._hits += 1
        return FragmentContent(id=fragment_id, data=data)

    def put(self, content: FragmentContent) -> None:
        self._entries[content.id] = content.data

    def __iter__(self) -> Iterator[FragmentId]:
        """Iterate the cached identities.

        Iterable rather than exposing `.keys()`: the key type is the whole
        point of this cache, so it belongs in the iteration protocol.
        """
        return iter(self._entries)

    @property
    def stats(self) -> tuple[int, int]:
        """(hits, misses)."""
        return self._hits, self._misses

    def __len__(self) -> int:
        return len(self._entries)
