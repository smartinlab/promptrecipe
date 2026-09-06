# ST-005-06: ⭐ Benchmark against the <10 ms budget

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Settle the host-language question with a **measurement** instead of an estimate.

**Why this subtask exists.** The stack was changed from a compiled core to pure Python on the reasoning that assembly costs well under 1 ms warm against a <10 ms budget (TRD §8), and is invisible beside 500 ms–30 s of model latency. **That reasoning was an estimate.** This subtask measures it and fails if the budget is missed. If it does fail, the four never-regress properties make a compiled-core port *verifiable* rather than speculative — so a failure here is recoverable, not fatal.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 99 passed
```

**Files** — Create: `scripts/benchmark.py`, `tests/test_performance_budget.py`

---

### Step 1 — Write the benchmark (5 min)

```bash
cat > scripts/benchmark.py <<'PY'
"""Measure the assembly path against the TRD §8 budget.

Budgets under test:
  - warm assembly, ~50-fragment recipe:  < 10 ms
  - cold assembly (parse included):      < 200 ms

Reports a full distribution rather than a mean: a mean hides the tail, and a
p99 spike on the request path of an agent call is what a user actually feels.
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from conftest import MemoryCustody  # noqa: E402

from promptrecipe import get_prompt  # noqa: E402
from promptrecipe.assemble import Params  # noqa: E402
from promptrecipe.resolve import Resolver  # noqa: E402

FRAGMENT_COUNT = 50
FRAGMENT_SIZE = 1000  # characters, so the assembled prompt is ~50 KB
WARM_BUDGET_MS = 10.0
COLD_BUDGET_MS = 200.0
ITERATIONS = 200


def build() -> tuple[Resolver, Params]:
    body = "x" * FRAGMENT_SIZE
    entries = {f"core/f{i}": f"FRAGMENT-{i} {body}" for i in range(FRAGMENT_COUNT)}
    recipe = ["Header {{customer}}\n"]
    recipe += [f"[if flag{i}] [load core/f{i}]\n" for i in range(FRAGMENT_COUNT)]
    recipe.append("Footer {{customer}}\n")
    entries["core/recipe"] = "".join(recipe)

    resolver = Resolver().register("core", "mem", MemoryCustody(entries))
    params = Params(
        controls={f"flag{i}": True for i in range(FRAGMENT_COUNT)},
        values={"customer": "Acme Corporation"},
    )
    return resolver, params


def measure(resolver: Resolver, params: Params, iterations: int) -> list[float]:
    timings = []
    for _ in range(iterations):
        start = time.perf_counter()
        get_prompt("core/recipe", params, resolver)
        timings.append((time.perf_counter() - start) * 1000.0)
    return timings


def report(label: str, timings: list[float], budget_ms: float) -> bool:
    ordered = sorted(timings)
    p50 = statistics.median(ordered)
    p95 = ordered[int(len(ordered) * 0.95)]
    p99 = ordered[min(int(len(ordered) * 0.99), len(ordered) - 1)]
    worst = ordered[-1]

    ok = p99 <= budget_ms
    status = "PASS" if ok else "FAIL"
    print(
        f"{status}  {label:<8} p50={p50:7.3f}ms  p95={p95:7.3f}ms  "
        f"p99={p99:7.3f}ms  max={worst:7.3f}ms  budget={budget_ms:.0f}ms"
    )
    return ok


def main() -> int:
    resolver, params = build()
    print(
        f"Recipe: {FRAGMENT_COUNT} fragments, ~{FRAGMENT_COUNT * FRAGMENT_SIZE // 1000} KB "
        f"assembled, {ITERATIONS} iterations\n"
    )

    cold = measure(resolver, params, 1)
    get_prompt("core/recipe", params, resolver)  # warm anything cacheable
    warm = measure(resolver, params, ITERATIONS)

    ok = report("warm", warm, WARM_BUDGET_MS)
    ok = report("cold", cold, COLD_BUDGET_MS) and ok

    p50 = statistics.median(warm)
    print(
        f"\nAgainst a 500 ms model call, warm assembly is {p50 / 500 * 100:.3f}% "
        f"of end-to-end latency."
    )

    if not ok:
        print(
            "\nFAIL: the assembly path missed its budget.\n"
            "This is the measurement the host-language decision rests on. If it\n"
            "cannot be closed by caching the parse or removing per-call work, the\n"
            "compiled-core option returns — and properties P1-P4 make that port\n"
            "verifiable rather than speculative.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY

python scripts/benchmark.py
```
Expected: something close to
```
Recipe: 50 fragments, ~50 KB assembled, 200 iterations

PASS  warm     p50=  0.4xx ms  p95=  0.5xx ms  p99=  0.6xx ms  max=  1.xxx ms  budget=10ms
PASS  cold     p50=  2.xxx ms  ...                                             budget=200ms

Against a 500 ms model call, warm assembly is 0.0xx% of end-to-end latency.
```

> **Record the real numbers.** If warm p99 lands anywhere near 10 ms, the estimate was wrong and that is worth knowing now rather than after Phase 2.

### Step 2 — Turn it into a CI test (3 min)

```bash
cat > tests/test_performance_budget.py <<'PY'
"""The TRD §8 performance budget, enforced.

Asserts p99, not mean: a mean hides the tail, and a tail spike on the
request path of an agent call is what a user actually feels.

The budget is deliberately generous relative to the measured cost, so this
test catches a REGRESSION (an accidental O(n^2), a per-call re-parse) rather
than failing on ordinary CI-runner noise.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "benchmark.py"


def test_assembly_meets_the_performance_budget():
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"the assembly path missed its budget:\n{result.stdout}\n{result.stderr}"
    )
    assert "PASS  warm" in result.stdout
PY

pytest tests/test_performance_budget.py
```
Expected: `1 passed`

### Step 3 — Add it to CI (2 min)

```bash
python3 - <<'PY'
import io
p = ".github/workflows/ci.yml"
s = io.open(p, encoding="utf-8").read()
s = s.replace("""      - name: Test
        run: pytest""",
"""      - name: Test
        run: pytest
      - name: Performance budget (TRD §8)
        # Runs on one interpreter only: a benchmark across the full matrix
        # measures runner noise more than it measures this library.
        if: matrix.python == '3.12' && matrix.os == 'ubuntu-latest'
        run: python scripts/benchmark.py""")
io.open(p, "w", encoding="utf-8").write(s)
PY
grep -n "Performance budget" .github/workflows/ci.yml
```
Expected: the step appears.

### Step 4 — Record the result where the decision lives (2 min)

```bash
python scripts/benchmark.py 2>&1 | tee /tmp/promptrecipe-bench.txt
```

> Paste the measured p50/p95/p99 into `docs/pre-dev/promptrecipe/dependency-map.md` under Decision 2, replacing the estimate table's caveat. **The decision then rests on a number rather than on an argument** — which is the whole point of this subtask.

### Step 5 — Commit (1 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test: enforce the TRD §8 performance budget

Settles the host-language question with a measurement. Asserts p99
rather than mean, because a tail spike on an agent's request path is
what a user feels. The budget is generous relative to measured cost, so
this catches regressions rather than CI noise."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f scripts/benchmark.py tests/test_performance_budget.py
```

---

## T-005 Definition of Done

- [ ] `get_prompt(recipe_path, params, resolver)` returns assembled text
- [ ] Assembly is pure over what custody returned (ADR-001)
- [ ] **Value substitution runs last and its output is never re-parsed** — `grep` confirms one call site immediately before the return (ADR-006)
- [ ] Injected directive-shaped text loads nothing
- [ ] **Property P1 green** — byte-identical, no drift, insertion-order independent
- [ ] **Cross-process determinism green** with forced distinct hash seeds
- [ ] **Performance budget green, and the real numbers recorded in the Dependency Map**
- [ ] `grep` confirms no clock, environment, randomness, locale casing, or set iteration in the assembly path
