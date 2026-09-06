# Contributing

Thanks for looking. This is a small library with strong opinions, so the most
useful thing this document can do is tell you which opinions are load-bearing
before you spend time on a change that cannot be merged.

## Four properties that must never regress

These are not style preferences. Each guards a failure mode the library exists
to make impossible, and each has property tests that will fail loudly.

| | |
|---|---|
| **Determinism** | Identical inputs produce byte-identical output and identical identities, **across processes**. No wall clock, no environment, no locale-sensitive comparison, and no output ordering derived from map or set iteration. |
| **Order-aware structural identity** | Permuting fragment order changes the structural identity. An order-blind identity corrupts every comparison *without ever erroring* — the worst kind of bug. |
| **Fragment content is never evaluated** | A fragment is inert text. It may name a sibling with `[load namespace/path]` and nothing more. This is the security guarantee, and it is what makes optimizer-written fragments safe to store. |
| **No partial output on failure** | Every failure path emits nothing. A half-assembled prompt that looks plausible is worse than an error. |

## Decisions that are settled

Please do not open a PR that reverses one of these without discussing it
first. Each was decided deliberately and the reasoning is written down.

- **Value substitution runs last and is never re-parsed** (ADR-006). The
  ordering *is* the security property: a caller-supplied value cannot change
  which fragments loaded, in what order, or at what version.
- **Ambiguity is an error, never a silent pick** (ADR-004). Namespace
  isolation, not first-match-wins.
- **Custody is the consuming project's repository.** Review, history, and
  origin are delegated to version control and are not reimplemented here.
- **The library never executes a prompt and never scores a result** (SD10).
- **Integrations stay optional and thin.** Nothing in the core imports them.
- **One runtime dependency.** A new one needs a real argument.

## Getting set up

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest          # 332 tests, a few seconds
.venv/bin/ruff check .
```

Both must pass before a commit. The evaluation integration has its own
runner, because promptfoo spawns `python3` from PATH rather than your venv:

```bash
integrations/promptfoo/run_eval.sh
```

## What a good change looks like

Write the failing test first. It is not ceremony here: several real bugs in
this codebase were caught only by executing the thing rather than reading it —
a lexer that closed a directive at the first `]` inside a list, a conditional
that leaked a blank line, a path helper that turned `recipe.claude` into
`recipe.md`. Unit tests missed the last one because the fixture used in-memory
custody keyed on strings.

Comments should explain **why**, not narrate what the line does. If a comment
would only restate the code, leave it out; if a decision would surprise the
next reader, write it down.

## Licence

Contributions are accepted under the [MIT licence](LICENSE), the same terms
the project ships under.

## Reporting a bug

The most useful report contains the recipe, the fragments, the params, and
what you got instead of what you expected. If assembly succeeded but produced
the wrong text, include `result.attestation` — it names every fragment and
every condition outcome that produced it, which usually locates the problem
immediately.
