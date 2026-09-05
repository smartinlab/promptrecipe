"""Metric M11 (FR-028) enforced, and the guard itself verified."""

import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "quickstart_walkthrough.py"


def run(script: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )


def test_first_value_is_reachable_within_budget():
    result = run(SCRIPT)
    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert "PASS" in result.stdout


def test_the_budget_guard_actually_fires():
    """A test that cannot fail is not a test.

    Rewrite the budget to zero and confirm the script exits non-zero.
    """
    source = SCRIPT.read_text().replace("BUDGET_SECONDS = 30 * 60", "BUDGET_SECONDS = 0")
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / "budget_zero.py"
        probe.write_text(source)
        result = run(probe)

    assert result.returncode == 1, "the budget guard did not fire"
    assert "over the" in result.stderr
