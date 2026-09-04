# ST-001-03: Vulnerability audit and license verification

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Close the condition Gate 6 passed on. **No CVE scan has ever run against these pinned versions.** Until this completes, the dependency selections are unverified.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 3 passed
```

**Files** — Create: `scripts/check_supply_chain.py`

---

### Step 1 — Install the audit tooling (3 min)

```bash
pip install --quiet pip-audit pip-licenses
```

### Step 2 — Run the audit — **the gate-closing step** (2 min)

```bash
pip-audit --strict --requirement requirements-dev.lock
```
Expected on success: `No known vulnerabilities found`

> **If any vulnerability appears, STOP and record it.** Gate 6 requires zero critical (≥9.0) and zero high (7.0–8.9), or a documented accepted-risk justification per finding. Do not proceed by ignoring output.
>
> The fallback identified at Gate 6: `blake3` is the only runtime dependency, and its documented alternative is stdlib `hashlib.sha256`, at a hot-path performance cost that ST-005-06 will let you quantify.

### Step 3 — Verify licenses from actual package metadata (2 min)

Closes task-zero 0.4 — Gate 6 marked license identifiers `[UNVERIFIED]`.

```bash
pip-licenses --format=markdown --with-urls \
  --packages blake3 pytest hypothesis ruff hatchling
```
Expected: `blake3` permissive (CC0-1.0 / Apache-2.0); `pytest`, `ruff`, `hatchling` MIT; **`hypothesis` MPL-2.0**.

> **The `hypothesis` MPL-2.0 result is expected, not a problem — but it must be verified, not assumed.** MPL-2.0 is weak copyleft. It is a dev-only dependency and must never reach the built wheel. Step 4 asserts that rather than trusting packaging to do the right thing.

### Step 4 — Assert the weak-copyleft dependency stays out of the wheel (3 min)

```bash
mkdir -p scripts
cat > scripts/check_supply_chain.py <<'PY'
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
PY

python scripts/check_supply_chain.py
```
Expected: `PASS: one runtime dependency; no copyleft dev package in the wheel`

### Step 5 — Commit (1 min)

```bash
git add -A
git commit -m "chore: audit dependencies and verify licences

Closes task-zero 0.3 and 0.4, and the CONDITIONAL pass on Gate 6.
The MPL-2.0 dev dependency is asserted absent from the built wheel
rather than assumed excluded."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf scripts dist
```
