# ST-005-05: ⭐ Cross-process determinism

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Catch the class of nondeterminism that is **invisible within a single process**. Python randomizes its string hash seed per process (`PYTHONHASHSEED`), so any code that leaks hash order produces a *consistent* order within one run and a *different* one in the next. ST-005-04 cannot see that. This can.

**Prerequisites**
```bash
cd ~/promptrecipe && . .venv/bin/activate && pytest
# Expected: 98 passed
```

**Files** — Create: `scripts/assemble_once.py`, `tests/test_cross_process_determinism.py`

---

### Step 1 — Write a script that assembles once and prints a digest (3 min)

```bash
mkdir -p scripts
cat > scripts/assemble_once.py <<'PY'
"""Assemble a fixed recipe once and print the digest of the result.

Used by the cross-process determinism test. Each run is a fresh process with
a fresh hash seed, so two runs printing the same digest is evidence that no
per-process state reached the output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))

from conftest import MemoryCustody  # noqa: E402

from promptrecipe import get_prompt  # noqa: E402
from promptrecipe.assemble import Params  # noqa: E402
from promptrecipe.identity import FragmentId  # noqa: E402
from promptrecipe.resolve import Resolver  # noqa: E402

# Many fragments and many bindings: the more there are, the more likely a
# hash-ordered iteration would show up as a different order.
COUNT = 24


def main() -> int:
    entries = {f"core/f{i}": f"FRAGMENT-{i}" for i in range(COUNT)}
    recipe = ["Header {{customer}}\n"]
    recipe += [f"[if flag{i}] [load core/f{i}]\n" for i in range(COUNT)]
    recipe.append("Footer {{customer}}\n")
    entries["core/recipe"] = "".join(recipe)

    resolver = Resolver().register("core", "mem", MemoryCustody(entries))
    params = Params(
        controls={f"flag{i}": (i % 3 != 0) for i in range(COUNT)},
        values={"customer": "Acme Corporation"},
    )

    out = get_prompt("core/recipe", params, resolver)
    print(FragmentId.of(out.text.encode("utf-8")).hex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY
```

### Step 2 — Verify by hand that two processes agree (2 min)

```bash
python scripts/assemble_once.py
python scripts/assemble_once.py
```
Expected: **the same 64-character hex digest twice.**

> Two different digests here is the highest-severity finding in this task list. It means output depends on per-process state, and every provenance record the library would ever write is untrustworthy. Do not proceed — find the source first.

### Step 3 — Automate it, with hash randomization forced on (4 min)

```bash
cat > tests/test_cross_process_determinism.py <<'PY'
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
    env = {**os.environ, "PYTHONHASHSEED": seed}
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        env=env,
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
PY

pytest tests/test_cross_process_determinism.py
```
Expected: `1 passed`

> Forcing `PYTHONHASHSEED=0`, `1`, and `random` is what makes this test *reliable* rather than lucky. Without it, two runs might happen to draw the same seed and the bug would hide.

### Step 4 — Lint and commit (2 min)

```bash
ruff check . && ruff format . && git add -A
git commit -m "test: cross-process determinism with forced hash seeds

Python's hash seed is per-process, so hash-ordered iteration looks
stable within one run and differs between runs. Forcing distinct
PYTHONHASHSEED values makes the test reliable rather than lucky."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -f tests/test_cross_process_determinism.py scripts/assemble_once.py
```
