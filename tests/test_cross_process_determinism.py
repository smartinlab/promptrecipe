"""Determinism ACROSS processes (TRD §4).

Python randomizes its string hash seed per process. Hash-ordered iteration
therefore looks stable inside one run and differs between runs — invisible to
a single-process property test. Spawning real processes is the only way to
see it.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "assemble_once.py"


def digest_from_fresh_process(seed: str) -> str:
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONHASHSEED": seed},
        check=False,
    )
    assert result.returncode == 0, f"script failed:\n{result.stderr}"
    return result.stdout.strip()


def test_assembly_is_identical_across_separate_processes():
    """Different hash seeds must produce identical output.

    Forcing distinct PYTHONHASHSEED values makes this deterministic rather
    than hoping the OS happens to pick different seeds.
    """
    first = digest_from_fresh_process("0")
    second = digest_from_fresh_process("1")
    third = digest_from_fresh_process("random")

    assert len(first) == 64, f"expected a full digest, got: {first}"
    assert first == second, (
        "two processes with different hash seeds produced different output — "
        "hash-ordered iteration reached the result"
    )
    assert first == third, "output drifted with a randomized hash seed"
