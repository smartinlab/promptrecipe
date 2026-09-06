# Technical Requirements Document: promptrecipe

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Gate** | 5 — Technical Requirements Document |
| **Inputs** | `brd.md` · `sbp.md` · `prd.md` · `feature-map.md` · `research.md` (all approved) |
| **Status** | Draft — pending human approval |
| **Confidence Score** | 82/100 |
| **Language** | en |

> **Technology-agnostic by mandate.** This document specifies architectural *patterns*, not products. No language, framework, engine, or storage product is named. Concrete versioned selection is Gate 6.

---

## Amendment 9 (stakeholder question, 2026-08-31) — three variable kinds, two-level identity

The stakeholder asked whether values should feed conditions, or be replace-style substitutions, and which is better. **They are not alternatives — they are three distinct roles**, and conflating them breaks comparison.

### The three variable kinds

| Kind | Role | Resolves to | Affects | Evaluated? |
|---|---|---|---|---|
| **Address variable** | Names *which fragment* loads | A fragment path | **Structure** | Yes — as path resolution |
| **Control variable** | Feeds a condition governing inclusion, order, or version | A comparable value | **Structure** | Yes — by the bounded expression evaluator |
| **Value variable** | Substitutes literal text into content | A literal string | **Content** | **No** — pure textual substitution, never interpreted |

They must be **syntactically distinguishable**. A reader must be able to tell, without running anything, whether a variable changes the *shape* of the prompt or only its *wording*. This is not cosmetic: the three have different security properties, different provenance obligations, and different effects on identity.

### The consequence that is easy to miss: identity must have two levels

If value variables entered assembly identity, **every call would produce a unique identity** — two A/B runs differing only in an end user's name would count as different prompts, nothing would be comparable, and FR-002/M12 would be unachievable in practice.

| Level | Composed of | Answers | Used for |
|---|---|---|---|
| **Structural identity** | fragment versions + resolved order + condition outcomes + address-variable resolutions | *"Which prompt shape is this?"* | **Comparison, A/B, experiments** (FR-005, FR-002, M12) |
| **Instance identity** | structural identity + value-variable bindings | *"Which exact rendered text was this?"* | **Byte-identical reproduction** (FR-003), debugging |

**Two assemblies share a structural identity when they are the same prompt design; they share an instance identity only when they are the same rendered text.** Comparison groups by the former; reproduction requires the latter. This resolves SD13 (order-aware identity) and FR-003 (byte-identical reproduction) without letting them conflict.

### Security consequence, and the one thing it does *not* protect against

Value variables are **substituted, never interpreted** — so amendment 8's guarantee survives intact: no fragment content is ever executed, and optimizer-written text remains inert.

However — stated plainly rather than buried — **value substitution is the prompt-injection surface.** A value drawn from untrusted input becomes part of a prompt. This is not a code-execution risk and the architecture cannot eliminate it, because injecting caller-supplied text is the feature. The architecture's obligations are to (a) keep value substitution incapable of altering structure, (b) record every value binding in provenance so an injection is *forensically visible*, and (c) never let a substituted value be re-parsed as a directive. See Security Architecture.

---

## 1. Architecture Overview

### 1.1 Architectural style

**An embedded, layered library with a single primary entry point and pluggable custody adapters.**

| Property | Choice | Rationale |
|---|---|---|
| **Deployment shape** | In-process library, no service, no daemon | Amendment 7: the deliverable is a library. A service would add operational cost with no job it serves |
| **Internal structure** | Layered with strictly one-directional dependencies | Enables SD3 (resolution separate from assembly) and lets Impact Analysis read the graph without invoking assembly (FR-011) |
| **Extension mechanism** | Adapter ports at exactly two boundaries: custody, and external capabilities | Keeps the core independent of both custody choice (SD2) and integration targets, whose ownership changed within 8 months |
| **Concurrency model** | Pure functions over immutable inputs in the assembly path | Determinism (SD7) is far cheaper to guarantee when nothing is mutated mid-assembly |
| **State** | None retained between calls except an optional resolution cache keyed by content identity | A library that accumulates hidden state cannot be deterministic |

### 1.2 The layers

```
      caller (agent framework / evaluation harness / tooling)
                            │
                            v
  ┌──────────────────────────────────────────────────────┐
  │  L4  ENTRY          getPrompt(params)                │  thin; no logic
  └──────────────────────────────────────────────────────┘
                            │
  ┌──────────────────────────────────────────────────────┐
  │  L3  ASSEMBLY       Composition + Provenance         │  pure, deterministic
  └──────────────────────────────────────────────────────┘
                            │
  ┌──────────────────────────────────────────────────────┐
  │  L2  RESOLUTION     path + context -> exact version  │  pure, no assembly
  └──────────────────────────────────────────────────────┘
                            │
  ┌──────────────────────────────────────────────────────┐
  │  L1  CUSTODY        fragment retrieval + identity    │  the only I/O
  └──────────────────────────────────────────────────────┘
                            │
                  custody adapter port
                            │
       local filesystem  │  version-controlled  │  remote object store
```

**All I/O is confined to L1.** L2 and L3 are pure functions over what L1 returned. This single constraint delivers determinism (SD7), testability without fixtures, and the ability to answer dependency questions without touching storage twice.

---

## 2. Component Design

### C1 — Fragment Library *(L1 · SBP module 1)*

**Responsibility:** retrieve fragment and recipe content from custody, and establish verifiable identity for what it retrieved.

| Concern | Design |
|---|---|
| **Identity (SD1, FR-009)** | **Content-derived**: a fragment version's identity is a cryptographic digest of its exact bytes. Independent of path, custody, and metadata. Two fragments with identical bytes have identical identity everywhere |
| **Naming vs identity** | Strictly separated. A **path** is a mutable human-readable address; an **identity** is an immutable content digest. A path resolves *to* an identity. Prior art: the digest/tag split in content-addressed distribution |
| **Custody port** | A narrow interface: `exists(path)`, `read(path, selector) -> (bytes, identity)`, `list(prefix)`, `versions(path)`. Deliberately minimal so adapters stay simple |
| **Diffability (amendment 7)** | **One fragment per separately addressable, separately diffable unit.** Bundling fragments would make per-fragment review impossible and break the delegation. This is a hard architectural constraint, not a storage preference |
| **Caching** | Keyed by content identity, never by path. A path-keyed cache would return stale content after a change; an identity-keyed cache is correct by construction |

### C2 — Resolution *(L2 · SBP module 2)*

**Responsibility:** turn a path reference plus a selection context into exactly one fragment identity. **Performs no assembly** (FR-011).

| Concern | Design |
|---|---|
| **Namespace routing (FR-029)** | **Prefix-routed dispatch**: a path's leading segment selects a namespace, which maps to a custody source. Prior art establishes this as the mature pattern for path-addressed content with namespacing |
| **Collision strategy (FR-031)** | **Namespace isolation, not search-order.** Gate 0 found two traditions: ordered search where first-match wins (collisions silently shadowed) and namespace isolation (collisions structurally impossible). FR-031 forbids silent shadowing, so isolation is mandatory. Where layering *is* configured, ambiguity is an **error**, never a silent pick |
| **Layering & precedence (FR-030)** | An explicitly ordered chain, evaluated fully rather than short-circuited, so that a **resolution trace** can be produced: every candidate considered, its source, and why the winner won. Gate 0 flagged that mature precedence systems become confusing at scale precisely because they are not inspectable |
| **Version selection** | The selection context may pin an exact identity, name a version, or leave it to the path's default. Pinning by identity always wins |
| **Failure mode** | Unresolvable or ambiguous → **hard failure** naming the reference, the candidates, and the chain. Never a fallback, never a silent shadow |
| **Dependency graph (FR-011)** | Resolution alone can construct the full reference graph by resolving references transitively **without reading a single fragment for assembly** — this is exactly why L2 is separate from L3 |

### C3 — Composition *(L3 · SBP module 3)*

**Responsibility:** evaluate conditions, determine inclusion and order, inline resolved fragments, substitute value variables, produce the assembled prompt.

| Concern | Design |
|---|---|
| **Recipe form** | A composition of **load-by-path directives**, an ordering declaration, and optional conditions and expectations. Structure-carrying, not free-form prose |
| **Expression evaluator (amendment 8)** | A **bounded, total expression language**: comparisons, boolean operators, membership, variable reference, literals. **No function calls, no loops, no I/O, no unbounded recursion — evaluation is guaranteed to terminate.** This is the *entire* evaluated surface of the system |
| **Fragment content** | **Never evaluated.** A fragment is text plus pure path references. Value-variable substitution is literal insertion, and a substituted value is **never re-parsed** — the substitution pass runs once, after all structural decisions are final |
| **Ordering (SD12, FR-019)** | Order is an explicit declaration over the selected loads, parameterizable by control variables. There is no implicit ordering derived from declaration sequence, map iteration, or file order — implicit ordering is a determinism hazard |
| **Recursive inclusion (FR-022)** | Depth-first expansion over the reference graph produced by C2, with an explicit depth ceiling |
| **Cycle detection (FR-022)** | Graph traversal maintaining an explicit path stack. On revisiting a node **on the current stack**, fail reporting the **complete cycle path** (`A → B → C → A`), with self-edges reported distinctly. Gate 0 documented both the quality bar and the anti-pattern of silently dropping a cycle and continuing — the latter is forbidden |
| **Expectations / asserts (FR-021)** | Evaluated **before** any content is produced. A violated expectation fails naming the expectation and the actual input, and emits **no partial output** |
| **Scoping** | **Parameter-scoped, not context-sharing.** A loaded fragment sees only what the load site passes it. Gate 0 found a mature engine deprecated scope-sharing inclusion for maintainability reasons that apply directly here |
| **Determinism (SD7)** | See §4 |

### C4 — Provenance *(L3 · SBP module 4)*

**Responsibility:** emit, at assembly time, the record that makes the assembly explainable, attributable, and reproducible. **Never reconstructed afterward** (SD5).

**Two representations, deliberately distinct:**

| Representation | Contents | Serves | Weight |
|---|---|---|---|
| **Span map** | Ordered spans over the output, each carrying the source fragment identity and its position in the load tree | FR-004 (which fragment produced this text), human debugging | Light; produced inline during assembly |
| **Assembly attestation** | Subject (output digest) · resolved dependencies (each fragment path + identity) · condition outcomes · resolved order · address-variable resolutions · value-variable bindings · producer identity and version | FR-001, FR-002, FR-003, FR-005, reproduction, comparison | Heavier; the durable artifact |

**Attestation structure follows established supply-chain provenance shape** — a subject with its digest, resolved dependencies each with their own digest, and the identity of the producer — because that model already solves "bind an output to its exact inputs".

**Both identities (amendment 9) are computed here:**
- **Structural identity** = digest over (ordered fragment identities · condition outcomes · resolved order · address resolutions). Excludes value bindings.
- **Instance identity** = digest over (structural identity · value bindings).

The span map is produced *during* assembly because reconstructing it afterward would require re-running assembly — which SD5 forbids and which would be unsound if any input had changed.

### C5 — Change Intake *(thin — SBP module 5, largely delegated per amendment 7)*

**Responsibility:** deliberately minimal. Review, approval, origin, and history are provided by version control.

| The library provides | The library does NOT provide |
|---|---|
| Fragments and recipes as plain reviewable text | A review workflow |
| One fragment per separately diffable unit | An approval mechanism |
| A validation entry point that checks a proposed change is well-formed and reports affected recipes (FR-012) | Audit history storage |
| Machine-proposed text routed to a specific fragment path (FR-026) | Identity or permission management |

> **⚠️ Accepted limitation (assumption A6) — ✅ RESOLVED 2026-09-05.** The gap as recorded: under remote custody *without* version control, the delegated review story does not hold and this architecture provides no substitute. Two options were stated and neither was chosen: (i) declare version-controlled custody a prerequisite, documenting remote custody as distribution-only; or (ii) build a minimal review capability later.
>
> **The stakeholder resolved it by removing the case rather than choosing a remedy.** Fragments live in the consuming project's repository, and there is no remote custody (T-026 deferred) and no versioned custody adapter (T-025 dropped — the host repository already versions them). With repository-resident custody as the *only* custody, A6 holds unconditionally and the delegation in ADR-007 is complete rather than conditional. This is stronger than option (i): remote custody is not documented as distribution-only, it does not exist.
>
> **What would reopen it:** any custody backend that is not the consuming project's repository. The review story is inherited from that repository and from nothing else, so leaving it forfeits review entirely — not one option out of two.

### C6 — Integration Surface *(SBP module 6)*

**Responsibility:** thin adapters. Deliberately thin because both external targets changed ownership within eight months (Gate 0) — the core must survive either disappearing.

| Adapter | Pattern |
|---|---|
| **Agent framework consumption (FR-038)** | The entry point returns assembled content in a plain, directly usable form. **Zero fragment awareness required of the caller** — no types, no wrappers, no registration. The assembly identity is returned *alongside*, never required for basic use |
| **Recipe evaluation (FR-024)** | A resolver-callable adapter: given a selection context, return assembled content plus identity. Matches the callable-prompt-source pattern that evaluation harnesses accept |
| **Fragment evaluation (FR-025)** | The same adapter addressed at a single fragment. Combined with a **pass-through sink** (which returns the prompt instead of calling a model), fragment text is assertable **with zero model execution** — Gate 0 verified this shape is achievable |
| **Optimization seeding (FR-026)** | Export a single fragment's text; import returned text as a proposed change *to that fragment path*. **Per-fragment only** — SD11: whole-recipe results carry no sub-fragment attribution, and the architecture must not imply otherwise |
| **Boundary (SD10, FR-027)** | The library has **no capability to call a model and no capability to score**. This is enforced by the absence of any outbound execution port, not by policy |

### C7 — Impact Analysis *(cross-module capability)*

**Responsibility:** answer "what depends on this, and what changes if it changes" **without assembling** (FR-011).

| Operation | Design |
|---|---|
| **Dependents (FR-011)** | Build the reference graph via C2 alone, invert it, return transitive dependents. **No assembly, no content reading beyond references** |
| **Change preview (FR-012)** | Deliberately *does* assemble — for each affected recipe, assemble before and after and diff. Separated from FR-011 so the cheap question stays cheap |
| **Decomposition verification (FR-035)** | Assemble the candidate decomposition and compare byte-for-byte against the original. Incremental: valid after extracting a single fragment, with the remainder still inline |

---

## 3. The `getPrompt` Call Path

```
 getPrompt(recipePath, params)
      │
  [1] LOAD RECIPE ......................... C1  (I/O)
      │
  [2] EVALUATE EXPECTATIONS ............... C3  fail early, no partial output
      │
  [3] EVALUATE CONDITIONS ................. C3  bounded evaluator; record every outcome
      │      -> which loads happen · which versions · what order
      │
  [4] RESOLVE PATHS ....................... C2  each reference -> exactly one identity
      │      -> resolution trace retained
      │
  [5] FETCH FRAGMENTS ..................... C1  (I/O) identity-keyed cache
      │
  [6] EXPAND RECURSIVELY .................. C3  cycle detection with full path
      │
  [7] ORDER ............................... C3  explicit declared order only
      │
  [8] SUBSTITUTE VALUE VARIABLES .......... C3  literal, once, never re-parsed
      │
  [9] EMIT ................................ C4  assembled text
      │                                          + span map
      │                                          + attestation
      │                                          + structural identity
      │                                          + instance identity
      v
 (assembled prompt, assembly identity)
```

**Steps 2–4 and 6–8 are pure.** Only 1 and 5 perform I/O. **Step 8 is deliberately last** — value substitution happens after every structural decision is final, so a substituted value can never influence which fragments load, in what order, or at what version. That ordering is the architectural expression of amendment 9's security property.

---

## 4. Determinism Architecture *(SD7 / FR-023 — not retrofittable)*

Gate 0 catalogued the hazards. Each is designed against explicitly.

| Hazard | Mitigation |
|---|---|
| **Unstable map/set iteration order** | No output ordering ever derives from map or set iteration. Order comes only from an explicit declared sequence. Where a collection must be traversed for output, it is an ordered sequence by construction |
| **Wall-clock leakage** | The expression evaluator has no time access. Timestamps may appear in the attestation as metadata but are **excluded from both identity computations** |
| **Environment leakage** | The evaluator cannot read environment or process state. Every input arrives through the explicit parameter set |
| **Locale-dependent operations** | Comparison and any ordering use locale-independent semantics. No locale-sensitive casing or collation in the assembly path |
| **Filesystem enumeration order** | Never used for output ordering. Enumeration is used only for discovery, and always sorted deterministically before use |
| **Hidden state across calls** | The assembly path retains no mutable state; the only cache is identity-keyed and semantically transparent |
| **Recursion order** | Depth-first with an explicit, declared traversal order |

**Verification obligation:** a determinism property test is a **Phase 1 deliverable**, not a later hardening task — repeated assembly of identical inputs must yield byte-identical output and identical identities, across processes and across machines.

---

## 5. Data Architecture *(conceptual — no storage technology implied)*

### 5.1 Entities

| Entity | Key attributes | Owner | Mutability |
|---|---|---|---|
| **Fragment version** | content bytes · content-derived identity | C1 | **Immutable** — a change creates a new version |
| **Fragment path** | hierarchical address · namespace · resolution policy | C1 | Mutable (it is a name) |
| **Recipe** | load directives · conditions · order declaration · expectations · parameter contract | C1 | Versioned like a fragment |
| **Selection context** | control-variable bindings · address-variable bindings · version pins | caller | Per-call |
| **Value bindings** | value-variable bindings | caller | Per-call |
| **Span map** | ordered (span → fragment identity, tree position) | C4 | Per-assembly |
| **Attestation** | subject digest · resolved dependencies · condition outcomes · order · bindings · producer | C4 | Per-assembly, immutable |
| **Structural identity** | digest over structure only | C4 | Derived |
| **Instance identity** | digest over structure + values | C4 | Derived |

### 5.2 Ownership and flow

| Data | Owner | Notes |
|---|---|---|
| Fragment content | Library, custody delegated | Retrieved, never mutated by the assembly path |
| Path namespace | **Library** | The addressing scheme is the library's, not the backend's — this is what makes custody swappable (SD2) |
| Parameters | Caller, retained in attestation | Retained because a branch cannot be replayed without them (SD6) |
| Attestations | Library emits; **caller stores** | The library does not own a datastore. Storage is the caller's or the harness's concern |
| Evaluation results | **External** | SD10 |

**No bidirectional synchronization anywhere (SD2).** One configuration names one source of truth.

---

## 6. Security Architecture

### 6.1 Trust model

| Input | Trust | Handling |
|---|---|---|
| **Recipe conditions** | Trusted-but-bounded | Evaluated by a total expression language with no calls, loops, or I/O. Evaluation terminates by construction |
| **Fragment content** | **Untrusted** — may be machine-written or remotely sourced | **Never evaluated.** Inlined as text. This is the load-bearing guarantee of amendment 8 |
| **Value variables** | **Untrusted** | Substituted literally, once, never re-parsed. Cannot alter structure — substitution runs after all structural decisions |
| **Paths** | Semi-trusted | Canonicalized and confined to their namespace root; traversal outside a namespace is rejected |

### 6.2 Threat analysis

| Threat | Assessment |
|---|---|
| **Code execution via a machine-written fragment** | **Structurally eliminated.** Fragment content is never evaluated. Gate 0 documented four sandbox-escape CVEs on a single general-purpose engine, each fix followed by a new indirect route — safety by construction avoids that class entirely |
| **Path traversal via a crafted reference** | Mitigated: canonicalization plus namespace confinement; traversal outside the root is an error |
| **Denial of service via deep or wide expansion** | Mitigated: explicit depth ceiling, cycle detection, total expression evaluation, and an output size ceiling |
| **Prompt injection via a value variable** | **Not eliminable — it is the feature.** Mitigations: values cannot affect structure; every binding is recorded in the attestation, so an injection is forensically visible after the fact; values are never re-parsed. **The library cannot validate the semantics of caller-supplied text, and this document does not claim it can** |
| **Substitution of a fragment by a hostile custody backend** | Mitigated: content-derived identity is verified on retrieval; a mismatch against a pinned identity is an error |
| **Silent shadowing of a fragment by a layered source** | Mitigated: namespace isolation plus mandatory error on ambiguity (FR-031) |

### 6.3 Access control

Access control is **delegated to custody** (filesystem permissions, version-control permissions, remote store policy). The library holds no identity model and no permission model — consistent with being a library. Actor identity in the audit record comes from version control (amendment 7).

---

## 7. Error Handling

**Principle: fail loudly, fail early, never produce partial output.** Every failure names what failed, what was expected, and what was actually supplied.

| Class | Trigger | Behavior |
|---|---|---|
| **Expectation violation** | A declared expectation does not hold | Fail before any content is produced. Name the expectation and the actual input |
| **Unresolvable reference** | Path resolves to nothing | Fail naming the reference and the namespaces searched |
| **Ambiguous reference** | Multiple candidates, no deterministic winner | Fail naming every candidate and its source. **Never pick one** |
| **Cycle** | A reference revisits a node on the current stack | Fail reporting the **complete cycle path**; self-edges reported distinctly |
| **Depth or size ceiling** | Expansion exceeds a limit | Fail naming the limit and the path that exceeded it |
| **Identity mismatch** | Retrieved content does not match a pinned identity | Fail; never substitute |
| **Reproduction failure** | A referenced version is unavailable | Fail explicitly. **Never substitute a different version** (FR-003) |
| **Malformed recipe** | Recipe does not parse | Fail naming the location |

**No warnings-that-continue in the assembly path.** A prompt that assembled "mostly correctly" is a silent behavior change — the failure mode the product exists to prevent.

---

## 8. Performance Targets

Targets are stated as budgets. Absolute numbers are indicative and to be confirmed with design partners.

| Operation | Target | Rationale |
|---|---|---|
| Assembly, warm cache, typical recipe (≤ 50 fragments) | < 10 ms | It is on the request path of an agent call; it must be negligible against model latency |
| Assembly, cold, typical recipe | < 200 ms | Dominated by custody I/O |
| Provenance overhead | < 15% of assembly time | Provenance is mandatory (SD5); if it were expensive, it would be disabled, and the highest-opportunity job would be lost |
| Dependents query (FR-011) | < 100 ms for a 1000-fragment library | Must be cheap enough to run before every change |
| Remote custody fetch | Cache-first, identity-keyed | Content-addressed identity makes caching sound |

**Scalability shape:** the design target is thousands of fragments, not millions. Resolution is a graph walk over an in-memory index; a library that outgrows memory is out of scope for this architecture and would be a different design.

---

## 9. Testing Strategy

| Layer | Approach |
|---|---|
| **Expression evaluator** | Exhaustive unit coverage plus property tests for totality — evaluation must terminate on every input |
| **Resolution** | Table-driven cases across namespace routing, layering, precedence, ambiguity, and traversal attempts. Every ambiguity case asserts a **failure**, never a resolution |
| **Composition** | Property tests: **determinism** (repeated assembly is byte-identical), **order sensitivity** (permuted order yields a different structural identity), cycle detection reports the complete path |
| **Provenance** | Round-trip property: assemble → record → reproduce → byte-identical. Plus the identity-separation property: differing value bindings preserve structural identity but change instance identity |
| **Decomposition (FR-035)** | Golden-file property: for a corpus of prompts, every incremental extraction preserves byte-identical output |
| **Integration adapters** | Contract tests against recorded fixtures of the external shapes, so adapters can be validated without depending on a live external tool |
| **First-value (FR-028)** | A timed scripted walkthrough executed in CI — the survival metric deserves a test, not an aspiration |

**The four properties that must never regress:** determinism · order-aware structural identity · no evaluation of fragment content · no partial output on failure.

---

## 9.5 Constraint on the Composition Engine *(build-vs-adopt is Gate 6's decision)*

Whether the recipe language is built or adopted from an existing engine is a **technology selection** and belongs to Gate 6. This section states the **architectural constraints any candidate must satisfy**, so that gate is a comparison rather than an open question.

### Mandatory constraints

| # | Constraint | Why |
|---|---|---|
| **E1** | **A fragment must never be rendered as a template.** It is read as inert text and inserted as a value. An engine's native "include/import" semantics — which *render* the included unit — are **forbidden as the fragment mechanism** | ADR-003. If fragment content is rendered, optimizer-written text becomes executable and amendment 8's guarantee is void |
| **E2** | An inserted value must never be re-parsed after insertion | ADR-006. Otherwise a value variable could smuggle a directive |
| **E3** | Evaluation of conditions must be **total** — guaranteed to terminate, no loops, no calls, no I/O | ADR-003, and DoS mitigation in §6.2 |
| **E4** | Evaluation order must be controllable so that **all structural decisions complete before value substitution** | §3 step 8; this ordering *is* the security property |
| **E5** | Output ordering must never derive from map/set iteration, filesystem enumeration, or locale-sensitive comparison | §4 determinism |
| **E6** | The engine must expose a **resolver hook** so path resolution is owned by C2, not by the engine's own file lookup | SD3, and namespace isolation per ADR-004 |
| **E7** | Failures must be reportable with position and cause, and must never degrade to partial output | §7 |

### The shape of the tradeoff

| Approach | Satisfies constraints how | Real cost |
|---|---|---|
| **Adopt a mature general-purpose engine, heavily constrained** | Possible **only** by using it for recipe structure while loading fragments as inert string values — never through its include mechanism. Its conditional and variable machinery is reused; most of its power is forbidden | Inherits the engine's evaluation surface and its vulnerability history for the recipe layer; requires **permanently policing** that nobody uses the forbidden 95%. A convenience feature added later can silently void E1 |
| **Adopt a minimal engine that has a load primitive** | Smaller surface to constrain; less to police | Fewer such engines exist and are well-maintained; may still evaluate included content by default (E1) |
| **Build a bounded directive language** | Satisfies every constraint by construction — the grammar contains nothing that violates them | Parser, error messages, and tooling become owned work. Editor and syntax support must be built or forgone |

### An honest observation on relative size

The decided semantics (amendment 8) are **deliberately smaller than any general-purpose engine**: literals, comparisons, boolean operators, membership, variable references, a load directive, an order declaration, and expectations. That is a small grammar. Adopting a large engine to use a fraction of it — while forbidding the rest and inheriting its evaluation surface — is a **poorer fit than it first appears**, because the constraint list above is not a configuration; it is a discipline that must hold forever.

Conversely, building means owning parsing, diagnostics, and tooling, which is real and recurring work that a mature engine provides for free.

**This document does not choose.** Gate 6 does, against constraints E1–E7.

---

## 10. Architecture Decision Records

**ADR-001: Layered library with I/O confined to the custody layer**
- **Context:** determinism (SD7) and assembly-free dependency analysis (FR-011) are both required.
- **Options:** (a) layered with I/O at the base; (b) I/O anywhere on demand; (c) fully preloaded library.
- **Decision:** (a).
- **Rationale:** purity above L1 makes determinism structural rather than a discipline, and allows L2 to answer dependency questions alone.
- **Consequences:** every input must be fetched before assembly begins; lazy mid-assembly fetching is forbidden.

**ADR-002: Content-derived identity, separate from path**
- **Context:** identity must survive custody changes (SD1, SD2) and support pinning.
- **Options:** (a) path + version label; (b) content digest; (c) backend-native identifier.
- **Decision:** (b), with paths as mutable names resolving to identities.
- **Rationale:** (a) breaks when a label is reassigned; (c) breaks when custody changes — precisely the boundary amendment 1 introduces.
- **Consequences:** identity is not human-readable; tooling must always present path *and* identity together.

**ADR-003: Bounded total expression language; fragment content never evaluated**
- **Context:** conditions need real expressiveness; fragments may be machine-written or remote (untrusted).
- **Options:** (a) general-purpose engine sandboxed; (b) bounded language, logic in recipes only; (c) logic permitted in fragments too.
- **Decision:** (b) — stakeholder decision, amendment 8.
- **Rationale:** Gate 0 documented that sandboxes on general-purpose engines are blocklists in a cat-and-mouse pattern; a machine-written fragment is adversarial input by definition. Safety by construction dominates safety by sandbox.
- **Consequences:** computed values must be prepared by the caller. Accepted deliberately.

**ADR-004: Namespace isolation over ordered search-order resolution**
- **Context:** FR-031 forbids silent shadowing.
- **Options:** (a) ordered search, first match wins; (b) namespace isolation; (c) hybrid with explicit layering.
- **Decision:** (b), with (c) permitted **only** where an explicit ordered chain is configured and ambiguity remains an error.
- **Rationale:** first-match-wins makes collisions invisible — exactly the silent failure class the product exists to remove.
- **Consequences:** configuration is more explicit; accidental override is impossible.

**ADR-005: Two-level assembly identity**
- **Context:** amendment 9. Comparison and reproduction have conflicting identity needs.
- **Options:** (a) one identity including values; (b) one identity excluding values; (c) two levels.
- **Decision:** (c).
- **Rationale:** (a) makes every call unique and destroys comparability; (b) makes byte-identical reproduction impossible.
- **Consequences:** two digests per assembly; consumers must be told which one to use, and the distinction must be prominent in the interface — if a caller compares instance identities, every comparison silently fails to group.

**ADR-006: Value substitution runs last, and substituted values are never re-parsed**
- **Context:** value variables are the injection surface (amendment 9).
- **Options:** (a) substitute inline during expansion; (b) substitute last, single pass, no re-parse.
- **Decision:** (b).
- **Rationale:** guarantees a caller-supplied value can never influence which fragments load, their order, or their version.
- **Consequences:** a value cannot itself name a fragment — that is an address variable's job, and the distinction is enforced by ordering.

**ADR-007: Change governance delegated to version control**
- **Context:** amendment 7.
- **Options:** (a) build review/approval/history; (b) delegate to version control; (c) hybrid.
- **Decision:** (b).
- **Rationale:** version control already provides isolation, origin, reviewer identity, accept/reject, and history. Rebuilding would duplicate a solved problem.
- **Consequences:** **one fragment per separately diffable unit becomes a hard architectural constraint.** Under remote custody without version control, review is not inherited and no substitute is provided — recorded as an accepted limitation.

---

## 11. Requirements Traceability

| Component | Requirements |
|---|---|
| **C1 Fragment Library** | FR-006, FR-007, FR-008, FR-009, FR-010 |
| **C2 Resolution** | FR-029, FR-030, FR-031, FR-020 (version selection) |
| **C3 Composition** | FR-018, FR-019, FR-020, FR-021, FR-022, FR-023, FR-032, FR-035, FR-036, FR-037 |
| **C4 Provenance** | FR-001, FR-002, FR-003, FR-004, FR-005 |
| **C5 Change Intake** | FR-012 (validation); FR-013–FR-017, FR-033 **delegated** |
| **C6 Integration Surface** | FR-024, FR-025, FR-026, FR-038, FR-027 (boundary) |
| **C7 Impact Analysis** | FR-011, FR-012, FR-035 |
| **Cross-cutting** | FR-028 (§8 targets, §9 CI test), FR-023 (§4) |
| **Deferred** | FR-034 |

**38/38 requirements accounted for** — 31 architected, 6 delegated, 1 deferred.

---

## 12. Gate 5 Validation

| Category | Check | Result |
|---|---|---|
| **Architecture Completeness** | All PRD features mapped to components | ✅ 38/38 |
| | Clear component boundaries | ✅ 7 components, one-directional layering |
| | Single clear responsibilities | ✅ |
| | Stable interfaces | ✅ two ports only: custody, external capabilities |
| **Data Design** | Ownership explicit | ✅ §5.2 |
| | Models support PRD | ✅ incl. two-level identity |
| | Consistency strategy | ✅ immutable versions, one source of truth, no bidirectional sync |
| | Flows documented | ✅ §3 |
| **Quality Attributes** | Performance targets set | ✅ §8 with rationale |
| | Security addressed | ✅ §6 incl. an honest non-mitigable threat |
| | Scalability path clear | ✅ with an explicitly stated ceiling |
| | Reliability defined | ✅ §7, no partial output |
| **Integration Readiness** | External deps by capability, not product | ✅ |
| | Patterns selected, not tools | ✅ |
| | Errors considered | ✅ §7 |
| **Technology Agnostic** | Zero product names | ✅ scan-verified |
| | Can swap technology without redesign | ✅ two adapter ports |

### Confidence Score

| Factor | Score | Justification |
|---|---|---|
| **Pattern Match** | 32/40 | The load-bearing pieces are proven prior art: prefix-routed namespace resolution, content-derived identity with mutable naming, supply-chain-style attestation, DFS cycle detection with path reporting, layered purity for determinism. Deducted 8: **two-level identity (ADR-005) is not borrowed** — it was derived from the comparison-vs-reproduction conflict and has no direct precedent found |
| **Complexity Management** | 24/30 | Amendments 7 and 8 removed substantial complexity — an entire governance domain, and the whole sandbox problem. Deducted 6: provenance carries genuine intrinsic complexity (two representations, two identities), and it sits on the critical path of the highest-opportunity job |
| **Risk Level** | 26/30 | Main risks are mitigated structurally rather than procedurally: determinism by purity, injection-class execution by non-evaluation, silent shadowing by mandatory failure. Deducted 4: the delegated-review gap under remote custody (A6) is **unresolved by design**, and both integration targets changed ownership within 8 months |
| **Total** | **82/100** | ≥ 80 → present autonomously |

**Gate Result:** ✅ **PASS**

**Carried forward:**
- 🔴 **A** — largely dissolved by amendment 7; it is now a version-control branch-protection setting, not a product feature. No review system is architected.
- ✅ **A6 gap — CLOSED 2026-09-05** by removing the case: custody is repository-resident only. T-025 dropped (the host repository versions fragments), T-026 deferred (no remote custody). The ADR-007 delegation is now unconditional. Reopens the moment any non-repository backend is added.
- ⚠️ Live traffic splitting remains out of scope by assumption, not decision.

**Next Step:** Gate 6 — Dependency Map (`souschef:pre-dev-dependency-map`)
