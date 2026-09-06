# Task Breakdown: promptrecipe

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 7 — Task Breakdown |
| **Inputs** | `trd.md` · `dependency-map.md` · `feature-map.md` · `prd.md` · `docs/PROJECT_RULES.md` |
| **Status** | Draft — **revision 2 (Python-only)**, pending human approval |
| **Confidence Score** | 79/100 |
| **Total tasks** | 27 across 5 phases |
| **Language** | en |

**Stack (Gate 6, revision 2 — Python-only):** Python floor **3.11**, ceiling `<3.15`, matrix 3.11–3.14 · `blake3` **1.0.9** (the *only* runtime dependency) · `pytest` 9.1.1 · `hypothesis` 6.167.1 · `ruff` 0.16.5 · `hatchling` 1.32.0. Everything else is the standard library. Composition engine is **built**, not adopted.

> **Revision 2.** The host language changed from a compiled core with bindings to pure Python (Dependency Map, Decision 2). **The task structure is almost entirely unchanged** — the architecture is technology-agnostic, so only T-001 (foundation) and T-007 (packaging) were rewritten, and one subtask was added to T-005. Every other task, dependency, phase, and risk survives verbatim.

---

## The Four Never-Regress Properties

Each is established by a **named task in the phase where the capability first exists** — not deferred to hardening. These are the load-bearing guarantees; a regression in any of them silently invalidates the product's core claims.

| # | Property | Established by | Phase |
|---|---|---|---|
| **P1** | **Determinism** — identical inputs yield byte-identical output and identical identities, across processes and machines | **T-005** | 1 |
| **P2** | **Order-aware structural identity** — permuting order changes the structural identity | **T-006** | 1 |
| **P3** | **No evaluation of fragment content** — fragment text is never executed | **T-012** | 2 |
| **P4** | **No partial output on failure** — every failure path emits nothing | **T-010** | 2 |

> **Why P2 gets its own property test rather than an example test.** An order-blind identity is a **silent** failure: nothing errors, comparisons simply group two different prompts as one, and every A/B result quietly becomes meaningless. Silent failures cannot be caught by example tests written by someone who already believes the code is correct.

---

# PHASE 0 — Foundation *(blocking; no feature work may start until complete)*

## T-001: Verified, reproducible project foundation

**Deliverable:** A version-controlled Python package that installs reproducibly, with every pinned dependency audited and license-verified.

**Scope**
- *Includes:* version control initialized · `src/` package layout with the Python floor pinned at 3.11 · all Gate 6 dependencies at exact versions · vulnerability audit executed · per-metadata license verification (including the `hypothesis` MPL-2.0 dev-only boundary) · dev lockfile committed · CI running lint + test across the 3.11–3.14 matrix
- *Excludes:* any library logic (T-002+) · Python packaging (T-007) · release automation

**Success Criteria**
- *Functional:* a clean clone builds and tests green with no manual steps
- *Technical:* every dependency pinned to an exact version, no ranges; dev lockfile committed; **exactly one runtime dependency**
- *Operational:* CI green on the target platform matrix
- *Quality:* **vulnerability audit reports zero critical (≥9.0) and zero high (7.0–8.9) findings**, or each is documented with an accepted-risk justification; every runtime license confirmed permissive from its own metadata; the weak-copyleft dev dependency confirmed absent from the built wheel

**User value:** none directly — and that is stated plainly rather than invented. **What it enables:** every subsequent task, plus it closes Gate 6's **CONDITIONAL** pass. TRD ADR-007 delegates review, history, and origin to version control; **that delegation is void until a repository exists**, so this is not ceremony.

**Dependencies:** Blocks *everything*. Requires nothing.
**Effort:** S · 3 pts · 1–3 days
**Risks:** *Audit surfaces a real CVE* — Medium impact / **Low** probability → with one runtime dependency the surface is minimal; the fallback for the identity package is stdlib `hashlib.sha256`, already evaluated at Gate 6. *A weak-copyleft dev dependency leaks into the wheel* — Medium / Low → assert its absence from the built artifact in CI rather than assuming packaging excludes it.
**Testing:** CI smoke build; audit in CI as a recurring job, not a one-off.
**DoD:** installs clean from a fresh checkout · CI green on 3.11–3.14 · audit clean or justified · licenses verified · lockfile committed · README states the Python floor and why it is 3.11.

---

# PHASE 1 — The Call
**Goal:** `getPrompt(recipePath, params)` returns a correct, deterministic, attributable prompt.
**Phase success:** M11 ≥ 75% — a new user reaches a working assembled prompt in under 30 minutes.

## T-002: Fragments load from disk with verifiable identity

**Deliverable:** The custody layer reads a fragment from a path and returns its bytes plus a content-derived identity.

**Scope**
- *Includes:* local filesystem adapter (`exists`/`read`/`list`/`versions`) · BLAKE3 content identity · identity-keyed cache · one fragment = one file · path canonicalization with namespace-root confinement
- *Excludes:* namespace routing (T-004) · versioned custody (T-025) · remote custody (T-026)

**Success Criteria**
- *Functional:* reading the same file twice yields the same identity; changing one byte changes the identity
- *Technical:* **all I/O is confined to this layer** — verified by the layer above having no filesystem access; the cache is keyed by identity, **never by path** (a path-keyed cache returns stale content after a change)
- *Operational:* path traversal outside a namespace root is rejected with an explicit error
- *Quality:* identical content at two different paths yields **identical** identity (ADR-002)

**User value:** a prompt part becomes an addressable, verifiable thing. **Enables:** T-004, T-005.
**Requirements:** FR-006, FR-009 (partial) · ADR-002
**Dependencies:** Requires T-001. Blocks T-004, T-005.
**Effort:** M · 5 pts · 3–5 days
**Risks:** *Cache invalidation subtlety* — High impact / Low probability → identity-keying makes staleness structurally impossible; a path-keyed cache would be a correctness bug, so the test suite asserts the cache key.
**Testing:** unit (identity stability, traversal rejection); property (same bytes ⇒ same identity, regardless of path).
**DoD:** reviewed · tests green · traversal rejection tested · no I/O outside this module (enforced by module boundary).

## T-003: A recipe parses into a structured composition

**Deliverable:** A hand-written parser turning recipe text into a validated structure: load directives, ordering declaration, conditions, expectations.

**Scope**
- *Includes:* grammar (literals · comparisons · boolean operators · membership · variable references · load directive · order declaration · expectations) · recursive-descent parser · position-carrying errors
- *Excludes:* condition *evaluation* (T-009) · expectation *enforcement* (T-010) · assembly (T-005)

**Success Criteria**
- *Functional:* every construct in the grammar parses; every malformed input fails with **line and column**
- *Technical:* **no parser-generator dependency**; the grammar contains no loop, call, or I/O production (E3 by construction)
- *Operational:* an error names what was expected and what was found
- *Quality:* the grammar is closed — it cannot express anything outside the decided semantics

**User value:** a recipe is a structured, checkable artifact rather than free text. **Enables:** T-005, T-009.
**Requirements:** FR-018 · ADR-003 · E3, E7
**Dependencies:** Requires T-001. Blocks T-005, T-009, T-010, T-011.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *Grammar creep* — Medium impact / **Medium probability** → the grammar is the security boundary (ADR-003). Any addition must be justified against E1–E7 in review. This is the most likely place for the design to erode quietly.
**Testing:** unit per construct; property (parse errors always carry a position; no input panics).
**DoD:** reviewed · grammar documented as a closed list · every construct tested · error positions verified.

## T-004: A path resolves to exactly one fragment

**Deliverable:** Resolution turns a path reference plus a selection context into exactly one fragment identity — or fails explicitly.

**Scope**
- *Includes:* prefix-routed namespace dispatch · **namespace isolation** (not first-match-wins) · ambiguity as an error · unresolvable as an error · resolution trace recording every candidate and the winner
- *Excludes:* layered override chains (T-017) · version selection (T-014) · dependency graph (T-021)

**Success Criteria**
- *Functional:* a valid reference resolves to one identity; an ambiguous reference **fails naming every candidate**; an unresolvable reference fails naming the namespaces searched
- *Technical:* resolution performs **no assembly** and reads no fragment content beyond what identity requires (this separation is what later makes T-021 cheap)
- *Operational:* a resolution trace is produced for every resolution, successful or not
- *Quality:* **no configuration can produce silent shadowing** (ADR-004, FR-031)

**User value:** a name means exactly one thing, and a typo fails instead of quietly resolving to the wrong fragment. **Enables:** T-005, T-017, T-021.
**Requirements:** FR-029, FR-031 (partial) · ADR-004
**Dependencies:** Requires T-002. Blocks T-005, T-014, T-017, T-021.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *Namespace isolation feels restrictive and someone adds a fallback* — High impact / Medium probability → first-match-wins is the exact silent-failure class the product exists to remove. Documented in the module as a hard constraint with the reason.
**Testing:** table-driven across routing, ambiguity, and traversal; **every ambiguity case asserts a failure, never a resolution**.
**DoD:** reviewed · ambiguity always errors · trace produced · no assembly performed (asserted).

## T-005: `getPrompt` returns an assembled prompt, deterministically ⭐

**Deliverable:** The end-to-end call — given a recipe path and parameters, return the assembled prompt. **Establishes property P1.**

**Scope**
- *Includes:* linear assembly (load → explicit declared order → concatenate) · value substitution as the **final** pass, never re-parsed · the entry point · determinism hazard mitigations (no ordering from map/set iteration, filesystem enumeration, or locale-sensitive comparison; no wall-clock or environment access) · **the determinism property test**
- *Excludes:* conditions (T-009) · recursion (T-012) · provenance (T-006)

**Success Criteria**
- *Functional:* a recipe referencing two fragments returns their concatenation in the declared order
- *Technical:* **P1 property test passes** — repeated assembly is byte-identical **across processes**, not merely within one; assembly is a pure function over what custody returned
- *Operational:* value substitution runs after all structural decisions, and a substituted value is never re-parsed (ADR-006)
- *Quality:* no map/set iteration, filesystem enumeration order, locale-sensitive comparison, wall-clock, or environment read appears anywhere in the assembly path

**User value:** **the product exists** — a prompt can be assembled from parts. **Enables:** everything downstream.
**Requirements:** FR-023, FR-027 · ADR-001, ADR-006 · TRD §4
**Dependencies:** Requires T-002, T-003, T-004. Blocks T-006 and all later assembly work.
**Effort:** L · 13 pts · 1–2 weeks
**Risks:** *Determinism is not retrofittable* — **High impact / Medium probability** → this is why the property test lands **here** rather than in a hardening phase. A determinism bug found in Phase 3 would invalidate every provenance record written before it.
**Testing:** unit (ordering, substitution); **property (P1 determinism, cross-process)**; the cross-process variant specifically catches hash-seed and iteration-order nondeterminism that a single-process test cannot; **plus a benchmark asserting the TRD §8 budget** *(added in revision 2)*.

> **Added in revision 2 — a real measurement.** The host-language decision was reversed on the reasoning that pure-Python assembly costs well under 1 ms warm against a <10 ms budget, and is invisible beside 500 ms–30 s of model latency. **That reasoning was an estimate, not a measurement.** This task now carries a benchmark subtask that measures the assembly path and fails if the budget is missed — so the decision stops resting on an estimate. If it fails, the four never-regress properties make a compiled-core port verifiable rather than speculative.
**DoD:** reviewed · **P1 green in CI** · no I/O outside custody · substitution-last verified · demo: two fragments assemble.

## T-006: Every assembly emits a provenance record with two-level identity ⭐

**Deliverable:** Each assembly returns, alongside the prompt, a record of what produced it — including both structural and instance identity. **Establishes property P2.**

**Scope**
- *Includes:* attestation record (subject digest · resolved dependencies with identities · condition outcomes · resolved order · address resolutions · value bindings · producer) · **structural identity** (excludes value bindings) · **instance identity** (includes them) · canonical field ordering before digesting · JSON serialization · **the order-aware identity property test**
- *Excludes:* span map (T-019) · reproduction (T-018) · result binding (T-020)

**Success Criteria**
- *Functional:* every assembly returns a record; **no assembly can be produced without one**
- *Technical:* **P2 property test passes** — permuting fragment order changes the structural identity; digests are computed over canonically-ordered fields; timestamps appear as metadata but are **excluded from both digests**
- *Operational:* differing value bindings **preserve** structural identity but **change** instance identity (ADR-005)
- *Quality:* the record is produced **at assembly time**, never reconstructed (SD5) — enforced by the record being a return value, not a query

**User value:** every prompt can be explained. **Enables:** T-018, T-019, T-020, T-023, and the entire trust story.
**Requirements:** FR-001, FR-002 · ADR-002, ADR-005 · SD5, SD6, SD13
**Dependencies:** Requires T-005. Blocks T-018, T-019, T-020, T-023.
**Effort:** L · 13 pts · 1–2 weeks
**Risks:** *Pressure to defer provenance to Phase 3 because "trust features" ship later* — **High impact / High probability** → **it is in Phase 1 by approved structural decision.** The record cannot be reconstructed afterward, and every assembly performed before it exists is permanently unattributable. *Two identities confuse consumers* — Medium → the API must make the distinction unmissable; a consumer who compares instance identities gets silently useless grouping.
**Testing:** property (**P2**; identity separation: value bindings change instance but not structural); round-trip serialization.
**DoD:** reviewed · **P2 green** · both identities documented with a "which one do I use" table · canonical ordering asserted · timestamp exclusion asserted.

## T-007: Packaged, installable, and consumable by an agent framework

**Deliverable:** An installable package whose `get_prompt` drops straight into an agent built on an orchestration framework, requiring **zero fragment awareness** from the caller.

**Scope**
- *Includes:* package metadata and build configuration · a pure-Python wheel that builds once and installs everywhere · the public surface (`get_prompt` returning plain text plus assembly identity) · a worked example consuming the output in an agent-framework-shaped call · install-from-wheel verification in CI
- *Excludes:* evaluation adapters (T-023, T-024) · optimization adapter (T-027)

**Success Criteria**
- *Functional:* a caller installs the package and assembles a prompt in under ten lines
- *Technical:* the caller needs **no** knowledge of fragments, recipes, conditions, or versions (FR-038); `get_prompt` returns a plain string
- *Operational:* a pure-Python wheel installs on the 3.11–3.14 matrix with **no compiler and no platform-specific build**
- *Quality:* the assembly identity is available **alongside** the prompt but never required for basic use

**User value:** the product is usable by the ecosystem it was built for. **Enables:** T-008 and every integration task.
**Requirements:** FR-038
**Dependencies:** Requires T-005 (T-006 recommended so identity ships with it). Blocks T-008, T-023, T-024, T-027.
**Effort:** S · 5 pts · 2–4 days *(reduced from M/8 in revision 1 — no bindings, no compiler, no platform matrix)*
**Risks:** *The public surface leaks internal concepts* — Medium impact / **Medium** probability → FR-038 is the requirement most easily eroded by convenience: exposing a fragment object "just for debugging" starts requiring callers to understand fragments. Review rule: the primary return is a plain string. *Import cost on a cold process* — Low → one runtime dependency keeps import cheap; measure it alongside the T-005 benchmark.
**Testing:** install-from-wheel test in CI across the matrix; a consumption example asserting the returned value is directly usable as prompt text.
**DoD:** reviewed · wheel builds and installs on 3.11–3.14 · assemble-in-ten-lines demo green · **no internal type required in the primary path**.

## T-008: A new user reaches a working prompt in under 30 minutes ⭐

**Deliverable:** A quickstart path — documentation plus examples — that takes someone from nothing to an assembled prompt, verified by a timed test in CI.

**Scope**
- *Includes:* quickstart doc · a runnable two-fragment example · a change-one-fragment-see-it-propagate example · **a timed scripted walkthrough executed in CI**
- *Excludes:* full reference documentation · advanced guides

**Success Criteria**
- *Functional:* following the quickstart produces a working assembled prompt from at least two fragments
- *Technical:* **the CI walkthrough completes in under 30 minutes of scripted wall time** and fails the build if it does not
- *Operational:* requires **no** remote custody, **no** evaluation tooling, **no** optimization tooling
- *Quality:* the second example demonstrates change-once propagation — the core promise, shown rather than described

**User value:** someone can decide whether this is worth adopting **before** investing in it. **Enables:** design-partner validation, which the PRD identified as the highest-value next action.
**Requirements:** FR-028 · metric M11
**Dependencies:** Requires T-007. Blocks nothing technically — **gates Phase 2 in practice.**
**Effort:** S · 3 pts · 1–3 days
**Risks:** *Treated as documentation polish and deprioritized* — **High impact / High probability** → Gate 0 established that copy-paste at zero switching cost is the real competitor, and nobody arrives holding 200 prompts. **A product that only wins at scale never reaches scale.** The CI test exists precisely so this cannot quietly rot.
**Testing:** the timed walkthrough **is** the test.
**DoD:** reviewed · CI walkthrough green and timed · a person who has never seen the project completes it successfully.

---

# PHASE 2 — Worth Adopting
**Goal:** an existing prompt — monolith or model-fork — can be brought in without risk.
**Phase success:** M1 ≤ 5 min · M2 100% propagation · M7 ≥ 60% fewer near-duplicates.

## T-009: Conditions decide which fragments load

**Deliverable:** A bounded, total expression evaluator; conditions in a recipe gate fragment inclusion.
**Scope:** *Includes:* evaluator (comparisons, boolean operators, membership, variable references, literals) · inclusion gating · condition outcomes recorded in provenance. *Excludes:* ordering (T-011) · version selection (T-014) · expectations (T-010).
**Success:** *Functional:* a fragment loads only when its condition holds. *Technical:* **evaluation is total** — a property test asserts termination on every generated input; no function call, loop, or I/O is reachable. *Operational:* every condition outcome appears in the provenance record (SD6). *Quality:* the evaluator cannot read wall-clock or environment.
**Value:** one recipe replaces near-duplicates. **Requirements:** FR-018, E3 · ADR-003.
**Dependencies:** Requires T-003, T-005, T-006. Blocks T-011, T-014.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *"Just one function call" pressure* — **High impact / Medium probability** → totality is the security guarantee; any call reopens the class ADR-003 closed. Enforced by review against E3.
**Testing:** unit per operator; property (**totality** — evaluation always terminates; no input panics).
**DoD:** reviewed · totality property green · outcomes recorded · no ambient state access.

## T-010: A violated expectation fails loudly and emits nothing ⭐

**Deliverable:** Declared expectations evaluated **before** any content is produced. **Establishes property P4.**
**Scope:** *Includes:* expectation evaluation ahead of assembly · failure naming the expectation and the actual input · **the no-partial-output property test across every failure path**. *Excludes:* other error classes' messages (refined per task).
**Success:** *Functional:* a missing or invalid binding fails with a message naming the expectation and what was supplied. *Technical:* **P4 property test passes** — no failure path anywhere emits partial content. *Operational:* expectations run before any fragment is read for content. *Quality:* **no warnings-that-continue exist in the assembly path.**
**Value:** a missing binding fails instead of silently producing a subtly wrong prompt — the exact failure mode the product exists to prevent. **Requirements:** FR-021 · TRD §7.
**Dependencies:** Requires T-009. Blocks nothing; **strengthens everything after it.**
**Effort:** S · 5 pts · 2–4 days
**Risks:** *A convenience "lenient mode" is added later* — High impact / Medium probability → it would reintroduce silent wrongness. Documented as prohibited in PROJECT_RULES.
**Testing:** property (**P4** across all failure paths).
**DoD:** reviewed · **P4 green** · messages name expectation and actual · no lenient path exists.

## T-011: Order is declared, and parameterizable

**Deliverable:** Assembly order is an explicit declaration, controllable by variables and conditions.
**Scope:** *Includes:* order declaration · parameterized ordering · order recorded in provenance and included in structural identity. *Excludes:* comparison tooling (T-020).
**Success:** *Functional:* the same fragments assemble in different orders under different parameters. *Technical:* **no implicit ordering** from declaration sequence, map iteration, or file order. *Operational:* each ordering yields a **distinct structural identity** (P2 already guards this). *Quality:* order appears in the provenance record.
**Value:** ordering variations become testable without maintaining separate recipes. **Requirements:** FR-019 · SD12, SD13.
**Dependencies:** Requires T-009. Blocks T-014.
**Effort:** S · 5 pts · 2–4 days
**Risks:** *Implicit ordering sneaks in via a convenience default* — Medium/Medium → P1 and P2 catch it, which is why they precede this task.
**Testing:** property (permuted order ⇒ different structural identity, already P2; extended to parameterized ordering).
**DoD:** reviewed · no implicit ordering · order in provenance · P2 still green.

## T-012: Fragments include fragments; cycles report the full path ⭐

**Deliverable:** Recursive fragment inclusion with cycle detection. **Establishes property P3.**
**Scope:** *Includes:* DFS expansion with an explicit path stack · **complete cycle path reporting** (`A → B → C → A`) with self-edges distinct · depth ceiling · parameter-scoped inclusion · **the no-evaluation property test**. *Excludes:* span mapping (T-019).
**Success:** *Functional:* a fragment referencing another expands correctly to a declared depth. *Technical:* **P3 property test passes** — a fragment containing text that *looks like* a directive or condition is inserted **verbatim and never interpreted**. *Operational:* a cycle fails reporting the **complete path**, never merely "a cycle exists", and **never silently drops an edge to continue**. *Quality:* a loaded fragment sees only what its load site passes it (parameter-scoped, not context-sharing).
**Value:** fragments compose like functions, and mistakes are diagnosable. **Requirements:** FR-022 · ADR-003, E1.
**Dependencies:** Requires T-005, T-009. Blocks T-016, T-019.
**Effort:** L · 13 pts · 1–2 weeks
**Risks:** *Recursion is where "just render the fragment" is most tempting* — **High impact / High probability.** This is the single most likely place for E1 to be violated, because rendering the included unit is what every conventional engine does. **P3 exists specifically to catch it**, and its test corpus must include fragments whose text mimics directives.
**Testing:** unit (depth, self-edge, multi-node cycle); property (**P3** — directive-shaped fragment text is never interpreted); cycle-path message asserted exactly.
**DoD:** reviewed · **P3 green** · complete cycle path asserted · parameter scoping verified · no render-the-fragment path exists.

## T-013: Change a fragment once; it propagates everywhere

**Deliverable:** A fragment edit takes effect for every recipe resolving it; multiple versions coexist as addressable candidates.
**Scope:** *Includes:* propagation on change · coexisting versions addressable. *Excludes:* selecting between them by condition (T-014) · dependents listing (T-021).
**Success:** *Functional:* editing one fragment changes every recipe using it — **verified by assembling all of them**. *Technical:* multiple versions coexist and are individually addressable. *Operational:* propagation requires no per-recipe action. *Quality:* metric M1 (≤5 min) is measurable on a realistic library.
**Value:** **the core promise** — fix the wrong instruction once, not forty times. **Requirements:** FR-007, FR-008.
**Dependencies:** Requires T-004. Blocks T-014, T-015.
**Effort:** M · 5 pts · 3–5 days
**Risks:** *A path-keyed cache would break this invisibly* — High/Low → T-002 made the cache identity-keyed precisely to prevent it; regression test asserts the cache key.
**Testing:** integration (edit → assemble all dependents → all changed).
**DoD:** reviewed · propagation demonstrated across ≥3 recipes · versions coexist.

## T-014: Conditions select a version or variant

**Deliverable:** A condition can choose among coexisting fragment versions — A/B needs no separate machinery.
**Scope:** *Includes:* version selection through the same condition mechanism · selected version recorded in provenance. *Excludes:* result binding (T-020).
**Success:** *Functional:* different parameters select different versions of the same fragment path. *Technical:* **no separate selection subsystem exists** (SD4). *Operational:* the selected version appears in provenance and in the structural identity. *Quality:* two variants produce **distinct structural identities**.
**Value:** A/B comparison across versions, using machinery that already exists. **Requirements:** FR-020, FR-032 · SD4.
**Dependencies:** Requires T-009, T-011, T-013. Blocks T-015, T-020.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *Temptation to add a dedicated experimentation subsystem* — Medium/Medium → SD4 forbids it; it would duplicate the condition language.
**Testing:** integration (parameter selects version, provenance reflects it, identities differ).
**DoD:** reviewed · no separate subsystem · provenance reflects selection.

## T-015: Model variants share fragments instead of forking ⭐

**Deliverable:** Two templates for two models coexist and share unchanged fragments **by reference**; a fix to a shared fragment corrects both.
**Scope:** *Includes:* separate recipes referencing shared fragment paths (**the primary form**, amendment 8) · in-recipe conditions as the alternative form · both supported, neither privileged in the API. *Excludes:* live model routing (out of scope).
**Success:** *Functional:* `getPrompt(templateA)` and `getPrompt(templateB)` return model-appropriate prompts sharing ~90% of their fragments. *Technical:* shared fragments are **the same fragments**, not copies — verified by identity equality. *Operational:* one fix to a shared fragment corrects **both** variants. *Quality:* creating variant B never modifies or degrades variant A.
**Value:** **the driving use case** — port to a new model without forking forever. **Requirements:** FR-036, FR-037 · amendment 8.
**Dependencies:** Requires T-013, T-014.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *Users copy fragments instead of referencing them, silently recreating the fork* — **High impact / Medium probability** → this is a *documentation and tooling* risk, not a code risk: nothing prevents copying. T-021 (dependents) is the tool that makes sharing visible and rewarding. Worth an explicit quickstart example.
**Testing:** integration (two templates, shared fragments, one fix corrects both).
**DoD:** reviewed · shared-by-identity verified · both expression forms work · quickstart example added.

## T-016: An existing prompt decomposes incrementally, byte-identically

**Deliverable:** Extract fragments from an existing prompt one at a time, verifying byte-identical output at every step.
**Scope:** *Includes:* decomposition verification (assemble candidate, compare byte-for-byte against original) · valid after a **single** extraction with the remainder still inline. *Excludes:* automatic decomposition suggestions.
**Success:** *Functional:* extracting one fragment yields byte-identical assembled output. *Technical:* a partially-decomposed prompt still assembles correctly. *Operational:* any difference is **reported explicitly**, never silently accepted. *Quality:* verified across a corpus of realistic prompts.
**Value:** **adoption without risking a behavior change** — the entry path for the monolith journey. **Requirements:** FR-035.
**Dependencies:** Requires T-012.
**Effort:** M · 8 pts · 3–5 days
**Risks:** *Whitespace and trailing-newline handling makes byte-identity harder than it reads* — **Medium impact / High probability.** This is the most underestimated task in the plan: byte-identity is unforgiving, and prompt text is full of significant whitespace.
**Testing:** golden-file property over a prompt corpus — every incremental extraction preserves output exactly.
**DoD:** reviewed · corpus property green · differences reported explicitly · whitespace semantics documented.

## T-017: Precedence is inspectable; ambiguity is explicit

**Deliverable:** Layered override chains with a deterministic, explainable winner.
**Scope:** *Includes:* ordered layering · full-chain evaluation (not short-circuited) so a trace can be produced · "why did this resolve here" explanation · ambiguity remains an error.
**Success:** *Functional:* a layered configuration resolves deterministically. *Technical:* the resolution trace names every candidate, its source, and the winner. *Operational:* ambiguity **errors** even under layering. *Quality:* metric M9 (≤1 collision per 100 fragments) is measurable.
**Value:** you can explain why a fragment won, instead of guessing. **Requirements:** FR-030, FR-031 · ADR-004.
**Dependencies:** Requires T-004.
**Effort:** M · 5 pts · 3–5 days
**Risks:** *Precedence becomes confusing at scale* — Medium/Medium → Gate 0 found mature systems need dedicated documentation for precedence rules; inspectability is the mitigation, which is why the trace is a requirement rather than a debug aid.
**Testing:** table-driven layering; every ambiguity asserts failure.
**DoD:** reviewed · trace explains every resolution · ambiguity still errors.

---

# PHASE 3 — Trustworthy
**Goal:** every result attributable, every assembly reproducible, blast radius known in advance.
**Phase success:** M3 ≥ 99% · M4 ≤ 2 min · M6 ≥ 95% · M12 100%.

## T-018: An assembly reproduces byte-identically from its record

**Deliverable:** Given a provenance record, reproduce the exact original prompt.
**Success:** *Functional:* reproduction is byte-identical. *Technical:* round-trip property (assemble → record → reproduce → identical) green. *Operational:* if a referenced version is unavailable, reproduction **fails explicitly and never substitutes** a different version. *Quality:* works across processes and machines.
**Value:** re-run last month's result and get last month's prompt. **Requirements:** FR-003 · metric M3.
**Dependencies:** Requires T-006, T-014. **Effort:** M · 8 pts · 3–5 days
**Risks:** *Silent substitution when a version is missing* — **High impact / Low probability** → would make every reproduction claim untrustworthy; explicit failure is asserted by test.
**Testing:** round-trip property; missing-version failure asserted.
**DoD:** reviewed · round-trip property green · missing-version fails explicitly.

## T-019: Output maps back to the fragment that produced it

**Deliverable:** A span map from portions of the assembled prompt to their source fragments, including through recursive inclusion.
**Success:** *Functional:* any character offset resolves to a fragment identity and its position in the load tree. *Technical:* the span map is produced **during** assembly, not reconstructed. *Operational:* metric M4 (≤2 min to identify a source fragment) is achievable. *Quality:* correct through nested inclusion.
**Value:** bad output localizes to a part instead of to "the prompt". **Requirements:** FR-004 · SD5.
**Dependencies:** Requires T-006, T-012. **Effort:** M · 8 pts · 3–5 days
**Risks:** *Offsets drift after value substitution* — **Medium impact / High probability** → substitution changes lengths and runs last (ADR-006); the span map must be adjusted in that final pass. Easy to get subtly wrong.
**Testing:** property (every offset maps to exactly one fragment, before and after substitution).
**DoD:** reviewed · nested inclusion correct · post-substitution offsets correct.

## T-020: An external result binds to exactly one assembly

**Deliverable:** A result produced elsewhere can be attached to one assembly identity and never confused with another.
**Success:** *Functional:* a result references exactly one structural identity. *Technical:* two variants differing only in order are never conflated (P2). *Operational:* **metric M12 = 100%** unambiguous attribution. *Quality:* results grouped by **structural** identity, not instance identity — otherwise every run groups alone.
**Value:** an A/B result means something. **Requirements:** FR-005 · ADR-005 · metric M12.
**Dependencies:** Requires T-006, T-014. **Effort:** S · 5 pts · 2–4 days
**Risks:** *Consumers use instance identity for comparison* — **High impact / High probability.** This is the most likely misuse in the whole design: it produces no error, just useless grouping. The API must make the correct choice obvious, and documentation must lead with it.
**Testing:** integration (two variants, results bind distinctly, grouping by structural identity works).
**DoD:** reviewed · M12 demonstrable · "which identity do I use" documented prominently.

## T-021: List every recipe depending on a fragment, without assembling

**Deliverable:** Given a fragment, list all recipes that can resolve to it — transitively, with no assembly.
**Success:** *Functional:* transitive dependents listed correctly. *Technical:* **no assembly performed** — asserted by test. *Operational:* under 100 ms on a 1000-fragment library. *Quality:* metric M6 (≥95% dependents identified before shipping) achievable.
**Value:** know the blast radius before changing anything. **Requirements:** FR-011 · TRD §8.
**Dependencies:** Requires T-004, T-012. **Effort:** M · 8 pts · 3–5 days
**Risks:** *Assembly creeps in "just to be accurate"* — Medium/Medium → the cheap question must stay cheap; that is why FR-012 is a separate task.
**Testing:** integration (transitive correctness); assertion that no assembly ran; performance test at 1000 fragments.
**DoD:** reviewed · no assembly asserted · performance target met.

## T-022: Preview a change's effect on every dependent

**Deliverable:** For a proposed fragment change, show how each dependent recipe's output would differ.
**Success:** *Functional:* before/after diff per dependent. *Technical:* uses assembly (deliberately, unlike T-021). *Operational:* completes in reasonable time on a realistic library. *Quality:* diffs are readable.
**Value:** judge risk before accepting a change. **Requirements:** FR-012 · metric M6.
**Dependencies:** Requires T-021. **Effort:** M · 8 pts · 3–5 days
**Risks:** *Slow on large libraries* — Low/Medium → scope to affected dependents only.
**Testing:** integration (change → preview → diffs correct).
**DoD:** reviewed · diffs correct · scoped to affected recipes.

## T-023: A recipe is evaluable by external evaluation tooling

**Deliverable:** A Python adapter exposing an assembled recipe as an evaluable unit with its identity attached.
**Success:** *Functional:* the evaluation tool consumes assembled prompts through the adapter. *Technical:* the adapter is an **optional extra**, never imported by the core. *Operational:* results carry the assembly identity. *Quality:* the core has zero knowledge of the evaluation tool.
**Value:** results come back attributable. **Requirements:** FR-024 · SD10.
**Dependencies:** Requires T-007, T-006. **Effort:** M · 5 pts · 3–5 days
**Risks:** *The integration target changed ownership 5 months ago and may change again* — **Medium impact / Medium probability** → the adapter is thin and optional; the core must survive its disappearance. Re-verify the integration surface before implementing. *Note:* Python-only removes the subprocess boundary revision 1 would have imposed on the optimization side (T-027), making that adapter simpler than originally scoped.
**Testing:** contract tests against recorded fixtures — so the adapter is testable without a live external tool.
**DoD:** reviewed · adapter thin and optional · core unaware · contract tests green.

## T-024: A single fragment is evaluable with zero model execution

**Deliverable:** An adapter exposing one fragment as an independently evaluable unit, plus a pass-through sink so text assertions cost no model call.
**Success:** *Functional:* a fragment is assertable on its own. *Technical:* **zero model execution** — no outbound model capability exists anywhere in the library (SD10, FR-027). *Operational:* fragment-level tests run at no model cost. *Quality:* fragment and recipe are **distinct** evaluation targets (SD14).
**Value:** catch a bad primitive without assembling around it or paying for a call. **Requirements:** FR-025 · SD14.
**Dependencies:** Requires T-023. **Effort:** S · 5 pts · 2–4 days
**Risks:** *Someone adds a model call for convenience* — High/Low → FR-027 is enforced structurally: no outbound execution port exists.
**Testing:** integration with the pass-through sink; assertion that no network call occurs.
**DoD:** reviewed · zero model execution asserted · both targets distinct.

---

# PHASE 4 — Scale & Improve
**Goal:** shared libraries across teams; improvement that is adoptable rather than all-or-nothing.
**Phase success:** M5 ≥ 80% · M9 ≤ 1 per 100.

## T-025: Fragments live under version control as first-class custody — ❌ DROPPED

> **Stakeholder decision (2026-09-05): not built, and not deferred.** Fragments live in the repository of the project that consumes them, so that project's git already versions them. `FsCustody` reads its working tree; because a fragment is one file (ADR-007), `git log`, `git blame`, and pull-request review already work on it per fragment. A versioned custody adapter inside this library would reimplement what the host repository does better — the very duplication amendment 7 and ADR-007 delegated away. Building it would have been the delegation quietly walking itself back.
>
> **Consequences recorded:** C5's coverage is now delegation with no adapter at all, not delegation via an adapter. `FsCustody.versions()` returning exactly one identity is the final answer rather than a placeholder. **T-026 no longer requires this task, and its blocker gets sharper, not looser** — local custody is now the only place review comes from, so leaving it is the whole cost.

**Original deliverable (for the record):** A versioned custody adapter reading the working tree, with history queries delegated rather than reimplemented.
**Success:** *Functional:* fragments resolve from a version-controlled tree. *Technical:* **no version-control library dependency** — working-tree reads use the filesystem adapter; history shells out. *Operational:* one fragment = one separately diffable file (ADR-007). *Quality:* per-fragment review works naturally in a normal review workflow.
**Value:** review, history, and origin come **free** — amendment 7's dividend collected. **Requirements:** FR-010 · ADR-007.
**Dependencies:** Requires T-002. **Effort:** S · 5 pts · 2–4 days
**Risks:** *Fragment granularity too coarse and per-fragment review breaks* — **High impact / Medium probability** → this is the hard constraint ADR-007 depends on; bundling fragments would void the entire delegation.
**Testing:** integration (resolve from a versioned tree; diff shows one fragment).
**DoD:** reviewed · no version-control library added · per-fragment diff demonstrated.

## T-026: Fragments can live remotely with identity intact

**Deliverable:** A remote custody adapter where a fragment's identity is unchanged by where it lives.
**Success:** *Functional:* fragments resolve from remote custody. *Technical:* identity is **verified on retrieval**; a mismatch against a pinned identity is an error, never tolerated. *Operational:* provenance recorded before a custody move still validates after it. *Quality:* cache-first, identity-keyed.
**Value:** libraries shared across teams. **Requirements:** FR-009, FR-010 · SD1, SD2.
**Dependencies:** Requires T-002. *(Was T-025, which is dropped — see above.)*
**Effort:** L · 13 pts · 1–2 weeks
**Risks:** ⚠️ **Remote custody without version control inherits NO review** — **High impact / High probability**, and **raised by dropping T-025**: with no versioned adapter, the consuming project's repository is the *only* source of review, so moving fragments out of it forfeits review entirely. The TRD stated two options (declare repository-resident custody a prerequisite, or build minimal review) and **chose neither**. **This task must not ship until that product decision is made** — it is a blocking decision, not a technical one. *Identity break at the boundary* — High/Low → verification on retrieval.
**Testing:** integration (identity survives a custody move; mismatch errors; pre-move provenance still validates).
**DoD:** reviewed · **the review-gap decision is made and documented** · identity verified on retrieval · mismatch errors.

## T-027: Machine-proposed improvements arrive as reviewable per-fragment changes

**Deliverable:** Export one fragment's text to seed an optimization run; import the returned text as a proposed change to that fragment path.
**Success:** *Functional:* a fragment seeds a run; returned text becomes a proposal against that fragment. *Technical:* **per-fragment only** — the API offers no whole-recipe seeding that implies attribution. *Operational:* the proposal enters the normal review workflow (delegated). *Quality:* metric M5 (≥80% proposals decided within a working day) is measurable.
**Value:** improve one part at a time, reviewably — instead of an all-or-nothing rewrite. **Requirements:** FR-026 · SD11.
**Dependencies:** Requires T-007, T-025. **Effort:** M · 8 pts · 3–5 days
**Risks:** *Whole-recipe seeding is requested and per-fragment attribution is implied* — **High impact / Medium probability** → Gate 0 verified no sub-prompt attribution exists. The API must **not offer** the shape that implies it; documentation must state the limitation plainly rather than let users infer capability.
**Testing:** integration (seed → return → proposal against the correct fragment path).
**DoD:** reviewed · per-fragment only · limitation documented · proposal enters review workflow.

---

## Delivery Sequence & Critical Path

```
T-001 ──> T-002 ──> T-004 ──┐
           │                ├──> T-005* ──> T-006* ──> T-007 ──> T-008*
           └──> T-003 ──────┘        (P1)      (P2)
                                        │
     PHASE 2 ────────────────────────── ┴────────────────────
     T-009 ──> T-010* ──> T-011 ──> T-014 ──> T-015
        │       (P4)                   ^
        └──> T-012* ──> T-016          │
              (P3)                  T-013
     T-017 (parallel, needs T-004)

     PHASE 3 ─────────────────────────────────────────────
     T-018 · T-019 · T-020   |   T-021 ──> T-022   |   T-023 ──> T-024

     PHASE 4 ─────────────────────────────────────────────
     T-025(❌ dropped)      T-026(⚠ blocked on a product decision)   ·   T-027
```

**Critical path:** T-001 → T-002 → T-004 → **T-005** → **T-006** → T-007 → T-008.
Seven tasks stand between nothing and a validated first-value demo. **T-005 and T-006 are the two Large tasks on that path** and carry properties P1 and P2 — they are where the plan is most likely to slip, and where slipping is most expensive.

**Parallelizable:** T-003 alongside T-002/T-004 · T-017 alongside Phase 2 · Phase 3's three groups are mutually independent.

| Phase | Tasks | Points | Rough duration |
|---|---|---|---|
| 0 — Foundation | 1 | 3 | 1–3 days |
| 1 — The Call | 7 | 55 | 4–6 weeks |
| 2 — Worth Adopting | 9 | 68 | 5–7 weeks |
| 3 — Trustworthy | 7 | 47 | 4–5 weeks |
| 4 — Scale & Improve | 3 | 26 | 2–3 weeks |
| **Total** | **27** | **199** | **~15–23 weeks** (single developer; parallelizable with more) |

> Durations assume one developer and are **estimates without historical velocity for this team or codebase**. Treat them as relative sizing, not commitments.

---

## Gate 7 Validation

| Category | Check | Result |
|---|---|---|
| **Task Completeness** | All TRD components have tasks | ✅ C1→T-002 · C2→T-004,T-017 · C3→T-005,T-009..T-012 · C4→T-006,T-018..T-020 · C5→delegated outright, no adapter (T-025 dropped) · C6→T-007,T-023,T-024,T-027 · C7→T-021,T-022,T-016 |
| | All PRD features have tasks | ✅ 31 built requirements covered; 6 delegated; 1 deferred |
| | Each task appropriately sized | ✅ **no task exceeds 2 weeks**; 4 Large (13 pts), rest S/M |
| **Delivery Value** | Every task delivers working software | ✅ — T-001 is the sole exception and **says so explicitly** rather than inventing user value |
| | Sequence optimizes value | ✅ first-value demo reachable at T-008, seven tasks in |
| **Technical Clarity** | Success criteria measurable | ✅ functional/technical/operational/quality per task |
| | Dependencies mapped | ✅ plus critical path and parallelization |
| | Testing approach defined | ✅ per task; 4 property tests named and placed |
| **Risk Management** | Risks identified per task | ✅ with impact × probability |
| | High-risk tasks scheduled early | ✅ P1 (T-005) and P2 (T-006) in Phase 1 |
| | Fallback plans | ✅ where one exists (e.g. identity package → stdlib SHA-256) |
| **Phasing constraint** | **Provenance in Phase 1, not deferred** | ✅ T-006 in Phase 1 per SD5 |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Task Decomposition** | 26/30 | All 27 tasks within 2 weeks; the four never-regress properties are placed at the task where the capability first exists. Deducted 4: T-005, T-006, T-012, T-026 are all Large and each could reveal a sub-task worth splitting once real code exists |
| **Value Clarity** | 22/25 | Every task states its deliverable and what it enables; a demo exists at T-008. Deducted 3: T-001 genuinely delivers no user value — stated honestly rather than dressed up |
| **Dependency Mapping** | 23/25 | Full graph, critical path, parallelization. Deducted 2: T-026 carries a **product** blocker (the review gap) rather than a technical one, which no dependency graph can express |
| **Estimation Quality** | 8/20 | **No historical velocity exists** — no team, no codebase, no comparable prior work. Sizes are relative and defensible; durations are educated guesses. Inflating this score would be dishonest |
| **Total** | **79/100** | Band 50–79 → **present options.** The gap is almost entirely estimation confidence, which no amount of planning can manufacture before the first tasks are actually done |

**Gate Result:** ✅ **PASS**

**Carried forward:**
- ❌ **T-025 is dropped** (2026-09-05): the consuming project's own git versions the fragments; an adapter here would reimplement it.
- ⚠️ **T-026 is blocked on a product decision**, not on engineering: remote custody without version control inherits no review, and the TRD deliberately chose neither remedy. Dropping T-025 sharpens this — repository-resident custody is now the only source of review. Must be decided before Phase 4.
- ⚠️ Live traffic splitting remains out of scope by assumption, awaiting confirmation.
- 🔴 Question A is now a version-control branch-protection setting rather than a product feature.
- **Estimates should be recalibrated after Phase 1**, when real velocity exists.

**Next Step:** Gate 8 — Subtask Creation (`souschef:pre-dev-subtask-creation`)
