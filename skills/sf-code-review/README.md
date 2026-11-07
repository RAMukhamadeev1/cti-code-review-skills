<div align="center">

<h1>&#128269; SF Code Review</h1>

<p>
  <strong>An independent code review skill for Claude Code and Codex, focused on Salesforce and the JavaScript/TypeScript, Node.js, NestJS, and Python code around it</strong>
</p>

<p>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-22c55e?style=flat-square" alt="License: MIT"/>
  </a>
  <img src="https://img.shields.io/badge/Claude_Code-Skill-7c3aed?style=flat-square&logo=anthropic&logoColor=white" alt="Claude Code Skill"/>
  <img src="https://img.shields.io/badge/Guides-25-f59e0b?style=flat-square" alt="25 guides"/>
  <img src="https://img.shields.io/badge/Stack-JS%2FTS%20%C2%B7%20Node.js%20%C2%B7%20Python%20%C2%B7%20Salesforce-0ea5e9?style=flat-square" alt="Stack: JS/TS, Node.js, Python, Salesforce"/>
</p>

</div>

> Adapted from [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) (MIT) and refocused on JavaScript/TypeScript, Node.js, NestJS, Python, and Salesforce.

---

## What is this?

**SF Code Review** (`sf-code-review`) is a skill for [Claude Code](https://claude.ai/code) and Codex. It reviews a change in a separate agent with a clean context, so the session that wrote the code can't bias the review:

1. Resolve exactly which change to review, and read what it claims to do.
2. Split a large change by feature and review the slices in parallel, one fresh agent each.
3. Run 16 review angles on every hunk, merge the candidates without dropping any, and sweep for gaps.
4. Drop a finding only when the code refutes it; keep the rest with a confidence.
5. Report in a fixed format: a verdict, the scope, severity-ranked findings with `file:line`, impact, fix, and confidence, open questions, and older problems outside the change.

It covers **JavaScript, TypeScript, Node.js, NestJS, Python, and the Salesforce platform**: Apex, triggers, SOQL/SOSL, Lightning Web Components, Aura, Visualforce, Flows, and metadata.

---

## &#10024; Key Features

- **Independent by design.** The skill runs as a forked subagent (`context: fork`) that never sees the conversation that wrote the code. Where a client can't fork (Codex, a direct read of SKILL.md), the skill hands the review to a fresh agent, or says `independent: no` in the report.
- **Recall first, then proof.** Sixteen angles (line by line, removed behavior, callers and callees, intent and parity, tests, data access, limits, async, metadata, conventions, and more) each surface candidates; none suppresses another. A gap sweep looks only for what the list lacks. Verification drops a candidate only with a quoted guard at `file:line`.
- **Scales with the change.** A small change gets one fresh agent. A large or multi-repo change is split by feature (an entry point with its callees, tests, and metadata), each slice gets its own fresh agent, and a blind verifier checks the blocking and important findings.
- **Checklist-first loading.** Only SKILL.md (~150 lines) loads when the skill activates. Each guide opens with a review checklist that doubles as its table of contents. Claude reads the checklists first and opens only the sections the diff touches. For example, an Apex trigger review starts from about 3.7k tokens of checklists, instead of about 49k tokens for the full guides.
- **An agent's procedure, not a human's.** An eight-step workflow: resolve target → gather context → plan the passes → load guides → find candidates → merge and sweep → verify → report. There are no time budgets, praise quotas, or "ask to split" steps.
- **Fixed output format.** Every review has a verdict, a scope line (with `independent` and `parallel`), numbered findings (severity, `path:line`, the defect stated as fact, impact, fix, confidence), Questions for facts outside the repository, and Outside this change for older problems the change doesn't touch.
- **Focused on the change.** The review reads each hunk's enclosing function or element, not the whole file, then what the angles point to: callers, mirrored code, rule files, object metadata, and the removed code. Findings cover the changed lines; an older problem is a finding, tagged "(pre-existing)", only when the change makes it reachable or worse. Anything a linter or compiler already enforces is skipped, and every absolute rule in the guides lists its legitimate exceptions.
- **Salesforce Review Path.** It detects Salesforce DX changes and routes each file type to its guide. It also traces entry points, counts governor limits at 200-record bulk volume, checks sharing and CRUD/FLS per API version, and looks for automation overlap. That includes the API 67.0 defaults, under which trigger bodies run in user mode too.
- **Static and safe.** The skill pre-approves only read-only `git`, `gh pr`, and `gh issue view` commands and its own analyzer, with no WebFetch. Reviewed code, comments, and PR text are treated as data, never as instructions. Salesforce reviews never deploy, run Apex or tests, or read org data.
- **Robust analyzer.** `scripts/pr-analyzer.py` still reads diffs produced under `color.ui=always`, `diff.mnemonicPrefix`, or `diff.noprefix`. It ignores lockfiles, snapshots, and minified files when it sizes a change or looks for missing tests. It also flags Salesforce risks such as renames, FlowDefinitions, and apiVersion bumps on classes and triggers.

---

## &#127760; Supported Languages & Frameworks

<table>
  <thead>
    <tr>
      <th>Category</th>
      <th>Technology</th>
      <th>Guide</th>
      <th>Lines</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="4"><strong>JavaScript / TypeScript</strong></td>
      <td>JavaScript (shared base for TypeScript, Node.js, NestJS, LWC, Aura)</td>
      <td><code>reference/javascript.md</code></td>
      <td>~500</td>
    </tr>
    <tr>
      <td>TypeScript (5.x to 7.0)</td>
      <td><code>reference/typescript.md</code></td>
      <td>~270</td>
    </tr>
    <tr>
      <td>Node.js 22/24 LTS and 26, Express 4/5</td>
      <td><code>reference/nodejs.md</code></td>
      <td>~520</td>
    </tr>
    <tr>
      <td>NestJS</td>
      <td><code>reference/nestjs.md</code></td>
      <td>~260</td>
    </tr>
    <tr>
      <td rowspan="1"><strong>Python</strong></td>
      <td>Python 3.11–3.14 (typing, asyncio, pytest)</td>
      <td><code>reference/python.md</code></td>
      <td>~160</td>
    </tr>
    <tr>
      <td rowspan="9"><strong>Salesforce</strong></td>
      <td>Platform foundations (load first): limits, security model, API versions, severity</td>
      <td><code>reference/salesforce/platform.md</code></td>
      <td>~510</td>
    </tr>
    <tr>
      <td>Apex classes, async Apex, callouts, tests</td>
      <td><code>reference/salesforce/apex.md</code></td>
      <td>~550</td>
    </tr>
    <tr>
      <td>Apex triggers and handlers</td>
      <td><code>reference/salesforce/apex-triggers.md</code></td>
      <td>~470</td>
    </tr>
    <tr>
      <td>SOQL &amp; SOSL</td>
      <td><code>reference/salesforce/soql-sosl.md</code></td>
      <td>~510</td>
    </tr>
    <tr>
      <td>Lightning Web Components (LWC)</td>
      <td><code>reference/salesforce/lwc.md</code></td>
      <td>~700</td>
    </tr>
    <tr>
      <td>Aura components</td>
      <td><code>reference/salesforce/aura.md</code></td>
      <td>~380</td>
    </tr>
    <tr>
      <td>Visualforce pages and controllers</td>
      <td><code>reference/salesforce/visualforce.md</code></td>
      <td>~440</td>
    </tr>
    <tr>
      <td>Flows</td>
      <td><code>reference/salesforce/flows.md</code></td>
      <td>~510</td>
    </tr>
    <tr>
      <td>Metadata &amp; permissions</td>
      <td><code>reference/salesforce/metadata.md</code></td>
      <td>~520</td>
    </tr>
    <tr>
      <td rowspan="11"><strong>Cross-Cutting</strong></td>
      <td>Architecture Design Review</td>
      <td><code>reference/architecture-review-guide.md</code></td>
      <td>~140</td>
    </tr>
    <tr>
      <td>Performance Review</td>
      <td><code>reference/performance-review-guide.md</code></td>
      <td>~250</td>
    </tr>
    <tr>
      <td>Universal Quality Anti-Patterns</td>
      <td><code>reference/code-quality-universal.md</code></td>
      <td>~170</td>
    </tr>
    <tr>
      <td>Security Review</td>
      <td><code>reference/security-review-guide.md</code></td>
      <td>~270</td>
    </tr>
    <tr>
      <td>Common Bugs Checklist</td>
      <td><code>reference/common-bugs-checklist.md</code></td>
      <td>~180</td>
    </tr>
    <tr>
      <td>Code Review Best Practices (for human reviewers and teams)</td>
      <td><code>reference/code-review-best-practices.md</code></td>
      <td>~120</td>
    </tr>
    <tr>
      <td>N+1 Queries</td>
      <td><code>reference/cross-cutting/n-plus-one-queries.md</code></td>
      <td>~170</td>
    </tr>
    <tr>
      <td>Error Handling Principles</td>
      <td><code>reference/cross-cutting/error-handling-principles.md</code></td>
      <td>~220</td>
    </tr>
    <tr>
      <td>Async &amp; Concurrency Patterns</td>
      <td><code>reference/cross-cutting/async-concurrency-patterns.md</code></td>
      <td>~340</td>
    </tr>
    <tr>
      <td>SQL Injection Prevention</td>
      <td><code>reference/cross-cutting/sql-injection-prevention.md</code></td>
      <td>~140</td>
    </tr>
    <tr>
      <td>XSS Prevention</td>
      <td><code>reference/cross-cutting/xss-prevention.md</code></td>
      <td>~170</td>
    </tr>
  </tbody>
</table>

---

## &#128260; The Review Workflow

```
   (a fresh agent with a clean context runs every step)

1. Resolve the target      PR, branch, commit range, several repos, or uncommitted work
          |
          v
2. Gather context          PR and issue text, commit messages, CLAUDE.md / AGENTS.md, sfdx-project.json
          |
          v
3. Plan the passes         small: review alone · large: one fresh agent per feature slice, in parallel
          |
          v
4. Load guides             each guide's Review Checklist first, then only matching sections
          |
          v
5. Find candidates         16 angles per hunk, up to 8 candidates each; read callers, mirrored code, metadata
          |
          v
6. Merge and sweep         merge duplicates without dropping any; one pass only for what the list lacks
          |
          v
7. Verify                  drop only with a quoted guard at file:line; blind verifier on split reviews
          |
          v
8. Report                  verdict · scope · findings (severity, file:line, impact, fix, confidence)
                           · questions · outside this change
```

Salesforce changes add the **Salesforce Review Path** from `SKILL.md` and the **Salesforce Investigation** from `assets/review-angles.md`:

- load the platform guide first and route each file type to its guide;
- trace entry points and count governor limits at bulk volume;
- check sharing and CRUD/FLS per API version;
- look for automation overlap;
- review tests, metadata, and deployment impact.

---

## &#127991;&#65039; Severity Labels

| Label | Meaning |
|-------|---------|
| &#128308; `blocking` | Must fix before merge: wrong results, data loss, a security hole, or a limit breach at realistic volume |
| &#128993; `important` | Should fix; discuss if you disagree |
| &#128994; `nit` | Optional polish |
| &#128161; `suggestion` | An alternative worth considering, not a defect |

Verdict: any blocking finding → Request changes; otherwise any important finding → Comment; otherwise Approve. Default severities for common Salesforce findings (SOQL in loops, missing CRUD/FLS, XSS escape hatches, recursion guards, permission over-grants, and more) are in [`reference/salesforce/platform.md`](reference/salesforce/platform.md#severity-calibration).

---

## &#128193; Repository Structure

```
cti-code-review-skills/
|
+-- README.md                             # The skills in this repository
+-- LICENSE                               # MIT (upstream notice kept)
+-- docs/                                 # Implementation notes
+-- skills/
    +-- sf-code-review/                   # This skill: install this folder
        +-- SKILL.md                      # Core skill - the forked agent's prompt (~150 lines)
        +-- README.md
        +-- LICENSE                       # A copy, so every install carries it
        +-- index.html                    # Landing page
        |
        +-- reference/                    # On-demand guides, each opening with its Review Checklist
        |   +-- javascript.md             # Shared JS base: semantics, async, modules, DOM, testing
        |   +-- typescript.md             # TypeScript type system, strict mode, typed linting
        |   +-- nodejs.md                 # Node.js runtime, streams, shutdown, Express, security
        |   +-- nestjs.md                 # NestJS DI, guards, interceptors, DTOs, lifecycle
        |   +-- python.md                 # Python 3.11-3.14: flag/don't-flag table, asyncio, pitfalls
        |   +-- architecture-review-guide.md  # Design fit, coupling, dependency direction, Salesforce layering
        |   +-- code-quality-universal.md # Reuse audit, parameter sprawl, TOCTOU, no-op updates
        |   +-- performance-review-guide.md   # Core Web Vitals, queries, memory, caching, governor limits
        |   +-- security-review-guide.md  # Security index for all stacks
        |   +-- common-bugs-checklist.md  # Stack-specific bug patterns
        |   +-- code-review-best-practices.md # For human reviewers and teams: communication, process
        |
        +-- reference/salesforce/         # Salesforce guides (platform.md first)
        |   +-- platform.md               # Limits, transactions, security model, API versions, severity
        |   +-- apex.md                   # Bulkification, sharing/user mode, async, callouts, tests
        |   +-- apex-triggers.md          # Trigger architecture, chunks, recursion, events and CDC
        |   +-- soql-sosl.md              # Injection, access mode, selectivity, pagination
        |   +-- lwc.md                    # Reactivity, LDS/wire, Apex contract, LWS, Jest
        |   +-- aura.md                   # Server actions, events, security, migration to LWC
        |   +-- visualforce.md            # Encoding, CSRF, controller security, view state
        |   +-- flows.md                  # Flow types, entry conditions, bulk safety, fault paths
        |   +-- metadata.md               # Permissions, sharing, schema, credentials, deployment
        |
        +-- reference/cross-cutting/      # Language-agnostic cross-cutting patterns
        |   +-- sql-injection-prevention.md   # Parameterized queries and identifiers: Python, Node.js
        |   +-- xss-prevention.md         # Output encoding, CSP, framework escape hatches
        |   +-- n-plus-one-queries.md     # SQLAlchemy, Prisma, TypeORM, DataLoader, SOQL in loops
        |   +-- error-handling-principles.md  # Python, TypeScript, Apex
        |   +-- async-concurrency-patterns.md # Event loop, cancellation, backpressure, async Apex
        |
        +-- assets/
        |   +-- review-angles.md          # The 16 angles, the gap sweep, the Salesforce Investigation
        |   +-- reviewer-brief.md         # Prompts for the slice reviewer and the blind verifier
        |   +-- review-checklist.md       # The line-by-line pass for any stack
        |   +-- pr-review-template.md     # A complete example review in the output format
        |
        +-- scripts/
            +-- pr-analyzer.py            # PR triage; Salesforce-aware; suggests guides
            +-- test_pr_analyzer.py       # Analyzer tests: parsing, git configs, scoring, report, CLI
            +-- test_skill.py             # SKILL.md contract, briefs, links, license, analyzer agreement
            +-- test_guides.py            # Guide structure, corrected facts, runnable examples
```

---

## &#128640; Installation

**Install with `npx skills` (Claude Code, Codex, Cursor, OpenCode, and other agents):**

```bash
npx skills add RAMukhamadeev1/cti-code-review-skills --skill sf-code-review
```

**Or clone the repository and link the skill folder:**

```bash
git clone https://github.com/RAMukhamadeev1/cti-code-review-skills.git ~/src/cti-code-review-skills

# Claude Code
ln -s ~/src/cti-code-review-skills/skills/sf-code-review ~/.claude/skills/sf-code-review

# Codex
ln -s ~/src/cti-code-review-skills/skills/sf-code-review ~/.agents/skills/sf-code-review
```

With a custom Claude Code config folder (`CLAUDE_CONFIG_DIR`), link the skill into its `skills/` folder too. A `git pull` updates every link at once.

**Or add to an existing plugin:**

```bash
cp -r skills/sf-code-review ~/.claude/plugins/your-plugin/skills/
```

---

## &#128161; Usage

Once installed, ask for a review in your session:

```
Use sf-code-review to review this PR
```

Or run it as `/sf-code-review`, optionally with a target: a PR number, a branch, a commit range `base...head`, or `repo=<path>:<base>...<head>` pairs for a change across several repositories, plus an issue key or a spec path. In Claude Code the review runs in a forked agent and its report comes back to your conversation; relay it as it is.

**Example prompts:**

| Prompt | What happens |
|--------|-------------|
| `Use sf-code-review to review PR 42` | `gh pr view` / `gh pr diff`, the linked issue, then the matching guides and the output format |
| `Review my uncommitted changes` | `git diff HEAD` plus untracked files from `git status --porcelain` |
| `/sf-code-review repo=~/src/crm:main...feature/orders repo=~/src/crm-eu:main...feature/orders` | one review across two repositories, split by feature, one fresh agent per slice |
| `Review this Apex trigger` | platform.md + apex-triggers.md + apex.md checklists: one trigger per object, 200-record chunks, recursion, user mode at API 67.0+ |
| `Review this Lightning Web Component` | lwc.md + javascript.md: reactivity, LDS/wire, the Apex contract, XSS, cleanup |
| `Security review of this Visualforce page` | visualforce.md + platform.md: encoding, CSRF, controller sharing, open redirects |
| `Review this flow` | flows.md: entry conditions, loops with data elements, fault paths, run context |
| `Review this Node.js service` | javascript.md + nodejs.md: event loop, async errors, streams, graceful shutdown, Express |
| `Review this NestJS module` | nestjs.md + typescript.md + javascript.md: DI, guards, DTO validation, lifecycle |
| `Review this Python module` | python.md: version-aware flag/don't-flag rules, asyncio, pitfalls |

A review across several repositories reads files outside the working directory: start Claude Code with `--add-dir <path>` for each other repository, or approve the reads when asked.

For large diffs, the bundled analyzer triages size and risk and prints which guides to load (run it from the skill folder):

```bash
git diff --no-color --default-prefix main...HEAD | python3 scripts/pr-analyzer.py
```

---

## &#128300; Highlights

<details>
<summary><strong>Salesforce</strong></summary>

- **Static review only**: never deploy, run Apex or tests, or query an org; ask the author or CI for org evidence
- **Platform foundations**: governor limits per transaction, records per entry point, order of execution, API-version rules
- **API 67.0 (Summer '26)**: user mode by default, also for SOQL/DML in trigger bodies; `with sharing` by default unless a parent class declares a mode; `WITH SECURITY_ENFORCED` removed; review each file against its own `apiVersion`
- **Apex**: bulkification, sharing and user-mode data access, partial success, async Apex, Named Credential callouts, meaningful tests
- **Triggers**: one trigger per object, logic in handlers, recursion control that survives 200-record chunks, one enqueue per async transaction
- **SOQL/SOSL**: injection, access mode, selectivity and large data volumes, pagination
- **LWC & Aura**: the Apex contract (`cacheable`, `AuraHandledException`), refresh after writes, Lightning Web Security, XSS escape hatches, guest reachability
- **Visualforce**: context-specific encoding, CSRF on page load, open redirects, view state
- **Flows & metadata**: entry conditions, fault paths, run context (`UserMode` at API 68.0), FlowDefinition pitfalls, FLS, sharing, credentials, destructive changes

</details>

<details>
<summary><strong>JavaScript &amp; TypeScript</strong></summary>

- Strict equality, `??` vs `||`, number and date pitfalls, mutation vs copying, prototype pollution
- Promises: floating promises, combinators, cancellation with `AbortSignal`, stale-response races
- Modules, DOM safety, listener and timer cleanup, testing with Vitest/Jest/`node:test`
- TypeScript: `unknown` over `any`, narrowing, strict mode, typed ESLint rules, TS 6/7 upgrade notes

</details>

<details>
<summary><strong>Node.js &amp; NestJS</strong></summary>

- Event loop and worker threads, unhandled rejections, streams with `pipeline()` and backpressure
- Graceful shutdown, configuration validation, Express 4 vs 5 async errors, server timeouts
- Node security: path traversal, open redirects, body limits, constant-time comparison, supply chain
- NestJS: DTO validation (`@ValidateNested` + `@Type`), guards vs interceptors, exception filters, shutdown hooks

</details>

<details>
<summary><strong>Python</strong></summary>

- A 3.11–3.14 table of what to flag and what not to flag
- asyncio: TaskGroup and `except*`, `gather` semantics, cancellation, timeouts, one session per task
- Exceptions: specific catches, `raise ... from`, picklable exception classes
- About 30 one-line pitfalls with the Ruff rule that catches each

</details>

---

## &#129309; Contributing

Contributions are welcome. Keep new content consistent with the existing guides:

- Start every guide with its title, a short scope line, and `## Review Checklist` within the first 40 lines. Group the checklist items under `### Group → [Section](#anchor)` links so the checklist doubles as the table of contents.
- Then write `##` topics and `###` rules: a short lead-in, then a `❌` / `✅` code block. Every rule states its legitimate exceptions.
- Keep each guide under 45,000 characters and its `## References` list to at most five links.
- Use only the four severity labels. Salesforce defaults live in the platform guide's severity table.
- Give each topic one owner file and link to it from the others instead of repeating it. Express searches as Grep patterns, not shell pipelines.
- Register new guides in `SKILL.md`, this README, and `index.html`. Review angles live in `assets/review-angles.md`; a new angle also goes on the `Angles:` line in `SKILL.md`.
- Write in English.
- Keep `SKILL.md` under 15,000 characters: after auto-compaction Claude Code re-attaches only the first 5,000 tokens of a skill.
- Run the tests from the repository root (standard library only): `python3 -m unittest discover -s skills/sf-code-review/scripts`. They check every link and anchor, the SKILL.md contract, the guide structure, corrected facts, and the runnable examples (the Node.js example test needs `node`). They also check that `SKILL.md` and the analyzer agree.
- Keep `scripts/pr-analyzer.py` at 100% line and branch coverage: `python3 -m coverage run -m unittest discover -s skills/sf-code-review/scripts && python3 -m coverage report` (needs `pip install coverage`; settings in `.coveragerc`).

---

## &#128196; License

MIT. See [LICENSE](LICENSE).

- Copyright (c) 2025 [awesome-skills](https://github.com/awesome-skills), the original project
- Copyright (c) 2026 Ruslan Mukhamadeev, this adaptation

---

<div align="center">
  Made with &#10084;&#65039; for developers who care about code quality
</div>
