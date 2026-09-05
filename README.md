# promptrecipe

A prompt-template library. A **recipe** is a template whose variables resolve to
reusable **fragments** addressed by path; conditions decide which fragments load,
in what order, and at which version. Composing them produces the final prompt.

```python
result = promptrecipe.get_prompt("core/recipe.claude", params, resolver)
agent = Agent(system_prompt=result.text)  # the caller never sees a fragment
```

**Status: planning complete, implementation not started.**

This repository currently contains only the pre-dev artifacts. The first code
commit is [ST-001-01](docs/pre-dev/promptrecipe/subtasks/T-001/ST-001-01-init-repo-and-package.md),
which creates the package layout. This README is replaced by the real one at
[ST-007-01](docs/pre-dev/promptrecipe/subtasks/T-007/ST-007-01-packaging.md).

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

## Known open items

- `pip-audit` has never run against the pinned versions — [ST-001-03](docs/pre-dev/promptrecipe/subtasks/T-001/ST-001-03-audit-and-licenses.md), blocking before code.
- None of the planned code has been executed. The first `pytest` is the real verification.
- Remote custody without version control inherits no review — blocks T-026 (Phase 4), needs a product decision.
