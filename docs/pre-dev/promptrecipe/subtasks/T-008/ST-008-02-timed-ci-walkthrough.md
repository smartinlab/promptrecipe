# ST-008-02: ⭐ Timed CI walkthrough that fails the build over 30 minutes

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Turn metric M11 from an aspiration into a test. Time-to-first-value is a **survival metric**, and survival metrics that live only in a document quietly rot.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && python examples/01_first_prompt.py
# Expected: prints the assembled prompt
```

**Files** — Create: `scripts/quickstart_walkthrough.py`, `tests/test_quickstart_budget.py`. Modify: `.github/workflows/ci.yml`

---

### Step 1 — Write the walkthrough (5 min)

It follows QUICKSTART.md literally, from an empty directory, and times itself.

```bash
cat > scripts/quickstart_walkthrough.py <<'PY'
"""Execute QUICKSTART.md end to end from an empty directory, and time it.

Enforces metric M11 (FR-028): a new user must reach a working assembled
prompt in under 30 minutes. Scripted time is a floor, not a simulation of a
human — but if the SCRIPTED path exceeds the budget, the human path has no
chance. Exits non-zero over budget so CI fails.

Requires no remote custody, no evaluation tooling, no optimization tooling.
"""

from __future__ import annotations

import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

BUDGET_SECONDS = 30 * 60


def main() -> int:
    print("Quickstart walkthrough — budget 30 minutes\n")
    overall = time.monotonic()

    def step(name: str, fn: Callable[[], None]) -> None:
        start = time.monotonic()
        fn()
        print(f"  [{time.monotonic() - start:6.2f}s] {name}")

    workdir = Path(tempfile.mkdtemp(prefix="promptrecipe-quickstart-"))
    prompts = workdir / "prompts"
    captured: dict[str, object] = {}

    # QUICKSTART step 2 — write two fragments.
    def write_fragments() -> None:
        prompts.mkdir(parents=True)
        (prompts / "role.md").write_text(
            "You are a technical support assistant for {{product}}.\n"
        )
        (prompts / "tone.md").write_text("Be concise. Lead with the answer.\n")

    step("write two fragments", write_fragments)

    # QUICKSTART step 3 — write a recipe.
    def write_recipe() -> None:
        (prompts / "recipe.md").write_text("[load core/role]\n[load core/tone]\n")

    step("write a recipe", write_recipe)

    # QUICKSTART step 4 — assemble it.
    def assemble() -> None:
        import promptrecipe
        from promptrecipe.assemble import Params
        from promptrecipe.custody.fs import FsCustody
        from promptrecipe.resolve import Resolver

        resolver = Resolver().register(
            "core", "fs", FsCustody().with_namespace("core", prompts)
        )
        captured["result"] = promptrecipe.get_prompt(
            "core/recipe", Params(values={"product": "Acme Cloud"}), resolver
        )

    step("assemble the prompt", assemble)

    result = captured["result"]
    assert "Acme Cloud" in result.text, "the value variable must be substituted"
    assert "Be concise." in result.text, "the second fragment must be present"
    assert len(result.fragments) == 2, f"expected 2 fragments, got {len(result.fragments)}"
    assert len(result.attestation.structural_identity) == 64

    # QUICKSTART step 5 — change once, see it propagate.
    def change_once() -> None:
        import promptrecipe
        from promptrecipe.assemble import Params
        from promptrecipe.custody.fs import FsCustody
        from promptrecipe.resolve import Resolver

        (prompts / "tone.md").write_text("Be thorough. Show your reasoning.\n")
        resolver = Resolver().register(
            "core", "fs", FsCustody().with_namespace("core", prompts)
        )
        again = promptrecipe.get_prompt(
            "core/recipe", Params(values={"product": "Acme Cloud"}), resolver
        )
        assert "Show your reasoning." in again.text, "the edit must propagate"
        assert (
            again.attestation.structural_identity != result.attestation.structural_identity
        )

    step("change one fragment and see it propagate", change_once)

    total = time.monotonic() - overall
    print(f"\nTotal scripted time: {total:.2f}s  (budget {BUDGET_SECONDS}s)")

    if total > BUDGET_SECONDS:
        print(
            f"\nFAIL: the quickstart took {total:.0f}s, over the {BUDGET_SECONDS}s budget.\n"
            "Metric M11 is a survival metric: Gate 0 established that the real\n"
            "competitor is copy-paste at zero switching cost, and nobody arrives\n"
            "holding 200 prompts. A product that only wins at scale never reaches\n"
            "scale. Do not raise the budget — shorten the path.",
            file=sys.stderr,
        )
        return 1

    print("PASS: first value is reachable within budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

python scripts/quickstart_walkthrough.py
```
Expected:
```
  [  0.00s] write two fragments
  [  0.00s] write a recipe
  [  0.0Xs] assemble the prompt
  [  0.0Xs] change one fragment and see it propagate

Total scripted time: 0.0Xs  (budget 1800s)
PASS: first value is reachable within budget.
```

> **The elapsed seconds are not the point** — a machine writing files is obviously fast. The point is that the script follows QUICKSTART.md **literally**, so it breaks the moment the documented path stops working. That drift is the real failure mode this guards.

### Step 2 — Prove the guard actually fires (3 min)

A test that cannot fail is not a test.

```bash
cat > tests/test_quickstart_budget.py <<'PY'
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
PY

pytest tests/test_quickstart_budget.py
```
Expected: `2 passed`

### Step 3 — Wire it into CI (2 min)

```bash
python3 - <<'PY'
import io
p = ".github/workflows/ci.yml"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""      - name: Test
        run: pytest""",
"""      - name: Test
        run: pytest
      - name: Quickstart walkthrough (metric M11 — fails over 30 minutes)
        run: python scripts/quickstart_walkthrough.py""", 1)
io.open(p, "w", encoding="utf-8").write(s)
PY
grep -n "M11" .github/workflows/ci.yml
```
Expected: the step appears.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "ci: timed quickstart walkthrough enforcing metric M11

The script follows QUICKSTART.md literally, so it breaks when the
documented path stops working — the drift this actually guards. The
budget guard is verified to fire rather than trusted."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f scripts/quickstart_walkthrough.py tests/test_quickstart_budget.py
```

---

## T-008 Definition of Done

- [ ] QUICKSTART.md takes someone from nothing to an assembled prompt
- [ ] Two runnable examples; the second **demonstrates** change-once propagation rather than describing it
- [ ] The quickstart needs no remote custody, no evaluation, no optimization tooling
- [ ] **The timed walkthrough runs in CI and fails the build over 30 minutes**
- [ ] **The budget guard is verified to fire** — a test that cannot fail is not a test
- [ ] Quickstart documents which identity to use for comparison vs reproduction

---

## Phase 1 complete

`get_prompt` returns a correct, deterministic, attributable prompt; properties
**P1** (determinism) and **P2** (order-aware structural identity) are
established; the **performance budget is measured, not estimated**; the wheel
installs everywhere with no compiler; and a new user reaches first value
inside the budget.

**Next:** generate subtasks for T-009 onward when Phase 2 begins — against the
real codebase, which is the context subtasks are meant to be written with.
