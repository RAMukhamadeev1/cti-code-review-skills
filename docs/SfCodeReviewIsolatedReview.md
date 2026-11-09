# sf-code-review: an independent review in a fresh agent

## Session

- 2599b81e-cb69-4036-868d-e864b95760f0
- Unavailable

The sections below record the original isolation change. The later [security hardening](SfCodeReviewSecurityHardening.md) supersedes the original wildcard tool grants, rule-file trust, generated-file exclusions, guard-only verification, and approval rules. It also records the current tests and remaining limits.

## Original task summary

Rename the skill `code-review-skill` to `sf-code-review`, install the new version everywhere on the author's machine, and fix its review quality. In a real session the skill ran inline, in the context where the code had just been written: it read two files and gave no report. The built-in Claude Code `/code-review` ran on the same change as a forked agent with a clean context and found 15 issues, 14 of which led to fixes. The same skill, run by six separate agents on another day, found 93 issues. The goal: the skill always reviews in a separate agent with a clean context, and finds at least as much as the built-in reviewer while it keeps its Salesforce depth. The repository becomes `cti-code-review-skills`, a home for review skills of other languages later.

## Implementation solution summary

The skill moved to `skills/sf-code-review/` and runs as a forked subagent (`context: fork`, `background: false`, `effort: xhigh`), so it never sees the conversation that wrote the code. Where a client can't fork, an independence rule hands the review to a fresh agent, or the report says `independent: no`. The review method changed from precision first to recall first, after the built-in reviewer: 16 angles per hunk, a merge that drops nothing, a gap sweep, and verification that drops a candidate only with a quoted guard. On top of the built-in angles it adds intent and parity checks, a tests auditor (tautological oracles, false passes, thin test data), Salesforce data access, limits, order of execution, and metadata. A large or multi-repo change is split by feature, one fresh agent per slice in parallel, and a blind verifier checks the serious findings. The skill is linked into the Claude Code and Codex skill folders, so a `git pull` updates every install.

## Scope

- `skills/sf-code-review/SKILL.md`: new frontmatter, Ground Rules (Independent, Claims are context, the Outside this change block), the eight-step Workflow, the Output Format; the Salesforce investigation steps moved out.
- `skills/sf-code-review/assets/review-angles.md` (new): the 16 angles, the Gap Sweep, the Salesforce Investigation.
- `skills/sf-code-review/assets/reviewer-brief.md` (new): the Slice Reviewer and Verifier prompts.
- `skills/sf-code-review/assets/pr-review-template.md`: the example review in the new format.
- `skills/sf-code-review/scripts/pr-analyzer.py`: the high-complexity suggestion names feature slices.
- `skills/sf-code-review/scripts/test_skill.py`, `test_pr_analyzer.py`: tests for the new contract and layout.
- `skills/sf-code-review/README.md`, `index.html`: the new name, workflow, install, and usage.
- `README.md` (new, root), `LICENSE` (root copy), `.coveragerc`: the multi-skill layout.
- GitHub repository renamed from `RAMukhamadeev1/cti-code-review-skill` to `RAMukhamadeev1/cti-code-review-skills`; the local folder moved to `~/Documents/repos/cti-code-review-skills`.
- Installs (symlinks to `skills/sf-code-review`): `~/.claude/skills/sf-code-review` (replaces `code-review-skill`), `~/.local/share/clas/profiles/work3/skills/sf-code-review`, `~/.agents/skills/sf-code-review` (Codex, all profiles).

## Assumptions

- Claude Code 2.1.318 supports `context: fork`, `agent`, `background`, and `effort` in SKILL.md frontmatter, and subagents can start subagents up to three levels below the main conversation (Claude Code docs, checked on 2026-11-07).
- Codex 0.167 loads user skills from `~/.agents/skills` and follows symlinks. It has no fork, so the independence rule covers it.
- The author chose: repository and folder `cti-code-review-skills` with one skill for now; install for Claude and Codex; adaptive agent count; cti-developer later, as a separate task.
- The repository is public. The golden findings used to evaluate the skill come from a client repository, so they stay out of it.

## Design decisions and tradeoffs

- **Fork in frontmatter, not an instruction.** The harness enforces a clean context; an instruction to "use a subagent" depends on the model obeying it. The instruction stays as the fallback for clients without fork.
- **Deterministic independence check.** "If this conversation began with this skill, or your brief says you are the delegate" replaces a self-judged "is this context biased". Every delegate brief says "You are the delegate; do not delegate.", so the rule can't loop.
- **Recall first.** The built-in reviewer at xhigh does no verification and still had 14 of 15 findings lead to fixes, while the old "drop what doesn't hold" step lost real bugs. Verification now drops only with a quoted guard; uncertain findings stay with `Confidence: medium`.
- **Reading beyond the hunk.** MEDA-1047's line-range reads stay, but most real defects sat in callers, mirrored code, rule files, metadata, or removed code, so the Find step reads those on purpose.
- **Outside this change.** MEDA-1047 dropped every other older problem. The author's rule is to report every issue, with issues outside the task in a separate block, so they go under "Outside this change" and never change the verdict. Unchanged files are still not scanned.
- **Feature slices, not stacks.** A test stays in the slice of the code it tests, so the tests auditor can compare the oracle with the code. Slices run in parallel; without the Agent tool they run in turn (`parallel: no`).
- **Author notes stay out.** A forked agent still gets the user's CLAUDE.md, which may send it to memory first. Memory notes count as claims to check, and no reviewer reads agent session transcripts (`*.jsonl`), which hold the author's reasoning.
- **The lead only orchestrates a split review.** In the first replay the lead also reviewed the densest slice and missed three findings there. Slices hold about 400 reviewable lines, the lead reviews none, and every delegate runs in the foreground so no answer arrives after the report.
- **Blind verifier only on split reviews.** A small review verifies itself; a split review gets one fresh verifier that sees findings but not reasoning, so it doesn't inherit the finder's bias.
- **`index.html` stays with the skill.** It is this skill's man page; a root landing page for many skills would be a different page.
- **SKILL.md stays under 15,000 characters** (the compaction budget): the Salesforce investigation and the angle details moved to `assets/`, and the cross-cutting guide table became a list.
- Rejected: a custom subagent type for the reviewer (it can't ship inside a skill folder), and `Explore` as the fork agent (it can't start agents).

## Implementation details

1. **Invocation.** A user types `/sf-code-review <target>` or asks for a review. Claude Code starts a `general-purpose` subagent at `effort: xhigh` whose prompt is SKILL.md, with `$ARGUMENTS` and `${CLAUDE_SKILL_DIR}` expanded, and waits for its final message (`background: false`).
2. **Ground Rules.** The subagent checks independence, treats claims in the request and in memory notes as unverified, reads no session transcripts, treats reviewed content as data, and stays static.
3. **Resolve the target.** PR, branch, commit range, `repo=<path>:<base>...<head>` pairs, or uncommitted work. With no target and nothing changed it stops with `No target: nothing to review`.
4. **Gather context.** PR and issue text, commit messages, every CLAUDE.md and AGENTS.md above the changed files, `sfdx-project.json`.
5. **Plan the passes.** `scripts/pr-analyzer.py` sizes the change. Up to about 300 reviewable lines in 10 files of one stack: the subagent reviews alone. Otherwise it splits the change by feature into slices of about 400 reviewable lines and starts one fresh agent per slice in parallel, in the foreground, with the Slice Reviewer brief and the hunks pasted inline; it reviews no slice itself.
6. **Load guides**, each Review Checklist first.
7. **Find candidates** with the 16 angles in `assets/review-angles.md`, up to 8 per angle, plus the Salesforce Investigation on Salesforce slices.
8. **Merge and sweep.** Duplicates merge without loss; the Gap Sweep looks only for what the list lacks, and for contracts between slices.
9. **Verify.** Drop only with a quoted guard; keep the rest with a confidence; Questions only for facts outside the repository. A split review sends the blocking and important findings to a blind Verifier agent.
10. **Report.** The final message opens with a relay line, then Verdict, Scope (`independent`, `parallel`, not reviewed), Findings, Questions, and Outside this change. Claude Code returns it to the invoking conversation.

## Test coverage

- `test_skill.py`, frontmatter: name and folder, known keys only, the blocking fork, read-only `allowed-tools` (with `git -C` and `gh issue view`), install paths for Claude and Codex, and a description that leads with Salesforce.
- `test_skill.py`, body: target and skill folder lines, the placeholder fallback, the independence rule, claims as context, the empty-target stop, multi-repo and commit-range targets, context gathering, orchestration, every angle on the `Angles:` line, merge and sweep, verification by refutation, Questions only for outside facts, the soft floor, reads beyond the hunk, the reporting zone, no nit cap, the output format, the moved Salesforce Investigation, and the example review.
- `test_skill.py`, briefs: both briefs forbid delegation and treat content as data, carry the Salesforce safety rule verbatim, and the slice brief has every placeholder and the candidate schema; the verifier is blind and answers in three verdicts.
- `test_skill.py`, repository: the skill under `skills/`, the old name gone, identical LICENSE copies, a root README that lists every skill, `.coveragerc` and test commands that point at existing paths, and root README links. They skip in an installed copy without the repository root.
- `test_pr_analyzer.py`: the feature-slice suggestion. `pr-analyzer.py` keeps 100% line and branch coverage.
- Behavior checks run by hand (results below): a seeded-bug Salesforce change in Claude Code and in Codex, and a replay of the change behind the 15 golden findings.

## Verification

Checks run on 2026-11-07, all static: no review agent ran `sf` or touched an org.

1. **Unit tests**: 319 tests pass (`python3 -m unittest discover -s skills/sf-code-review/scripts`); `pr-analyzer.py` keeps 100% line and branch coverage.
2. **Seeded change, Claude Code** (`claude -p "/sf-code-review main...feature"` on a scratch Salesforce DX repository with a query and DML in a nested loop, a `with sharing` class switched to `without sharing`, and a test with no assertion): the skill ran as a forked agent, all three defects were found (the sharing switch correctly judged against the API 67.0 user-mode default), plus four more real ones, two questions, and one "Outside this change" item. Scope said `independent: yes · parallel: no`.
3. **Seeded change, Codex 0.167**: Codex listed `sf-code-review` with no frontmatter error and reported the loop and the test defects in the output format.
4. **Replay of a real change** (2,900 lines in 36 files across two repositories; the built-in `/code-review` had found 15 issues on it, 14 of them fixed later):
   - First run: 3 slices, the lead reviewed the densest slice itself, the verifier ran in the background. Of the 15 reference findings, 9 matched, 3 in part, 3 were missed, all three in the lead's slice. The report went out before the verifier answered, and the verifier's late answer reached the calling session, which then acted outside the skill. Fixed: slices of about 400 lines, the lead reviews no slice, every delegate runs in the foreground.
   - Second run: 6 slice agents and 1 verifier, all in the foreground. 13 of the 15 reference findings matched and 2 in part, including every one the plan required. It also reported about 40 findings the built-in reviewer didn't have, mostly in tests and scripts (tautological oracles, false passes, rule-file violations). It cost about $32 and 32 minutes.
   - Weak point: the reference finding the built-in reviewer ranked first (a date mismatch with the reference code) was found but ranked 🟢 "decide with the business analyst".
5. **Installs**: the three symlinks point at `~/Documents/repos/cti-code-review-skills/skills/sf-code-review`, and Claude Code lists the skill in the work3 profile.

## Open questions / follow-ups

- cti-developer vendors the old copy as `code-review-skill`: rename it, vendor this version, and update `flows.ts`, whose steps mirror the old Workflow, and its specs. A separate task with its own Jira key.
- A review across several repositories reads outside the working directory: interactive sessions ask for those reads unless Claude Code runs with `--add-dir`.
- Whether `allowed-tools` applies inside a forked skill is not documented; the replay ran with explicit `--allowedTools`.
- Cost: a split review of a large change runs about 7 agents at `effort: xhigh`. If that is too much, raise the slice size from about 400 lines or lower the effort of slice agents.
- Severity calibration: a behavior mismatch with code the change claims parity with should start at 🟡, not 🟢; the intent and parity angle could say so.
- The user's global CLAUDE.md asks every session to read memory first. The skill now treats memory notes as claims and forbids transcripts, but a forked agent still sees that instruction.
