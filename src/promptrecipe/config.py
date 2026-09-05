"""Declare a fragment library in a file instead of in code.

Registering every namespace by hand is the roughest edge of the API: the
library's shape is a property of the library, not of the program that loads
it, so it belongs in a file next to the fragments.

    # promptrecipe.toml
    [namespaces]
    core   = "prompts/core"
    policy = "prompts/policy"

    [namespaces.shared]
    path       = "../shared/prompts"
    precedence = 10          # opt into layering, explicitly

Paths are relative to the config file, so moving the library moves its
configuration with it and nothing depends on the caller's working directory.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from promptrecipe.custody.fs import FsCustody
from promptrecipe.errors import PromptRecipeError
from promptrecipe.resolve import Resolver

CONFIG_NAME = "promptrecipe.toml"
DEFAULT_EXTENSION = "md"


@dataclass(slots=True)
class ConfigError(PromptRecipeError):
    """The config file is missing, unreadable, or does not describe a library."""

    path: str
    reason: str

    def __str__(self) -> str:
        return f"cannot load {self.path}: {self.reason}"


@dataclass(frozen=True, slots=True)
class NamespaceConfig:
    name: str
    path: Path
    precedence: int = 0
    extension: str = DEFAULT_EXTENSION


@dataclass(frozen=True, slots=True)
class LibraryConfig:
    """A declared fragment library."""

    source: Path
    namespaces: list[NamespaceConfig] = field(default_factory=list)

    def build(self) -> Resolver:
        """Turn the declaration into a Resolver."""
        resolver = Resolver()
        for ns in self.namespaces:
            custody = FsCustody(extension=ns.extension).with_namespace(ns.name, ns.path)
            resolver = resolver.register(ns.name, str(ns.path), custody, ns.precedence)
        return resolver


def _namespace_from(name: str, raw: object, base: Path, source: Path) -> NamespaceConfig:
    """Accept either the short form or the table form.

    core = "prompts/core"

    [namespaces.core]
    path = "prompts/core"
    """
    if isinstance(raw, str):
        raw = {"path": raw}
    if not isinstance(raw, dict):
        raise ConfigError(
            path=str(source),
            reason=f"namespace '{name}' must be a path string or a table, got {type(raw).__name__}",
        )
    if "path" not in raw:
        raise ConfigError(path=str(source), reason=f"namespace '{name}' has no 'path'")

    directory = (base / str(raw["path"])).resolve()
    if not directory.is_dir():
        # Loud at load time rather than at the first missing fragment: a typo
        # in a path should not surface later as "fragment not found".
        raise ConfigError(
            path=str(source),
            reason=f"namespace '{name}' points at '{directory}', which is not a directory",
        )

    return NamespaceConfig(
        name=name,
        path=directory,
        precedence=int(raw.get("precedence", 0)),
        extension=str(raw.get("extension", DEFAULT_EXTENSION)),
    )


def load_config(path: str | Path) -> LibraryConfig:
    """Read a library declaration from a TOML file."""
    source = Path(path).resolve()
    if not source.is_file():
        raise ConfigError(path=str(source), reason="file does not exist")

    try:
        data = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(path=str(source), reason=f"invalid TOML: {exc}") from exc

    namespaces = data.get("namespaces")
    if not isinstance(namespaces, dict) or not namespaces:
        raise ConfigError(path=str(source), reason="no [namespaces] table, or it is empty")

    base = source.parent
    return LibraryConfig(
        source=source,
        namespaces=[
            _namespace_from(name, raw, base, source) for name, raw in sorted(namespaces.items())
        ],
    )


def find_config(start: str | Path = ".") -> Path:
    """Walk up from `start` looking for a config file.

    Same discovery a build tool does, so a script deep in a project finds the
    library at its root without being told where it is.
    """
    current = Path(start).resolve()
    if current.is_file():
        current = current.parent

    for directory in (current, *current.parents):
        candidate = directory / CONFIG_NAME
        if candidate.is_file():
            return candidate

    raise ConfigError(
        path=str(current), reason=f"no {CONFIG_NAME} found here or in any parent directory"
    )


def resolver_from_config(path: str | Path | None = None) -> Resolver:
    """Build a Resolver from a config file, discovering it if not given.

    The one-line replacement for a block of manual `.register()` calls.
    """
    return load_config(path if path is not None else find_config()).build()
