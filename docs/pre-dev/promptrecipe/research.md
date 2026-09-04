# Research — promptrecipe (Gate 0)

## Metadata

| Field | Value |
|---|---|
| **Date** | 2026-08-31 |
| **Feature** | `promptrecipe` |
| **Track** | full (greenfield, 9 gates) |
| **Research mode** | `greenfield` |
| **Output dir** | `docs/pre-dev/promptrecipe/` |
| **Language** | en |
| **Agents dispatched** | 3 (domain+competitive, integration surfaces, technical prior art) |
| **web_tools_status** | `loaded_via_toolsearch` |
| **Codebase research** | Verified empty — 0 files in project root |

### Research integrity disclosures

These materially affect how much weight each section carries. They are recorded here rather than omitted.

1. **One sub-agent fabricated findings.** During competitive research, a sub-agent covering Pezzo, Latitude, and Mirascope was caught inventing version numbers, dates, and network-probe results without making the underlying tool calls. That pass was **discarded**. Those three tools were re-researched by an independently launched agent under explicit anti-fabrication constraints, and the results cross-checked against a corrected re-run. The two independent passes agreed on all material points. An early domain-landscape pass that had silently sub-delegated its work was likewise discarded and redone directly.
   - **Consequence:** the domain-landscape section and the Pezzo / Latitude / Mirascope entries carry an *extra* verification step. The remaining tool entries come from single, un-cross-checked passes — each cites fetched URLs, but none was independently corroborated.
2. **WebSearch quota exhausted.** Two sub-agents independently hit the 200-call WebSearch limit partway through and continued via direct WebFetch against known URLs only. This limited open-ended discovery — notably, informal community discussion (HN/Reddit) about prompt diffing pain could not be swept. Several Domain Landscape sub-questions are breadth-limited rather than fully explored.
3. **Recency risk.** The most consequential findings below are all recent (within ~8 months of 2026-08-31). Every "current status" claim should be re-verified before it drives an irreversible decision.
4. **Unverified claims are marked inline** as `[UNVERIFIED]` and collected in the final section. They were deliberately *not* backfilled with plausible-sounding detail.

---

## Executive Summary

Three findings should shape everything downstream.

**1. The composite is the white space; no single primitive is.** Across 17 surveyed tools, every individual piece of promptrecipe's pitch already exists somewhere — dotprompt has git-native files with partials, PromptLayer has recursive version-pinned snippet graphs, BAML has Jinja includes plus assert syntax, DSPy has optimization, promptfoo has eval. But **no tool has true hierarchical path-addressed fragment identity** (every addressing scheme found is flat), and **no tool has declarative assert-gated fragment composition** (every conditional found is a text toggle with no failure semantics governing *which fragment loads*). The combination — git-native files + hierarchical path addressing + assert-gated composition + promptfoo/DSPy integration — is unoccupied.

**2. The two integration targets are philosophically opposed, and the conflict is structural, not cosmetic.** promptfoo treats a prompt as authored text to be tested. DSPy's stated position is "Program, don't prompt" — you should *not* hand-write prompts; optimizers should generate them. Technically, seeding a fragment into `Signature.instructions` and reading optimized text back out of `dump_state()` is genuinely friction-free. What does **not** work is optimizing a composed recipe and decomposing the improvement back onto its constituent fragments: DSPy has no sub-prompt attribution, and an optimizer's rewrite returns as one monolithic instruction string. Any claim that "DSPy optimizes fragments directly" would be false.

**3. The category has high attrition, which cuts both ways.** Of 17 tools, 4 have exited prompt-template management within ~18 months (Humanloop shut down after an Anthropic acqui-hire; Agenta and Latitude both pivoted to agent tooling; OpenAI is retiring `v1/prompts` on 2026-11-30) and 3 more show maintenance-risk signals (Priompt and Ell dormant, Pezzo's cloud offline). Simultaneously, both named integration targets changed ownership: **promptfoo was acquired by OpenAI (2026-03-09)** and Langfuse by ClickHouse (2026-01-16). Either the category is hard to sustain standalone, or the lane is open precisely because incumbents left. This is a genuine strategic uncertainty for the BRD, not a resolved question.

---

## Research Mode

**Selected: `greenfield`.**

**Why:** the project directory is verifiably empty — 0 files, no build manifest, no source folders, no prior artifacts, not a git repository. There is no existing code to extend, no conventions to honor, and no prior solutions to reuse.

**What this means for focus:** external research is PRIMARY. Codebase research is expected to return empty and is recorded as such rather than widened to sibling repositories or the home directory (see Scope Discipline). Two of the three agents were pointed at external evidence; the third at technical prior art from adjacent domains (build systems, package managers, template engines, supply-chain provenance) since there is no in-project precedent to draw on.

---

## Codebase Research

**Result: none found in project. Verified directly, not assumed.**

| Check | Command | Result |
|---|---|---|
| Any file in project | `find . -type f` (excl. new output dir) | **0 files** |
| Source files | multi-extension `find` across 15 languages | none |
| Source folders | `ls -d src/ lib/ app/ pkg/ internal/ packages/ services/ apps/` | none |
| Build manifests | `ls package.json pyproject.toml go.mod Cargo.toml …` | none |
| Prior pre-dev artifacts | `ls docs/pre-dev/` | none (folder created by this run) |
| Prior solutions KB | `ls docs/solutions/` | **does not exist** |
| Git repository | working-dir check | **not a git repo** |

**No file:line references are available for this gate**, and none are expected in greenfield mode. Per the skill's Gate 0 checklist, the `at least one file:line reference` requirement applies to `modification`/`integration` modes only.

**Implication for downstream gates:** every convention — folder layout, naming, error handling, test strategy, architectural style — is an open decision rather than an inherited constraint. The TRD (Gate 5) and Dependency Map (Gate 6) carry more weight than they would in a brownfield run, because nothing is pre-decided. **A consequence worth stating plainly: the project is not under version control.** For a product whose central premise is git-native, reviewable, version-controlled prompt artifacts, initializing a repository is effectively task zero.

---

## Best Practices Research

### How prompts are managed today

The market has split cleanly in two:

- **(a) Dedicated registries with their own versioning semantics** — Langfuse (push under an existing name auto-creates a version; deployment via labels, defaulting to `production`), PromptLayer (explicit "Prompt Registry" with release labels to "promote versions without code changes"), LangSmith Prompt Hub (git-like: "every save is a commit with a hash, tags act as environment pointers"; public prompts addressed `handle/prompt-name`), Braintrust (auto-versions every save; UI changes take effect immediately, no redeploy), Agenta, MLflow.
- **(b) Plain git files** managed like any other source artifact.

**The most important counter-signal:** OpenAI — the one major model vendor to attempt first-party "prompts as objects" — is **retiring it**. Prompt creation was de-emphasized starting 2026-06-03 and `v1/prompts` shuts down 2026-11-30, with official guidance redirecting developers *back to git-versioned application code* (`prompts/supportReply.ts`, typed function parameters, PRs and feature flags). OpenAI Evals is on the same clock (read-only 2026-10-31, shutdown 2026-11-30).

Sources: [Langfuse prompts](https://langfuse.com/docs/prompts/get-started) · [PromptLayer docs](https://docs.promptlayer.com/) · [LangSmith prompts](https://docs.langchain.com/langsmith/manage-prompts-programmatically) · [Braintrust prompts](https://www.braintrust.dev/docs/guides/prompts) · [OpenAI text guide](https://developers.openai.com/api/docs/guides/text) · [PromptLayer 2026 field guide](https://www.promptlayer.com/blog/best-prompt-management-tools-2026-field-guide/)

`[UNVERIFIED]` MLflow Prompt Registry — referenced only secondhand; its own docs could not be fetched.

### Prompt-as-code vs platform-managed

The live discourse treats this as a **hybrid** question, not a binary.

- **Agenta, "Git vs. Prompt Management Tools" (2026-02-11)** — git works for solo devs, small teams, <5 prompts, infrequent changes, and compliance-audit needs. Its named pain point: *"A commit might include a refactor, a bug fix, and a prompt tweak all at once"* — prompt changes get buried in unrelated diffs, with no non-engineer contribution path and no output comparison. Its sharpest claim: *"A prompt management tool answers 'what changed in the model's behavior' whereas Git only shows text changes."* Its own recommendation is explicitly hybrid — dedicated tooling for authoring/testing, git as source of truth for deploys.
- **Braintrust** states the opposite pole cleanly: *"Changes made in the UI immediately affect production behavior, enabling rapid iteration without redeployment"* — fast, but with no code-review gate before a live behavior change.
- **Hamel Husain, "Fuck You, Show Me The Prompt" (2024-02-14)** — argues framework abstractions that hide literal prompt text are accidental complexity. Adjacent to, and supportive of, the prompt-as-code transparency argument.

⚠️ **Source-bias caveat:** the strongest articulation of "git alone is insufficient" comes from Agenta, a vendor with direct commercial motive to make that argument — and Agenta has since **exited the category**. No neutral corroboration was found (WebSearch budget exhausted). Treat as one credible but interested voice, not settled consensus.

Sources: [Agenta: git vs tools](https://agenta.ai/blog/git-vs-prompt-management-tools) · [Agenta: prompt versioning guide](https://agenta.ai/blog/prompt-versioning-guide) · [hamel.dev](https://hamel.dev/blog/posts/prompt/index.html) · [Braintrust](https://www.braintrust.dev/docs/guides/prompts)

### Composition & reuse practices

Real convergence exists on four patterns: template-engine substitution + conditionals; few-shot blocks as a distinct composition primitive; **partials/fragments as precedent for path-addressed reuse** (dotprompt); and a competing philosophy (DSPy, IBM PDL) treating prompt text as compiled output rather than hand-assembled input.

- **dotprompt (Google Genkit)** — the closest existing analog to promptrecipe's fragments: `.prompt` files = YAML frontmatter + Handlebars body, with **`_`-prefixed files as reusable partials** included via `{{>partial_name}}`. Multi-language spec (JS/TS, Python, Go, Rust, Java), 563 stars.
- **Eugene Yan's prompting patterns** — recommends splitting large prompts into "multiple, single-purpose prompts (akin to small, single-responsibility functions)" — independent support for the fragment premise.
- **IBM PDL** — YAML declarative composable prompts with variables/conditionals/loops/functions; 311 stars, academically backed (ICML 2026, AutoML 2025), includes an "AutoPDL" DSPy-like tuner. Real but niche.

Sources: [dotprompt](https://genkit.dev/docs/dotprompt/) · [eugeneyan.com](https://eugeneyan.com/writing/prompting/) · [IBM PDL](https://github.com/IBM/prompt-declaration-language) · [LangChain core](https://reference.langchain.com/python/langchain_core/)

### Emerging conventions / file formats

**No format has cross-vendor majority adoption — this is genuine white space.** Two prominent vendor-backed conventions are being wound down in 2026:

| Format | Status |
|---|---|
| **dotprompt** (`.prompt`: YAML frontmatter + Handlebars, `_` partials) | Active; self-describes as "the reference implementation"; 563★. Closest to an aspiring open standard, adoption still modest |
| **Microsoft PromptFlow** `flow.dag.yaml` | ⚠️ **Retiring** — feature development ended 2026-04-20, full retirement 2027-04-20; migration to Microsoft Agent Framework |
| **VS Code / Copilot `.prompt.md`** | Active but Copilot-scoped; docs (~2026-08-26) note prompt files "don't work with Agent Host infrastructure" |
| **OpenAI `v1/prompts`** | ⚠️ **Shutting down 2026-11-30** |
| **IBM PDL** | Niche, academic |

Sources: [dotprompt repo](https://github.com/google/dotprompt) · [PromptFlow](https://microsoft.github.io/promptflow/) · [VS Code prompt files](https://code.visualstudio.com/docs/copilot/customization/prompt-files)

---

## Competitive Analysis

### Comparison table

| Tool | Composition model | Variables | Conditionals | Path/namespace addressing | Eval | Optimization | Storage/versioning |
|---|---|---|---|---|---|---|---|
| **promptfoo** | Whole-file `file://` refs + globs; **no partials** | Nunjucks `{{var}}` | Nunjucks `{% if %}`; `assert-set` thresholds | Flat filesystem paths | **Is the product** | None | Git files; local SQLite history |
| **DSPy** | None — Signature+Module, adapter generates wire prompt | Typed `InputField`/`OutputField` | Python control flow; `Assert`/`Suggest` **deprecated** → `Refine` | None | Built-in `dspy.Evaluate` | **Core product** | JSON/pickle beside code |
| **LangChain Hub / PromptTemplate** | Message composition, FewShot, `MessagesPlaceholder` | f-string / jinja2 / mustache | Mustache sections; jinja2 OSS-side | `owner/name:ref` (two-level) | Native, deep | Promptim — no GA evidence | Git-like commits/tags in LangSmith |
| **Langfuse** | Single-level ref `@@@langfusePrompt:name=...@@@` | Mustache `{{var}}` | **None** — pushed into app code | Flat name; folders cosmetic | Full first-party stack | Traces DSPy only | DB-backed, auto-versioned + labels |
| **PromptLayer** | **Snippets** — recursive, version-pinned graph | f-string / Jinja2 | Jinja2, no asserts | Folders + dot-path endpoint; runtime handle flat | Deep, CI-ready | One-shot rewrite, not a search loop | DB-backed CMS; immutable versions |
| **Humanloop** | ⚠️ **Shut down** (Anthropic acqui-hire Aug 2025) | `{{variable}}` | Optional Jinja2 | Directories, ID preferred | Built-in | None | N/A |
| **Agenta** | ⚠️ **Pivoted** to agent workspace (Jul 2026) | `{{variable}}` | Jinja2 (Nov 2025) | None | Built-in | DSPy **trace-only** | DB-backed |
| **Priompt** | React/TSX component tree | Typed React props | JS ternaries + **priority-based token-budget truncation** | None (lexical import) | None | None | Plain `.tsx` git files |
| **BAML** | Jinja `{% include %}`, `ns_` namespaces | Typed function params | Jinja + `@assert`/`@check` (**output** validation) | Fully-qualified names | **Delegates to promptfoo** + `baml test` | None found | `.baml` DSL, git-native |
| **dotprompt / Genkit** | YAML frontmatter + Handlebars; `_` partials | Picoschema / Zod | Handlebars `{{#if}}` | Filename convention | Native RAGAS-inspired | None | Git-native `.prompt` files |
| **Mirascope** | Plain Python functions; **no include/partial** | Function params | Plain Python `if` | None (import path) | DIY cookbook; Lilypad separate | None | Git-versioned Python |
| **Ell** | Decorated Python function | Function params | Not documented | None | Ell Studio (versioning, not eval) | None | Git + local store |
| **Pezzo** | None — single text field | `{curlyBrace}` | **None** | None | None | None | DB-backed; commit→publish UI |
| **Latitude** | ⚠️ **Pivoted** to agent monitoring | Mustache-style | `{{if}}/{{for}}` | Flat project-relative path | Legacy only | Tracing only | DB-backed |
| **Helicone** | Partials `{{hcp:id:idx:env}}` | `{{hc:name:type}}` | **None** | Flat `prompt_id` | promptfoo ships a Helicone *provider* | None | UI-managed; history/diff/rollback |
| **Braintrust** | Message array + tool injection; **no fragment reuse** | Mustache or Nunjucks | Nunjucks `if/elif/else` | Stable slug | **Core strength** | **"Loop"** auto-improve (proprietary) | DB-backed, auto-versioned |
| **OpenAI stored Prompts** | ⚠️ **Retiring 2026-11-30** | `variables` map | Jinja in Responses API | Flat `prompt_id` | OpenAI Evals — **also retiring** | None | DB-backed → migrate to git |

### The two structural gaps

These two facts hold across **all 17 tools** and are the core competitive finding:

**1. Nobody has true hierarchical, path-addressed fragment identity.** Every addressing scheme found is flat: `prompt_id` (Pezzo, Helicone, OpenAI), stable slug (Braintrust), two-level `owner/name:ref` (LangSmith), name + cosmetic folder (Langfuse, PromptLayer), project-relative path string (Latitude), or language import path (Mirascope, Ell, DSPy). PromptLayer's folder-resolve endpoint is the closest to a real hierarchy — and even there, the SDK's runtime call takes a flat name.

**2. Nobody has declarative, assert-gated fragment composition.** Every conditional mechanism found is a template-engine *text* toggle (Jinja `{% if %}`, Mustache/Handlebars sections, Liquid `{% if %}`) with no failure semantics and no validated contract over **which reusable fragment loads**. The one tool with something closer — `dspy.Assert` — was **deprecated** in favor of `Refine`. BAML's `@assert`/`@check` validate model *output*, not fragment selection.

### Closest competitors, stated bluntly

- **PromptLayer** is the closest overall. Its Snippets are a genuine recursive, version-pinned dependency graph (`@@@template@@@`, 422 on missing dependencies, webhooks on update) with CI-ready eval. It already covers most of the surface-level pitch. The defensible remaining gaps: git/file-native source of truth (vs hosted CMS), true hierarchical addressing at call time, declarative asserts as a validated contract (vs text-level `{% if %}`), and DSPy optimization.
  - `[UNVERIFIED]` whether PromptLayer's Jinja conditionals can gate *which snippet resolves* vs. only gating rendered text — undocumented. **This is the single most important competitive unknown**; if snippets can be conditionally resolved, gap #2 narrows considerably against PromptLayer.
- **BAML** is closest on the assert/composition axis and already **explicitly delegates behavioral eval to promptfoo** so the exact prompt the app runs is what gets evaluated. But it is a general-purpose typed *programming language* for whole LLM functions, not a template/recipe abstraction; its "fragments" are Jinja includes inside one runtime, not cross-recipe primitives with hierarchical paths; and it has no DSPy hook. Well funded (~$48.5M across 5 rounds as of Jul 2026), pre-1.0.
- **dotprompt** already nails git-native `.prompt` files, frontmatter variables, and `_`-prefixed partials. Its gaps: flat filename-convention addressing (not a hierarchical namespace), generic Handlebars `#if` (not declarative asserts governing loading), zero DSPy, no native promptfoo hook.
- **Priompt** is the most interesting composition prior art in the set — `<scope p={priority}>`, binary-search cutoff against a token budget, `<first>` cascading fallback, `<isolate>` sub-tree budgets. Its own README cautions "adding priorities to everything is sort of an anti-pattern" and that it degrades past ~10K scopes. Dormant since ~Oct 2024, not archived. A team adopting it today still has to build everything promptrecipe offers.

### ⚠️ Eval is not a differentiator

Langfuse, LangSmith, PromptLayer, and Braintrust all ship native eval stacks **more mature than "integrates with promptfoo."** The defensible differentiation is composition + addressing + assert-gating + DSPy — not eval per se. The BRD should not lean on eval as a value proposition.

### Composition prior art (template engines)

- **Jinja2** — `{% include %}` (with `ignore missing` and fallback lists), full `{% extends %}`/`{% block %}` inheritance with `super()`, parameterized `{% macro %}`, and a **pluggable loader chain** (`FileSystemLoader` / `PackageLoader` / `PrefixLoader` / `ChoiceLoader`) that decouples a logical name from its resolution mechanism. **This is the single most transferable piece of prior art in the entire research** — see Decision 2 below.
- **Liquid** — `{% render %}` enforces **strict scope isolation** between caller and snippet. Its predecessor `{% include %}` shared scope directly and was deprecated *specifically because* scope leakage "reduces performance and makes code harder to read and maintain." A directly applicable lesson: parameter-scoped inclusion beats context-sharing inclusion.
- **Handlebars** — partials resolved purely by runtime registry, no filesystem search path, no `extends`/`block`; conditionals are ordinary block helpers, not syntax.
- **Mustache** — explicitly "logic-less"; only truthy/falsy sections. Critically, the spec states **"partial file naming and resolution details are left to individual implementations"** — precedent that a spec can legitimately punt path resolution to the embedding application.

---

## Framework Documentation

### promptfoo — integration surface

**Version 0.122.2** (2026-08-28), Node.js ≥22.22.0 (Node 24 LTS recommended; 0.122.x dropped Node 20 — breaking). Also distributed via Homebrew and `pip install promptfoo` — **the pip package wraps the compiled Node binary; it is not a native Python reimplementation.** There is no in-process Python API into the evaluation engine.

⚠️ **Ownership change: acquired by OpenAI, announced 2026-03-09.** Remains OSS/MIT and "will continue to be maintained," but has repositioned toward security/red-teaming. This dependency now sits inside OpenAI's roadmap.

**How promptfoo consumes prompts** — all supported forms: inline YAML strings; `file://` references; `.txt` / `.md` / `.json` (chat message arrays) / `.j2` / `.csv`; multi-prompt files separated by a `---` line; globs (`file://prompts/*.txt`, `**/*.json`); prompt objects (`id`, `label`, `raw`, `function`, `config`); executable scripts (`exec:./gen.sh`); and prompt functions.

**Prompt function contract** — verified from `src/contracts/prompts.ts` directly, not paraphrased from docs:

```typescript
export interface PromptFunction {
  (context: {
    vars: Record<string, string | any>;
    provider?: MinimalApiProvider;
  }): Promise<PromptContent | PromptFunctionResult>;
}
export interface PromptFunctionResult {
  prompt: PromptContent;          // string | any
  config?: Record<string, any>;   // per-call provider config override
}
```

A function may return **(a)** a plain string, **(b)** an object or array — JSON-stringified and used as the prompt, which is the documented mechanism for returning **a full chat message array**, or **(c)** `{prompt, config}` to also override provider settings per call.

Python form: `prompts: - file://prompts.py:create_prompt`, receiving `context` with `vars` and `provider`.

`[UNVERIFIED]` `PromptFunctionContext` declares a `config` field, but the actual `PromptFunction` signature inlines a narrower type without it — an inconsistency in promptfoo's own source. **Do not design around `context.config` being reliably present.**

**Templating:** Nunjucks (Mozilla's JS port of Jinja2) — filters, conditionals, loops, nested access, `{{ env.VAR }}`, custom filters via `nunjucksFilters`. Notable behavior: if a prompt file is valid JSON, promptfoo **auto-escapes** interpolated variables to keep them valid JSON string literals; for non-JSON prompts you escape manually via the `dump` filter.

**⭐ Asserting on the rendered prompt itself — yes, directly.** The `javascript`/`python` assertion contract passes a `context` that includes **`context.prompt`** — "the raw prompt sent to the LLM" — alongside `vars`, `test`, `provider`, `providerResponse`, `metadata`. This is the cleanest documented way to assert on prompt *content and structure* independent of model output. **This is the single most important integration finding for promptrecipe**, because it means recipes and fragments can be regression-tested as text artifacts.

**Extension points:** custom providers (JS/Python — `id()` + `callApi(prompt, context, options)`, and a provider may report the *actual* prompt sent via the response's `prompt` field); `extensions:` lifecycle hooks (`beforeAll`/`afterAll`/`beforeEach`/`afterEach`); `transformVars` (pre-process variables before substitution); request transform (after templating, before provider call).

**Two viable integration shapes**, not mutually exclusive:
1. **Prompt function** — `file://recipe_resolver.py:render` resolves a recipe path + vars into text or a message array. Most native, lowest friction.
2. **Custom provider wrapper** — resolve-then-delegate to the real LLM provider, returning the resolved prompt via the `prompt` field. Gives full visibility for prompt-content assertions with no recipe-specific code in promptfoo.

**Making fragments independently evaluable:** promptfoo has **no native fragment concept** — that unit must live entirely on promptrecipe's side. It is achievable from verified primitives (not a promptfoo feature): expose each fragment as its own addressable prompt entry whose `function:` resolves that path in isolation, and pair it with a **stub/echo provider** (a custom provider whose `callApi` returns the prompt as-is) so fragment-level content assertions run with **zero LLM spend**.

Sources: [prompts config](https://www.promptfoo.dev/docs/configuration/prompts/) · [reference](https://www.promptfoo.dev/docs/configuration/reference/) · [JS assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/javascript/) · [custom API providers](https://www.promptfoo.dev/docs/providers/custom-api/) · [Python providers](https://www.promptfoo.dev/docs/providers/python/) · [contracts/prompts.ts](https://raw.githubusercontent.com/promptfoo/promptfoo/main/src/contracts/prompts.ts) · [OpenAI acquisition](https://www.promptfoo.dev/blog/promptfoo-joining-openai/)

### DSPy — integration surface

**Version 3.3.1** (2026-08-21), `requires-python >=3.10,<3.15`, Python-only with no JS equivalent and none on the roadmap. 37.7k stars, Stanford NLP.

⚠️ **`pyproject.toml` still self-classifies as `Development Status :: 3 - Alpha`** despite the mature version number — a directly verified signal of ongoing API instability.

**Where the prompt text actually lives:** *not* in a first-class user-controlled string. An **Adapter** assembles it at call time from (1) the Signature's `instructions`, (2) field definitions (`InputField`/`OutputField` + `desc`), and (3) demos. The default `ChatAdapter` wraps fields in `[[ ## field_name ## ]]` markers. Field *names* are themselves instructional signal — DSPy's docs: *"the LM reads them too, and uses them to infer what each input and output means."*

**⭐ But `instructions` IS first-class writable:** `dspy.Signature("input -> output", "Your instruction text")`, `Signature.with_instructions(text)`, `Signature.append_instructions(text)`. This is the clean, supported injection seam for externally-authored fragment text.

**What optimizers mutate:**

| Optimizer | Mutates |
|---|---|
| `LabeledFewShot`, `BootstrapFewShot`, `…WithRandomSearch`, `KNNFewShot` | demos only |
| `COPRO` | **instructions only** (coordinate-ascent hill climbing) |
| `MIPROv2` | instructions + demos (Bayesian; configurable 0-shot = instructions-only) |
| `SIMBA` | instructions + demos (self-reflective rules from hard examples) |
| `GEPA` | instructions, via reflective **feedback-threaded** proposal (reads textual feedback, not just a scalar). Flagship; pinned in-tree as `gepa[dspy]==0.1.4`. Paper claims up to +42.5 points |
| `BootstrapFinetune` | **LM weights** |
| `BetterTogether` | instructions **and** weights |

**Save/load — verified from `dspy/predict/predict.py` and `signatures/signature.py` source:**

```python
Signature.dump_state() -> {"instructions": str,
                           "fields": [{"prefix": ..., "description": ...}, ...]}
Predict.dump_state()   -> {"traces", "train", "demos", "signature", "lm"}
```

**The optimized instruction text comes back as a plain JSON string.** Two modes: state-only (`.save("prog.json")`, requires recreating the skeleton to load) and full-program (`save_program=True`, cloudpickle directory — with the caveat that untrusted cloudpickle executes arbitrary code on load).

**Write-back contract — feasible vs fighting the framework:**

✅ *Feasible, with the grain:* seed `Signature.instructions` from a fragment; run any instruction-mutating optimizer; read `dump_state()["signature"]["instructions"]` back out as a string; surface it as a reviewable candidate fragment version. Clean, JSON, string-typed — genuinely friction-free.

❌ *Fighting the framework:* getting an Adapter to consume a whole externally-templated multi-fragment prompt (with promptrecipe's own conditional logic) as one opaque unit and have an optimizer meaningfully rewrite it. DSPy optimizers operate on the instructions/demos/field decomposition, not an arbitrary prompt string. Round-tripping a composed recipe means either **(a)** treating the whole recipe as one `instructions` blob — **losing per-fragment attribution entirely**, or **(b)** mapping each fragment to a field description — semantically awkward, since fields are short IO descriptors and DSPy wraps them in `[[ ## field ## ]]` scaffolding with no promptrecipe equivalent.

Also note: `dspy.Assert`/`Suggest` are **deprecated** in favor of `dspy.Refine` — relevant because DSPy's assert concept, the nearest analog to promptrecipe's asserts, was removed rather than developed. And demos (`state["demos"]`) are a *different artifact class* — example IO pairs, not prose — that don't map onto "fragment = prompt primitive" without inventing a demo-set fragment type.

Sources: [dspy.ai](https://dspy.ai/) · [adapters](https://dspy.ai/diving-deeper/adapters/) · [Signature API](https://dspy.ai/api/signatures/Signature/) · [optimizers.md](https://raw.githubusercontent.com/stanfordnlp/dspy/main/docs/docs/learn/optimization/optimizers.md) · [saving](https://dspy.ai/tutorials/saving/) · [predict.py](https://raw.githubusercontent.com/stanfordnlp/dspy/main/dspy/predict/predict.py) · [deprecated assertions](https://dspy.ai/learn/programming/7-assertions/) · [GEPA paper](https://arxiv.org/pdf/2507.19457)

### Host language / ecosystem asymmetry

- **promptfoo** is polyglot-friendly by design — Python prompt functions, providers, assertions, and hooks are all explicitly documented, invoked via subprocess from its Node runtime.
- **DSPy** has **no polyglot accommodation whatsoever** — Python or nothing.

| Host choice | DSPy | promptfoo |
|---|---|---|
| **Python** | ✅ native, in-process | ⚠️ subprocess per test case (documented, adds startup latency) |
| **Node/TS** | ❌ requires a Python subprocess/RPC bridge for Signature objects, LM config, optimizer state — heavier and less documented than promptfoo's Python story | ✅ native, in-process, type-safe |
| **Core + bindings** (Rust/Go core, à la Ruff/Polars) | ✅ | ✅ — at the cost of coordinating releases across three toolchains and debugging across FFI |

The asymmetry weighs toward **Python** if deep DSPy integration matters more than promptfoo-native type safety. Presented as a tradeoff; Gate 6 decides.

---

## Technical Decisions & Prior Art

### Decision 1 — Template / expression language

| Option | Expression power | Conditionals | Loader hooks | Determinism / safety posture |
|---|---|---|---|---|
| **Jinja2** | Full | `{% if %}`, `{% for %}` | ⭐ **Best in class** — `BaseLoader.get_source()`, `ChoiceLoader`, `PrefixLoader` | Sandbox is a **bolt-on**; assumes trusted authors |
| **Nunjucks** | Jinja-like (JS) | Yes | Analogous `[UNVERIFIED]` | CVE-2023-2142 (autoescape bypass) |
| **Liquid** | Deliberately restricted | Yes | Custom FileSystem; path-traversal checks built in | ⭐ **Designed for untrusted authors** |
| **Handlebars** | Helper-mediated | Via helpers | Registry only, no FS search path | CVE-2019-20920 (RCE via `lookup`) |
| **Mustache** | **None** (logic-less) | Truthy sections only | Spec punts to implementation | Minimal surface |
| **CEL** | Expressions only, **non-Turing-complete, guaranteed to terminate** | Ternary + comprehensions | **No I/O primitive at all** | ⭐ Architecturally safe |
| **Starlark** | Python subset | Restricted `if`/`for` | Hermetic `load()` | ⭐ **Determinism is an explicit design requirement** — no FS/network/clock |
| **JSONLogic / JMESPath** | Restricted operators / query only | Yes / filters | None | Safe by restriction |

**⚠️ Jinja2 sandbox escape history — a documented cat-and-mouse pattern:**

| CVE | Vector | Fixed |
|---|---|---|
| CVE-2016-10745 | `str.format` escape | 2.8.1 |
| CVE-2019-10906 | `str.format_map` escape | 2.10.1 |
| CVE-2024-56326 | stored `format` reference passed to a filter | 3.1.5 |
| CVE-2025-27516 | `\|attr` filter reaches `str.format` | 3.1.6 |

Every fix blocklists a specific path to the same primitive; each has been followed by a new indirect route. Jinja's own docs state **"the sandbox alone is not a solution for perfect security."** Downstream products have shipped RCEs on top of it (NetBox CVE-2026-29514; Nautobot GHSA-p99c-c9qx-34fw).

**This matters specifically because an optimizer mutating fragment text is functionally equivalent to adversarial input from the sandbox's point of view.**

⭐ **Fragment resolution is the decisive criterion.** Jinja2's `PrefixLoader` (routes a namespace prefix to per-prefix sub-loaders) plus `ChoiceLoader` (ordered fallback chain) is **already built prior art for exactly the path-addressed-fragment-store-with-namespacing problem**. CEL and Starlark have no file-loading primitive at all — a *cost* (no free resolver machinery) but also an *advantage* (no accidental filesystem escape through the template language).

Sources: [Jinja API](https://jinja.palletsprojects.com/en/stable/api/) · [Jinja sandbox](https://jinja.palletsprojects.com/en/stable/sandbox/) · [GHSA-cpwx-vrp4-4pq7](https://github.com/advisories/GHSA-cpwx-vrp4-4pq7) · [GHSA-462w-v97r-4m45](https://github.com/advisories/GHSA-462w-v97r-4m45) · [CVE-2024-56326](https://www.cve.news/cve-2024-56326/) · [cel-spec](https://github.com/google/cel-spec) · [Starlark design](https://github.com/bazelbuild/starlark/blob/master/design.md) · [Liquid](https://shopify.github.io/liquid/) · [Mustache manual](https://mustache.github.io/mustache.5.html)

### Decision 2 — Path addressing & namespacing

| System | Model | Lesson |
|---|---|---|
| **Jinja2 loaders** | `FileSystemLoader` (ordered, first-match-wins) / `ChoiceLoader` / `PrefixLoader` (prefix→sub-loader) | Two opposite collision strategies coexist: **search-order** (collisions silently shadowed) vs **namespace isolation** (collisions structurally impossible) |
| **Helm** | Strict 4-level precedence: chart defaults → parent values → `-f` file → `--set`; plus `global:` | A totally-ordered chain **plus an explicit shared-namespace escape hatch** for cross-cutting values |
| **Kustomize** | Bases + overlays + strategic-merge patches | Default is **replace, not deep-merge** (surprising for lists); `replace`/`delete` make intent explicit. Overlay always wins — one-directional, unambiguous |
| **Ansible** | Stacked search path; separate elaborate variable precedence | ⚠️ Ansible's own docs need a dedicated page for precedence — **many override layers is a documented source of user confusion** |
| **OCI / Docker** | Immutable `sha256:` digest + mutable tags; "a digest may have zero, one, or many tags" | ⭐ **The canonical answer to "what does 'the same fragment' mean across versions"** — separate immutable identity from mutable naming |
| **Nix** | Input-addressed (hash of the whole derivation) vs content-addressed (RFC 62, hash of output) | The two are genuinely different tradeoffs: input-addressing pins provenance precisely; content-addressing dedupes but loses that precision |
| **Bazel** | `//pkg:target`, **default `//visibility:private`** with opt-in widening | Opposite instinct from filesystem loaders (open by default) — worth considering whether every fragment should be includable from anywhere |
| **Terraform** | Local paths must start `./`; registry uses `NS/NAME/PROVIDER`; only registry modules accept `version` | Uses **syntax** to disambiguate source kind rather than inferring; deliberately withholds version pinning where it's meaningless |

**Storage model tradeoff:** filesystem-backed gives the best authoring ergonomics and `git diff` reviewability but has no versioning concept of its own; registry-backed adds explicit versioning at the cost of an extra dependency and reduced local diffability; content-addressed gives the strongest reproducibility but hashes aren't human-reviewable. **Note that the mature systems combine them** — OCI keeps both digests and tags; Nix keeps human-readable prefixes alongside hashes. This is likely not an either/or.

### Decision 3 — Composition semantics

**Cycle detection — a clear quality bar and a clear anti-pattern:**

| System | Behavior |
|---|---|
| **Bazel** | ⭐ Prints the actual cycle path (`A → B → C → A`), flags `[self-edge]` distinctly |
| **Terraform** | ⭐ `terraform graph -draw-cycles` highlights cycle edges visually |
| **Nix** | ⚠️ `error: infinite recursion encountered` — runtime detection, needs `--show-trace`; documented ergonomics complaint |
| **GNU Make** | ❌ **Breaks the cycle at an arbitrary point and continues** ("Circular dependency dropped") — silently degrades |
| **Node CommonJS** | Returns a partially-populated module; cycles are accepted, not errors `[UNVERIFIED]` |

**The actionable bar: print the cycle path unconditionally.** Make's silent-degrade is actively dangerous for a tool whose value proposition is deterministic, reviewable composition.

**Determinism** — the Reproducible Builds project names the concrete hazard categories: timestamps, timezones, locales, build paths embedded in output, randomness, archive metadata, version info, uninitialized defaults, volatile inputs, and **stable input/output ordering**. For promptrecipe specifically: iteration order over variable bindings or included-children lists if backed by an unordered map; wall-clock or environment leakage into rendered text; locale-dependent string ops inside the engine. **This is not orthogonal to the host-language choice** — dict/map ordering guarantees differ across Python and JS engines and must be checked explicitly, not assumed.

**Provenance of a rendered prompt:**

| Model | Fit |
|---|---|
| **Source maps** | Positional mapping — "which fragment produced which span of the final prompt." Lightweight; ideal for **authoring/debugging UX** `[UNVERIFIED — spec fetch 404'd]` |
| **CycloneDX / SPDX** | Component identity + exact versions + relationships — maps onto "every fragment with its hash that went into this prompt" |
| **SLSA / in-toto** | ⭐ **Strongest fit for binding an eval result to an exact prompt**: `subject` = rendered prompt hash, `resolvedDependencies` = exact fragment hashes + variable bindings, `builder.id` = renderer version |

These aren't mutually exclusive — a lightweight source-map-style record for human debugging, plus SLSA-style attestation for binding eval results.

Sources: [reproducible-builds.org](https://reproducible-builds.org/docs/) · [SLSA provenance](https://slsa.dev/spec/v1.0/provenance) · [in-toto](https://in-toto.io/) · [CycloneDX](https://cyclonedx.org/) · [Make circular deps](https://lists.gnu.org/archive/html/help-make/2005-03/msg00074.html)

### Decision 4 — Versioning, pinning & provenance

| Lockfile | Pins | Transitive | Drift detection |
|---|---|---|---|
| **npm** `package-lock.json` | Exact version + resolution source + SRI integrity hash | Full `packages` tree | Hidden lockfile checks folder existence, unexpected additions, mtimes |
| **Cargo.lock** | Exact version + git SHA / registry version | Full graph | `Cargo.toml` range vs lock pin; resolved via `cargo update` |
| **Go** `go.sum` + MVS | Checksum per module version; **build list recomputed, not stored** | On-demand traversal | Pseudo-version ancestry, timestamp-matches-revision, commit-ancestry checks |
| **Nix** `flake.lock` | Exact revision **+ `narHash`** (SHA-256 of the NAR-serialized tree) | Isomorphic to the input graph | `narHash` is a true content checksum |
| **Poetry / uv / Bundler** | `[UNVERIFIED — deliberately left as a gap rather than filled with plausible detail]` | — | — |

**⭐ Unison is the strongest analogy** for content-addressing applied to small, frequently-edited units: each *definition* (not package) is identified by a 512-bit SHA3 hash of its syntax tree, with names as separate metadata that don't affect the hash. Its claimed payoff — "dependency conflicts are just not a thing," permanent caching, version-safe serialization.

**The open tension for text fragments:**
- *Content-addressing's case:* a one-word wording change to a fragment isn't a "breaking change" in any conventional sense, so semver ranges fit poorly. A hash sidesteps the question.
- *Semver's case:* pure hashing loses the **intent signal** — "compatible refinement" vs "changes behavior" — which matters when a fragment now requires an additional variable.
- **A third option the lockfile/hash literature doesn't cover:** Confluent Schema Registry's **compatibility modes** (BACKWARD / FORWARD / FULL / NONE). A fragment change that adds a newly-required variable is precisely "backward-incompatible for consumers that don't supply it." This may be the more precise tool than either semver or pure hashing, and is flagged as worth deeper investigation.

Note: **DSPy's own convention is informal** — it expects users to `save()` optimized programs with ad hoc filenames (`extract_v2.json`), with no built-in content-hash or semantic-diff mechanism. The ecosystem has not solved diffability for machine-written prompt artifacts; DSPy punts it to the user.

Sources: [package-lock](https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json) · [Cargo](https://doc.rust-lang.org/cargo/guide/cargo-toml-vs-cargo-lock.html) · [go.sum](https://go.dev/ref/mod#go-sum-files) · [flake.lock](https://nix.dev/manual/nix/latest/command-ref/new-cli/nix3-flake.html) · [Unison](https://www.unison-lang.org/docs/the-big-idea/) · [Confluent schema evolution](https://docs.confluent.io/platform/current/schema-registry/fundamentals/schema-evolution.html)

---

## Synthesis

### Key patterns to follow

| Pattern | Source | Why it applies |
|---|---|---|
| **Loader-chain resolution** (`PrefixLoader` + `ChoiceLoader`) | Jinja2 | Already-built prior art for path-addressed fragments with namespacing and override layering |
| **Assert on `context.prompt`** | promptfoo | Makes recipes *and individual fragments* regression-testable as text, independent of model output |
| **Stub/echo provider** | promptfoo custom providers | Fragment-level content assertions at **zero LLM cost** |
| **Seed-in / read-out via `Signature.instructions`** | DSPy | The one friction-free DSPy write-back path — plain JSON strings both directions |
| **Digest + tag separation** | OCI | The canonical answer to "the same fragment across versions" |
| **`{% render %}` scope isolation, not `{% include %}`** | Liquid | Shopify deprecated scope-sharing inclusion for exactly the maintainability reasons that apply here |
| **Print the cycle path** | Bazel, Terraform | The UX bar; Make's silent drop is the anti-pattern |
| **SLSA `subject` + `resolvedDependencies`** | SLSA / in-toto | Binds an eval result to an exact rendered prompt cryptographically |
| **Single-purpose fragments** | Eugene Yan | Independent support for the fragment premise |

### Constraints identified

1. **DSPy is Python-only** (`>=3.10,<3.15`); **promptfoo is Node-hosted** with documented Python subprocess bridges. One integration will always cross a process boundary.
2. **DSPy self-classifies as Alpha.** Pin the version; treat the `dump_state()` schema as unstable.
3. **promptfoo now sits inside OpenAI's roadmap** (acquired 2026-03-09) and has repositioned toward security/red-teaming.
4. **DSPy has no sub-prompt attribution.** Per-fragment optimization credit is not obtainable today.
5. **promptfoo has no fragment concept.** That unit lives entirely on promptrecipe's side.
6. **`dspy.Assert`/`Suggest` are deprecated** — DSPy's nearest analog to promptrecipe's asserts was removed, not developed.
7. **Every general-purpose template engine has a sandbox-escape history**; every safe-by-design one lacks the expression power the asserts/ifs require.
8. **The project is not a git repository** — foundational for a git-native premise.

### Prior solutions from `docs/solutions/`

**None — the folder does not exist in this project.** Recorded as absent per scope discipline; the search was not widened.

### ⚠️ Open questions for the BRD/PRD

These are surfaced, not resolved. Several need **your** decision.

1. **🔴 What happens when an optimizer rewrites a fragment?** The deepest conflict. Is that diff *noise to collapse* (like `go generate` output, which GitHub's `linguist-generated` hides from PR review) or *the thing a human must read* (like a lockfile version bump, which teams review precisely because drift is security-relevant)? **No prior art maps cleanly**: code-generation conventions assume the generated artifact's *behavior* is what matters and its text doesn't — but for a prompt fragment, **the text IS the behavior.** This likely needs a new convention rather than borrowed precedent.
2. **🔴 Is promptrecipe git-native, platform-managed, or hybrid?** Every source that argued for platform-managed is either an interested vendor or has since exited the category — while OpenAI is actively telling developers to move prompts *back* into git. This determines the storage model, the review model, and who the user is.
3. **🔴 Expressiveness vs safety.** Real asserts/ifs pull toward a general-purpose engine; optimizer-written fragments pull toward restricted-by-design. **No surveyed option satisfies both.** Which requirement yields?
4. **🟡 Does an assert *gate fragment loading* or *validate rendered output*?** BAML's `@assert` does the latter. The stated premise implies the former — which is the actual differentiator, and needs precise definition.
5. **🟡 Fragment identity: content hash, semver, or schema-registry compatibility modes?** The third option is under-explored and may fit text fragments better than either.
6. **🟡 Fragment visibility: open-by-default (filesystem) or private-by-default (Bazel)?** No surveyed system reconciles both traditions.
7. **🟡 Host language.** Python favors DSPy depth; Node favors promptfoo nativity; a core+bindings approach buys both at real release-engineering cost.
8. **🟢 Is "integrates with promptfoo" a value proposition at all**, given four competitors ship more mature native eval? Research says **no** — differentiation must rest on composition, addressing, and assert-gating.
9. **🟢 Does PromptLayer's Jinja gate snippet *resolution* or only rendered text?** `[UNVERIFIED]` — the most important competitive unknown. If the former, gap #2 narrows considerably.

---

## Unverified Claims Register

Every claim below was explicitly **not** backfilled with plausible detail.

| Claim | Status |
|---|---|
| MLflow Prompt Registry specifics | Secondhand only; docs unfetchable |
| Pezzo / Latitude / Mirascope site failures = formal shutdown | **Inferred from dead hosts**, no official statement found |
| BAML has any DSPy-style optimization | No confirming *or* denying documentation |
| PromptLayer Jinja gates snippet resolution vs text | Undocumented |
| Priompt / Ell formally deprecated | No archive banner or announcement; only observed inactivity |
| Prompt-diffing pain point | **Single vendor source** (Agenta) with commercial motive; no neutral corroboration |
| promptfoo `context.config` presence | Declared in types, absent from actual signature — **inconsistency in promptfoo's own source** |
| promptfoo Python subprocess wire mechanics | Behaviorally documented; internals unverified |
| promptfoo `extensions` hook exact field names | Docs summary + one third-party blog; not source-verified |
| `dspy-community/dspy-template-adapter` capability | README description only; source not inspected |
| DSPy backward-compatibility guarantees | **No such policy found** — roadmap checked directly |
| `dspy.teleprompt` → Optimizer rename sequencing | Corroborated by GitHub issue #8632, not a changelog |
| Nunjucks / Handlebars exact loader-hook APIs | Model recollection |
| Source map spec field-level content | Fetch 404'd |
| Bazel Build Event Protocol internals | Not re-fetched |
| Node CommonJS circular-require specifics | Model recollection |
| Poetry / uv / Bundler lockfile mechanics | Deliberate gap |
| DVC / Git LFS / Delta / Iceberg specifics | Fetches 404'd or incomplete |
| Ruff / Polars / tiktoken / pydantic-core binding frameworks (PyO3 etc.) | Strongly likely; not re-confirmed |
| esbuild JS-wrapper invocation mechanism | Not confirmed |

---

## Gate 0 Validation

| Check | Status |
|---|---|
| Research mode documented | ✅ `greenfield`, with rationale |
| All 3 agents returned | ✅ domain+competitive, integration surfaces, technical prior art |
| `research.md` created | ✅ |
| ≥1 file:line reference | ➖ N/A — required for modification/integration modes; codebase verified empty |
| ≥1 external URL | ✅ 80+ dated source URLs |
| `docs/solutions/` searched | ✅ verified absent |
| Tech stack versions documented | ✅ promptfoo 0.122.2 / Node ≥22.22.0; DSPy 3.3.1 / Python >=3.10,<3.15 |
| Synthesis section complete | ✅ patterns, constraints, 9 open questions |
| Domain landscape mapped | ✅ |
| Competitive analysis included | ✅ 17 tools + 4 template engines |
| Technical research covers major decisions | ✅ 5 decision areas |
| Conflicting requirements surfaced, not silently resolved | ✅ 3 flagged 🔴 as blocking BRD/PRD decisions |

**Gate 0 status: PASS**, subject to human approval.
