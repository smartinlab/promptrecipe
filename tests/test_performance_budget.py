"""The TRD §8 performance budget, enforced.

Asserts p99, not mean: a mean hides the tail, and a tail spike on the
request path of an agent call is what a user actually feels.

The budget is deliberately generous relative to the measured cost, so this
catches a REGRESSION (an accidental O(n^2), a per-call re-parse) rather than
failing on ordinary CI-runner noise.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark.py"


def test_assembly_meets_the_performance_budget():
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, (
        f"the assembly path missed its budget:\n{result.stdout}\n{result.stderr}"
    )
    assert "PASS  warm" in result.stdout
