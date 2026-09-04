# System Big Picture: promptrecipe

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 2 — System Big Picture (SBP) |
| **Track** | full (greenfield, 9 gates) |
| **BRD Reference** | `docs/pre-dev/promptrecipe/brd.md` (approved, amendments 1–4) |
| **Research Reference** | `docs/pre-dev/promptrecipe/research.md` (approved) |
| **Status** | Draft — pending human approval |
| **Confidence Score** | 87/100 |
| **Language** | en |

> **Amendment 4 (stakeholder, 2026-08-31):** the recipe's variables and control flow (`if`) exist so fragments load **automatically**, and so that **variations of ORDER** can be tested — sequence is a parameterizable dimension, not a fixed property of a recipe. Optimization is used for **minor per-fragment adjustments**, not wholesale rewrites. **Both individual fragments and the whole assembled recipe are independently evaluable.** See SD12 and the Composition/Provenance capabilities below.
>
> **Amendment 3 (stakeholder, 2026-08-31):** version and variant selection uses the **recipe's own condition mechanism** — loading A or B, v1 or v2, is expressed the same way any other conditional fragment loading is expressed. There is therefore **no separate experimentation subsystem** in this system structure. This is recorded here because it materially shapes the module decomposition below.

---

## System Vision

promptrecipe is a composition system: it holds prompt fragments as independently addressed, independently versioned units, and assembles them into finished prompts according to recipes that declare which fragments they need and under what conditions each one loads. Every assembly emits not just the finished prompt but a complete record of what produced it — which fragment versions, which variable bindings, and which portion of the output came from which fragment — so any downstream result can be attributed back to an exact assembly and reproduced from it. Fragments may live in local or remote custody without changing how they are addressed or identified, and changes to them — whether written by a person or proposed by an automated improvement capability — enter through the same reviewable path.

---

## Actors

| Actor | Type | Role | Key Interactions |
|---|---|---|---|
| **Library Owner** | User | Authors and maintains fragments and recipes; owns the library's structure and naming | Creates and edits fragments; defines recipes and their conditions; changes a shared fragment and needs to know what it affects |
| **Change Reviewer** | User | Approves or rejects changes to fragments and recipes, including machine-proposed ones | Reviews a proposed change scoped to a named fragment; accepts or rejects; needs the change in isolation from unrelated work |
| **Evaluator** | User | Runs evaluations and acts on results | Requests assembled prompts for evaluation; compares variants; must reconcile every result to an exact assembly |
| **Improvement Adopter** | User | Decides whether machine-proposed wording is safe to ship | Seeds an optimization run from existing fragment text; receives proposals; accepts or rejects |
| **Domain Contributor** | User *(deferred)* | Holds domain knowledge but does not work in engineering tooling | Proposes wording changes. **Deferred per BRD** — named for completeness; the current structure does not serve this actor directly |
| **Consuming Application** | External System | The product that actually uses the assembled prompt to call a model | Requests an assembled prompt with a selection context; receives the prompt and its provenance record |
| **Evaluation Capability** | External System | Runs tests and scores results | Requests assembled prompts or individual fragments as testable units; returns results carrying the provenance it was given |
| **Prompt Optimization Capability** | External System | Generates improved instruction wording against a metric | Receives fragment text as a starting point; returns improved text as a proposal. **Returns one result with no per-fragment attribution** |
| **Fragment Custody Backend** | External System | Where fragments physically reside — local or remote | Stores and retrieves fragment content and versions. Interchangeable; identity must survive the swap |
| **Version Control System** | External System | May serve as the local versioning mechanism, including change representation as patches | Records fragment history; supplies change sets for review |
| **Model Provider** | External System *(outside)* | Executes the prompt | **No interaction with this system.** Listed to make the boundary explicit — promptrecipe produces prompts; it never calls models |

---

## Main Modules

Six modules. Amendment 3 removed a seventh (an experimentation/variant-selection module) by folding version and variant selection into Composition.

### 1. Fragment Library

**Responsibility:** Holds fragments and recipes as addressable, versioned units, and owns what it means for two things to be "the same fragment." It is the system's custody and identity layer.

**Key Capabilities:**
- Assigns each fragment a stable address within a hierarchical namespace
- Maintains multiple coexisting versions of a fragment as concurrently addressable candidates
- Establishes verifiable identity for a fragment version that does not depend on where it is stored
- Presents a uniform view over interchangeable custody backends

**Dependencies:**
- Depends on: *(none internal)* — external Fragment Custody Backend, external Version Control System
- Provides to: Resolution, Provenance, Impact Analysis, Change Intake

---

### 2. Resolution

**Responsibility:** Turns a reference — a path, plus the selection context in force — into one specific fragment version. This is where addressing semantics live: namespace routing, layering, override precedence, and collision handling.

**Key Capabilities:**
- Routes a hierarchical path to the fragment it names
- Applies ordered layering and override rules deterministically, so precedence is predictable rather than incidental
- Selects among coexisting versions according to the selection context
- Detects and reports ambiguity or an unresolvable reference explicitly rather than silently shadowing it

**Dependencies:**
- Depends on: Fragment Library
- Provides to: Composition, Impact Analysis

> **Why this is separate from Composition:** resolution answers *which fragment*, composition answers *what the assembled text is*. Keeping them separate is what allows custody to change without composition changing, and what makes dependency analysis possible without assembling anything.

---

### 3. Composition

**Responsibility:** Assembles a finished prompt from a recipe by evaluating its declared conditions, binding its variables, and incorporating the fragments those conditions select — including fragments that themselves reference other fragments.

**Key Capabilities:**
- Evaluates declared conditions to determine which fragments load — **including conditions that select a variant or a version** *(amendment 3)*
- Binds variables and substitutes fragment content
- Determines the **order** in which selected fragments assemble, where order is itself expressible through variables and conditions rather than fixed by the recipe's text *(amendment 4)*
- Handles recursive inclusion, detecting cycles and reporting the actual cycle path rather than merely its existence
- Produces an identical result for identical inputs
- Emits, as a first-class output alongside the prompt, the record of everything the assembly consumed and every branch it took

**Dependencies:**
- Depends on: Resolution
- Provides to: Provenance, Integration Surface

> **Amendment 3 consequence:** because variant and version selection is expressed as ordinary conditional loading, A/B comparison requires no distinct machinery. The cost is that a version choice is a *runtime* outcome rather than a static declaration — which is precisely why the variable bindings that drove the choice must be captured, not only the fragments that resulted. That obligation lands on Provenance.

---

### 4. Provenance

**Responsibility:** Records what produced what, at sufficient fidelity that any assembled prompt can be reproduced exactly and any downstream result can be attributed to an exact assembly. This is the module the BRD's highest-scoring jobs depend on.

**Key Capabilities:**
- Records the identity of every fragment version consumed by an assembly
- Records the variable bindings and condition outcomes that determined what loaded — *without these, a branch cannot be replayed*
- Records the **order** in which fragments were assembled — under amendment 4 two assemblies may contain an identical fragment set and still differ, so the fragment list alone no longer identifies an assembly
- Maps portions of the assembled output back to the fragments that produced them
- Gives each assembled prompt a verifiable identity that downstream results can reference
- Enables an assembly to be reproduced from its record alone

**Dependencies:**
- Depends on: Composition, Fragment Library
- Provides to: Integration Surface, Impact Analysis

> **Two distinct needs, deliberately grouped:** span mapping (which fragment produced which portion — a human-debugging concern) and assembly attestation (binding a result to exact inputs — a reproducibility concern). They are grouped because both are the same act of recording, performed at assembly time. Whether they warrant separate treatment is a TRD question, noted below.

---

### 5. Change Intake & Review

**Responsibility:** The single path through which any change to a fragment or recipe enters the library — whether authored by a person or proposed by an automated improvement capability. It is where a proposal becomes an accepted change, or does not.

**Key Capabilities:**
- Accepts a proposed change scoped to a named fragment
- Presents the change in isolation, so it can be judged on its own rather than alongside unrelated work
- Carries the origin of a proposal, so a reviewer knows whether a person or a machine wrote it
- Records the acceptance decision and who made it
- Admits a change into the library only through this path

**Dependencies:**
- Depends on: Fragment Library, Impact Analysis
- Provides to: Fragment Library

> **This module is where Open Question A lands.** The structure places a review boundary between a proposal and the library, and routes machine-written and human-written changes through it identically. If A resolves toward "trusted," this module becomes a pass-through for machine proposals rather than a gate — the *structure* survives either answer, which is why it is modeled this way rather than assuming the outcome.

---

### 6. Integration Surface

**Responsibility:** Presents the system's artifacts in the forms external capabilities consume, and receives what they return — without letting either capability's model of the world leak into the rest of the system.

**Key Capabilities:**
- Exposes a recipe as an assembled prompt on demand, given a selection context
- Exposes **both** an individual fragment **and** the whole assembled recipe as independently evaluable units — the two are distinct evaluation targets, not one nested inside the other *(amendment 4)*
- Attaches provenance to what it hands out, so results come back attributable
- Supplies fragment text as a starting point for an optimization run
- Receives optimized text and routes it into Change Intake as a proposal against a named fragment

**Dependencies:**
- Depends on: Composition, Provenance
- Provides to: Change Intake; external Evaluation and Optimization capabilities

> **A limit this module must not disguise:** the optimization capability returns a single improved result with no attribution to individual fragments. When an optimization run is seeded from a *composed* recipe, what comes back cannot be split across the fragments that composed it. The honest shapes are seeding from a single fragment, or accepting that a whole-recipe result becomes a proposal against one designated fragment. This system structure must not imply per-fragment optimization credit exists.

---

### Module Dependency Overview

```
        [Fragment Custody Backend]   [Version Control System]
                      \                    /
                       \                  /
                    [1. Fragment Library]
                       /        |        \
                      /         |         \
          [2. Resolution]       |     [5. Change Intake & Review]
                  |             |              ^
                  v             |              |
          [3. Composition] -----+              |
                  |     \                      |
                  |      \                     |
                  v       v                    |
          [4. Provenance] --> [6. Integration Surface]
                  ^                   |    ^   |
                  |                   |    |   |
          [Impact Analysis*]          v    |   v
                              [Evaluation] | [Optimization]
                                           |
                                    (proposal returns)
```

*\*Impact Analysis is a capability spanning Resolution, Fragment Library, and Provenance — the ability to answer "which recipes depend on this fragment, and what changes if it changes." It is called out in the flows and boundaries but is **not** a seventh module: it reads from three existing modules and owns no custody of its own. Whether it deserves module status is flagged for the TRD.*

---

## Primary Flow

**Narrative:**

A Library Owner authors fragments into the Fragment Library, each at its own address, and writes a recipe declaring which fragments it needs and the conditions under which each loads. When a Consuming Application or the Evaluation Capability requests a finished prompt, it supplies a selection context — the variable bindings, including any that choose a variant or version. Resolution turns each reference in the recipe into one exact fragment version; Composition evaluates the conditions, assembles the text, and emits both the finished prompt and the full record of what went into it. Provenance gives that assembly a verifiable identity and retains the fragment versions, the bindings, the branches taken, and the mapping from output portions back to their source fragments. The prompt and its provenance travel out together — so when a result comes back, it is attributable to that exact assembly and reproducible from its record alone.

**The value chain does not end at "a prompt was produced."** It ends at *an attributable, reproducible result*, because that is what the BRD's highest-opportunity jobs (F5 at 16, F9 at 14) are actually starving for.

**Flow Diagram:**

```
[Library Owner]
      |
      | authors fragments + recipe (with conditions)
      v
[1. Fragment Library] <----------------- [5. Change Intake & Review] <---- proposals
      |                                            ^                       (human or machine)
      v                                            |
[2. Resolution] --- exact fragment version ---> [3. Composition]
      ^                                            |
      | selection context                          | assembled prompt
      |                                            |    + what produced it
[Consuming App] / [Evaluator] --------------------->
                                                   v
                                          [4. Provenance]
                                                   |
                                                   v
                                        [6. Integration Surface]
                                           /                \
                                          v                  v
                              [Evaluation Capability]  [Optimization Capability]
                                          |                  |
                                    attributable        proposed wording
                                      result                 |
                                                             +--> back to [5]
```

### Secondary Flows

- **Impact check before change.** Before a shared fragment changes, the Library Owner asks which recipes depend on it and what would be affected. Reads from Resolution and Fragment Library; no assembly occurs. Serves F8 / O5.
- **Variant comparison.** Two assemblies are produced from the same recipe under different selection contexts — the difference expressed entirely through the recipe's own conditions *(amendment 3)*. Each carries its own provenance, so results are separable. **The comparison's scoring happens outside this system.**
- **Order variation.** The same fragment set is assembled in different sequences, the difference expressed through the recipe's own variables and conditions *(amendment 4)*. Each ordering is a distinct assembly with its own identity and provenance, so results are separable — see SD13.
- **Improvement proposal round trip.** Fragment text is supplied to the Optimization Capability as a starting point; the improved text returns through Integration Surface as a proposal against a named fragment and enters Change Intake & Review like any other change.
- **Fragment-level testing.** A single fragment is exposed as an independently testable unit rather than a whole recipe — assertable as a text artifact without requiring a model call.
- **Unresolvable reference / cycle.** Resolution reports an ambiguous or missing reference explicitly; Composition reports a cyclic inclusion with the actual cycle path. Both halt assembly rather than degrading silently.
- **Custody migration.** Fragments move between local and remote custody. Identity must be unchanged by the move; if it is not, provenance recorded before the move stops validating after it.

---

## System Boundaries

### Inside the System

- Custody of fragments and recipes as addressed, versioned units, and the definition of fragment identity
- Resolution of a path reference and selection context to one exact fragment version, including layering and precedence rules
- Assembly of a finished prompt from a recipe, including condition evaluation, variable binding, recursive inclusion, and cycle detection
- Selection of variants and versions **as an expression of the composition mechanism, not as separate machinery** *(amendment 3)*
- Determination of the **order** in which fragments assemble, as a parameterizable dimension *(amendment 4)*
- Presentation of both individual fragments and whole recipes as distinct, independently evaluable units *(amendment 4)*
- Recording of provenance sufficient to reproduce an assembly exactly and attribute a downstream result to it
- Mapping of assembled output portions back to their source fragments
- Determination of which recipes depend on a given fragment
- The single reviewable path through which any change — human or machine-proposed — enters the library
- Presentation of recipes and individual fragments as units external capabilities can consume

### Outside the System

| External Item | Responsible Party | Interaction Pattern |
|---|---|---|
| **Executing a prompt against a model** | Consuming Application / Evaluation Capability | This system produces prompts and never calls a model |
| **Scoring, grading, and test execution** | Evaluation Capability | This system supplies assembled prompts and fragments as testable units, with provenance attached; results come back attributable |
| **Generating improved wording** | Optimization Capability | This system supplies fragment text as a starting point and receives proposed text back |
| **Physical storage of fragment content** | Fragment Custody Backend (local or remote) | Interchangeable behind a uniform view; **identity must survive the swap** |
| **Change history and patch representation** | Version Control System *(where used locally)* | Supplies history and change sets; the system does not reimplement version history |
| **Live production traffic splitting between variants** | *Not assigned — a gateway concern* | ⚠️ **Outside by current assumption, not by decision.** Amendment 2 reads A/B as offline comparison. If live traffic splitting is intended, it is a gateway function that would need to be brought in deliberately. **Flagged for confirmation.** |
| **A no-code authoring experience for non-engineers** | *Deferred per BRD* | The Domain Contributor actor is named but unserved by this structure |

### Data Ownership

| Data | Owner | Access Pattern |
|---|---|---|
| Fragment content and versions | **System** (custody delegated to a backend) | Read for resolution and assembly; written only through Change Intake & Review |
| Fragment addresses and namespace structure | **System** | Owned outright; the addressing scheme is the system's, not the backend's |
| Recipes and their declared conditions | **System** | Authored by Library Owner; changed through Change Intake & Review |
| Provenance records | **System** | Written at assembly; read by anyone reconciling a result to an assembly |
| Selection context / variable bindings | **Shared** — supplied by the caller, retained by the system | Supplied per assembly request; **retained in provenance, because a branch cannot be replayed without them** |
| Evaluation results and scores | **External** (Evaluation Capability) | This system supplies attributable inputs; it does not store results |
| Optimization outputs | **External until accepted** | Enters as a proposal; becomes system-owned only on acceptance |
| Change history | **Shared** — system-defined, backend-recorded | Read for review and audit |

---

## Structural Decisions

| # | Decision | Rationale | Downstream Impact |
|---|---|---|---|
| **SD1** | Fragment identity is verifiable from content and stable independent of where the fragment is stored | Amendment 1 makes custody interchangeable. If identity were derived from location, swapping custody would silently invalidate every provenance record — reproducibility would break exactly at the boundary the amendment introduces | TRD: identity scheme. PRD: identity must be visible in every reference and record |
| **SD2** | Custody is interchangeable behind a uniform view; one source of truth per configuration | Amendment 1. Deliberately *not* bidirectional synchronization between two live stores — that shape was rejected as a known source of drift | TRD: custody abstraction. PRD: migration between backends is a supported operation with an identity-preservation requirement |
| **SD3** | Resolution is separate from assembly | Answering *which fragment* is a different question from *what the text is*. Separation is what lets custody change without assembly changing, and what makes dependency analysis possible without assembling anything | TRD: two distinct concerns. PRD: impact analysis is specifiable without reference to rendering |
| **SD4** | Variant and version selection is expressed through the composition mechanism, not separate machinery | Amendment 3. A/B is conditional loading with a different condition. Adding a parallel selection subsystem would duplicate the condition language and create two ways to express the same idea | Removes a module. TRD: the condition mechanism must be able to express version and variant identity. PRD: no distinct experimentation feature set |
| **SD5** | Provenance is a first-class output of assembly, produced at assembly time — never reconstructed afterward | The BRD's highest-opportunity job (F5, 16) is attribution. Reconstruction after the fact cannot recover condition outcomes, and under SD4 a version choice *is* a condition outcome | TRD: assembly emits two artifacts. PRD: provenance is not an optional mode |
| **SD6** | Provenance retains variable bindings and condition outcomes, not only the fragments that resulted | Direct consequence of SD4. When a version is chosen by a runtime condition, the resulting fragment list records *what* loaded but not *why* — and a branch that cannot be explained cannot be replayed | TRD: record contents. PRD: reproduction is specified in terms of the full context |
| **SD7** | Assembly is deterministic: identical inputs yield an identical prompt | Without this, provenance records what happened once rather than what will happen again, and both reproduction (O2) and comparison (O11) become unsound | TRD: determinism hazards catalogued in Gate 0 must be designed against from the start, not audited later |
| **SD8** | Every change enters the library through one reviewable path, regardless of whether a person or a machine authored it | Keeps Open Question A open structurally. If A resolves to "reviewed," the path is a gate; if "trusted," it is a pass-through for machine origin. Either answer fits without restructuring | TRD: single intake path. PRD: proposal origin is recorded and visible |
| **SD9** | The trust model distinguishes condition logic from fragment text content | Open Question C, tightened by amendment 1: remote custody means fragments may cross trust boundaries. Condition logic is evaluated; fragment text is only ever text destined for a prompt. The two do not warrant the same latitude | TRD: this is the key safety boundary. PRD: constrains what conditions may express. **Not final — C is open** |
| **SD10** | The system produces prompts and provenance; it never executes a prompt or scores a result | Gate 0 found evaluation is table stakes with four more mature incumbents. Crossing this line means competing on the product's weakest ground while its differentiator goes unbuilt | Bounds scope permanently. TRD: no model-calling capability. PRD: no scoring features |
| **SD11** | Optimization is seeded per fragment; a whole-recipe optimization result cannot be attributed across its fragments | Gate 0 verified the optimization capability returns one monolithic result with no sub-prompt attribution. Designing as if per-fragment credit existed would build on a false premise. **Amendment 4 largely dissolves this as a practical limit**: optimization is used for minor per-fragment adjustments, which is exactly the shape the capability supports natively | TRD: integration shape. PRD: must not promise per-fragment optimization attribution |
| **SD12** | Fragment **order** is a parameterizable dimension of a recipe, controlled by the same variables and conditions that control inclusion | Amendment 4. Order affects a prompt's behavior as much as content does, so it must be variable to be testable. Treating order as fixed would make an entire class of variation untestable, and adding separate ordering machinery would fragment the condition language | TRD: assembly must expose ordering as a resolved outcome. PRD: order variation is a first-class case, not a workaround |
| **SD13** | An assembly is identified by its fragment versions, its bindings, **and its order** — never by the fragment set alone | Direct consequence of SD12: two assemblies with an identical fragment set can differ by sequence. An identity that ignores order would attribute two genuinely different prompts to the same assembly, silently corrupting every comparison | TRD: identity and record contents. PRD: reproduction and comparison are specified over the ordered assembly |
| **SD14** | A fragment and a whole recipe are **distinct evaluation targets**, both first-class | Amendment 4. Fragment-level evaluation catches a bad primitive; recipe-level evaluation catches bad composition. Neither substitutes for the other, and Gate 0 verified both are achievable — fragment-level without any model call | TRD: two integration shapes. PRD: two distinct evaluation capabilities |

---

## Notes for PRD/TRD

**For the PRD (Gate 3):**
- Feature priority should follow the BRD's opportunity scores, which place provenance and attribution (F5=16, F9=14) at or above composition mechanics. A feature set ordered "build composition, then add provenance" would invert the finding.
- Impact Analysis is described here as a cross-module capability, not a module. The PRD should specify it as a distinct user-facing capability regardless.
- The Domain Contributor actor is named but unserved. The PRD should record what would have to change to serve it, so the deferral stays visible rather than becoming an accidental omission.
- Order variation *(amendment 4, SD12)* is a first-class case. The PRD must specify how order is expressed and how an ordering is referenced, not treat reordering as an edge case of inclusion.
- Fragment-level and recipe-level evaluation *(SD14)* are two distinct capabilities with different costs — Gate 0 verified fragment-level is achievable without a model call. The PRD should specify them separately.
- The live-traffic-splitting boundary is currently an **assumption**, not a decision. The PRD should either confirm it or surface it for decision.

**For the TRD (Gate 5) and Dependency Map (Gate 6):**
- Prefix-routed namespace dispatch with ordered fallback and override layering is well-established prior art for Resolution and should be evaluated rather than reinvented.
- Cycle detection must report the actual cycle path. Gate 0 documented both the quality bar and a widely-copied anti-pattern of silently continuing past a cycle.
- The determinism hazards catalogued in Gate 0 (unstable iteration order, wall-clock and environment leakage, locale-dependent operations) must be designed against under SD7 — they are not testable-in later.
- Provenance may warrant two distinct representations: a lightweight positional map for human debugging (F3/O3) and a heavier attestation binding a result to exact inputs (F5/O2). Grouped as one module here because both are recorded in the same act; splitting them is a TRD decision.
- The evaluation seam verified in Gate 0 permits asserting on the **rendered prompt itself**, which is what makes SD10 tenable — fragments and recipes are testable as text artifacts without a model call.
- SD9 is the safety boundary and depends on Open Question C. The TRD must not select a condition mechanism before C is decided.
- **The project is not yet under version control**, and SD2 contemplates version control as a local custody option. Initializing it is task zero.

---

## SBP Validation

| Category | Check | Result |
|---|---|---|
| **System Vision** | Describes the solution's nature, not the problem | ✅ |
| | Holistic, covers the whole system | ✅ |
| | Concise | ✅ 3 sentences |
| | Technology-agnostic | ✅ |
| | Actor-aware | ✅ |
| **Actors** | Human actors identified | ✅ 5 (one explicitly deferred) |
| | External systems identified | ✅ 6, including the model provider named to mark the boundary |
| | Automated processes noted | ✅ optimization capability as a proposal source |
| | Each actor has a clear role | ✅ |
| **Modules** | Named by business function | ✅ |
| | Singular responsibility each | ✅ |
| | 4–7 modules | ✅ 6 (amendment 3 removed a 7th) |
| | Dependencies documented | ✅ per module + overview diagram |
| **Primary Flow** | Starts from initiating actor | ✅ Library Owner |
| | Ends at value delivery | ✅ at an attributable, reproducible result — not merely at a rendered prompt |
| | Decision points included | ✅ condition evaluation, review acceptance |
| | Module handoffs shown | ✅ |
| | Secondary flows noted | ✅ 6 |
| **Boundaries** | Inside/outside clearly defined | ✅ |
| | Every external actor appears in boundaries | ✅ |
| | Data ownership stated | ✅ 8 categories |
| | Delegation targets identified | ✅ |
| **Structural Decisions** | Each has rationale and downstream impact | ✅ 11 decisions |
| | No technology names | ✅ |
| **Purity** | Zero technology product names | ✅ verified by scan |
| | Zero implementation terms | ✅ |
| | Zero feature specifications | ✅ |
| | Zero user stories | ✅ |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **System Clarity** | 22/25 | Vision is holistic and the value chain correctly terminates at attribution rather than rendering. Deducted 3: two structural decisions (SD8, SD9) remain contingent on open questions A and C. |
| **Actor Completeness** | 23/25 | 11 actors including all external systems and the deliberately-deferred one; the model provider is named specifically to mark a boundary. Deducted 2: whether a live-traffic-splitting actor belongs is an unconfirmed assumption. |
| **Module Cohesion** | 23/25 | 6 cohesive modules with a clear separation between resolution and assembly. Deducted 2: Impact Analysis sits ambiguously between a capability and a module, and Provenance groups two arguably separable concerns. |
| **Flow Coverage** | 19/25 | Primary flow is clear with 6 secondary flows including failure paths. Deducted 6: the assembly→evaluation→result-attribution loop is the system's core value chain and crosses an external boundary where this gate cannot verify the round trip end to end. |
| **Total** | **87/100** | ≥ 80 → proceed to PRD |

**Gate Result:** ✅ **PASS** — with SD8 and SD9 explicitly contingent on Open Questions A and C, which Gate 3 (PRD) requires as input.

**Next Step:** Gate 3 — PRD Creation (`souschef:pre-dev-prd-creation`)
