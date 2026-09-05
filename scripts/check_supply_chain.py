"""Supply-chain assertions that must hold at every build.

1. Exactly one runtime dependency.
2. The weak-copyleft dev dependency never reaches the distributed wheel.

Point 2 matters because "packaging probably excludes it" is an assumption,
and licence boundaries are a poor place for assumptions.
"""

import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

EXPECTED_RUNTIME = ["blake3==1.0.9"]
COPYLEFT_DEV_PACKAGES = {"hypothesis"}


def check_runtime_dependencies() -> list[str]:
    deps = tomllib.loads(Path("pyproject.toml").read_text())["project"]["dependencies"]
    if deps != EXPECTED_RUNTIME:
        return [f"runtime dependencies changed: expected {EXPECTED_RUNTIME}, found {deps}"]
    return []


def check_wheel_excludes_copyleft() -> list[str]:
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", "dist"],
        check=True,
        capture_output=True,
    )
    wheels = sorted(Path("dist").glob("promptrecipe-*.whl"))
    if not wheels:
        return ["no wheel was produced"]

    problems = []
    with zipfile.ZipFile(wheels[-1]) as zf:
        names = "\n".join(zf.namelist()).lower()
        for package in COPYLEFT_DEV_PACKAGES:
            if package in names:
                problems.append(f"'{package}' (weak copyleft, dev-only) appears in the wheel")
    return problems


def main() -> int:
    problems = check_runtime_dependencies() + check_wheel_excludes_copyleft()
    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        return 1
    print("PASS: one runtime dependency; no copyleft dev package in the wheel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
