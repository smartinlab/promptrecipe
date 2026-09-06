"""Shared test helpers."""

from __future__ import annotations

from promptrecipe.custody import FragmentContent
from promptrecipe.errors import FragmentNotFound
from promptrecipe.paths import FragmentPath


class MemoryCustody:
    """In-memory custody. Lets resolution and assembly be tested without I/O."""

    def __init__(self, entries: dict[str, str] | None = None) -> None:
        self._entries = {k: v.encode("utf-8") for k, v in (entries or {}).items()}

    def exists(self, path: FragmentPath) -> bool:
        return str(path) in self._entries

    def read(self, path: FragmentPath) -> FragmentContent:
        data = self._entries.get(str(path))
        if data is None:
            raise FragmentNotFound(path=str(path), namespaces=["memory"])
        return FragmentContent.of(data)

    def list(self, namespace: str) -> list[FragmentPath]:
        return sorted(FragmentPath.parse(k) for k in self._entries if k.startswith(f"{namespace}/"))

