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
    p95 = ordered[min(int(len(ordered) * 0.95), len(ordered) - 1)]
    p99 = ordered[min(int(len(ordered) * 0.99), len(ordered) - 1)]

    ok = p99 <= budget_ms
    print(
        f"{'PASS' if ok else 'FAIL'}  {label:<6} p50={p50:7.3f}ms  p95={p95:7.3f}ms  "
        f"p99={p99:7.3f}ms  max={ordered[-1]:7.3f}ms  budget={budget_ms:.0f}ms"
    )
    return ok


def main() -> int:
    resolver, params = build()
    print(
        f"Recipe: {FRAGMENT_COUNT} fragments, "
        f"~{FRAGMENT_COUNT * FRAGMENT_SIZE // 1000} KB assembled, {ITERATIONS} iterations\n"
    )

    cold = measure(resolver, params, 1)
    get_prompt("core/recipe", params, resolver)  # warm anything cacheable
    warm = measure(resolver, params, ITERATIONS)

    ok = report("warm", warm, WARM_BUDGET_MS)
    ok = report("cold", cold, COLD_BUDGET_MS) and ok

    p50 = statistics.median(warm)
    print(
        f"\nAgainst a 500 ms model call, warm assembly is "
        f"{p50 / 500 * 100:.3f}% of end-to-end latency."
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
