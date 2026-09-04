# Product Requirements Document: promptrecipe

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 3 — Product Requirements Document |
| **Track** | full (greenfield, 9 gates) |
| **BRD Reference** | `docs/pre-dev/promptrecipe/brd.md` (approved, amendments 1–2) |
| **SBP Reference** | `docs/pre-dev/promptrecipe/sbp.md` (approved, amendments 1–4) |
| **Research Reference** | `docs/pre-dev/promptrecipe/research.md` (approved) |
| **Status** | Draft — pending human approval (amendment 5 applied) |
| **Confidence Score** | 67/100 — see the note below; this is a **validation** signal, not a requirements-quality signal |
| **Language** | en |

> **⚠️ Read the confidence score correctly.** 63/100 falls in the rubric's "present options" band. It is low because this is a greenfield product with **zero users**: there is no direct user feedback, no established baseline, and no quantified ROI. It is *not* low because the requirements are unclear. The score is saying **go validate with design partners before building**, and the highest-value action right now is establishing the baselines that every metric below depends on. Details in Gate 3 Validation.

---

## Executive Summary

promptrecipe makes a large prompt manageable by decomposing it into named, path-addressed fragments assembled by a recipe whose variables and conditions decide which fragments load, in what order, and at which version — so a prompt too big to change, test, or improve safely as a monolith becomes a set of parts each of those things can be done to individually. Every assembly emits a provenance record identifying exactly which fragment versions, variable bindings, condition outcomes, and ordering produced it, making any downstream evaluation result attributable to an exact assembly and reproducible from its record alone. Fragments and whole recipes are both independently evaluable, and machine-proposed wording improvements enter through the same reviewable path as human edits.

---

## Problem Definition

> **Amendment 6 (stakeholder, 2026-08-31) — the consumer, the mental model, and the driving use case.**
>
> **(a) The consumer is an agent framework.** The library's job is to load a prompt — **small or large** — into an agent built on an orchestration framework. Size is not the qualifier; the qualifier is that the prompt must be **manageable, structured, testable, and reusable** at any size. This softens amendment 5: decomposing a monolith is one entry point, not the only one.
>
> **(b) The mental model is functions.** A fragment is to a prompt what a function is to a program: defined once, called from many places, parameterized at the call site, composable, and testable in isolation. This framing should be used in user-facing material — it makes the product immediately legible to the audience that has it.
>
> **(c) The driving use case is model portability.** Prompt A is a template of several parts, loaded for Model X. Moving to Model B means loading Template B — **90% the same parts, a few changed — without losing Prompt A.** Both coexist. This is the concrete reason templates and fragments exist, and it is now a primary driver rather than one example of contextual variation. See FR-036/FR-037 and US-26/US-27.

> **Amendment 5 (stakeholder, 2026-08-31) — primary problem reframed.** The problem is not first about *many* prompts. It is about **one large prompt** and the impossibility of managing it through its lifecycle: changing it, testing it, validating it, improving it. The many-prompts problem is real but **secondary** — it is what the same structure also solves. This reframing is recorded because it lowers the product's activation threshold substantially (see A1) and adds FR-035.

**The problem.** A prompt that has grown large becomes unmanageable as a single unit: changing part of it risks the rest, no part of it can be tested in isolation, nothing validates that its pieces are internally consistent, and improving one section means re-reading and re-approving the whole thing. Secondarily, once several such prompts exist they come to share large amounts of identical text, which cannot then be corrected in one place.

### The four lifecycle activities a large prompt resists

| Activity | Why a monolithic prompt resists it | What decomposition makes possible |
|---|---|---|
| **Change** | Editing one section means re-reading and re-approving the whole prompt; the blast radius of a small edit is the entire prompt | Change one fragment; know exactly what else uses it (FR-007, FR-011) |
| **Test** | The only testable unit is the whole prompt, so a failure localizes to nothing smaller than "the prompt" | Test each fragment independently, and the assembly separately (FR-024, FR-025) |
| **Validate** | Nothing checks that the prompt's pieces are internally consistent or that required context was supplied — errors surface as bad output, not as failures | Declared expectations that fail loudly at assembly (FR-021) |
| **Improve** | Automated improvement returns a rewritten monolith no one can review section by section; accepting it is all-or-nothing | Seed improvement per fragment; receive a proposal scoped to that fragment (FR-026) |
| **Port** *(amendment 6)* | Adapting a prompt to a different model means copying it and editing — the copy immediately begins diverging, and every later fix must be applied twice, forever | Model-specific templates share the fragments that don't change and differ only where they must; neither variant is lost (FR-036) |

### Who has this problem

**Primarily: anyone loading a prompt into an agent built on an orchestration framework**, where that prompt must be maintained over time — whether it is small or large *(amendment 6)*. Two entry points into the same pain:

- **The monolith** *(amendment 5)* — a prompt that outgrew comfortable review: a system prompt, an agent instruction set, a long extraction or classification prompt. **One big prompt is enough; a library is not required.**
- **The fork** *(amendment 6)* — a prompt that must run against more than one model, where the second version was made by copying the first and now diverges permanently.

Secondarily, teams past roughly a dozen prompts where instructions repeat. Gate 0 found this population is served by tools that solve *storage and versioning* well and *composition* barely at all.

### Quantified and qualitative evidence

| Evidence | Source | Confidence |
|---|---|---|
| Prompt changes get buried in mixed commits — "a commit might include a refactor, a bug fix, and a prompt tweak all at once" — leaving no visibility into prompt evolution | Published vendor analysis (Feb 2026) | ⚠️ **Interested source.** That vendor has since exited the category, and no neutral corroboration was found. Treat as credible but not settled |
| Splitting large prompts into "multiple, single-purpose prompts (akin to small, single-responsibility functions)" is recommended practice | Independent practitioner writing | **High relevance** — a non-vendor source recommending decomposition of *a large prompt*, which is precisely the amendment-5 framing |
| No surveyed tool (17) offers hierarchical path-addressed fragment identity; all addressing is flat | Gate 0 direct documentation survey | High — verified per tool |
| No surveyed tool offers conditional logic that governs *which fragment loads* with failure semantics; all conditionals are text toggles | Gate 0 direct documentation survey | High — verified per tool |
| The one framework whose assert concept came closest deprecated it | Gate 0, official documentation | High |

**⚠️ Honest gap:** the pain is well-evidenced *structurally* (nobody has built this) and thinly evidenced *empirically* (no direct user research). BRD assumption A1 — that teams reach painful repetition quickly enough to matter — remains the highest-risk untested assumption. **Validating it precedes building.**

### Current workarounds

| Workaround | Why teams use it | Where it fails |
|---|---|---|
| Copy-paste into separate prompts | Zero setup, total transparency | Copies drift; no search finds them all; a known-wrong instruction stays wrong because fixing it is too expensive |
| Near-duplicate prompt variants per language/tier/model | Simplest way to handle variation | Multiplies the maintenance surface; consolidation never happens |
| Hosted prompt registries | Mature versioning, non-engineer access, strong evaluation | Flat addressing; composition is single-level text substitution at best |
| Host-language string assembly | Version-controlled and reviewable | No addressable cross-recipe fragments; no provenance; no dependency analysis |
| Tolerating the mess | No cost today | **The real competitor.** Switching cost is attention, not money |

---

## User Personas

| # | Persona | Core Jobs | Primary Frustration | Success Looks Like |
|---|---|---|---|---|
| **P1** | **Library Owner** *(primary)* — maintains the prompts a product depends on; started with six, now has 80–300 | F1, F3, F7, F8, E1, E2, E4 | Knows there are wrong instructions in production; fixing means finding every copy | Corrects a shared instruction once and can *prove* it propagated |
| **P2** | **Change Reviewer** — approves prompt changes they did not write | F4, F6, S2, E3 | Prompt changes arrive mixed into unrelated work, so real review never happens | Sees exactly what wording changed, in isolation, with enough context to judge |
| **P3** | **Evaluator** — runs evaluations and acts on results | F5, F8, E1 | A result exists, but which exact assembly produced it, and can it be reproduced next week? | Every result carries an exact, reproducible identity |
| **P4** | **Improvement Adopter** — wants automated improvement but won't ship unread wording | F6, E3, S2 | All-or-nothing choice between hand-authored and machine-generated prompts | Machine proposals arrive as reviewable changes against a named fragment |
| **P5** | **Domain Contributor** *(secondary — deliberately deferred)* — holds the knowledge that makes a prompt good, doesn't work in engineering tooling | S3, E2 | Files requests and waits | Proposes wording without an engineer intermediary. **Not served in this requirement set — see FR-034** |

---

## User Stories

### Epic 1 — Traceability & Attribution *(P0 — highest opportunity: F5 = 16)*

**US-01** — As an **Evaluator**, I want every assembled prompt to carry a record of exactly what produced it, so that I can attribute any test result to a specific assembly.
- **Given** a recipe is assembled with a set of variable bindings, **when** the assembly completes, **then** a provenance record is produced identifying every fragment version consumed, every variable binding, every condition outcome, and the resulting order.
- **And** the record is produced as part of the assembly, never reconstructed afterward.
- **And** an assembly cannot be produced without its record.

**US-02** — As an **Evaluator**, I want to reproduce an assembly from its record alone, so that I can re-run last month's result today and get the identical prompt.
- **Given** a provenance record, **when** I request reproduction, **then** the resulting prompt is byte-identical to the original.
- **And** if any referenced fragment version is no longer retrievable, reproduction fails explicitly rather than substituting a different version.

**US-03** — As an **Evaluator**, I want two assemblies that differ only in fragment order to be distinguishable, so that ordering experiments produce trustworthy results.
- **Given** two assemblies with an identical fragment set but different order, **when** each is identified, **then** their identities differ.
- **And** a result attributed to one is never attributable to the other.

**US-04** — As a **Library Owner**, I want to see which fragment produced which portion of an assembled prompt, so that when output is wrong I can fix the right fragment.
- **Given** an assembled prompt, **when** I inspect any portion of it, **then** the fragment and version that produced it is identified.
- **And** this works for fragments included recursively through other fragments.

### Epic 2 — Change Once, Propagate Everywhere *(P0 — F1 = 15)*

**US-05** — As a **Library Owner**, I want a repeated instruction to exist as one fragment, so that correcting it once corrects it everywhere.
- **Given** a fragment referenced by many recipes, **when** I change it and the change is accepted, **then** every recipe resolving that reference uses the changed fragment according to its selection policy.
- **And** I can list every recipe affected.

**US-06** — As a **Library Owner**, I want to know which recipes depend on a fragment *before* I change it, so that I don't discover the blast radius afterward.
- **Given** a fragment, **when** I request its dependents, **then** every recipe that can resolve to it is listed, including through recursive inclusion.
- **And** this requires no assembly to be performed.

**US-07** — As a **Library Owner**, I want to preview what a proposed change would do to dependent recipes, so that I can judge risk before accepting it.
- **Given** a proposed fragment change, **when** I request a preview, **then** for each dependent recipe I see how its assembled output would differ.

### Epic 3 — Reviewable Change, Human or Machine *(P0 — F6 = 15, E3 = 14)*

**US-08** — As a **Change Reviewer**, I want every change to arrive through one path with its origin visible, so that I know whether a person or a machine wrote it.
- **Given** a proposed change, **when** it is presented, **then** its origin is identified — the person, or the automated capability and the run that produced it.
- **And** machine-originated and human-originated changes traverse the same path.

**US-09** — As a **Change Reviewer**, I want to see a prompt change in isolation from unrelated work, so that I can actually review it.
- **Given** a proposed change, **when** I review it, **then** I see only the fragment text that changed and its immediate context.

**US-10** — As an **Improvement Adopter**, I want to accept or reject a machine proposal explicitly, so that no wording reaches production unread.
- **Given** a proposal, **when** I decide, **then** the decision, the deciding actor, and the time are recorded.
- **And** a proposal not accepted does not affect any assembly.
- **And** *(policy — see Open Question A)* whether acceptance is **required** is configurable; the path is identical either way.

### Epic 4 — Composition with Conditions *(P0/P1 — F2 = 13)*

**US-11** — As a **Library Owner**, I want a recipe to declare which fragments it needs and under what conditions each loads, so that one recipe replaces many near-duplicates.
- **Given** a recipe with conditions and a set of bindings, **when** assembled, **then** exactly the fragments whose conditions hold are included.
- **And** the outcome of every condition is recorded in provenance.

**US-12** — As a **Library Owner**, I want conditions to control the **order** fragments assemble in, so that I can test ordering variations without maintaining separate recipes.
- **Given** a recipe whose ordering is bound to a variable, **when** assembled with different values, **then** the same fragments assemble in different orders.
- **And** each ordering is a distinct assembly with its own identity.

**US-13** — As an **Evaluator**, I want to select a fragment version or variant through the recipe's own conditions, so that A/B comparison needs no separate mechanism.
- **Given** a recipe whose condition selects among coexisting versions, **when** assembled with different bindings, **then** the corresponding version is used.
- **And** the selected version appears in provenance.

**US-14** — As a **Library Owner**, I want to declare expectations that must hold for an assembly to be valid, so that a missing binding fails loudly rather than producing a silently wrong prompt.
- **Given** a recipe with a declared expectation, **when** it does not hold, **then** assembly fails with a message naming the expectation and what was actually supplied.
- **And** no partial prompt is emitted.

**US-15** — As a **Library Owner**, I want cyclic fragment references reported with the actual cycle, so that I can fix them quickly.
- **Given** fragments that reference each other cyclically, **when** assembly is attempted, **then** it fails reporting the **complete cycle path**, not merely that a cycle exists.
- **And** assembly never silently drops part of a cycle to continue.

### Epic 5 — Addressing at Scale *(P1 — F7 = 12)*

**US-16** — As a **Library Owner**, I want fragments addressed hierarchically, so that names stay unambiguous as the library grows.
- **Given** a growing library, **when** I address a fragment by path, **then** exactly one fragment version resolves for a given selection context.
- **And** two fragments in different parts of the hierarchy may share a leaf name without colliding.

**US-17** — As a **Library Owner**, I want an ambiguous or missing reference reported explicitly, so that a typo doesn't silently resolve to the wrong fragment.
- **Given** a reference that is ambiguous or unresolvable, **when** resolution runs, **then** it fails naming the reference and the candidates considered.
- **And** resolution never silently shadows one fragment with another.

**US-18** — As a **Library Owner**, I want override and layering precedence to be inspectable, so that I can explain why a particular fragment won.
- **Given** layered sources, **when** I ask why a reference resolved as it did, **then** the precedence chain and the winner are shown.

### Epic 6 — Custody Across Local and Remote *(P0/P1)*

**US-19** — As a **Library Owner**, I want fragments to live locally or remotely without changing how I address them, so that custody is an operational choice rather than a rewrite.
- **Given** a fragment, **when** custody moves between local and remote, **then** its address and identity are unchanged.
- **And** provenance recorded before the move still validates after it.

**US-20** — As a **Library Owner**, I want fragment identity to be verifiable rather than asserted, so that I can trust a remotely-sourced fragment is the one my record names.
- **Given** a fragment version from any custody, **when** its identity is checked, **then** it is verifiable from the content itself.
- **And** a mismatch is reported rather than tolerated.

### Epic 7 — Evaluation & Optimization Integration *(P0)*

**US-21** — As an **Evaluator**, I want to evaluate an assembled recipe as a unit with its provenance attached, so that results come back attributable.
- **Given** a recipe and a selection context, **when** exposed for evaluation, **then** the assembled prompt is provided with its assembly identity.

**US-22** — As an **Evaluator**, I want to evaluate an individual fragment independently, so that I can catch a bad primitive without assembling anything around it.
- **Given** a fragment, **when** exposed for evaluation, **then** it is evaluable on its own.
- **And** evaluating a fragment's text requires no model execution.

**US-23** — As an **Improvement Adopter**, I want to seed an improvement run from a single fragment's text, so that what comes back is attributable to that fragment.
- **Given** a fragment, **when** I seed a run, **then** its current text is supplied as the starting point.
- **And** the returned text enters as a proposal against **that** fragment.
- **And** *(limitation, stated deliberately)* a run seeded from a whole assembled recipe returns one result that **cannot** be attributed across its constituent fragments.

### Epic 9 — Model Portability *(P0 — amendment 6, the driving use case)*

**US-26** — As a **Library Owner**, I want a prompt adapted for a different model to share the parts that don't change, so that the two versions don't diverge permanently.
- **Given** a prompt in use for one model, **when** I create a variant for another model, **then** the fragments that are unchanged are the *same fragments*, not copies.
- **And** correcting a shared fragment corrects it for every model variant at once.
- **And** the original variant remains fully usable — creating the second never degrades or replaces the first.

**US-27** — As a **Library Owner**, I want to express model variation either as separate recipes sharing fragments **or** as conditions inside one recipe, so that I can match the expression to how much actually diverges.
- **Given** variants differing only in a few fragments, **when** I express the difference as conditions on one recipe, **then** one recipe serves both models.
- **Given** variants differing structurally, **when** I express them as separate recipes referencing shared fragments, **then** both are maintained without duplicating the shared parts.
- **And** neither form is privileged; the choice is the author's.

**US-28** — As a **developer using an agent orchestration framework**, I want to load an assembled prompt into my agent without the framework needing to know about fragments, so that adoption requires no change to how my agent is built.
- **Given** an agent built on an orchestration framework, **when** it requests a prompt, **then** it receives assembled prompt content in a directly usable form.
- **And** the framework requires no awareness of fragments, recipes, conditions, or versions.
- **And** the accompanying assembly identity is available but never required for basic use.

### Epic 8 — First Value Fast *(P0 — survival metric M11)*

**US-25** — As a **Library Owner with one large existing prompt**, I want to break it into fragments without changing what it produces, so that I can adopt the structure without risking a behavior change.
- **Given** an existing prompt, **when** I decompose it into fragments assembled by a recipe, **then** the assembled output is byte-identical to the original.
- **And** any difference is reported explicitly rather than silently accepted.
- **And** decomposition is incremental: extracting one fragment at a time is valid, and a partially-decomposed prompt still assembles correctly.


**US-24** — As a **new Library Owner**, I want to produce my first assembled prompt within 30 minutes of starting, so that the approach proves itself before I have invested in it.
- **Given** a person who has never used the product, **when** they follow the introductory path, **then** they produce a working assembled prompt from at least two fragments within 30 minutes.
- **And** this requires no remote custody and no evaluation or optimization integration.

> **Why this story is P0 despite looking like polish.** Gate 0 identified copy-paste and doing nothing as the real competitor, with zero switching cost. Nobody arrives holding 200 prompts. A product that only demonstrates value at scale never gets the chance to reach scale.

---

## Feature Requirements

Priority follows the BRD's opportunity scores. **Traceability and trust rank at or above composition mechanics** — an ordering of "build composition first, add provenance later" would invert the BRD's central finding.

| ID | Requirement | Module | Priority | Stories | Metric |
|---|---|---|---|---|---|
| **FR-001** | Every assembly emits a provenance record as a first-class output, produced at assembly time | Provenance | **P0** | US-01 | M3 |
| **FR-002** | An assembly's identity comprises fragment versions, variable bindings, condition outcomes, **and order** — never the fragment set alone | Provenance | **P0** | US-01, US-03 | M12 |
| **FR-003** | An assembly is reproducible byte-identically from its provenance record alone; failure to reproduce is explicit | Provenance | **P0** | US-02 | M3 |
| **FR-004** | Any portion of an assembled prompt maps back to the fragment version that produced it, including through recursive inclusion | Provenance | **P0** | US-04 | M4 |
| **FR-005** | An externally-produced result can be bound to exactly one assembly identity | Provenance | **P0** | US-03, US-21 | M12 |
| **FR-006** | Fragments and recipes are addressed within a hierarchical namespace; each fragment has one definition | Fragment Library | **P0** | US-05, US-16 | M1, M9 |
| **FR-007** | Changing a fragment once causes every recipe resolving that reference to use the changed fragment per its selection policy | Fragment Library | **P0** | US-05 | M1, M2 |
| **FR-008** | Multiple versions of a fragment coexist as concurrently addressable candidates | Fragment Library | **P0** | US-13 | M12 |
| **FR-009** | Fragment version identity is verifiable from content and stable across custody backends | Fragment Library | **P0** | US-19, US-20 | M3 |
| **FR-010** | Custody backends are interchangeable (local and remote) behind a uniform view; one source of truth per configuration, no bidirectional synchronization | Fragment Library | **P0** | US-19 | — |
| **FR-011** | All recipes depending on a given fragment can be listed without performing any assembly, including recursive dependents | *Impact Analysis* | **P0** | US-06 | M6 |
| **FR-012** | The effect of a proposed fragment change on each dependent recipe can be previewed before acceptance | *Impact Analysis* | **P0** | US-07 | M6 |
| **FR-013** | All changes — human-authored and machine-proposed — enter the library through a single intake path | Change Intake & Review | **P0** | US-08 | M8 |
| **FR-014** | Every proposal records its origin: the person, or the automated capability and run that produced it | Change Intake & Review | **P0** | US-08 | M5 |
| **FR-015** | A proposed change is presentable in isolation from unrelated changes | Change Intake & Review | **P0** | US-09 | M8 |
| **FR-016** | Acceptance or rejection is recorded with the deciding actor and time; an unaccepted proposal affects no assembly | Change Intake & Review | **P0** | US-10 | M5, M9 |
| **FR-017** | Whether acceptance is *required* before a proposal takes effect is a **configurable policy**, not a structural property | Change Intake & Review | **P0** | US-10 | — |
| **FR-018** | A recipe declares the fragments it needs and the conditions governing each one's inclusion | Composition | **P0** | US-11 | M7 |
| **FR-019** | Conditions and variables determine the **order** in which fragments assemble | Composition | **P0** | US-12 | M12 |
| **FR-020** | Conditions can select among coexisting fragment versions or variants, using the same mechanism as inclusion — no separate selection subsystem | Composition | **P0** | US-13 | M12 |
| **FR-021** | A recipe can declare expectations that must hold; a violated expectation fails assembly with a message naming the expectation and the actual input, emitting no partial output | Composition | **P0** | US-14 | — |
| **FR-022** | Recursive fragment inclusion is supported; a cycle fails assembly and reports the **complete cycle path** | Composition | **P0** | US-15 | — |
| **FR-023** | Assembly is deterministic: identical inputs yield an identical prompt | Composition | **P0** | US-02 | M3 |
| **FR-024** | An assembled recipe is exposable as an evaluable unit with its assembly identity attached | Integration Surface | **P0** | US-21 | M3 |
| **FR-025** | An individual fragment is exposable as an independently evaluable unit; evaluating its text requires no model execution | Integration Surface | **P0** | US-22 | — |
| **FR-026** | A fragment's text can seed an improvement run, and returned text enters as a proposal against that fragment | Integration Surface | **P0** | US-23 | M5 |
| **FR-027** | The system never executes a prompt against a model and never scores a result | *(boundary)* | **P0** | — | — |
| **FR-028** | A new user produces a working assembled prompt from at least two fragments within 30 minutes, without remote custody or external integrations | *(cross-cutting)* | **P0** | US-24 | M11 |
| **FR-036** | Model-specific prompt variants share unchanged fragments by reference rather than by copy, and coexist — creating one never replaces or degrades another | Fragment Library, Composition | **P0** | US-26, US-27 | M2, M7 |
| **FR-037** | Model variation is expressible **either** as separate recipes referencing shared fragments **or** as conditions within a single recipe; neither form is privileged | Composition | **P0** | US-27 | M7 |
| **FR-038** | Assembled prompt content is consumable by an agent orchestration framework with no awareness of fragments, recipes, conditions, or versions required on the framework's side | Integration Surface | **P0** | US-28 | M11 |
| **FR-035** | An existing prompt can be decomposed into fragments incrementally, with byte-identical assembled output verified against the original at every step | Composition, Provenance | **P0** | US-25 | M11 |
| **FR-029** | A path reference plus selection context resolves to exactly one fragment version | Resolution | **P1** | US-16 | M9 |
| **FR-030** | Layering and override precedence is deterministic and inspectable — the winner and the chain that produced it can be shown | Resolution | **P1** | US-18 | M9 |
| **FR-031** | An ambiguous or unresolvable reference fails explicitly, naming the reference and candidates; resolution never silently shadows | Resolution | **P1** | US-17 | M9 |
| **FR-032** | One recipe covers contextual variation that would otherwise require separate near-duplicate prompts | Composition | **P1** | US-11 | M7 |
| **FR-033** | A complete history is available showing what changed, when, and who accepted it | Change Intake & Review | **P2** | US-10 | — |
| **FR-034** | **DEFERRED** — a contribution path for people who do not work in engineering tooling | *(none — deferred)* | **P3** | — | — |

### FR-034 — the deferral, stated so it stays visible

Persona **P5 (Domain Contributor)** is not served by this requirement set. The job it holds (S3) scored lowest at 9, and serving it pulls directly against the model serving P1–P4.

**What would have to become true to serve it:** evidence that the people who hold prompt-quality knowledge are predominantly *not* the people who can work in an engineering workflow. If design-partner validation shows the pain concentrates among non-engineer prompt owners, P5 becomes primary and this requirement set needs rework — not extension. **This is a deliberate, reversible position, recorded so it cannot become an accidental omission.**

---

## Access & Audit Requirements *(business level)*

| Question | Requirement |
|---|---|
| Does the feature need to identify who performed an action? | **Yes.** Every accepted change records the deciding actor and time (FR-016, FR-033) |
| Are there roles with different permissions? | **Yes.** Proposing a change and accepting one are distinct capabilities; not everyone who can propose can accept |
| Does it handle access to shared resources? | **Yes.** Remote custody means fragments may be readable across team or organizational boundaries; who may read and who may write must be distinguishable |
| Is an audit trail required? | **Yes.** What changed, when, who accepted, and whether the origin was human or machine (FR-014, FR-033) |
| Regulatory requirements | **None identified.** The system holds prompt text and provenance, not personal data. Should a team place regulated content in a fragment, that is their data-handling concern; note it as a documented caveat rather than a system requirement |

---

## Success Metrics

| ID | Metric | Target | Timeframe | Requirements |
|---|---|---|---|---|
| **M1** | Median time to correct a repeated instruction everywhere | ≤ 5 min | 3 months post-launch | FR-006, FR-007 |
| **M2** | Corrections reaching every affected prompt | 100% | 3 months | FR-007, FR-011 |
| **M3** | Results traceable to an exact assembly and reproducible | ≥ 99% | 6 months | FR-001, FR-003, FR-023, FR-024 |
| **M4** | Median time to identify which fragment produced a portion of output | ≤ 2 min | 6 months | FR-004 |
| **M5** | Machine proposals decided within one working day | ≥ 80% | 9 months | FR-014, FR-015, FR-016, FR-026 |
| **M6** | Dependents identified before a shared change ships | ≥ 95% | 6 months | FR-011, FR-012 |
| **M7** | Reduction in maintained near-duplicate prompts | ≥ 60% | 6 months per team | FR-018, FR-032 |
| **M8** | Prompt changes reviewable in isolation | ≥ 90% | 3 months | FR-013, FR-015 |
| **M9** | Naming collisions or ambiguous references per 100 fragments | ≤ 1 | 12 months | FR-029, FR-030, FR-031 |
| **M10** | Design-partner teams still maintaining a library ≥ 20 fragments | ≥ 6 of 8 | 6 months | composite |
| **M11** | Teams reaching first assembled prompt within 30 min | ≥ 75% | 6 months | FR-028 |
| **M12** | Version comparisons attributing unambiguously to an exact version | 100% | 6 months | FR-002, FR-005, FR-008, FR-019, FR-020 |

**All baselines remain unestablished.** Establishing them across 5–8 design-partner teams is prerequisite work, not follow-up — see the confidence note.

---

## Scope Boundaries

### In Scope

Fragment custody and hierarchical addressing (FR-006, FR-010) · verifiable cross-backend identity (FR-009) · coexisting versions (FR-008) · resolution with inspectable precedence and explicit failure (FR-029–031) · condition-driven inclusion, ordering, and version selection (FR-018–020) · declared expectations (FR-021) · recursive inclusion with full cycle reporting (FR-022) · deterministic assembly (FR-023) · first-class provenance with order-aware identity, span mapping, and reproduction (FR-001–005) · dependency listing and change preview (FR-011, FR-012) · single reviewable intake path with origin tracking and configurable acceptance policy (FR-013–017, FR-033) · recipe-level and fragment-level evaluation exposure (FR-024, FR-025) · per-fragment optimization seeding and proposal return (FR-026) · first-value-in-30-minutes (FR-028) · incremental decomposition of an existing prompt with byte-identical verification (FR-035) · model-portable variants sharing fragments by reference and coexisting (FR-036, FR-037) · consumption by agent orchestration frameworks without fragment awareness (FR-038)

### Out of Scope

| Item | Rationale |
|---|---|
| **Executing prompts against a model** | FR-027. The system produces prompts and provenance |
| **Scoring, grading, test execution** | Four surveyed competitors ship more mature evaluation. Competing here spends the budget on the weakest ground while the differentiator goes unbuilt |
| **Generating improved wording** | Mature capability exists. The unserved job is *review and adoption* of proposals (F6 = 15), not generation |
| **Live production traffic splitting between variants** | ⚠️ **Out by assumption, not decision.** A/B is read as offline comparison over datasets. If live splitting is intended, that is a gateway function requiring a deliberate decision. **Flagged for confirmation** |
| **Model routing, caching, gateway functions** | Different category; unrelated to every identified job |
| **Production observability / live trace monitoring** | Where two surveyed competitors pivoted *to*. Adjacent and mature |
| **No-code authoring for non-engineers** | FR-034, deferred with stated reversal conditions |
| **Automatically applying machine proposals without any review path** | FR-017 makes acceptance a configurable policy, so a "trusted" resolution relaxes a setting. Removing the path entirely would dissolve the product's clearest differentiator |
| **Migration tooling from specific competitor platforms** | Premature before design-partner validation identifies where teams are actually migrating from |

### Assumptions

| ID | Assumption | If wrong |
|---|---|---|
| **A1** | ~~Teams reach painful prompt repetition quickly enough to matter~~ → **revised by amendment 5:** a prompt grows large enough to be hard to change, test, validate, and improve as one unit | **Substantially de-risked.** The original assumption needed a *library* to accumulate before pain activated. The revised one needs **one** prompt to get big — which is near-universal and observable today. This is the single largest risk reduction in the plan |
| **A2** | Teams want to author prompt text rather than delegate authorship entirely | Premise inverts; this becomes a workflow layer over an optimizer. Tied to Open Question A |
| **A3** | Composition value appears early enough to beat copy-paste's zero switching cost | Adoption stalls at first contact. Guarded by FR-028 / M11 |
| **A4** | Evaluation and optimization capabilities remain available and integrable | Both changed ownership within 8 months; one sits inside a competitor's roadmap |
| **A5** | The people feeling this pain will adopt an engineering-workflow-shaped solution | If not, P5 becomes primary and FR-034 inverts from deferred to central |

---

## Open Questions

### 🔴 A. Is acceptance of a machine proposal *required*?

FR-017 makes this a **configurable policy** rather than a structural property, so either answer fits without rework. What still needs deciding is the **default**.

Carried recommendation: **acceptance required by default.** F6 (15) and E3 (14) score high precisely because no existing tool serves review of machine-proposed prompt changes — the product's clearest unoccupied ground. A permissive default concedes it.

### 🔴 C. How much power does condition logic get?

This PRD specifies **what conditions must express** — inclusion (FR-018), ordering (FR-019), version and variant selection (FR-020), and declared expectations (FR-021) — and deliberately **does not select the mechanism**, which is Gate 5/6.

Tightened by amendment 1: remote custody means fragments may cross trust boundaries, which is the untrusted-author case. The carried position splits the trust model — restricted condition logic, unrestricted fragment text — on the grounds that condition logic is *evaluated* while fragment text is only ever text destined for a prompt. **The TRD must not select a condition mechanism before this is decided.**

### ⚠️ Assumption awaiting confirmation

A/B is read throughout as **offline comparison over datasets**, not live production traffic splitting. If live splitting is intended, it pulls a gateway function into scope and should be decided deliberately rather than inherited.

---

## Technical Notes for TRD

Captured here and deliberately excluded from the requirements above.

- Prefix-routed namespace dispatch with ordered fallback and override layering is established prior art for FR-029–031 and should be evaluated rather than reinvented.
- FR-022's cycle-path reporting has both a documented quality bar and a widely-copied anti-pattern (silently continuing past a cycle) catalogued in Gate 0.
- FR-023's determinism must be designed for from the first structural decision. Gate 0 catalogued the specific hazards: unstable iteration order, wall-clock and environment leakage, locale-dependent operations. These are not testable-in afterwards.
- FR-002's order-aware identity and FR-005's result binding have a direct prior-art model in supply-chain attestation: a subject with its hash, resolved dependencies each with their own hash, and the identity of the producer.
- FR-004 (span mapping, human debugging) and FR-003 (reproduction, attestation) may warrant distinct representations despite being recorded in the same act.
- FR-025's "no model execution" is achievable via a pass-through provider plus assertions on the rendered prompt itself — verified in Gate 0.
- FR-026's per-fragment seeding matches the optimization capability's native shape; whole-recipe seeding does not, and Gate 0 verified no sub-prompt attribution is available.
- The host-ecosystem choice is asymmetric: one integration target is single-ecosystem with no alternative, the other is deliberately polyglot. Gate 6 decides.
- **The project is not under version control**, and FR-010 contemplates version control as a local custody option. Initializing it is task zero.
- Gate 0's most consequential unverified claim — whether the closest competitor's conditionals gate *which fragment resolves* or only rendered text — is worth resolving before the TRD commits.

---

## Gate 3 Validation

| Category | Check | Result |
|---|---|---|
| **Problem Definition** | Problem articulated in 1–2 sentences | ✅ |
| | Impact quantified or qualified | ⚠️ **Partial** — structurally strong, empirically thin; gap stated explicitly |
| | Users specifically identified | ✅ 5 personas, JTBD-grounded |
| | Current workarounds documented | ✅ 5, including "tolerating the mess" as the real competitor |
| **Solution Value** | Features address the core problem | ✅ 34 requirements traced to jobs |
| | Success metrics measurable | ✅ 12, each with number + timeframe |
| | User value clear per feature | ✅ via story mapping |
| | ROI case documented | ❌ **Not documented** — no pricing, GTM, or cost model. Drives the confidence score |
| **Scope Clarity** | In-scope explicit | ✅ |
| | Out-of-scope with rationale | ✅ 9 items |
| | Assumptions documented | ✅ 5 with failure consequences |
| **Market Fit** | Differentiation clear | ✅ two structural gaps verified across 17 tools |
| | Value proposition validated | ⚠️ **Validated against the market, not against users** |
| | Go-to-market outlined | ❌ **Not outlined** |
| **Alignment** | Every requirement traces to an SBP module | ✅ 34/34 |
| | Impact Analysis specified despite not being a module | ✅ FR-011, FR-012 |
| | Priority follows opportunity scores, not intuition | ✅ provenance/trust requirements are P0 ahead of composition mechanics |
| **Purity** | Zero technology names | ✅ scan-verified |
| | Zero architecture or implementation | ✅ moved to Technical Notes |
| | Zero protocol or storage specifications | ✅ |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Market Validation** | 15/25 | Thorough market research — 17 tools surveyed against primary sources. **No direct user feedback.** The rubric awards 25 only for direct user validation |
| **Problem Clarity** | 20/25 | Structural evidence is strong and verified. **+2 from amendments 5–6:** the activation condition is now directly observable in a candidate team's existing setup (a prompt that got big, or one forked across models) rather than a prediction about library growth. Still deducted 5: no direct user research, and every baseline unestablished |
| **Solution Fit** | 17/25 | Individual patterns are proven (path resolution, lockfiles, attestation, template composition). **+2 from amendment 6:** "fragments are functions" is not a novel pattern but the single most proven abstraction in software — define once, call many, parameterize, test in isolation. The *composite* remains novel, which is still both the opportunity and the risk |
| **Business Value** | 15/25 | Value is clear and job-linked but **indirect**: no ROI model, no pricing, no go-to-market |
| **Total** | **67/100** | Rubric band 50–79 → **present options**. Amendments 5–6 raised it 4 points by making the problem observable and the abstraction familiar; the remaining gap is **entirely** absent user validation and commercial modeling |

**Gate Result:** ✅ **PASS with a validation condition.**

The requirements are complete, traced, prioritized correctly against the BRD's findings, and pure. The 63 reflects **absence of user validation and commercial modeling** — not weakness in the requirements. Per the rubric's 50–79 guidance, the recommended next action is to **present options rather than proceed autonomously**:

| Option | When it's right |
|---|---|
| **Validate first** — recruit 5–8 design partners, establish baselines, test assumption A1 before building | If the goal is a product with users. A1 is the assumption that, if wrong, invalidates everything downstream |
| **Proceed through remaining gates** — complete the technical planning, treating the requirements as a well-formed hypothesis | If the goal is a clear buildable plan, accepting that market validation is deferred |
| **Narrow to a validation-sized slice** — build only the P0 requirements that test A1 fastest | A middle path: FR-035, FR-036, FR-018, FR-006, FR-025 would test model portability plus decomposition —  "does decomposing one large prompt make it genuinely easier to change, test, validate, and improve" — the amendment-5 question, answerable with a single design partner and a single big prompt |

**Next Step:** Gate 4 — Feature Map (`souschef:pre-dev-feature-map`)

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
