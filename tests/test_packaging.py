"""Packaging properties that must hold at every release."""

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_wheel() -> Path:
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(ROOT / "dist")],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    wheels = sorted((ROOT / "dist").glob("promptrecipe-*.whl"))
    assert wheels, "no wheel was produced"
    return wheels[-1]


def test_the_wheel_is_pure_python_and_platform_independent():
    """py3-none-any: one wheel installs everywhere, no compiler required.

    This is the concrete benefit of the Python-only decision, so it is
    asserted rather than assumed.
    """
    name = build_wheel().name
    assert name.endswith("-py3-none-any.whl"), f"expected a universal wheel, got {name}"


def test_the_wheel_contains_the_package_and_no_tests():
    with zipfile.ZipFile(build_wheel()) as zf:
        names = zf.namelist()
    assert any(n.startswith("promptrecipe/") for n in names)
    assert not any(n.startswith("tests/") for n in names), "tests must not ship"
    assert not any(n.startswith("scripts/") for n in names), "scripts must not ship"


def _metadata() -> str:
    with zipfile.ZipFile(build_wheel()) as zf:
        name = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        return zf.read(name).decode("utf-8")


def test_the_wheel_declares_exactly_one_runtime_dependency():
    """Optional extras carry an `extra ==` marker and are NOT installed by
    default, so only unmarked Requires-Dist lines are runtime dependencies.
    Counting every line would wrongly flag the dev extras."""
    requires = [ln for ln in _metadata().splitlines() if ln.startswith("Requires-Dist:")]
    runtime = [ln for ln in requires if "extra ==" not in ln]
    optional = [ln for ln in requires if "extra ==" in ln]

    assert len(runtime) == 1, f"expected one runtime dependency, found: {runtime}"
    assert "blake3==1.0.9" in runtime[0]
    assert optional, "the dev extras should still be declared, just gated"


def test_the_wheel_declares_the_python_floor_and_ceiling():
    """Asserts both bounds regardless of their order.

    Packaging metadata normalises and reorders a specifier set, so an
    assertion on the literal string is brittle. Checking each bound
    separately is formatting-independent — and needs no extra dependency,
    which matters because `packaging` is only ever present transitively.
    """
    line = next(ln for ln in _metadata().splitlines() if ln.startswith("Requires-Python:"))

    assert ">=3.11" in line, "3.10 is EOL in October 2026 and must be excluded"
    assert "<3.15" in line, "the ceiling matches the optimization target's own constraint"
