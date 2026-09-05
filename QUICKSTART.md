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

Two runs of the same prompt design for different customers share a
*structural* identity and differ in *instance* identity — comparable as one
variant, reproducible as two renderings.

> Comparing by `instance_identity` groups nothing, because every call is
> unique. If your A/B results all stand alone, this is why.

## Model variants

Name fragments with dots and keep one recipe per model. Both reference the
same shared fragments, so a fix to `core/safety` corrects both:

```
[load core/role]
[load core/tone.claude]     # recipe.claude.md
[load core/safety]
```

## Next

- Conditional loading: `[if model == "claude"] [load core/tone.claude]`
- Expectations: `[expect language in ["pt", "en"]]` — fails before any output
