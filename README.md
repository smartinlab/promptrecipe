# promptrecipe

A prompt-template library. A **recipe** is a template whose variables resolve to
reusable **fragments** addressed by path; conditions decide which fragments load,
in what order, and at which version. Composing them produces the final prompt.

```python
result = promptrecipe.get_prompt("core/recipe.claude", params, resolver)
agent = Agent(system_prompt=result.text)  # the caller never sees a fragment
```

**Status: Phase 1 complete.** `get_prompt` works, is deterministic, and every
assembly is attributable. Python 3.11+, one runtime dependency, pure-Python
wheel. See [QUICKSTART.md](QUICKSTART.md).

Phase 2 onward (reproduction from a record, span mapping, dependency queries,
evaluation and optimization adapters, remote custody) is planned in
[tasks.md](docs/pre-dev/promptrecipe/tasks.md) — tasks T-009 to T-027.

## The plan

| Artifact | What it settles |
|---|---|
| [research.md](docs/pre-dev/promptrecipe/research.md) | 17 competing tools surveyed; the two structural gaps nobody fills |
| [brd.md](docs/pre-dev/promptrecipe/brd.md) | Jobs, personas, outcomes — trust and traceability outrank composition |
| [sbp.md](docs/pre-dev/promptrecipe/sbp.md) | 6 modules, 14 structural decisions |
| [prd.md](docs/pre-dev/promptrecipe/prd.md) | 38 requirements, 28 user stories |
| [feature-map.md](docs/pre-dev/promptrecipe/feature-map.md) | Domains, journeys, 4 phases |
| [trd.md](docs/pre-dev/promptrecipe/trd.md) | Architecture, 7 ADRs — technology-agnostic |
| [dependency-map.md](docs/pre-dev/promptrecipe/dependency-map.md) | Python 3.11+, one runtime dependency |
| [tasks.md](docs/pre-dev/promptrecipe/tasks.md) | 27 tasks; 7 on the critical path to first value |
| [subtasks.md](docs/pre-dev/promptrecipe/subtasks.md) | 30 zero-context steps for T-001…T-008 |
| [PROJECT_RULES.md](docs/PROJECT_RULES.md) | Stack and prohibitions |

## Four properties that must never regress

| | Property | Established by |
|---|---|---|
| **P1** | Determinism — identical inputs, byte-identical output, across processes | ST-005-04, ST-005-05 |
| **P2** | Order-aware identity — reordering fragments changes the structural identity | ST-006-04 |
| **P3** | Fragment content is never evaluated | ST-003-02, ST-002-04 |
| **P4** | No partial output on any failure path | ST-005-01 |

## Measured, not assumed

| | Result |
|---|---|
| Assembly, warm p99 | **0.842 ms** against a 10 ms budget — 0.14% of a 500 ms model call |
| Dependency audit | `pip-audit` clean; licences verified from package metadata |
| Determinism | identical output across processes with distinct hash seeds |
| Wheel | `py3-none-any` — one artefact, every platform, no compiler |

## Known open items

- Remote custody without version control inherits no review — blocks T-026 (Phase 4), needs a product decision.
- Coverage tooling is not pinned; `pytest-cov` was deliberately deferred rather than added unpinned.
