# Business Requirements Development: promptrecipe

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 1 — Business Requirements Development |
| **Track** | full (greenfield, 9 gates) |
| **Research Reference** | `docs/pre-dev/promptrecipe/research.md` (Gate 0, approved) |
| **Status** | **Approved** 2026-08-31, with amendments 1 & 2 (see Open Questions) |
| **Amendments** | 1 — storage/versioning resolved (local + remote, pluggable). 2 — versions coexist and are A/B comparable. **5 — primary problem reframed: the core problem is managing ONE LARGE prompt through change/test/validation/improvement; the many-prompts repetition problem is secondary. This lowers the activation threshold and substantially de-risks assumption A1. Applied in full in `prd.md`.** |
| **Confidence Score** | 88/100 |
| **Language** | en |

> **Document purity note.** This document names competing products **only** in the Market Context and Competing Solutions sections, where they are market facts (who exists, who exited, who was acquired) rather than technology selections. Everywhere else — press release, jobs, personas, outcomes, success criteria — capabilities are described in capability terms. No template engines, programming languages, storage technologies, or file formats appear anywhere in this document. Those belong to Gate 5 (TRD) and Gate 6 (Dependency Map).

---

## Press Release

### Fix a prompt once. Every prompt that used it updates.

**For teams whose prompt library has outgrown copy-paste — where the same paragraph lives in thirty places and correcting it means finding all thirty.**

Teams building with language models start with a handful of prompts and end up with hundreds. The same safety instruction, the same tone guidance, the same output-format rule gets pasted into prompt after prompt. When one of them turns out to be wrong, someone has to find every copy — and the copies have already drifted, so no search finds them all. Meanwhile the prompts differ by language, by customer tier, by model, so what began as one prompt is now nine near-identical variants nobody dares consolidate. When something breaks, nobody can say which part of a long prompt caused it, or which version of that part was in the prompt the day the test passed. And when a prompt change ships, it arrives buried in a commit alongside a refactor and a bug fix, so the review that should have caught it never really happened.

promptrecipe treats a prompt the way engineering treats everything else that matters: as something assembled from named, reusable parts you can find, review, and change once. Each part lives at its own address in a structure that scales past a handful of prompts without name collisions. A recipe declares which parts it needs and states the conditions under which each one loads — so one recipe covers what used to be nine variants, and the conditions are declared rules that fail loudly when they are not met, not silent text tricks. Every assembled prompt carries a record of exactly which parts and which versions produced it, so an evaluation result can always be traced back to the exact prompt that earned it. And when an automated improvement tool proposes better wording, it arrives as a reviewable change against a specific part — a proposal a human accepts or rejects, never a silent rewrite.

> "We had the same eleven-word safety line in about forty prompts. We knew it was wrong for six months and kept not fixing it, because 'find all forty' was a day of work and we'd still miss some. Now it is one part, in one place, and I changed it in a minute. The part that actually surprised me was the review — my teammate could see that one line change and nothing else. Before, that change would have been page four of a diff nobody reads."
> — Priya, staff engineer on a four-person platform team maintaining prompts for a customer-support product

**How It Works:**

1. Break the instructions you keep repeating into named parts, each at its own address.
2. Write a recipe that names the parts it needs and states the conditions under which each one loads.
3. Ask for the finished prompt — the recipe assembles it, and tells you exactly what went into it.
4. Test recipes and individual parts against your existing evaluation tooling; the record of what produced each result travels with it.
5. When automated improvement suggests better wording, review the proposed change against the part it affects, and accept or reject it.

> "Every team we talked to had independently invented the same broken workaround: copy the prompt, tweak it, promise to consolidate later, never consolidate. The industry has spent two years building places to *store* prompts. Almost nobody has worked on how prompts are *composed* — and composition is where the maintenance cost actually lives. That is the gap we are building into, and we are deliberately not trying to out-build the evaluation tools that already do their job well."
> — Founding team

**Start by naming the three instructions you have pasted most often. Those are your first parts.**

---

## Market Context

*This section names real products because their existence, status, and ownership are market facts. It selects no technology.*

**The category is churning hard, and this cuts both ways.** Of 17 surveyed tools, four have left prompt-template management within roughly 18 months: Humanloop shut down following an Anthropic acqui-hire (Sept 2025); Agenta pivoted to a general agent workspace (July 2026); Latitude pivoted to agent observability; and OpenAI is retiring its hosted prompt object (de-emphasized June 2026, shutdown November 2026), with its evaluation product on the same clock. Three more show dormancy signals: Priompt and Ell have had no functional releases in over a year, and Pezzo's hosted product appears offline.

**Both intended integration partners changed ownership within the last eight months** — promptfoo was acquired by OpenAI (March 2026) and Langfuse by ClickHouse (January 2026).

**Two readings of this evidence are equally supportable, and the BRD does not resolve it:**

| Reading | Supporting evidence |
|---|---|
| **The category is hard to sustain standalone** | Four exits and three dormancies in 18 months; the survivors are mostly features inside larger observability or evaluation platforms, not standalone prompt tools |
| **The lane is open because incumbents left** | The exits were pivots toward agent tooling and acqui-hires, not failures to find demand for composition; and the composition problem specifically was never solved by any of them |

**One clear tailwind:** as OpenAI retires its hosted prompt object, its official migration guidance tells developers to move prompts back into version-controlled application code, managed through the normal review process. The largest vendor in the market is actively pushing developers toward the model this product assumes.

**One clear headwind for the original framing:** four competitors (Langfuse, LangSmith, PromptLayer, Braintrust) ship native evaluation more mature than "integrates with an evaluation tool." **Evaluation integration is table stakes, not a value proposition.** This is reflected in Scope Boundaries below.

---

## JTBD Analysis

### Core Job Statement

**When** the prompts my team depends on have multiplied past the point where I can hold them in my head — the same instructions repeated across many of them, each drifting slightly — **I want to** assemble prompts from named parts I can change in one place, under conditions I declare explicitly, **so I can** correct something once and know it actually took effect everywhere, and explain afterwards exactly what produced any given result.

### Functional Jobs

| ID | Job Statement | Importance | Satisfaction | Opportunity |
|---|---|---|---|---|
| **F1** | When the same instruction appears in many prompts, change it once and have every prompt using it reflect the change | 9 | 3 | **15** ⬆ |
| **F2** | When a prompt must differ by context (language, tier, model, channel), express the differences as declared conditions on one recipe instead of maintaining near-duplicate copies | 8 | 3 | **13** |
| **F3** | When an assembled prompt misbehaves, identify which specific part contributed which portion of it | 8 | 2 | **14** ⬆ |
| **F4** | When reviewing a change, see the prompt's evolution on its own rather than buried among unrelated changes | 8 | 3 | **13** |
| **F5** | When an evaluation result comes back, know precisely which assembled prompt and which part versions produced it, and reproduce it exactly | 9 | 2 | **16** ⬆⬆ |
| **F6** | When automated improvement proposes better wording, receive it as a reviewable change against a specific part rather than an opaque replacement | 8 | 1 | **15** ⬆ |
| **F7** | When referring to a part by name in a library that keeps growing, have that name stay unambiguous | 7 | 2 | **12** |
| **F8** | Before shipping, know whether a change to a shared part breaks any recipe that depends on it | 8 | 2 | **14** ⬆ |
| **F9** | When two versions of a part or recipe exist, run them side by side and attribute each result to the exact version that produced it *(added by amendment 2)* | 8 | 2 | **14** ⬆ |

### Emotional Jobs

| ID | Job Statement | Importance | Satisfaction | Opportunity |
|---|---|---|---|---|
| **E1** | Feel confident that changing one prompt will not silently break another | 9 | 3 | **15** ⬆ |
| **E2** | Feel the prompt library is something I understand and own, rather than an accumulation nobody dares touch | 8 | 4 | **12** |
| **E3** | Not feel uneasy accepting wording a machine wrote, because I can see exactly what changed and why it was proposed | 8 | 2 | **14** ⬆ |
| **E4** | Stop feeling the low-grade guilt of a known-wrong instruction left unfixed because fixing it is too expensive | 7 | 2 | **12** |

### Social Jobs

| ID | Job Statement | Importance | Satisfaction | Opportunity |
|---|---|---|---|---|
| **S1** | Be seen by my engineering peers as running a disciplined practice, not ad-hoc prompt tinkering | 7 | 3 | **11** |
| **S2** | Show a reviewer or auditor exactly what changed in a prompt, when, and who approved it | 7 | 2 | **12** |
| **S3** | Let a domain expert contribute wording without needing an engineer to mediate every edit | 6 | 3 | **9** |

**Reading the scores.** The highest-opportunity jobs are **F5 (16)**, **F1, F6, E1 (15)**, and **F3, F8, E3 (14)**. Notably, three of the top jobs — F5, F6, E3 — concern **trust and traceability of change**, not composition mechanics. The composition capability is the means; what people are underserved on is *knowing what happened and being able to stand behind it*. This should shape the PRD's priority ordering.

**S3 scores lowest (9)** and is the only job where a version-control-native approach is structurally weak. It is honestly reported rather than inflated, and its implications appear in Open Question B.

### Competing Solutions

| Current Solution | Jobs It Serves | Strengths | Weaknesses | Switching Barriers |
|---|---|---|---|---|
| **Copy-paste into separate prompt files or strings** | F2 (badly), E2 | Zero setup; total transparency; no dependency | Fails F1 outright — copies drift and no search finds them all; fails F3, F5, F8 | None — this is what most teams do today, and the product must beat it on day one with a handful of prompts, not only at scale |
| **Hosted prompt registries** (Langfuse, PromptLayer, Braintrust, LangSmith) | F4, F5 (partially), S2, S3 | Mature versioning, labels, side-by-side output comparison, non-engineer access, strong native evaluation | Addressing is flat in every case; conditionals are text toggles with no failure semantics; composition is single-level text substitution at best. PromptLayer's snippets are the sole exception with a genuine recursive dependency graph | Real: existing evaluation history, team habits, and in PromptLayer's case genuinely overlapping capability |
| **Template engines used directly** | F1, F2 | Mature include/inheritance/conditional semantics; excellent resolution and namespacing machinery already exists | Serve none of F3, F5, F6, F8 — no notion of a prompt, a version, an evaluation result, or a proposal | Low — this is a building block the product should stand on rather than compete with |
| **Code-first prompt libraries** (Mirascope, Ell, BAML, Priompt) | F1 (via ordinary code reuse), F4, S1 | Version-control-native; reviewable; typed; BAML delegates evaluation cleanly | Composition is host-language reuse or single-runtime includes, not addressable cross-recipe parts; no path hierarchy; no proposal workflow | Moderate — teams that adopted these value the code-first model and would need composition to be clearly better, not merely different |
| **Automated prompt optimization** (DSPy and similar) | F6 (in a sense — it writes the prompt for you) | Genuinely effective at improving instruction text against a metric | Philosophically opposed: holds that humans should not author prompts. Produces no reviewable per-part change; its own artifact-versioning convention is informal filenames | High philosophically, low technically — the two models can compose if the boundary is drawn carefully. See Open Question A |
| **Doing nothing / tolerating the mess** | — | No cost today | Every job above goes unserved; the known-wrong-instruction problem compounds | **The real competitor.** Most teams live here, and the switching cost is attention, not money |

---

## User Personas

*Personas are defined by the jobs they hire a solution for, not by demographics.*

### P1 — The Library Owner *(primary)*

Maintains the prompts a product depends on. Started with six; now has somewhere between eighty and several hundred and has lost confidence that they are consistent. Knows there are wrong instructions still in production because fixing them means finding every copy.

**Jobs:** F1, F3, F7, F8, E1, E2, E4
**Success feels like:** correcting a shared instruction in one place and being *able to prove* it propagated.
**Currently hires:** copy-paste plus grep, and a mental list of known-wrong things not yet worth fixing.

### P2 — The Change Reviewer

Approves prompt changes but did not write them. May be a tech lead, a domain owner, or a compliance reviewer. Their core difficulty is that prompt changes arrive mixed into unrelated work, so meaningful review rarely happens.

**Jobs:** F4, F6, S2, E3
**Success feels like:** seeing precisely what wording changed, in isolation, with enough context to judge it.
**Currently hires:** code review that structurally under-serves this, plus trust in the author.

### P3 — The Evaluator

Runs evaluations and must act on the results. Their recurring frustration is reconciliation: a result exists, but which exact assembled prompt produced it, and can it be reproduced next week?

**Jobs:** F5, F8, E1
**Success feels like:** every result carrying an exact, reproducible identity of the prompt that earned it.
**Currently hires:** mature evaluation tooling that runs the tests well but does not know what a *part* is.
**Note:** this persona is well served on *running* evaluations and badly served on *provenance*. The product must respect that division — see Scope.

### P4 — The Improvement Adopter

Wants automated prompt improvement but will not ship wording no human has read. Blocked by an all-or-nothing choice between hand-authored prompts and machine-generated ones.

**Jobs:** F6, E3, S2
**Success feels like:** machine-proposed wording arriving as a reviewable change against a named part, accepted deliberately.
**Currently hires:** either nothing, or optimization run in isolation with results copied back by hand.

### P5 — The Domain Contributor *(secondary — deliberately)*

Holds the knowledge that makes a prompt good — support lead, clinician, lawyer, policy owner — but does not work in engineering tooling. Today they file requests and wait.

**Jobs:** S3, E2
**Success feels like:** proposing a wording change without an engineer as intermediary.
**Why secondary:** the jobs this persona holds score lowest (S3 = 9), and serving them well pulls directly against the version-control-native model that serves P1–P4. This tension is Open Question B and is **not** resolved here. Naming P5 as secondary is a deliberate, reversible position, not an oversight.

---

## Desired Outcomes

| ID | Outcome Statement | Dimension | Opportunity | Priority |
|---|---|---|---|---|
| **O1** | Minimize the effort required to correct a repeated instruction everywhere it appears | Functional (F1) | 15 | **P0** |
| **O2** | Maximize the certainty that an evaluation result can be traced to, and reproduced from, the exact assembled prompt that produced it | Functional (F5) | 16 | **P0** |
| **O3** | Minimize the time to identify which part of an assembled prompt produced a given portion of it | Functional (F3) | 14 | **P0** |
| **O4** | Maximize the reviewer's confidence when judging a machine-proposed wording change | Emotional (E3) / Functional (F6) | 15 / 14 | **P0** |
| **O5** | Minimize the risk that changing a shared part silently breaks a dependent recipe | Functional (F8) / Emotional (E1) | 14 / 15 | **P0** |
| **O6** | Minimize the number of near-duplicate prompts a team maintains to cover contextual variation | Functional (F2) | 13 | **P1** |
| **O7** | Maximize the reviewer's ability to see prompt changes in isolation from unrelated changes | Functional (F4) | 13 | **P1** |
| **O8** | Minimize name ambiguity as the library of parts grows | Functional (F7) | 12 | **P1** |
| **O11** | Maximize the ability to run two versions side by side and attribute each result to the exact version that produced it | Functional (F9) | 14 | **P0** *(amendment 2)* |
| **O9** | Maximize the team's ability to demonstrate what changed, when, and who approved it | Social (S2) | 12 | **P2** |
| **O10** | Minimize the dependence on an engineer for a domain expert to propose a wording change | Social (S3) | 9 | **P3** — deferred pending Open Question B |

---

## Success Criteria

All baselines are marked *to be established* because this is a greenfield product with no users. **Establishing these baselines from 5–8 design-partner teams is itself a required activity, not an afterthought** — without them, every target below is a guess. Baseline establishment must be scheduled before the first target's measurement window opens.

| ID | Metric | Target | Timeframe | Baseline | Linked Outcome |
|---|---|---|---|---|---|
| **M1** | Median wall-clock time to correct a repeated instruction across all prompts using it | ≤ 5 minutes | Measured at 3 months post-launch | To be established (hypothesis: 2–6 hours, incomplete) | O1 |
| **M2** | Proportion of corrections that reach **every** affected prompt | 100% | Measured at 3 months post-launch | To be established (hypothesis: 60–80%) | O1 |
| **M3** | Proportion of evaluation results that can be traced to an exact assembled prompt and reproduced byte-identically | ≥ 99% | 6 months post-launch | To be established (hypothesis: near 0% for composed prompts) | O2 |
| **M4** | Median time to identify which part produced a given portion of an assembled prompt | ≤ 2 minutes | 6 months post-launch | To be established (hypothesis: 15–45 min, often unresolved) | O3 |
| **M5** | Proportion of machine-proposed wording changes a reviewer reaches an accept/reject decision on within one working day | ≥ 80% | 9 months post-launch | To be established (hypothesis: no workflow exists) | O4 |
| **M6** | Proportion of shared-part changes where every dependent recipe affected is identified **before** the change ships | ≥ 95% | 6 months post-launch | To be established (hypothesis: < 30%) | O5 |
| **M7** | Reduction in maintained near-duplicate prompts for teams with contextual variation | ≥ 60% reduction | 6 months post-adoption, per team | To be established per team at onboarding | O6 |
| **M8** | Proportion of prompt changes reviewable in isolation from unrelated changes | ≥ 90% | 3 months post-launch | To be established (hypothesis: low — the documented pain is mixed commits) | O7 |
| **M9** | Naming collisions or ambiguous references reported per 100 parts | ≤ 1 | 12 months post-launch | 0 (new library) | O8 |
| **M12** | Proportion of side-by-side version comparisons whose results attribute unambiguously to an exact version | 100% | 6 months post-launch | To be established (hypothesis: not currently possible for composed prompts) | O11 |
| **M10** | Design-partner teams still actively maintaining a library ≥ 20 parts | ≥ 6 of 8 | 6 months post-onboarding | 0 | O1, O2, O5 (composite retention) |
| **M11** | Teams that report reaching first assembled prompt within 30 minutes of starting | ≥ 75% | 6 months post-launch | 0 | Adoption — guards against the "beats copy-paste only at scale" risk |

**M11 exists deliberately.** The Competing Solutions table identifies copy-paste as the real competitor, with zero switching cost. A product that only wins at 200 prompts loses, because nobody arrives with 200 prompts. Time-to-first-value is a survival metric, not a nice-to-have.

---

## Scope Boundaries

### In Scope

- Assembling prompts from named, reusable parts addressed within a structure that stays unambiguous as the library grows.
- Declaring, within a recipe, the conditions under which each part loads — as explicit rules with defined behavior when unmet, not silent text substitution.
- Recording, for every assembled prompt, exactly which parts and which versions produced it, sufficient to reproduce it exactly.
- Identifying which part contributed which portion of an assembled prompt.
- Determining which recipes depend on a given part, before that part changes.
- Presenting machine-proposed wording improvements as reviewable changes scoped to a specific part.
- Storing and versioning parts across interchangeable local and remote backends, with identity stable across the boundary *(amendment 1)*.
- Allowing multiple versions of a part or recipe to coexist as concurrently addressable, comparable candidates *(amendment 2)*.
- Working alongside the team's existing evaluation and prompt-optimization capabilities rather than replacing them.

### Out of Scope

| Item | Rationale |
|---|---|
| **Building a competing evaluation engine** | Four surveyed competitors ship more mature native evaluation. Competing here spends the product's entire budget on its weakest ground while leaving its actual differentiator unbuilt. Integrate; do not rebuild. |
| **Building a prompt optimization algorithm** | Mature optimization capability exists and works. The unserved job (F6, opportunity 15) is the **review and adoption** of proposed improvements, not their generation. |
| **Model hosting, routing, caching, or gateway functions** | A different product category entirely, well served, and unrelated to every job identified. |
| **Production observability and live trace monitoring** | Where two surveyed competitors pivoted *to*. Adjacent, mature, and orthogonal to composition. |
| **A no-code authoring environment for non-engineers** *(initially)* | Serves only S3, the lowest-scoring job (9), and pulls directly against the model serving P1–P4. Deferred pending Open Question B — deferred, explicitly, not rejected. |
| **Automatically applying machine-proposed changes without review** | Directly contradicts E3 and O4. Even if requested, it dissolves the product's core value proposition. Revisit only if Open Question A resolves against human review. |
| **Migration tooling from specific competitor platforms** | Premature before the storage model is decided (Open Question B). |

### Assumptions

| ID | Assumption | If wrong |
|---|---|---|
| **A1** | Teams reach a prompt count where repetition becomes painful — and do so quickly enough to matter | The core job never activates; the product solves a problem people do not yet feel. **Highest-risk assumption; test first.** |
| **A2** | Teams want to *author* prompt text, not delegate authorship entirely to optimization | The premise inverts and this becomes a workflow layer on top of an optimizer. Directly tied to Open Question A. |
| **A3** | Composition value shows up early enough to beat copy-paste's zero switching cost | Adoption stalls at first contact. Guarded by M11. |
| **A4** | Existing evaluation and optimization capabilities remain available and integrable | Both partners changed ownership within 8 months; one now sits inside a competitor's roadmap. Real risk, not hypothetical. |
| **A5** | The teams that feel this pain are willing to adopt an engineering-workflow-shaped solution | If the pain concentrates among non-engineer prompt owners instead, P5 becomes primary and Open Question B resolves differently. |

### Constraints

- Must work alongside existing evaluation capability rather than requiring its replacement — teams have evaluation history they will not abandon.
- Must work alongside existing prompt-optimization capability, whose philosophy is opposed to hand-authored prompts. The integration boundary must be drawn where both models remain coherent.
- Must produce prompt output that is reproducible: identical inputs must yield an identical assembled prompt, or the traceability outcome (O2) is unachievable.
- Must deliver value at small library sizes, not only at scale.
- Machine-generated parts must be assumed possible, which constrains what authoring power can safely be granted. See Open Question C.

---

## Open Questions Requiring a Decision

These three are **unresolved by design**. Each changes what gets built. Resolving them silently would be the most damaging thing this gate could do.

### 🔴 A. When a machine rewrites a part, is that change reviewed or trusted?

The product's premise is authored, reviewed prompt parts. The optimization capability it integrates with holds the opposite view — that people should not hand-write prompts at all. The question is not technical; it is about **trust, review, and ownership**.

Research found **no prior art that maps cleanly**. Established conventions for machine-written artifacts split in opposite directions: generated code is conventionally hidden from review by default, while dependency lockfiles are conventionally reviewed precisely because drift matters. Both conventions rest on the same assumption — that the generated artifact's *behavior* is what matters and its literal text does not. **For a prompt part, the text is the behavior.** Neither convention transfers.

| Option | Business consequence |
|---|---|
| **Always reviewed** — every proposal is a change a human accepts or rejects | Serves E3, O4, S2 fully. Costs reviewer attention on every optimization cycle, which may throttle how much optimization a team runs. Positions the product as the trust layer over optimization. |
| **Trusted by default, reviewable on demand** | Much faster iteration; forfeits E3 and O4 — the highest-opportunity emotional job. Effectively concedes that the optimizer owns the prompt, making the product a storage layer. |
| **Tiered by consequence** — parts declare whether changes to them require review | Most faithful to how teams actually work; a safety instruction and a phrasing tweak genuinely differ. Costs a new concept users must understand and maintain, and the tiering itself becomes a thing to get wrong. |

**Recommendation to carry into the PRD:** *always reviewed* as the default, with tiering as a deliberate later extension. Rationale: F6 and E3 score 15 and 14 precisely because no existing tool serves review of machine-proposed prompt changes — that is the product's clearest unoccupied ground, and conceding it removes the reason to choose this product over running an optimizer directly. **This is a recommendation, not a decision. It needs your confirmation.**

### ✅ B. Where does the source of truth live — **RESOLVED (amendment 1, 2026-08-31)**

**Decision (stakeholder):** *both* — versioning is **pluggable across local and remote backends**, not a single fixed store.

- **Local:** parts addressed **by path**, with the option of using **version control itself** as the versioning mechanism (including patch-based change representation).
- **Remote:** an object store or other remote backend.

**Why this is materially different from the three options originally posed.** The "hybrid" option in the original framing meant two-way synchronization between a repository and a managed platform — a well-known source of conflict and drift. This decision is **not** that. It makes the part store an abstraction with interchangeable backends, so there is one source of truth per configuration and no bidirectional sync problem. That is a substantially more tractable shape than the hybrid this gate warned against.

**Consequences:**

| Area | Consequence |
|---|---|
| **O2 / F5 (traceability)** | Strengthened and made harder. A part's identity must be stable and verifiable *across backends* — a part resolved from a remote store must be identifiable as the same part resolved locally, or reproducibility breaks at the backend boundary. |
| **O8 / F7 (naming)** | Path-based local addressing is now settled as the local model. Remote addressing must map onto the same namespace or collisions reappear at the boundary. |
| **Open Question C** | ⚠️ **Materially affected — see below.** |
| **P5 / S3 (non-engineer contribution)** | Still deferred. A remote backend does not by itself provide a contribution path for non-engineers; it changes where parts live, not who can safely edit them. |
| **Out-of-scope: migration tooling** | The rationale for deferring it ("premature before the storage model is decided") is now partly discharged. Revisit at PRD. |

**⚠️ This decision tightens Open Question C rather than leaving it neutral.** The original recommendation for C (trusted authors, full expressive power) rested on the assumption that every part is authored and reviewed by team members. A remote backend means parts may cross organizational or trust boundaries — which is precisely the untrusted-author case. **C should now be resolved at least as restrictively as the split model, and possibly more so.** The dependency between A and C now extends to B.

---

### ✅ B2. Versions coexist and are A/B testable — **NEW (amendment 2, 2026-08-31)**

**Decision (stakeholder):** multiple versions of a part or recipe must be able to **coexist as concurrently addressable things**, so A/B experiments can be run across them.

**Why this changes the shape of the product.** The BRD as originally written treated versioning primarily as *history for review and reproduction* — a backward-looking concern. This decision makes versioning **forward-looking and experimental**: a version is a live, selectable candidate, not only a past state. Two consequences follow:

1. **Provenance moves from valuable to load-bearing.** O2/F5 already scored highest at 16. An A/B result that cannot be attributed to an exact version is not merely hard to audit — it is *meaningless as an experiment*. Traceability is now a precondition for the product's experimentation story, not an auditing nicety.
2. **A new functional job is added below (F9).** Comparing versions is a distinct job from composing prompts or reviewing changes.

**Scope boundary this creates — stated explicitly because it is easy to blur:**

| In scope | Out of scope |
|---|---|
| Making versions **addressable, coexisting, and comparable**, and carrying the provenance that lets a result be attributed to an exact version | **Running** the experiment's scoring, and **production traffic splitting** between versions for live users |

Rationale for the split: scoring belongs to the evaluation capability (already out of scope, and better served by incumbents), and live traffic splitting is a gateway function (already out of scope). The product's contribution is that versions are *identifiable and comparable at all* — which is precisely what no surveyed competitor provides for composed, fragment-based prompts.

> **⚠️ Assumption flagged for confirmation:** this reads "A/B tests on versions" as **offline/experimental comparison over datasets**, not **live production traffic splitting**. If live traffic splitting is intended, that pulls a gateway function into scope and should be decided explicitly rather than inherited from this note.

---

### 🔴 C. How much authoring power should a part be allowed, given that a machine may have written it?

Genuine conditional logic in recipes requires real expressive power. Parts that may be machine-written argue for restricting that power sharply. **Research found no option that satisfies both** — every general-purpose approach surveyed carries a documented history of being escaped, and every safe-by-design approach lacks the expressiveness the conditions require.

The business question is: **what trust model does the product assume about whoever — or whatever — wrote a part?**

| Option | Business consequence |
|---|---|
| **Assume parts are trusted** (authored by team members, reviewed before use) | Permits full expressive power. Coherent only if Open Question A resolves toward *always reviewed* — review is then the control that makes the assumption true. |
| **Assume parts may be untrusted** (machine-written, third-party, or contributed) | Requires restricting expressive power, which limits what conditions can express. Necessary if parts are ever auto-applied or shared across organizational boundaries. |
| **Split the trust model** — conditions restricted, part content unrestricted | Promising: the logic governing *which* parts load is constrained, while part *text* stays free. Content is text destined for a prompt, not executable logic, which is a meaningful distinction. Adds conceptual complexity. |

**Recommendation to carry into the PRD:** the **split model**, contingent on A resolving toward *always reviewed*. Note the dependency explicitly — **A and C cannot be decided independently.** If machine-written parts are ever applied without review, the trusted-author assumption collapses and C must resolve restrictively regardless of what is convenient. **Confirm or overrule.**

---

## Notes for PRD/TRD

Captured during this gate; deliberately excluded from the business sections above.

**For the PRD (Gate 3):**
- Priority ordering should follow opportunity scores, which put **traceability and trust (F5, F6, E1, E3)** at least level with composition mechanics. The composition capability is the means; provenance and reviewability are what people are actually underserved on.
- M11 (time-to-first-value) implies a first-run experience requirement that the PRD must specify concretely.
- "Which recipes depend on this part" (F8/O5) is a distinct capability from composition itself and needs its own requirements.
- P5 is deferred, not deleted. The PRD should record what would have to become true to serve it.

**For the TRD (Gate 5) and Dependency Map (Gate 6):**
- Gate 0 identified strong prior art for path-addressed resolution with namespacing and layered overrides; it should be evaluated rather than reinvented.
- Reproducibility (constraint above, O2) is not a feature — it is a property that must hold from the first design decision. Gate 0 catalogued the specific hazards that break it.
- Cycle detection among parts that reference other parts must report the actual cycle path. Gate 0 documented both the quality bar and a widely-copied anti-pattern of silently continuing.
- Provenance binding an evaluation result to an exact assembled prompt has a directly applicable model from supply-chain attestation practice.
- The host-ecosystem choice is genuinely asymmetric: one integration partner is single-ecosystem with no alternative, the other is deliberately multi-ecosystem. Gate 6 decides; Gate 0 laid out the tradeoff.
- **The project is not yet under version control.** For a product premised on version-control-native artifacts, initializing it is task zero.
- 19 claims in the Gate 0 research are explicitly marked unverified. The single most consequential is whether the closest competitor's conditionals can gate *which part resolves* or only rendered text — if the former, the second structural gap narrows considerably against that competitor. Worth resolving before the TRD commits.

---

## Gate 1 Validation

| Category | Check | Result |
|---|---|---|
| **Press Release** | Customer-facing headline | ✅ |
| | Problem paragraph evidence-based, no solution bias | ✅ grounded in Gate 0 findings |
| | Solution paragraph experience-focused | ✅ |
| | Customer quote emotionally resonant, specific | ✅ |
| | Leadership quote frames strategic value | ✅ includes the deliberate non-goal |
| | No technical jargon | ✅ |
| | Compelling to a non-technical reader | ✅ |
| **JTBD** | Core job identified | ✅ |
| | Functional dimension | ✅ 8 jobs |
| | Emotional dimension | ✅ 4 jobs |
| | Social dimension | ✅ 3 jobs |
| | Competing solutions mapped | ✅ 6, including "do nothing" |
| | Satisfaction gaps identified | ✅ |
| | Opportunity scores calculated | ✅ all 15 |
| **Personas** | JTBD-grounded, not demographic | ✅ 5 personas |
| | Every persona maps to specific jobs | ✅ 5/5 |
| **Outcomes** | Correct format, linked to dimensions | ✅ 10 outcomes |
| | Prioritized by opportunity score | ✅ |
| **Success Criteria** | Every metric has a number | ✅ 11/11 |
| | Every metric has a timeframe | ✅ 11/11 |
| | Every metric links to an outcome | ✅ 11/11 |
| | Baseline documented or marked for establishment | ✅ with baseline establishment named as required work |
| **Scope** | In-scope aligns with press release | ✅ |
| | Out-of-scope with rationale | ✅ 7 items |
| | Assumptions listed | ✅ 5, with failure consequences |
| | Constraints identified | ✅ 5 |
| **Purity** | Zero technology names outside market context | ✅ |
| | Zero feature specifications | ✅ |
| | Zero user stories | ✅ deferred to PRD |
| | Zero implementation details | ✅ moved to Notes |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Vision Clarity** | 20/25 | Press release is compelling and specific. Deducted 5: three foundational questions (A, B, C) remain open, and the vision cannot be fully clear until they are decided. |
| **Job Understanding** | 25/25 | All three dimensions covered in depth, 15 scored jobs, grounded in researched pain points rather than assumed ones. |
| **Outcome Measurability** | 20/25 | All 11 metrics carry numbers and timeframes. Deducted 5: every baseline is unestablished, so targets are hypotheses until design-partner data exists. |
| **Competitive Insight** | 23/25 | 17 tools surveyed with status, ownership, and specific gaps. Deducted 2: the most consequential competitive unknown (whether the closest competitor gates part resolution or only text) is unresolved. |
| **Total** | **88/100** | ≥ 80 → proceed to PRD. |

**Gate Result:** ✅ **PASS** — conditional on human decisions for Open Questions A, B, and C, which Gate 3 (PRD) requires as input.

**Next Step:** Gate 2 — System Big Picture (`souschef:pre-dev-sbp-creation`)
