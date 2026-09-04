# ST-007-01: Build and install a pure-Python wheel

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Produce a wheel that installs on every supported Python **with no compiler and no platform-specific build** — the concrete dividend of the Python-only decision.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 119 passed
```

**Files** — Create: `README.md`, `tests/test_packaging.py`. Modify: `.github/workflows/ci.yml`

---

### Step 1 — Write the README the packaging metadata points at (3 min)

```bash
cat > README.md <<'MD'
# promptrecipe

Compose prompts from named, path-addressed fragments. Fix a shared
instruction once instead of hunting every copy.

```python
import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", "prompts"))
result = promptrecipe.get_prompt("core/recipe", Params(values={"product": "Acme"}), resolver)

print(result.text)                                # hand this to your agent
print(result.attestation.structural_identity)     # compare A/B by this
print(result.attestation.instance_identity)       # reproduce exact text from this
```

**Requires Python 3.11+.** One runtime dependency. Pure Python — no compiler needed.

See [QUICKSTART.md](QUICKSTART.md) to go from nothing to an assembled prompt.
MD
```

### Step 2 — Build the wheel (3 min)

```bash
pip install --quiet build
python -m build --wheel
ls -la dist/
```
Expected: a file named `promptrecipe-0.1.0-py3-none-any.whl`

> **`py3-none-any` is the point.** `py3` = any Python 3, `none` = no ABI dependency, `any` = any platform. **One wheel, everywhere.** A compiled core would have produced a separate wheel per Python version per platform — the multi-platform matrix the Python-only decision removed.

### Step 3 — RED/GREEN: assert the packaging properties (4 min)

```bash
cat > tests/test_packaging.py <<'PY'
"""Packaging properties that must hold at every release."""

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_wheel() -> Path:
    subprocess.run(  # noqa: S603
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(ROOT / "dist")],
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


def test_the_wheel_declares_exactly_one_runtime_dependency():
    with zipfile.ZipFile(build_wheel()) as zf:
        metadata = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        content = zf.read(metadata).decode("utf-8")
    requires = [ln for ln in content.splitlines() if ln.startswith("Requires-Dist:")]
    assert len(requires) == 1, f"expected one runtime dependency, found: {requires}"
    assert "blake3" in requires[0]


def test_the_wheel_declares_the_python_floor():
    with zipfile.ZipFile(build_wheel()) as zf:
        metadata = next(n for n in zf.namelist() if n.endswith(".dist-info/METADATA"))
        content = zf.read(metadata).decode("utf-8")
    assert "Requires-Python: >=3.11,<3.15" in content
PY

pytest tests/test_packaging.py
```
Expected: `4 passed`

### Step 4 — Add a clean-environment install check to CI (3 min)

```bash
python3 - <<'PY'
import io
p = ".github/workflows/ci.yml"
s = io.open(p, encoding="utf-8").read()
s += """
  wheel:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.11", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Build the wheel
        run: |
          pip install build
          python -m build --wheel
      - name: Install into a clean environment
        # No editable install, no source tree on the path: this proves the
        # published artefact works, not the working copy.
        run: pip install dist/*.whl
        shell: bash
      - name: Import from outside the source tree
        run: cd .. && python -c "import promptrecipe; print(promptrecipe.__version__)"
"""
io.open(p, "w", encoding="utf-8").write(s)
PY
grep -n "Install into a clean environment" .github/workflows/ci.yml
```
Expected: the step appears.

> Importing **from outside the source tree** is what makes this meaningful — an editable install in the project directory would pass even if packaging were broken.

### Step 5 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "build: pure-Python wheel, verified universal

py3-none-any: one wheel installs everywhere with no compiler. Asserted
rather than assumed, along with one runtime dependency, the 3.11 floor,
and tests staying out of the artefact. CI imports from outside the
source tree so it tests the artefact, not the working copy."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf dist README.md tests/test_packaging.py
```
