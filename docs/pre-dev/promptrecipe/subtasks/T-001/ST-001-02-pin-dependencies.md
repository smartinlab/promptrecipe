# ST-001-02: Pin dependencies and lock the dev environment

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Prove every pinned version resolves as pinned, and lock the dev environment so CI installs exactly what you have.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 1 passed
```

**Files** — Create: `requirements-dev.lock`. Modify: `tests/test_smoke.py`

---

### Step 1 — Confirm exact resolved versions (2 min)

```bash
pip list --format=freeze | grep -iE "^(blake3|pytest|hypothesis|ruff|hatchling)="
```
Expected — these exact versions:
```
blake3==1.0.9
hypothesis==6.167.1
pytest==9.1.1
ruff==0.16.5
```
> If any differs, the `==` pin failed. Stop and investigate — a drifted dependency invalidates the audit in ST-001-03.

### Step 2 — RED: assert the runtime dependency actually works (2 min)

```bash
cat > tests/test_smoke.py <<'PY'
import promptrecipe


def test_package_imports():
    assert promptrecipe.__version__ == "0.1.0"


def test_the_single_runtime_dependency_resolves():
    """The only runtime dependency. If this breaks, the audit is moot."""
    import blake3

    digest = blake3.blake3(b"promptrecipe").hexdigest()
    assert len(digest) == 64
    # Determinism at the lowest level: same input, same digest.
    assert digest == blake3.blake3(b"promptrecipe").hexdigest()


def test_runtime_dependencies_are_exactly_one():
    """Guards a deliberate property: one runtime dependency.

    A second one is not forbidden forever, but adding it silently is.
    """
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    deps = pyproject["project"]["dependencies"]
    assert deps == ["blake3==1.0.9"], f"runtime dependencies changed: {deps}"
PY
```

### Step 3 — GREEN: run the tests (1 min)

```bash
pytest
```
Expected: `3 passed`

### Step 4 — Lock the dev environment (2 min)

```bash
pip freeze --exclude-editable > requirements-dev.lock
head -20 requirements-dev.lock
```
Expected: a flat list including `blake3==1.0.9`, `pytest==9.1.1`, `hypothesis==6.167.1`, `ruff==0.16.5`, and their transitive dependencies.

> A library does not ship a lockfile to consumers — `pyproject.toml` declares what they need. This lock exists so **CI installs exactly what you tested against**, which is what makes an audit result meaningful.

### Step 5 — Commit (1 min)

```bash
git add -A
git commit -m "build: pin dependencies exactly and lock the dev environment

blake3 1.0.9 (the only runtime dependency), pytest 9.1.1,
hypothesis 6.167.1, ruff 0.16.5. A test asserts the runtime dependency
list, so a second one cannot be added silently."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f requirements-dev.lock
```
