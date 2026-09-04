# Subtasks: promptrecipe — Critical Path (T-001 … T-008)

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 8 — Subtask Creation (final gate of the full track) |
| **Scope** | **T-001 … T-008 only** — Phase 0 + Phase 1, the critical path to first validated value |
| **Subtask files** | `docs/pre-dev/promptrecipe/subtasks/T-XXX/ST-XXX-NN-*.md` |
| **Status** | Draft — **revision 2 (Python-only)**, pending human approval |
| **Confidence Score** | 84/100 |
| **Language** | en |

> ### Scoping decision — stated explicitly
>
> This gate covers **only the eight critical-path tasks**. Subtasks for **T-009 … T-027 were deliberately not generated**, at the stakeholder's direction: they would specify implementation details against code that does not exist yet, and would age before anyone read them. Generate them **when each phase begins**, using the real codebase as context — which is exactly the situation subtasks are meant for.
>
> The remaining 19 tasks are fully specified as *tasks* in `tasks.md`; only their step-level decomposition is deferred.

**Stack (pinned, Gate 6 revision 2, verified 2026-08-31):** Python floor **3.11**, ceiling `<3.15`, matrix 3.11–3.14 · `blake3` **1.0.9** — *the only runtime dependency* · `pytest` 9.1.1 · `hypothesis` 6.167.1 · `ruff` 0.16.5 · `hatchling` 1.32.0. Everything else is the standard library.

**Prohibited throughout:** template engine · parser generator · version-control library · object-store client · async framework · logging framework · serialization library · **`eval` / `exec` / `compile` / `__import__` anywhere in the library**.

---

## Planned Package Layout

```
promptrecipe/
├── pyproject.toml                   hatchling; deps pinned exactly
├── ruff.toml                        lint + format config
├── src/promptrecipe/
│   ├── __init__.py                  public surface: get_prompt
│   ├── errors.py                    every failure variant
│   ├── identity.py                  FragmentId — BLAKE3 content identity
│   ├── paths.py                     canonicalization + namespace confinement
│   ├── custody/
│   │   ├── __init__.py              the Custody protocol  ← ONLY I/O in the package
│   │   ├── fs.py                    local filesystem adapter
│   │   └── cache.py                 identity-keyed cache
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── lexer.py                 tokens + positions
│   │   ├── nodes.py                 closed grammar — the security boundary
│   │   └── parse.py                 recursive descent
│   ├── resolve.py                   path + context -> exactly one FragmentId
│   ├── assemble.py                  pure, deterministic assembly
│   └── provenance.py                attestation + two-level identity
├── tests/                           unit, integration, and property tests
├── examples/                        the 30-minute path
└── scripts/                         timed walkthrough, benchmark
```

## Subtask Index

### T-001 — Verified, reproducible project foundation *(S · 3 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-001-01](subtasks/T-001/ST-001-01-init-repo-and-package.md) | Initialize repository and package layout | 5 min |
| [ST-001-02](subtasks/T-001/ST-001-02-pin-dependencies.md) | Pin dependencies and lock the dev environment | 5 min |
| [ST-001-03](subtasks/T-001/ST-001-03-audit-and-licenses.md) | **Vulnerability audit and license verification** — closes Gate 6's conditional pass | 10 min |
| [ST-001-04](subtasks/T-001/ST-001-04-ci-pipeline.md) | CI across the 3.11–3.14 matrix | 5 min |

### T-002 — Fragments load from disk with verifiable identity *(M · 5 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-002-01](subtasks/T-002/ST-002-01-fragment-identity.md) | `FragmentId` — BLAKE3 content identity | 5 min |
| [ST-002-02](subtasks/T-002/ST-002-02-error-types.md) | Errors that name what failed and what was supplied | 5 min |
| [ST-002-03](subtasks/T-002/ST-002-03-path-confinement.md) | Path canonicalization with namespace-root confinement | 5 min |
| [ST-002-04](subtasks/T-002/ST-002-04-fs-custody.md) | Filesystem custody — the only I/O in the package | 5 min |
| [ST-002-05](subtasks/T-002/ST-002-05-identity-keyed-cache.md) | **Identity-keyed cache** — a path-keyed cache would be a correctness bug | 5 min |

### T-003 — A recipe parses into a structured composition *(M · 8 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-003-01](subtasks/T-003/ST-003-01-lexer.md) | Lexer with line/column positions | 5 min |
| [ST-003-02](subtasks/T-003/ST-003-02-nodes.md) | Grammar nodes — **the closed grammar, and the security boundary** | 5 min |
| [ST-003-03](subtasks/T-003/ST-003-03-expression-parser.md) | Expression parser — comparisons, booleans, membership | 5 min |
| [ST-003-04](subtasks/T-003/ST-003-04-recipe-parser.md) | Recipe parsing end to end | 5 min |

### T-004 — A path resolves to exactly one fragment *(M · 8 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-004-01](subtasks/T-004/ST-004-01-namespace-registry.md) | Namespace registry — prefix-routed dispatch | 5 min |
| [ST-004-02](subtasks/T-004/ST-004-02-resolve-isolated.md) | Resolve under **namespace isolation**, never first-match-wins | 5 min |
| [ST-004-03](subtasks/T-004/ST-004-03-ambiguity-errors.md) | **Ambiguity is an error naming every candidate** | 5 min |

### T-005 ⭐ — `get_prompt` returns an assembled prompt, deterministically *(L · 13 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-005-01](subtasks/T-005/ST-005-01-assembly-pipeline.md) | Assembly pipeline — evaluate, load, order, concatenate | 5 min |
| [ST-005-02](subtasks/T-005/ST-005-02-value-substitution-last.md) | **Value substitution as the final pass, never re-parsed** | 5 min |
| [ST-005-03](subtasks/T-005/ST-005-03-get-prompt-entry.md) | The `get_prompt` entry point | 5 min |
| [ST-005-04](subtasks/T-005/ST-005-04-property-p1-determinism.md) | **Property P1 — determinism** (hypothesis) | 10 min |
| [ST-005-05](subtasks/T-005/ST-005-05-cross-process-determinism.md) | **Cross-process determinism** — catches hash-seed nondeterminism | 10 min |
| [ST-005-06](subtasks/T-005/ST-005-06-performance-budget.md) | **Benchmark against the <10 ms budget** — settles the host-language question with a measurement *(revision 2)* | 10 min |

### T-006 ⭐ — Provenance record with two-level identity *(L · 13 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-006-01](subtasks/T-006/ST-006-01-attestation-record.md) | The attestation record | 5 min |
| [ST-006-02](subtasks/T-006/ST-006-02-canonical-digest.md) | **Canonical ordering before digesting; timestamps excluded** | 5 min |
| [ST-006-03](subtasks/T-006/ST-006-03-two-level-identity.md) | **Structural vs instance identity** (ADR-005) | 5 min |
| [ST-006-04](subtasks/T-006/ST-006-04-property-p2-order-identity.md) | **Property P2 — order-aware structural identity** (hypothesis) | 10 min |

### T-007 — Packaged and consumable by an agent framework *(S · 5 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-007-01](subtasks/T-007/ST-007-01-packaging.md) | Build and install a pure-Python wheel | 10 min |
| [ST-007-02](subtasks/T-007/ST-007-02-agent-consumption.md) | **Zero fragment awareness** — agent-framework consumption proof | 5 min |

### T-008 ⭐ — First value in under 30 minutes *(S · 3 pts)*

| ID | Subtask | Est. |
|---|---|---|
| [ST-008-01](subtasks/T-008/ST-008-01-quickstart-examples.md) | Quickstart + two runnable examples | 10 min |
| [ST-008-02](subtasks/T-008/ST-008-02-timed-ci-walkthrough.md) | **Timed CI walkthrough that fails the build over 30 minutes** | 10 min |

**Total: 30 subtasks across 8 tasks.**

## Execution Order

Strictly sequential within a task. Across tasks, follow the critical path:

```
T-001 → T-002 → T-004 → T-005 → T-006 → T-007 → T-008
          └── T-003 (parallelizable with T-002/T-004; required by T-005)
```

---

## The Two Properties Established Here

| | Property | Subtask | Why it is a *property* test and not an example test |
|---|---|---|---|
| **P1** | Determinism | ST-005-04, ST-005-05 | Nondeterminism appears on inputs nobody thought to write by hand. The **cross-process** variant (ST-005-05) is not redundant: hash-seed and iteration-order nondeterminism is invisible within a single process |
| **P2** | Order-aware structural identity | ST-006-04 | An order-blind identity is a **silent** failure — nothing errors, comparisons simply group two different prompts as one. Someone who believes the code is correct will not write the example that catches it |

---

## Gate 8 Validation

| Category | Check | Result |
|---|---|---|
| **Atomicity** | Each step 2–5 minutes | ✅ 30 subtasks, none over 10 min including verification |
| | No architecture understanding required | ✅ each file self-contained |
| **Completeness** | All code provided in full | ✅ no placeholders, no ellipses, no TODOs |
| | File paths explicit | ✅ |
| | Imports listed | ✅ |
| | TDD cycle followed | ✅ RED → GREEN → commit |
| **Verifiability** | Commands copy-pasteable | ✅ |
| | Expected output stated | ✅ |
| **Reversibility** | Rollback provided | ✅ per subtask |
| **Scoping** | Deferred subtasks stated explicitly | ✅ T-009…T-027 documented as deliberate |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Step Atomicity** | 27/30 | All within 2–10 min. Deducted 3: the two property-test subtasks, the benchmark, and the wheel build genuinely take longer than 5 minutes to run, and saying otherwise would be false |
| **Code Completeness** | 27/30 | Complete Python with real pinned versions, no placeholders. Deducted 3: **the code has not been executed** — no interpreter run was performed in this session, so minor drift against pinned package APIs is possible |
| **Context Independence** | 22/25 | Self-contained with exact paths and commands. Deducted 3: ST-001-03 requires judgment if the audit surfaces a real finding — that cannot be scripted away |
| **TDD Coverage** | 12/15 | RED→GREEN throughout the library subtasks. Deducted 3: T-001 and T-008 are genuinely not TDD-shaped (repository setup and documentation), and forcing a test-first framing on them would be theater |
| **Total** | **84/100** | ≥ 80 → autonomous |

**Gate Result:** ✅ **PASS**

> ⚠️ **One honest caveat carried into implementation:** none of this code was executed — no interpreter run was performed in this session. Treat the first `pytest` run as the real verification step. Drift against the pinned package APIs is possible and is exactly what ST-001-02 and the first RED step of each subtask will surface.

---

## Execution Handoff

Subtasks are ready. Two execution options:

1. **Subagent-driven** — a fresh subagent per subtask with automated review between, high throughput → `souschef:subagent-driven-development`
2. **Batched with checkpoints** — a new session running batches and pausing for feedback → `souschef:executing-plans`

Or run the whole task list through `/souschef:dev-cycle`.

---

> **Revision 2.** These subtasks were rewritten for the Python-only stack. The **decomposition is unchanged** — same tasks, same order, same properties in the same places — because the architecture is technology-agnostic. Only the code changed, plus ST-005-06 (the performance benchmark), added so the host-language decision rests on a measurement rather than on an estimate.
