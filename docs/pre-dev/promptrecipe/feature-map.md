# Feature Map: promptrecipe

## Overview

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 4 — Feature Map |
| **PRD Reference** | `docs/pre-dev/promptrecipe/prd.md` (approved, amendments 5–6) |
| **SBP Reference** | `docs/pre-dev/promptrecipe/sbp.md` (approved, amendments 1–4) |
| **Status** | Draft — pending human approval |
| **Confidence Score** | 84/100 |
| **Language** | en |

> ### ⚠️ Amendment 7 (stakeholder, 2026-08-31) — **it is a library, and its surface is `getPrompt(params)`**
>
> This reframes the entire feature landscape and is the organizing principle of this map.
>
> **The deliverable is a library, not a platform.** Its primary surface is essentially one call: given parameters, return the assembled prompt. Everything in the PRD must be re-examined against that. A feature that does not either (a) serve that call, (b) travel back with its result, or (c) exist as separate tooling *around* the library, does not belong in the library at all.
>
> **The largest consequence: change governance is not built — it is inherited.** PRD requirements FR-013 through FR-017 and FR-033 describe review, approval, origin tracking, isolation, and audit history. Under amendment 1 (version control may serve as the local versioning mechanism, including patch-based change representation), **these are properties of version control, not features of a library.** A pull request already provides isolation, origin, reviewer identity, accept/reject, and history. The library should *fit* that workflow, not reimplement it.
>
> This is exactly what the BRD predicted when it recommended version-control-native: *"inherits review, history, and approval for free."* Amendment 7 collects that dividend.
>
> **What this removes from the build:** an entire feature domain. **What it adds:** an obligation that fragments and recipes be diffable and reviewable as ordinary text — see Domain G.

---

## The Shape of the Product

```
                        ┌─────────────────────────────┐
   agent framework ---> │   getPrompt(params)         │ ---> assembled prompt
                        │                             │      + assembly identity
                        └─────────────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
      [A. Fragment Custody]   [B. Assembly]          [C. Provenance]
       addressing, versions    conditions, order      identity, record,
                               asserts, recursion     span map, reproduce
              │                       │                       │
              └───────────────────────┴───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │                                               │
    [D. Library Tooling]                          [E. External Integration]
     impact analysis, decomposition,               evaluation exposure,
     inspection — around the call,                 optimization seeding,
     not inside it                                 framework consumption
                                      │
                        [G. Change Governance — DELEGATED]
                         review, approval, history, origin
                         ← provided by version control, not built
```

**Read the diagram as the priority statement it is.** The call is the product. A, B, and C are what make the call trustworthy. D is tooling beside it. E is adapters. G is not built.

---

## Feature Inventory

### Core — the call path *(nothing works without these)*

| ID | Feature | User Value | Module | Depends On |
|---|---|---|---|---|
| **FR-006** | Fragments and recipes addressed hierarchically, each defined once | A part exists in one place, findable by name | Fragment Library | — |
| **FR-018** | A recipe declares which fragments it needs and the conditions for each | The prompt has a structure instead of being one blob | Composition | FR-006 |
| **FR-029** | A reference plus selection context resolves to exactly one fragment version | The call is unambiguous | Resolution | FR-006 |
| **FR-023** | Assembly is deterministic — identical inputs yield an identical prompt | The same call tomorrow returns the same prompt | Composition | FR-018, FR-029 |
| **FR-001** | Every assembly emits a provenance record, produced at assembly time | You can always say what produced this prompt | Provenance | FR-023 |
| **FR-002** | Assembly identity = fragment versions + bindings + condition outcomes + **order** | Two different prompts are never confused for one | Provenance | FR-001 |
| **FR-038** | Assembled content consumable by an agent framework with **zero** fragment awareness | Adoption changes nothing about how the agent is built | Integration Surface | FR-023 |
| **FR-028** | First assembled prompt within 30 minutes, no remote custody, no integrations | The approach proves itself before you invest in it | *(cross-cutting)* | FR-006, FR-018, FR-023 |
| **FR-027** | Never executes a prompt against a model; never scores a result | The library stays a library | *(boundary)* | — |

### Supporting — what makes the call worth making

| ID | Feature | User Value | Module | Depends On |
|---|---|---|---|---|
| **FR-007** | Changing a fragment once propagates to every recipe resolving it | Fix the wrong instruction once, not forty times | Fragment Library | FR-006 |
| **FR-008** | Multiple fragment versions coexist as addressable candidates | v1 and v2 both live; comparing them is possible | Fragment Library | FR-006 |
| **FR-019** | Conditions and variables determine assembly **order** | Ordering is testable, not baked in | Composition | FR-018 |
| **FR-020** | Conditions select among versions/variants — same mechanism as inclusion | A/B needs no separate machinery | Composition | FR-008, FR-018 |
| **FR-021** | Declared expectations fail loudly; no partial output | A missing binding fails, instead of silently producing a wrong prompt | Composition | FR-018 |
| **FR-022** | Recursive inclusion; a cycle fails reporting the **complete cycle path** | Fragments compose like functions; mistakes are diagnosable | Composition | FR-018 |
| **FR-030** | Layering and override precedence deterministic and inspectable | You can explain why *this* fragment won | Resolution | FR-029 |
| **FR-031** | Ambiguous or unresolvable references fail explicitly, never shadow silently | A typo fails; it doesn't quietly resolve to the wrong part | Resolution | FR-029 |
| **FR-003** | Byte-identical reproduction from the provenance record alone | Re-run last month's result and get last month's prompt | Provenance | FR-001, FR-023 |
| **FR-004** | Any portion of output maps back to the fragment that produced it | Bad output localizes to a part, not to "the prompt" | Provenance | FR-001 |
| **FR-032** | One recipe covers contextual variation | One recipe instead of nine near-duplicates | Composition | FR-018, FR-020 |
| **FR-035** | Incremental decomposition of an existing prompt, byte-identical at each step | Adopt without risking a behavior change | Composition, Provenance | FR-018, FR-023 |
| **FR-036** | Model variants share unchanged fragments **by reference**, and coexist | Port to a new model without forking forever | Fragment Library, Composition | FR-006, FR-007 |
| **FR-037** | Model variation expressible as separate recipes **or** as conditions — neither privileged | Match the expression to how much actually diverges | Composition | FR-018, FR-020 |

### Enhancement — tooling around the call, not inside it

| ID | Feature | User Value | Module | Depends On |
|---|---|---|---|---|
| **FR-011** | List every recipe depending on a fragment, **without assembling** | Know the blast radius before you change anything | *Impact Analysis* | FR-006, FR-029 |
| **FR-012** | Preview a proposed change's effect on each dependent recipe | Judge risk before accepting | *Impact Analysis* | FR-011, FR-023 |
| **FR-005** | Bind an externally-produced result to exactly one assembly | An A/B result means something | Provenance | FR-002 |
| **FR-009** | Fragment identity verifiable from content, stable across custody | Trust that a remote fragment is the one your record names | Fragment Library | FR-006 |
| **FR-010** | Pluggable local/remote custody; one source of truth, no bidirectional sync | Custody is an operational choice, not a rewrite | Fragment Library | FR-009 |

### Integration — adapters at the boundary

| ID | Feature | User Value | Module | Depends On |
|---|---|---|---|---|
| **FR-024** | A recipe exposable as an evaluable unit with its assembly identity | Test the whole prompt; results stay attributable | Integration Surface | FR-002, FR-023 |
| **FR-025** | A fragment exposable as an evaluable unit — **no model execution** | Catch a bad part without paying for a model call | Integration Surface | FR-006 |
| **FR-026** | Per-fragment optimization seeding; returned text enters as a proposal | Improve one part at a time, reviewably | Integration Surface | FR-006 |

### Delegated — inherited from version control, **not built** *(amendment 7)*

| ID | PRD Requirement | Who provides it | What the library must do instead |
|---|---|---|---|
| **FR-013** | Single intake path for all changes | Version control — every change is a commit | Ensure fragments/recipes are ordinary reviewable text |
| **FR-014** | Origin recorded (human vs machine + run) | Version control — author/committer metadata | Ensure machine-generated changes are *attributable* when authored |
| **FR-015** | Change presentable in isolation | Version control — per-file diffs | **Keep one fragment per addressable unit**, so a diff is naturally scoped |
| **FR-016** | Accept/reject recorded with actor and time | Version control — review and merge | Nothing |
| **FR-017** | Acceptance-required is configurable policy | Version control — branch protection | Nothing |
| **FR-033** | Full history of what changed, when, who accepted | Version control — log | Nothing |

> **This delegation has one hard obligation attached:** it only works if a fragment is a **separately diffable unit**. If fragments were bundled together, per-fragment review would be impossible and the delegation would fail. That constraint is carried into Domain G and flagged for the TRD.
>
> **It also has one honest cost:** delegation binds the review story to version-control-based custody. Under remote custody (FR-010) with no version control, review is **not** inherited and there is no substitute in this feature set. Flagged in Risks.

### Deferred

| ID | Feature | Status |
|---|---|---|
| **FR-034** | Contribution path for people outside engineering tooling | **P3, deferred.** Reversal condition recorded in the PRD: evidence that prompt-quality knowledge sits predominantly with non-engineers |

---

## Domain Groupings

### Domain A — Fragment Custody & Addressing
**Purpose:** Give every prompt part a name, a location, and an identity that survives being moved.
**Features:** FR-006, FR-007, FR-008, FR-009, FR-010
**Owns:** fragment content, addresses, versions, identity
**Provides to:** Resolution (candidates), Provenance (identity), Impact Analysis (the graph)
**Consumes:** custody backends (local, remote)
**Boundary:** owns *what a fragment is*; owns nothing about how it is assembled.

### Domain B — Assembly
**Purpose:** Turn a recipe plus parameters into a finished prompt — the substance of the call.
**Features:** FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-029, FR-030, FR-031, FR-032, FR-035, FR-036, FR-037
**Owns:** condition evaluation, binding, ordering, recursion, cycle detection, precedence
**Provides to:** Provenance (what happened), Integration (the prompt)
**Consumes:** Domain A (fragments)
**Boundary:** decides *which parts, in what order, at what version*; decides nothing about where parts live.

### Domain C — Provenance & Reproduction
**Purpose:** Make every assembly explainable, attributable, and repeatable.
**Features:** FR-001, FR-002, FR-003, FR-004, FR-005
**Owns:** assembly identity, the record, span mapping, reproduction
**Provides to:** Integration (attributable results), Library Tooling (inspection)
**Consumes:** Domain B (assembly events), Domain A (identity)
**Boundary:** records and reproduces; never decides what to assemble.

> **Domain C is not a supporting domain.** It carries the highest-opportunity job in the BRD (F5 = 16, above every composition job). It is placed third because it *depends on* B, not because it matters less.

### Domain D — Library Tooling
**Purpose:** Answer questions *about* the library that the call itself does not answer.
**Features:** FR-011, FR-012
**Owns:** the dependency view
**Consumes:** Domain A, Domain B (for preview only)
**Boundary:** **beside the call, not inside it.** FR-011 explicitly requires no assembly.

### Domain E — External Integration
**Purpose:** Meet three external capabilities on their own terms without letting their models leak inward.
**Features:** FR-024, FR-025, FR-026, FR-038
**Owns:** adapters only
**Consumes:** Domain B, Domain C
**Boundary:** FR-027 is the wall — never executes a prompt, never scores a result.

### Domain F — First Value
**Purpose:** Get a new user to a working assembled prompt before they have invested anything.
**Features:** FR-028
**Consumes:** the minimum of A + B
**Boundary:** must work with **no** remote custody, **no** evaluation, **no** optimization.

### Domain G — Change Governance *(delegated — amendment 7)*
**Purpose:** Review, approval, origin, and history.
**Features:** FR-013–FR-017, FR-033 — **provided by version control, not built**
**The library's only obligation:** fragments and recipes must be **ordinary text, one fragment per separately diffable unit**, so that per-fragment review works naturally.
**Boundary:** the library fits the review workflow; it does not implement one.

---

## User Journeys

### Journey 1 — The Fork *(amendment 6 — the driving use case)*

**User:** Library Owner · **Goal:** run an existing prompt on a second model without forking it forever.

| Step | Action | Features |
|---|---|---|
| 1 | Has a working prompt for Model X, already copied and edited for Model B; the two are diverging | *(the pain)* |
| 2 | Decomposes the prompt into fragments, verifying byte-identical output at each step | FR-035, FR-018, FR-023 |
| 3 | Identifies the ~10% that genuinely differs between models | FR-011 |
| 4 | Makes the shared ~90% one set of fragments referenced by both variants | FR-006, FR-007, FR-036 |
| 5 | Expresses the difference — separate recipes sharing fragments, **or** conditions in one recipe | FR-037, FR-020 |
| 6 | Calls `getPrompt` with the model as a parameter; the right variant assembles | FR-018, FR-029, FR-023 |
| 7 | Agent framework receives usable content, knowing nothing about fragments | FR-038 |
| **Success** | One fix to a shared fragment now corrects **both** models | FR-007 |
| **Failure** | A reference is ambiguous → fails explicitly naming candidates, never silently resolves wrong | FR-031 |

### Journey 2 — The Monolith *(amendment 5)*

**User:** Library Owner · **Goal:** make one oversized prompt manageable.

| Step | Action | Features |
|---|---|---|
| 1 | Has a prompt too large to change, test, or improve safely | *(the pain)* |
| 2 | Extracts one fragment; verifies assembled output is byte-identical | FR-035, FR-023 |
| 3 | Repeats incrementally; a partially decomposed prompt still assembles correctly | FR-035 |
| 4 | Adds declared expectations so missing context fails loudly | FR-021 |
| 5 | Tests individual fragments without any model call | FR-025 |
| 6 | Tests the assembled recipe as a whole | FR-024 |
| **Success** | Failure now localizes to a fragment, not to "the prompt" | FR-004 |
| **Failure** | Fragments reference each other cyclically → fails with the complete cycle path | FR-022 |

### Journey 3 — Attributable Comparison *(highest-opportunity job, F5 = 16)*

**User:** Evaluator · **Goal:** compare two variants and trust the result.

| Step | Action | Features |
|---|---|---|
| 1 | Calls `getPrompt` twice with different parameters — different version, or different order | FR-020, FR-019 |
| 2 | Each assembly returns its identity: versions + bindings + condition outcomes + **order** | FR-001, FR-002 |
| 3 | Passes both to the evaluation capability with identity attached | FR-024 |
| 4 | Results return bound to exactly one assembly each | FR-005 |
| 5 | Weeks later, reproduces the winning assembly byte-identically from its record | FR-003 |
| **Success** | The comparison means something and remains meaningful over time | FR-002, FR-003 |
| **Failure** | A referenced version is no longer retrievable → reproduction fails explicitly rather than substituting | FR-003 |

### Journey 4 — Reviewed Improvement *(uses delegated governance)*

**User:** Improvement Adopter · **Goal:** adopt machine-suggested wording without shipping unread text.

| Step | Action | Features |
|---|---|---|
| 1 | Seeds an improvement run from **one fragment's** text | FR-026 |
| 2 | Improved text returns as a proposed change to **that** fragment | FR-026 |
| 3 | Checks which recipes the fragment affects | FR-011, FR-012 |
| 4 | Reviews the change **in version control**, scoped to one fragment | *Domain G — delegated* |
| 5 | Accepts or rejects through the normal review workflow | *Domain G — delegated* |
| 6 | On acceptance, every recipe using the fragment picks it up | FR-007 |
| **Limitation, stated** | A run seeded from a whole recipe returns one result that **cannot** be split across its fragments | FR-026 |

### Journey 5 — First Contact *(survival — M11)*

**User:** brand-new user · **Goal:** decide whether this is worth adopting.

| Step | Action | Features |
|---|---|---|
| 1 | Creates two fragments locally | FR-006 |
| 2 | Writes a recipe referencing both | FR-018 |
| 3 | Calls `getPrompt(params)` and gets a prompt | FR-023, FR-029 |
| 4 | Changes one fragment; calls again; sees the change propagate | FR-007 |
| **Success** | Working assembled prompt in **under 30 minutes**, with no remote custody and no integrations | FR-028 |
| **Why it's critical** | The real competitor is copy-paste at zero switching cost. Nobody arrives holding 200 prompts | — |

---

## Feature Interaction Map

```
                    ┌──────────────────────────────────────┐
                    │        getPrompt(params)             │
                    └──────────────────────────────────────┘
                            │                    ▲
                            v                    │
   [FR-018 recipe] ──> [FR-029 resolve] ──> [FR-023 assemble] ──> prompt
        │                    ▲                    │                + identity
        │                    │                    │
   [FR-019 order]            │              [FR-001 record]
   [FR-020 version]          │                    │
   [FR-021 expects]     [FR-006 address]     [FR-002 identity]
   [FR-022 recursion]        │                    │
        │              [FR-008 versions]    [FR-004 span map]
        │              [FR-007 propagate]   [FR-003 reproduce]
        │              [FR-009 identity]    [FR-005 bind result]
        │              [FR-010 custody]           │
        │                    │                    │
        └────────> [FR-011/012 impact] <──────────┘
                             │
                    ┌────────┴────────┐
                    v                 v
            [FR-024 recipe eval] [FR-025 fragment eval]
            [FR-026 optimize]    [FR-038 framework]
                             │
                             v
                   [Domain G — version control]
                    review · origin · history
```

### Dependency Matrix

| Feature | Depends On | Blocks | Notes |
|---|---|---|---|
| FR-006 | — | almost everything | **Foundational** |
| FR-018 | FR-006 | FR-019, FR-020, FR-021, FR-022, FR-023 | Foundational |
| FR-029 | FR-006 | FR-023, FR-011 | Foundational |
| FR-023 | FR-018, FR-029 | FR-001, FR-024, FR-035, FR-038 | **Determinism gates provenance** |
| FR-001 | FR-023 | FR-002, FR-003, FR-004 | Must be emitted *at* assembly |
| FR-002 | FR-001 | FR-005, FR-024 | Order-aware or comparisons corrupt |
| FR-007 | FR-006 | FR-036 | The change-once promise |
| FR-008 | FR-006 | FR-020 | Coexistence precondition |
| FR-020 | FR-008, FR-018 | FR-032, FR-037 | A/B without separate machinery |
| FR-019 | FR-018 | — | Forces FR-002 to include order |
| FR-035 | FR-018, FR-023 | — | Adoption path; needs determinism |
| FR-036 | FR-006, FR-007 | — | Driving use case |
| FR-011 | FR-006, FR-029 | FR-012 | **Requires no assembly** |
| FR-038 | FR-023 | — | Zero fragment awareness required |
| FR-025 | FR-006 | — | No model execution |
| FR-026 | FR-006 | — | Per-fragment only |
| FR-028 | FR-006, FR-018, FR-023 | — | **Survival metric** |
| FR-013–017, FR-033 | *version control* | — | **Delegated, not built** |

**No circular dependencies.** One near-cycle resolved deliberately: FR-012 (preview a change's effect) needs assembly, while FR-011 (list dependents) must not. They are kept separate so the cheap question stays cheap.

---

## Phasing Strategy

### Phase 1 — The Call *(proves the premise)*
**Goal:** `getPrompt(params)` returns a correct, deterministic, attributable prompt.
**Features:** FR-006, FR-018, FR-029, FR-023, FR-001, FR-002, FR-038, FR-028, FR-027
**Value:** structure and reuse where there was one blob. First value in under 30 minutes.
**Success:** M11 ≥ 75%; a new user assembles from two fragments in 30 minutes.
**Trigger to Phase 2:** the call is stable and deterministic under repetition.

### Phase 2 — Worth Adopting *(the two entry journeys)*
**Goal:** an existing prompt — monolith or fork — can be brought in without risk.
**Features:** FR-007, FR-008, FR-019, FR-020, FR-021, FR-022, FR-035, FR-036, FR-037, FR-030, FR-031, FR-032
**Value:** decompose without behavior change; unify model variants; fix once.
**Success:** M1 ≤ 5 min; M2 100%; M7 ≥ 60% fewer near-duplicates.
**Trigger to Phase 3:** a real prompt is in production through the library.

### Phase 3 — Trustworthy *(the highest-opportunity jobs)*
**Goal:** every result attributable; every assembly reproducible; blast radius known in advance.
**Features:** FR-003, FR-004, FR-005, FR-011, FR-012, FR-024, FR-025
**Value:** comparisons that mean something; failures that localize.
**Success:** M3 ≥ 99%; M4 ≤ 2 min; M6 ≥ 95%; M12 100%.
**Trigger to Phase 4:** teams are comparing variants and acting on results.

### Phase 4 — Scale & Improve
**Goal:** remote custody, cross-boundary identity, reviewable machine improvement.
**Features:** FR-009, FR-010, FR-026
**Value:** shared libraries across teams; improvement that is adoptable rather than all-or-nothing.
**Success:** M5 ≥ 80%; M9 ≤ 1 per 100.

**Deferred:** FR-034 (P3).
**Never built:** FR-013–017, FR-033 — delegated to version control.

> **Phasing note.** Provenance (FR-001, FR-002) is in **Phase 1**, not Phase 3, despite the trust *features* landing later. The record must be emitted from the first assembly (SD5) — it cannot be reconstructed afterward. Phase 3 adds what you can *do* with the record, not the record itself.

---

## Scope Boundaries

### In Scope
The `getPrompt(params)` call and everything that makes it correct, deterministic, and attributable (Domains A, B, C) · tooling that answers questions about the library without assembling (Domain D) · thin adapters to evaluation, optimization, and agent frameworks (Domain E) · a 30-minute path to first value (Domain F).

### Out of Scope

| Item | Rationale |
|---|---|
| **Executing prompts / scoring results** | FR-027. Four competitors ship more mature evaluation |
| **Generating improved wording** | The unserved job is *review and adoption*, not generation |
| **Review, approval, and history features** | **Amendment 7** — delegated to version control. Building them would reimplement a solved problem |
| **Live production traffic splitting** | ⚠️ Out by **assumption**, not decision. A/B is read as offline comparison. Still awaiting confirmation |
| **Model routing, caching, gateway** | Different category |
| **Production observability** | Where two surveyed competitors pivoted *to* |
| **A managed platform or hosted service** | **Amendment 7** — it is a library |
| **No-code authoring for non-engineers** | FR-034, deferred with reversal conditions |

### Assumptions
**A1** *(revised)* a prompt grows too large to manage, or gets forked across models — **directly observable today**, not a prediction · **A2** teams want to author prompt text · **A3** value appears before the switching cost of copy-paste bites (guarded by FR-028) · **A4** evaluation and optimization capabilities remain integrable · **A5** the audience adopts an engineering-workflow-shaped solution · **A6** *(new, amendment 7)* teams keep fragments under version control — **if custody is remote-only, the delegated review story does not hold**.

### Constraints
The library never calls a model · assembly must be deterministic or provenance is worthless · a fragment must be a separately diffable unit or delegated review fails · value must arrive at small library sizes · fragments may be machine-written, constraining how much power condition logic may safely have (Open Question C).

---

## Risk Assessment

### Feature Complexity Risks

| Risk | Features | Severity | Mitigation |
|---|---|---|---|
| **Determinism is not retrofittable** | FR-023 → FR-001, FR-002, FR-003 | **High** | Phase 1. Gate 0 catalogued the specific hazards. Everything trustworthy depends on it |
| **Order-blind identity silently corrupts comparisons** | FR-002 vs FR-019 | **High** | Order is in the identity from the first version. The failure mode is silent — two different prompts attributed to one assembly |
| **Cross-backend identity breaks at the custody boundary** | FR-009, FR-010 | **Medium** | Content-verifiable identity (FR-009) precedes remote custody (FR-010) in Phase 4 |
| **Condition expressiveness vs safety unresolved** | FR-018–FR-021 | **Medium** | 🔴 **Open Question C.** The TRD must not select a mechanism before it is decided |
| **Incremental decomposition proves harder than it reads** | FR-035 | **Medium** | Byte-identical verification at each step is the whole guarantee; without it, adoption is a rewrite-and-hope |
| **Fragment granularity is a user judgment the library cannot make** | FR-006, FR-018 | **Medium** | Same failure mode as over-decomposed functions. Guidance, not enforcement — but Gate 0 found a comparable tool warning its own users that over-decomposition is an anti-pattern |

### Integration Risks

| Risk | Features | Severity | Mitigation |
|---|---|---|---|
| **Both integration targets changed ownership within 8 months** | FR-024, FR-025, FR-026 | **High** | Keep adapters thin (Domain E). The core must not depend on either surviving |
| **No per-fragment optimization attribution exists** | FR-026 | **Medium** | Per-fragment seeding only. Amendment 6 makes this the natural shape anyway |
| **Framework consumption must require zero fragment awareness** | FR-038 | **Medium** | If adoption required changing how the agent is built, the entry cost would exceed the benefit |
| **Delegated review fails under remote-only custody** | Domain G, FR-010 | **Medium** | 🔴 Honest gap: assumption A6. No substitute exists in this feature set |
| **Evaluation is not a differentiator** | FR-024, FR-025 | **Low** | Four competitors ship more mature evaluation. Do not position on it |

---

## Gate 4 Validation

| Category | Check | Result |
|---|---|---|
| **Feature Completeness** | All PRD features mapped | ✅ 38/38 — 32 built, 6 delegated |
| | Categories assigned | ✅ Core / Supporting / Enhancement / Integration / Delegated / Deferred |
| | None missing | ✅ including FR-034 as explicitly deferred |
| **Grouping Clarity** | Domains logically cohesive | ✅ 7 domains, one of them delegated |
| | Cross-domain dependencies minimized | ✅ one deliberate near-cycle documented |
| | Business-function names | ✅ |
| **Journey Mapping** | Primary journeys start to finish | ✅ 5, including both adoption entry points |
| | Happy and failure paths | ✅ each journey names its failure mode |
| **Integration Points** | All interactions identified | ✅ |
| | Directional dependencies clear | ✅ dependency matrix |
| | Circular dependencies resolved | ✅ FR-011/FR-012 split deliberately |
| **Priority & Phasing** | MVP identified | ✅ Phase 1 = the call |
| | Incremental value delivery | ✅ each phase ships usable value |
| | Dependencies don't block MVP | ✅ |
| | **Provenance not demoted below composition** | ✅ Domain C carries F5=16; FR-001/002 are Phase 1 |
| **Purity** | No technology names | ✅ scan-verified |
| | No architecture or components | ✅ |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Feature Coverage** | 25/25 | All 38 requirements mapped, categorized, and traced to a module — including the 6 reclassified as delegated and 1 as deferred |
| **Relationship Clarity** | 22/25 | Full dependency matrix; the one near-cycle resolved deliberately. Deducted 3: Domain G's delegation boundary depends on assumption A6, which is untested |
| **Domain Cohesion** | 22/25 | 7 cohesive domains; amendment 7 removed an entire built domain. Deducted 3: Impact Analysis remains a cross-module capability rather than owning a module, as in the SBP |
| **Journey Completeness** | 15/25 | 5 journeys with failure paths. Deducted 10: **journeys 3 and 4 cross an external boundary** — the evaluation round trip and the review workflow — that this gate cannot verify end to end, and journey 4 now depends on a delegated capability the library does not control |
| **Total** | **84/100** | ≥ 80 → proceed to TRD |

**Gate Result:** ✅ **PASS**

Two open questions carry forward, and one is now blocking:
- 🔴 **A** — default acceptance policy. Largely dissolved by amendment 7: it becomes a branch-protection setting, not a product feature.
- 🔴 **C** — condition expressiveness vs safety. **Blocking for Gate 5** — the TRD cannot select a condition mechanism before this is decided.
- ⚠️ Live traffic splitting remains out of scope by assumption, awaiting confirmation.

**Next Step:** Gate 5 — TRD Creation (`souschef:pre-dev-trd-creation`)

---

## Amendment 8 (stakeholder, 2026-08-31) — Question C decided, and the core mechanic stated precisely

### C — DECIDED: restricted logic, recipe only

| Aspect | Decision |
|---|---|
| **Where logic may live** | **In the recipe only.** A fragment is text plus pure references — never conditional logic |
| **Expressive power** | A bounded expression language: comparisons, boolean operators, membership, variable references. No arbitrary function calls, no loops, no I/O, guaranteed termination |
| **What conditions must express** | Fragment inclusion · assembly order · version/variant selection · declared expectations (asserts) |
| **What a fragment may contain** | Text, and pure references to other fragments by path — with no condition attached |
| **Consequence for computed values** | Anything requiring real computation is prepared by the caller and passed as a parameter to the call |

**Why this option.** The evaluated surface stays small and bounded, and — decisively — **text written by an optimizer is never executed**. Safety is by construction rather than by sandbox. Gate 0 documented that sandboxes on general-purpose engines are blocklists in a cat-and-mouse pattern (four CVEs on one engine's sandbox alone, each fix followed by a new indirect route), and that a machine-written fragment is adversarial input by definition.

**Second-order effect:** because fragment content is never evaluated, Open Question A's default genuinely stays a *policy* choice. Had logic been allowed inside fragments, mandatory review would have become a safety requirement rather than a preference.

### The core mechanic, stated precisely

> **A template variable is not a string value. It is an address.**
> Substituting the variable means *resolving that path and inlining the fragment found there*. Variable substitution **is** path resolution — which is why path addressing is foundational rather than a convenience.

A recipe is, in essence, a composition of **load-by-path directives**, illustratively `[load prompts/A/init.md]`, where:
- the path may be given literally, or supplied through a variable;
- a condition may gate whether a load happens at all;
- order is declared over the loads.

### Model variation happens at the call, not inside the template

```
getPrompt(templateA)   ->  assembled prompt for one model
getPrompt(templateB)   ->  assembled prompt for another model
```

The caller selects the template. Templates A and B are separate, coexist, and **share the fragments that do not differ by referencing the same paths**. This is the primary form of model portability (FR-036).

**This refines FR-037.** The PRD stated that model variation is expressible either as separate recipes sharing fragments *or* as conditions inside one recipe, with neither form privileged. Amendment 8 privileges the first: **separate templates selected at the call site is the primary form.** In-recipe conditions remain available for variation *within* a template, but are not the mechanism for choosing a model.

**Why this matters architecturally:** it keeps each template readable as a flat, reviewable composition rather than a thicket of nested conditionals — which is precisely what makes the delegated per-fragment review of amendment 7 work in practice.
