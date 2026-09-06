# ST-001-01: Initialize repository and package layout

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Create a version-controlled Python package that installs reproducibly, so every later subtask has a foundation that behaves identically everywhere.

**Prerequisites**
```bash
cd ~/promptrecipe && pwd
# Expected: ~/promptrecipe
python3 --version
# Expected: Python 3.11 or newer
```

**Files** — Create: `.gitignore`, `pyproject.toml`, `ruff.toml`, `src/promptrecipe/__init__.py`, `tests/test_smoke.py`

---

### Step 1 — Initialize the repository (2 min)

ADR-007 delegates review, history, and origin to version control. That delegation is void until this exists.

```bash
cd ~/promptrecipe
git init
git branch -M main
```
Expected: `Initialized empty Git repository in ~/promptrecipe/.git/`

### Step 2 — Create `.gitignore` (1 min)

```bash
cat > .gitignore <<'GITIGNORE'
__pycache__/
*.py[cod]
.venv/
venv/
build/
dist/
*.egg-info/
.pytest_cache/
.ruff_cache/
.hypothesis/
GITIGNORE
```

### Step 3 — Create `pyproject.toml` (2 min)

```bash
cat > pyproject.toml <<'TOML'
[build-system]
requires = ["hatchling==1.32.0"]
build-backend = "hatchling.build"

[project]
name = "promptrecipe"
version = "0.1.0"
description = "Compose prompts from path-addressed fragments, deterministically and attributably."
readme = "README.md"
license = "MIT OR Apache-2.0"
# Floor is 3.11, not 3.10: Python 3.10 reaches end-of-life in October 2026.
# Ceiling matches the optimization integration target's own constraint.
requires-python = ">=3.11,<3.15"
classifiers = [
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
]
# Exactly one runtime dependency. This is a deliberate property, not an accident.
dependencies = ["blake3==1.0.9"]

[project.optional-dependencies]
dev = [
    "pytest==9.1.1",
    "hypothesis==6.167.1",
    "ruff==0.16.5",
]

[tool.hatch.build.targets.wheel]
packages = ["src/promptrecipe"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
TOML
```

> **Why `==` on every version:** PROJECT_RULES prohibits ranges without documented justification. Exact pins make installs reproducible and drift visible.

### Step 4 — Create `ruff.toml` (1 min)

```bash
cat > ruff.toml <<'TOML'
target-version = "py311"
line-length = 100

[lint]
select = ["E", "F", "I", "UP", "B", "SIM", "S"]
# S101 (assert) is fine in tests.
[lint.per-file-ignores]
"tests/**" = ["S101"]
"scripts/**" = ["S101"]
TOML
```

> `S` is the security ruleset. It flags `eval`, `exec`, and `subprocess` misuse — the exact prohibitions in PROJECT_RULES, enforced by tooling rather than by memory.

### Step 5 — Create the package and a smoke test (2 min)

```bash
mkdir -p src/promptrecipe tests
cat > src/promptrecipe/__init__.py <<'PY'
"""promptrecipe — compose prompts from path-addressed fragments.

Invariants enforced throughout this package:
- All I/O is confined to the `custody` subpackage. Everything else is pure.
- Fragment content is never evaluated. It is inert text.
- Assembly is deterministic: identical inputs yield byte-identical output.
- `eval`, `exec`, `compile`, and `__import__` never appear in this package.
"""

__version__ = "0.1.0"
PY

cat > tests/test_smoke.py <<'PY'
import promptrecipe


def test_package_imports():
    assert promptrecipe.__version__ == "0.1.0"
PY
```

### Step 6 — Install and verify (2 min)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --quiet -e ".[dev]"
pytest
```
Expected: `1 passed`

### Step 7 — Commit (1 min)

```bash
git add -A
git commit -m "chore: initialize package, Python floor 3.11

Closes task-zero 0.1 and 0.2. ADR-007 delegates review and history to
version control; that delegation requires this repository to exist.
Floor is 3.11 because 3.10 reaches end-of-life in October 2026."
```

**Rollback**
```bash
rm -rf .git .venv src tests pyproject.toml ruff.toml .gitignore
```
