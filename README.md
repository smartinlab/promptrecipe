# promptrecipe

A prompt is text you assemble, not a string you paste. A **recipe** declares
which **fragments** to load — reusable pieces addressed by path — and under
what conditions. Every assembly carries a record of exactly what produced it.

```python
import promptrecipe
from promptrecipe import Params, resolver_from_config

resolver = resolver_from_config("promptrecipe.toml")

result = promptrecipe.get_prompt(
    "core/agent.claude",
    Params(
        controls={"tier": "enterprise", "language": "pt-br"},  # decide STRUCTURE
        values={"product": "Acme Cloud"},  # fill CONTENT
    ),
    resolver,
)

agent = Agent(system_prompt=result.text)  # the caller never sees a fragment
```

**Status:** phases 1 and 2 complete, plus both integrations. 286 tests.
Python 3.11+, **one runtime dependency**, pure-Python wheel.
Start at [QUICKSTART.md](QUICKSTART.md).

## What it does

| | |
|---|---|
| **Change once** | A repeated instruction is one fragment. Fix it once; every recipe using it follows. |
| **Port across models** | `agent.claude` and `agent.gpt` share the fragments that do not differ — by reference, not by copy. |
| **Condition, order, select** | `[if model == "claude"][load core/tone.claude]`, `[order: role, tone, safety]`. Ordering and version selection reuse the same condition mechanism — there is no second subsystem. |
| **Attribute every result** | Two identities per assembly: **structural** (group A/B by this) and **instance** (reproduce exact text from this). One digest cannot serve both. |
| **Fail loudly** | An ambiguous reference, a cycle, a missing binding, a violated expectation — all errors, never a silent pick. |

## A library on disk

```
promptrecipe.toml          declares the namespaces
prompts/
  core/identity.md         one fragment, one file
  core/tone.claude.md      `tone.claude` and `tone.gpt` fill the same slot
  core/agent.claude.md     a recipe is a list of [load] directives
  policy/refusal.md        a fragment may reference a sibling
```

Fragments are plain text. Markdown survives untouched — the `.md` extension is
a convention that makes editors and diffs read better, nothing is parsed.

See [examples/support-agent](examples/support-agent) for a full library, and
`python examples/support-agent/build_prompt.py` to watch it assemble.

## Integrations

Both live in an optional subpackage the core never imports, and both are
declared as extras. Neither may become load-bearing.

| | |
|---|---|
| **Evaluation** | Recipes *and* individual fragments become evaluable units. With the pass-through provider, prompt-content assertions cost **zero model calls**. Verified: 6 cases, 38 assertions, all passing. |
| **Optimization** | Seed a fragment's text; take improved text back as a **proposal with a diff**. Never written to custody — accepting a change is version control's job. Per-fragment only: a whole-recipe result carries no sub-fragment attribution. |

See [integrations/promptfoo](integrations/promptfoo).

## Four properties that must never regress

| | Property |
|---|---|
| **P1** | Determinism — identical inputs, byte-identical output, **across processes** |
| **P2** | Order-aware identity — reordering fragments changes the structural identity |
| **P3** | Fragment content is never evaluated |
| **P4** | No partial output on any failure path |

P2 guards a silent failure: an order-blind identity raises no error, it just
groups two different prompts as one and quietly corrupts every comparison.

## Measured, not assumed

| | Result |
|---|---|
| Assembly, warm p99 | **0.967 ms** against a 10 ms budget — 0.14% of a 500 ms model call |
| Dependency audit | `pip-audit` clean; licences read from package metadata |
| Determinism | identical across processes with distinct `PYTHONHASHSEED` |
| Wheel | `py3-none-any` — one artefact, every platform, no compiler |
| First value | a scripted walkthrough of QUICKSTART.md, timed in CI |

## What is not built yet

Phase 3 — the trust layer, and the highest-opportunity job in the plan:

- **T-018** reproduce an assembly byte-identically from its record
- **T-019** span map: which fragment produced which portion of the output
- **T-020** bind an external result to exactly one assembly
- **T-021** list every recipe depending on a fragment, **without assembling**
- **T-022** preview a change's effect on each dependent

Phase 4 — custody:

- **T-025** version-controlled custody
- **T-026** remote custody — ⚠️ **blocked on a product decision, not on
  engineering**: remote custody without version control inherits no review,
  and the TRD deliberately chose neither remedy.

## How this was built

Planned before it was written: nine pre-dev gates producing research, a BRD,
a system picture, a PRD, a feature map, a TRD with seven ADRs, a dependency
map, tasks and subtasks. All of it is in [docs/pre-dev](docs/pre-dev/promptrecipe).

[NOTES.md](NOTES.md) is the earlier history — the first attempt, why a
ready-made template engine did not survive contact with the problem, and what
was kept when it was rewritten. It is still why the design looks the way it
does.

| Artifact | What it settles |
|---|---|
| [research.md](docs/pre-dev/promptrecipe/research.md) | 17 competing tools surveyed; the two structural gaps nobody fills |
| [brd.md](docs/pre-dev/promptrecipe/brd.md) | Jobs and outcomes — trust and traceability outrank composition |
| [sbp.md](docs/pre-dev/promptrecipe/sbp.md) | 6 modules, 14 structural decisions |
| [prd.md](docs/pre-dev/promptrecipe/prd.md) | 38 requirements, 28 user stories |
| [trd.md](docs/pre-dev/promptrecipe/trd.md) | Architecture, 7 ADRs, technology-agnostic |
| [dependency-map.md](docs/pre-dev/promptrecipe/dependency-map.md) | Why pure Python, measured rather than argued |
| [tasks.md](docs/pre-dev/promptrecipe/tasks.md) | 27 tasks; 20 done |
| [PROJECT_RULES.md](docs/PROJECT_RULES.md) | Stack and prohibitions |
