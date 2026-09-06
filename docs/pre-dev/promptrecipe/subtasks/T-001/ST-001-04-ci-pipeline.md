# ST-001-04: CI across the 3.11–3.14 matrix

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Make the audit recurring rather than one-off, and prove the package works on every supported Python.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate
python scripts/check_supply_chain.py && pytest
# Expected: PASS ...; 3 passed
```

**Files** — Create: `.github/workflows/ci.yml`

---

### Step 1 — Create the workflow (3 min)

```bash
mkdir -p .github/workflows
cat > .github/workflows/ci.yml <<'YAML'
name: CI

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Advisories are published after a version is pinned, so a one-off audit
    # goes stale. Re-run weekly against the same pinned versions.
    - cron: "0 6 * * 1"

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python: ["3.11", "3.12", "3.13", "3.14"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - name: Install
        run: pip install -e ".[dev]"
      - name: Lint
        run: ruff check .
      - name: Format check
        run: ruff format --check .
      - name: Test
        run: pytest

  supply-chain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: pip install -e ".[dev]" pip-audit
      - name: Audit
        run: pip-audit --strict --requirement requirements-dev.lock
      - name: Supply-chain assertions
        run: python scripts/check_supply_chain.py
YAML
```

> The matrix runs **3.11 and 3.14** as well as the middle versions deliberately: the floor and the ceiling are where incompatibilities appear, and testing only the middle hides both.

### Step 2 — Verify locally what CI will run (3 min)

```bash
ruff check . && ruff format --check . && pytest
```
Expected: no lint findings, no format differences, `3 passed`
> If `ruff format --check` reports differences, run `ruff format .` and re-check. Fixing it now avoids a red first CI run.

### Step 3 — Commit (1 min)

```bash
git add -A
git commit -m "ci: test across 3.11-3.14 on three platforms; weekly audit

Floor and ceiling are both in the matrix — that is where version
incompatibilities appear, and testing only the middle hides them."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf .github
```

---

## T-001 Definition of Done

- [ ] Repository initialized, `main` branch
- [ ] Package installs from a fresh clone with no manual steps
- [ ] Every dependency pinned exactly; dev environment locked
- [ ] **`pip-audit` reports zero critical and zero high findings** (or each documented as accepted risk)
- [ ] **Licences verified from package metadata**; the MPL-2.0 dev dependency asserted absent from the wheel
- [ ] **Exactly one runtime dependency**, asserted by test
- [ ] CI green on 3.11–3.14 across three platforms
