"""Local filesystem custody adapter.

One fragment is one file (ADR-007). That is not a storage preference:
per-fragment review is delegated to version control, and bundling fragments
into one file would make a per-fragment diff impossible.
"""

from __future__ import annotations

from pathlib import Path

from promptrecipe.custody import FragmentContent
from promptrecipe.errors import FragmentNotFound, PathEscapesNamespace, UnknownNamespace
from promptrecipe.identity import FragmentId
from promptrecipe.paths import FragmentPath


class FsCustody:
    """Maps namespaces to filesystem roots."""

    def __init__(self, extension: str = "md") -> None:
        self._roots: dict[str, Path] = {}
        self._extension = extension

    def with_namespace(self, namespace: str, root: Path | str) -> FsCustody:
        # Resolved once, so confinement checks compare real paths rather than
        # whichever spelling the caller happened to pass.
        self._roots[namespace] = Path(root).resolve()
        return self

    @property
    def known_namespaces(self) -> list[str]:
        # Sorted: this list appears in error messages, which must be stable.
        return sorted(self._roots)

    def _file_for(self, path: FragmentPath) -> Path | None:
        """Map a fragment path to a file.

        The extension is APPENDED, never substituted. `Path.with_suffix`
        would turn `recipe.claude` into `recipe.md`, because it treats
        `.claude` as an existing suffix and replaces it — which would break
        the whole model-variant naming convention (`tone.claude`,
        `tone.gpt`) that amendment 6's driving use case depends on.

        Returns None when the path names no fragment (a bare namespace).
        """
        root = self._roots.get(path.namespace)
        if root is None:
            raise UnknownNamespace(
                namespace=path.namespace, path=str(path), known=self.known_namespaces
            )
        if not path.segments:
            return None
        *parents, name = path.segments
        candidate = root.joinpath(*parents) / f"{name}.{self._extension}"

        # Path canonicalization is LEXICAL by design (ADR-001 keeps paths.py
        # free of I/O), so it cannot see a symlink. Without this check a
        # symlink under the namespace root — planted by the same optimizer or
        # remote-custody actor the threat model treats as untrusted — reads
        # any file on the machine. Confinement has to be re-checked against
        # the real filesystem at the one place that touches it.
        try:
            real = candidate.resolve()
        except OSError:
            return candidate
        if real != root and root not in real.parents:
            raise PathEscapesNamespace(path=str(path), root=str(root))
        return candidate

    def exists(self, path: FragmentPath) -> bool:
        try:
            file = self._file_for(path)
        except UnknownNamespace:
            return False
        # PathEscapesNamespace deliberately propagates: a fragment that
        # escapes its root is a configuration error to surface, not an
        # absence to report quietly.
        return file is not None and file.is_file()

    def read(self, path: FragmentPath) -> FragmentContent:
        file = self._file_for(path)
        if file is None or not file.is_file():
            raise FragmentNotFound(path=str(path), namespaces=self.known_namespaces)
        return FragmentContent.of(file.read_bytes())

    def list(self, namespace: str) -> list[FragmentPath]:
        root = self._roots.get(namespace)
        if root is None:
            raise UnknownNamespace(namespace=namespace, path=namespace, known=self.known_namespaces)
        suffix = f".{self._extension}"
        found = [
            # Strip exactly the extension we appended — `f.stem` would drop
            # `.claude` from `tone.claude.md` and collapse model variants.
            FragmentPath.parse(f"{namespace}/{f.name[: -len(suffix)]}")
            for f in root.iterdir()
            if f.is_file() and f.name.endswith(suffix)
        ]
        # Directory iteration order is not stable across platforms and must
        # never reach output (TRD §4). Sort explicitly.
        return sorted(found)

    def versions(self, path: FragmentPath) -> list[FragmentId]:
        # The filesystem holds exactly one version: whatever is on disk now.
        return [self.read(path).id]
