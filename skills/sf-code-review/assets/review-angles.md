# Review Angles

Run every angle on every hunk of your slice, in turn, in this context. Each angle surfaces up to 8 candidates. One angle never suppresses another: when two angles flag the same line for different reasons, record both. Don't drop a candidate because you are unsure; the Verify step decides.

A candidate has a `file:line` (head side), the defect in one sentence, a failure scenario (the input or state that triggers it → the wrong result, crash, or cost), the angle, a severity, and a confidence. Cleanup angles state the concrete cost instead of a crash: what is duplicated, wasted, or harder to change, or which rule is broken. When the output must be cut, correctness findings outrank cleanup.

## Correctness

### Line by line

Read every hunk line by line, then the enclosing function. A bug in an unchanged line of a touched function counts when the change makes it reachable or worse ("(pre-existing)"); any other one goes under "Outside this change". For each line ask what input, state, timing, or platform makes it wrong: inverted or wrong conditions, off-by-one, null dereference, a missing `await`, a falsy zero, a copy-paste with the wrong variable, an error swallowed in a catch, an unescaped regex character, a date compared in the wrong time zone.

### Removed behavior

For every line the diff deletes or replaces, name the invariant it enforced, read the base side (`git show <base>:<path>`), and find where the new code enforces it again. If you can't find it, that's a candidate: a removed guard, a dropped error path, a narrowed validation, a deleted test that covered a real case, a moved block that lost its anchor.

### Callers and callees

For each changed function, Grep its callers and check every call site against the change: a new precondition, a changed return shape or `null`, a new exception, an ordering or timing dependency, a changed default. Check the callees too: does a parallel change in the same diff make a call unsafe? In Salesforce, include every entry point from the [Salesforce Investigation](#salesforce-investigation).

### Stack pitfalls

The classic traps of the changed language, from the loaded guides' checklists. For example: JavaScript `==` coercion, `||` against `??`, closures over loop variables; Python mutable defaults and late-binding closures; Apex queries and DML in loops, `Map.get` on a missing key, `Date` against `Datetime`, a record list that only 200-record chunks expose; SOQL without a bind; LWC reactivity that misses a nested mutation.

### Wrappers

When the change adds or edits a type that wraps another (cache, proxy, decorator, adapter, selector, service facade): every method routes to the wrapped instance, not back through a registry, global, or static that re-enters the wrapper; every method the callers use is forwarded; the wrapper keeps the wrapped contract (sharing mode, exceptions, ordering).

### Intent and parity

Compare the change with what it claims: the PR description, the linked issue, commit messages, test case names, and comments. Flag a stated requirement the code doesn't meet, a case it handles differently from the spec, and an assumption the issue contradicts. When the change mirrors other code or claims parity with it ("like the form", "same as the trigger", a copied rule), read that code and compare the logic line by line: the date it uses, the record types and order types it covers, its filters, its sharing context, its defaults. A difference is a candidate unless the change explains it.

## Tests

### Tests

- Changed behavior that no test exercises, and a requirement or test case named in the issue that no test covers.
- A tautological oracle: the expected value is computed by the code under test, or by the same query or helper, so the test passes whatever the code does.
- A false pass: an assertion on an in-memory list instead of what the database holds, a query that isn't filtered by the run, user, or record it means, a `LIMIT 1` that picks an arbitrary record, an assertion that can't fail, a script that prints PASS without checking.
- Test data that can't show the bug: one parent for "many accounts", two accounts for "200 orders", dates that fall on a weekend or a holiday, data built as an admin when the code runs as a restricted user.
- Setup and teardown asymmetry, shared state between tests, order dependence, and time dependence (`today` without a fixed clock).
- Salesforce: bulk tests with 201+ records, negative paths, `System.runAs` with a least-privilege user, `Test.startTest`/`Test.stopTest` around async work, callout mocks, `Assert` calls with messages, and no `SeeAllData=true`.

## Platform

### Data access and security

Authorization on every new path, injection (SQL, SOQL, shell, path, HTML), secrets in code or logs, trusted client-supplied Ids or field names. In Salesforce: the sharing context of every query and DML (keyword, parent class, apiVersion default), the access mode (user mode, `stripInaccessible`, or a justified system-mode exception), and a class whose result depends on record access that the user may not have (`with sharing` on a Private object, while the rest of the flow reads in system mode). Read the object's OWD and the sharing rules in the repo before you call it safe.

### Limits at volume

Walk each entry point at realistic volume and show the math: queries, DML, callouts, and enqueues per chunk and per transaction, heap and CPU for large collections, nested loops over two collections (O(n × m)), and work repeated per record that could run once per batch. Include downstream triggers, flows, and roll-ups.

### Async and order of execution

Races, shared mutable state across chunks or slices (an instance field reused between calls), lost updates, recursion, retries that aren't idempotent, and order of execution: other triggers, flows, and validation rules on the same object, async work that reads data the transaction hasn't committed, and mixed DML.

### Metadata and deployment

Permissions and FLS for new fields, over-grants, OWD and sharing changes, schema changes against existing data, validation rules against integrations, destructive changes and renames (the old component stays in the org), flow status and FlowDefinition, credentials and endpoints, `.forceignore` and manifests, apiVersion bumps across 67.0, and configuration defaults the change flips.

## Cleanup

### Reuse

New code that re-implements something the codebase already has. Grep shared and utility modules and the files next to the change, and name the existing helper to call instead. A business rule that now exists in a third copy is 🟡: the copies drift.

### Simplification

Complexity the change adds without need: redundant or derivable state, copy-paste with small variations, deep nesting, dead code left behind. Name the simpler form that does the same job.

### Efficiency

Wasted work the change adds: repeated computation or I/O, queries that run even when their result isn't used, independent steps run one after another, blocking work on a hot path or at startup, a long-lived closure that keeps a large scope alive. Name the cheaper alternative.

### Altitude

Does the change fix the root cause at the right depth, or patch a symptom? A special case layered on shared code is a sign the fix sits too high; name the general change to the underlying mechanism.

### Conventions

Read every CLAUDE.md, CLAUDE.local.md, and AGENTS.md from the repository root down to each changed file (a file in a directory governs only what is under it). Flag a violation only when you can quote the exact rule and the exact line that breaks it, and name the rule file in the finding. No style preferences, no "spirit of the doc".

## Gap Sweep

After the merge, make one more pass as a fresh reviewer who has the list. Re-read the hunks and their enclosing functions and look only for defects the list doesn't have; don't re-confirm what is there. Zero new findings is a valid result; don't pad. Look where the first pass tends to miss:

- Moved or extracted code that dropped a guard, a filter, or an anchor.
- Second-tier traps: a default evaluated once, non-deterministic ordering (`Set`, `Map` iteration, `hash()`), a lock or transaction scope that shrank, a predicate with a side effect.
- Setup and teardown asymmetry in tests, and test data with a single parent.
- Configuration defaults flipped, and feature flags whose off state now breaks.
- Salesforce: a field queried but not covered by FLS checks or permission metadata, a date that lands on a weekend or in another time zone, a record type or order type the change doesn't handle, an apiVersion that crosses 67.0.

On a split review, also check the contracts between slices: LWC ↔ Apex (`@AuraEnabled` signatures, cacheable, errors), trigger ↔ handler, flow ↔ invocable, script or test ↔ the class it calls, and shared constants and settings.

## Salesforce Investigation

Run these on every Salesforce slice, the way a Salesforce reviewer would:

1. **Context.** Read `sfdx-project.json` (`sourceApiVersion`, namespace) and each changed file's `<apiVersion>`, base and head. At API 67.0+ a class without a sharing keyword runs `with sharing` unless a parent class declares a mode, and database operations run in user mode by default, in trigger bodies too (the trigger context itself is always `without sharing`). A namespace means a managed package, where released `global` members are permanent.
2. **Entry points.** Grep for how a transaction reaches each changed method: `@salesforce/apex/` imports (also namespaced `ns.Class.method`), `controller="Class"` in Aura, `<actionName>Class</actionName>` in flows, `controller=`/`extensions=` in Visualforce, trigger handlers, `System.enqueueJob(new Class`, `Database.executeBatch(new Class`, `System.schedule(`, `@RestResource(`, platform-event triggers, and the class name as a string (`Type.forName`, handler registrations in `customMetadata/`). Note sync or async, the running user (end user, guest, Automated Process, integration), and records per invocation.
3. **Limits at bulk volume.** Walk each entry point with 200 records per trigger chunk (up to 2,000 for platform-event triggers and Batch scopes); count SOQL, DML, callouts, and enqueues per chunk and per transaction, including downstream triggers, flows, and roll-ups.
4. **Data access.** For every query and DML: the sharing context (keyword, parent class, apiVersion default), the access mode (user mode, `stripInaccessible`, or a justified system-mode exception), trusted client-supplied Ids or field names, and bind variables in dynamic SOQL.
5. **UI layer.** XSS escape hatches, Apex error handling in the client, cache refresh after writes, `isExposed`/`targets`. An Experience Cloud target makes Apex guest-reachable only when a guest profile or permission set grants the class (`classAccesses`); if that metadata isn't in the repo, ask under Questions.
6. **Automation overlap.** Other triggers, record-triggered flows (`<object>X</object>` in `flows/`), and validation rules on the same object; order of execution, recursion, duplicated logic.
7. **Tests.** Bulk tests (201+ records), negative paths, `System.runAs` with a least-privilege user, `Test.startTest`/`Test.stopTest` around async work, callout mocks, and `Assert` calls with messages; no `SeeAllData=true`.
8. **Metadata and deployment.** FLS for new fields, permission over-grants, OWD and sharing changes, schema changes against existing data, validation rules against integrations, destructive changes and renames (the old component stays in the org), flow `<status>` and FlowDefinition, credentials and endpoints, `.forceignore` and manifests, and apiVersion bumps across 67.0.
