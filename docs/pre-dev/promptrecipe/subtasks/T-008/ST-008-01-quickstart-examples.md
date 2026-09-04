# ST-008-01: Quickstart and two runnable examples

> **For Agents:** REQUIRED SUB-SKILL: Use `souschef:executing-plans`

**Goal:** Get someone from nothing to a working assembled prompt, then show them the promise — change one fragment, watch it propagate.

**Why this is P0 and not documentation polish:** Gate 0 established that the real competitor is copy-paste at **zero switching cost**. Nobody arrives holding 200 prompts. A product that only demonstrates value at scale never reaches scale.

**Prerequisites**
```bash
cd /Users/michael.martim/fontes/promptrecipe && . .venv/bin/activate && pytest
# Expected: 128 passed
```

**Files** — Create: `QUICKSTART.md`, `examples/fragments/*.md`, `examples/01_first_prompt.py`, `examples/02_change_once.py`

---

### Step 1 — Create the example fragments and recipes (3 min)

```bash
mkdir -p examples/fragments
cat > examples/fragments/role.md <<'MD'
You are a technical support assistant for {{product}}.
MD
cat > examples/fragments/tone.claude.md <<'MD'
Be concise. Lead with the answer.
MD
cat > examples/fragments/tone.gpt.md <<'MD'
Be thorough. Explain your reasoning step by step.
MD
cat > examples/fragments/safety.md <<'MD'
Never invent product features that do not exist.
MD
cat > examples/fragments/recipe.claude.md <<'MD'
[load core/role]
[load core/tone.claude]
[load core/safety]
MD
cat > examples/fragments/recipe.gpt.md <<'MD'
[load core/role]
[load core/tone.gpt]
[load core/safety]
MD
```

### Step 2 — Example 1: a prompt from three fragments (3 min)

```bash
cat > examples/01_first_prompt.py <<'PY'
"""Example 1 — your first assembled prompt.

    python examples/01_first_prompt.py
"""

from pathlib import Path

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

FRAGMENTS = Path(__file__).parent / "fragments"

resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", FRAGMENTS))
result = promptrecipe.get_prompt(
    "core/recipe.claude",
    Params(values={"product": "Acme Cloud"}),
    resolver,
)

print("--- assembled prompt ---")
print(result.text)
print("--- what produced it ---")
for path, fragment_id in result.fragments:
    print(f"  {path:<24} {fragment_id.short}")

att = result.attestation
print(f"\nstructural identity: {att.structural_identity[:16]}…  (compare A/B by this)")
print(f"instance identity:   {att.instance_identity[:16]}…  (reproduce exact text from this)")
PY

python examples/01_first_prompt.py
```
Expected: the assembled prompt, the three fragments with their short identities, and both identities.

### Step 3 — Example 2: change once, propagate everywhere (4 min)

```bash
cat > examples/02_change_once.py <<'PY'
"""Example 2 — the promise: fix one fragment, every recipe using it updates.

Two model variants share `core/safety`. Editing that one file changes BOTH,
because they reference the same fragment rather than each holding a copy.

    python examples/02_change_once.py
"""

from pathlib import Path

import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

FRAGMENTS = Path(__file__).parent / "fragments"
SAFETY = FRAGMENTS / "safety.md"


def assemble(recipe: str):
    resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", FRAGMENTS))
    return promptrecipe.get_prompt(recipe, Params(values={"product": "Acme Cloud"}), resolver)


original = SAFETY.read_text()
try:
    before_claude = assemble("core/recipe.claude")
    before_gpt = assemble("core/recipe.gpt")

    shared_before = dict(before_claude.fragments)["core/safety"]
    assert shared_before == dict(before_gpt.fragments)["core/safety"]
    print(f"Both variants share core/safety at {shared_before.short}")

    # Edit ONE file.
    SAFETY.write_text("Never invent features. Always cite the documentation page.\n")

    after_claude = assemble("core/recipe.claude")
    after_gpt = assemble("core/recipe.gpt")

    shared_after = dict(after_claude.fragments)["core/safety"]
    print(f"After one edit, both share      {shared_after.short}")

    assert "cite the documentation page" in after_claude.text
    assert "cite the documentation page" in after_gpt.text
    assert shared_after != shared_before

    print("\nOne edit. Both model variants updated. No copies to hunt down.")
finally:
    SAFETY.write_text(original)
PY

python examples/02_change_once.py
```
Expected: ends with `One edit. Both model variants updated. No copies to hunt down.`

### Step 4 — Write the quickstart (4 min)

```bash
cat > QUICKSTART.md <<'MD'
# promptrecipe — quickstart

Assemble prompts from named, reusable fragments. Fix a shared instruction
once instead of hunting every copy.

**Target: a working assembled prompt in under 30 minutes.** CI enforces this.

---

## 1. Install

```bash
pip install promptrecipe
```

Pure Python, one dependency, no compiler. Requires Python 3.11+.

## 2. Write two fragments

A fragment is a plain text file. One fragment per file, so a review shows one
change at a time.

```bash
mkdir -p prompts
printf 'You are a technical support assistant for {{product}}.\n' > prompts/role.md
printf 'Be concise. Lead with the answer.\n'                      > prompts/tone.md
```

## 3. Write a recipe

A recipe declares which fragments to load, by path.

```bash
printf '[load core/role]\n[load core/tone]\n' > prompts/recipe.md
```

## 4. Assemble it

```python
import promptrecipe
from promptrecipe.assemble import Params
from promptrecipe.custody.fs import FsCustody
from promptrecipe.resolve import Resolver

resolver = Resolver().register("core", "fs", FsCustody().with_namespace("core", "prompts"))
result = promptrecipe.get_prompt("core/recipe", Params(values={"product": "Acme"}), resolver)

print(result.text)
```

Hand `result.text` to your agent — it needs to know nothing about fragments.

## 5. See the promise

Edit `prompts/tone.md`. Run again. Every recipe using that fragment changed.
No copies to find.

---

## Three variables, three jobs

|            | What it does                     | Affects   |
|------------|----------------------------------|-----------|
| `controls` | feeds `[if ...]` conditions      | structure |
| `addresses`| its value is a **fragment path** | structure |
| `values`   | substituted as literal text      | content   |

A value is inserted as text and **never interpreted** — it cannot change
which fragments load.

## Two identities, and which to use

| Identity                            | Use it to                                    |
|-------------------------------------|----------------------------------------------|
| `attestation.structural_identity`   | **compare** — group A/B results by this      |
| `attestation.instance_identity`     | **reproduce** — recover exact text from this |

They differ deliberately. Two runs of the same prompt design for different
customers share a *structural* identity and differ in *instance* identity —
comparable as one variant, reproducible as two renderings.

> Comparing by `instance_identity` groups nothing, because every call is
> unique. If your A/B results all stand alone, this is why.

## Next

- Conditional loading: `[if model == "claude"] [load core/tone.claude]`
- Model variants: separate recipes sharing the fragments that do not change
- Expectations: `[expect language in ["pt", "en"]]` — fails before any output
MD
```

### Step 5 — Commit (1 min)

```bash
git add -A
git commit -m "docs: quickstart and two runnable examples

Example 2 demonstrates the core promise rather than describing it: one
edit, both model variants updated. Documents which identity to use for
comparison versus reproduction — the most likely misuse."
```

**Rollback**
```bash
git reset --hard HEAD~1 && rm -rf QUICKSTART.md examples
```
