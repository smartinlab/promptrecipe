"""Property P3, enforced structurally: the library never evaluates anything.

A grep for `eval(` matches its own prohibition in a docstring. This walks the
AST instead, so it sees calls and imports rather than text — and it fails the
build if anyone ever adds one.
"""

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "promptrecipe"
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__"}
FORBIDDEN_IMPORTS = {"importlib", "subprocess", "marshal", "pickle"}


def source_files() -> list[Path]:
    return sorted(PACKAGE.rglob("*.py"))


def test_the_package_has_source_files():
    """Guards against this whole suite silently passing on an empty tree."""
    assert source_files(), "no source files found — the guard would pass vacuously"


def test_no_dynamic_execution_anywhere_in_the_package():
    """ADR-003 / P3: fragment content is never evaluated, and neither is
    anything else. This is what makes optimizer-written text safe by
    construction rather than by sandbox."""
    offences: list[str] = []

    for file in source_files():
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in FORBIDDEN_CALLS
            ):
                offences.append(f"{file.name}:{node.lineno} calls {node.func.id}()")

    assert not offences, "dynamic execution found: " + "; ".join(offences)


def test_no_dangerous_imports_in_the_package():
    """The runtime library imports nothing that can execute or deserialize
    arbitrary code. (Phase 2 adds `subprocess` for version-control history —
    when it does, this list is the place to record that decision.)"""
    offences: list[str] = []

    for file in source_files():
        tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        offences.append(f"{file.name}:{node.lineno} imports {alias.name}")
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.split(".")[0] in FORBIDDEN_IMPORTS
            ):
                offences.append(f"{file.name}:{node.lineno} imports from {node.module}")

    assert not offences, "dangerous import found: " + "; ".join(offences)
