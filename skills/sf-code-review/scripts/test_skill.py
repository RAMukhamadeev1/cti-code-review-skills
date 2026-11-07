#!/usr/bin/env python3
"""Tests for the skill package itself (stdlib unittest, no extra deps).

Checks the SKILL.md frontmatter, every local link and heading anchor in the
Markdown files and index.html, the guide registration rule from the README,
and that SKILL.md and scripts/pr-analyzer.py agree: the guides the analyzer
names exist and are linked from SKILL.md, and the Salesforce files SKILL.md
routes are flagged by the analyzer and get the guides SKILL.md lists.
"""

import configparser
import functools
import html
import importlib.util
import os
import re
import tempfile
import unicodedata
import unittest
from collections import Counter
from urllib.parse import unquote

_HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(_HERE)
SKILL_NAME = 'sf-code-review'
SKILL_MD = os.path.join(SKILL_ROOT, 'SKILL.md')
README = os.path.join(SKILL_ROOT, 'README.md')
INDEX_HTML = os.path.join(SKILL_ROOT, 'index.html')
LICENSE = os.path.join(SKILL_ROOT, 'LICENSE')
PR_TEMPLATE = os.path.join(SKILL_ROOT, 'assets', 'pr-review-template.md')
ANGLES = os.path.join(SKILL_ROOT, 'assets', 'review-angles.md')
BRIEF = os.path.join(SKILL_ROOT, 'assets', 'reviewer-brief.md')
REPOSITORY = 'RAMukhamadeev1/cti-code-review-skills'

# The repository holds one folder per skill under skills/. An installed copy of
# the skill has no repository root, so the tests that need it are skipped there.
_SKILLS_DIR = os.path.dirname(SKILL_ROOT)
REPO_ROOT = (os.path.dirname(_SKILLS_DIR)
             if os.path.basename(_SKILLS_DIR) == 'skills'
             and os.path.isfile(os.path.join(os.path.dirname(_SKILLS_DIR), 'README.md'))
             else None)
needs_repo_root = unittest.skipUnless(REPO_ROOT, 'runs only in the repository checkout')

# Frontmatter keys Claude Code documents for SKILL.md that this skill uses
KNOWN_FRONTMATTER_KEYS = frozenset({
    'name', 'description', 'argument-hint', 'allowed-tools',
    'context', 'agent', 'background', 'effort',
})

# The old name lives on only in the upstream project's URL
_OLD_NAME_RE = re.compile(r'(?<!awesome-skills/)code-review-skill(?!s)')

# After auto-compaction Claude Code re-attaches only the first 5,000 tokens of a
# skill; at roughly 3.5 characters per token this keeps all of SKILL.md.
SKILL_MD_MAX_CHARS = 15_000

# The script has a hyphen in its name, so load it by path.
_spec = importlib.util.spec_from_file_location(
    'pr_analyzer', os.path.join(_HERE, 'pr-analyzer.py')
)
pr_analyzer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr_analyzer)

# Default Salesforce DX package directory
SF = 'force-app/main/default/'


@functools.lru_cache(maxsize=None)
def read(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def rel(path):
    """Path relative to the skill root, with forward slashes."""
    return os.path.relpath(path, SKILL_ROOT).replace(os.sep, '/')


def skill_files(*extensions):
    """Files of the skill package with the given extensions (no dot or cache dirs)."""
    found = []
    for directory, subdirs, names in os.walk(SKILL_ROOT):
        subdirs[:] = sorted(d for d in subdirs if not d.startswith('.') and d != '__pycache__')
        found += [os.path.join(directory, n) for n in sorted(names) if n.endswith(extensions)]
    return found


def file_stats(filename):
    """Build FileStats the way parse_diff does (detected language/test/config)."""
    return pr_analyzer.FileStats(
        filename=filename,
        additions=10,
        is_test=pr_analyzer.is_test_file(filename),
        is_config=pr_analyzer.is_config_file(filename),
        is_generated=pr_analyzer.is_generated_file(filename),
        language=pr_analyzer.detect_language(filename),
    )


# ═══════════════════════════════════════════════════════════════
# Helpers: frontmatter, links, and anchors
# ═══════════════════════════════════════════════════════════════

def parse_frontmatter(text):
    """Parse the YAML subset SKILL.md uses: 'key: value', 'key: |' blocks, '- item' lists."""
    lines = text.split('\n')
    if lines[0] != '---' or '---' not in lines[1:]:
        raise ValueError('SKILL.md must open with a --- delimited frontmatter block')
    fields, key, in_block = {}, None, False
    for line in lines[1:lines.index('---', 1)]:
        if isinstance(fields.get(key), list) and line.startswith('  - '):
            fields[key].append(line[4:])
        elif in_block and (line.startswith('  ') or not line.strip()):
            fields[key] += line[2:] + '\n'
        elif line.strip():
            match = re.fullmatch(r'([a-z][a-z-]*):(?: (.+))?', line)
            if not match:
                raise ValueError(f'unsupported frontmatter line: {line!r}')
            key, scalar = match.groups()
            in_block = scalar == '|'
            fields[key] = [] if scalar is None else '' if in_block else scalar
    return fields


_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
_INLINE_CODE_RE = re.compile(r'(`+).+?\1')
_MD_LINK_RE = re.compile(
    r'\[(?:[^\[\]]|\[[^\]]*\])*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)')
_HTML_LINK_RE = re.compile(r'\b(?:href|src)="([^"]*)"')
_HTML_ID_RE = re.compile(r'<[^>]*\b(?:id|name)="([^"]+)"')
_HEADING_RE = re.compile(r'^#{1,6}\s+(.*?)\s*#*\s*$')
_EXTERNAL_RE = re.compile(r'^(?:[a-z][a-z0-9+.-]*:|//)', re.IGNORECASE)


def prose_lines(text):
    """(line number, line) for Markdown lines outside fenced code blocks."""
    fence = None
    for number, line in enumerate(text.split('\n'), 1):
        match = _FENCE_RE.match(line)
        if match and fence is None:
            fence = match.group(1)
        elif (match and match.group(1)[0] == fence[0]
              and len(match.group(1)) >= len(fence) and line.strip() == match.group(1)):
            fence = None
        elif fence is None:
            yield number, line


def github_slug(heading):
    """The anchor GitHub generates for a heading's text."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', heading)  # [text](url) -> text
    text = html.unescape(re.sub(r'<[^>]+>', '', text)).lower()
    kept = (c for c in text if c in ' -_' or unicodedata.category(c)[0] in 'LMN')
    return ''.join(kept).replace(' ', '-')


@functools.lru_cache(maxsize=None)
def anchors(path):
    """Fragments a file defines: heading slugs (Markdown) and id/name attributes."""
    text = read(path)
    if path.endswith('.html'):
        return frozenset(_HTML_ID_RE.findall(text))
    found, seen = set(), Counter()
    for _, line in prose_lines(text):
        found.update(_HTML_ID_RE.findall(line))
        match = _HEADING_RE.match(line)
        if match:
            slug = github_slug(match.group(1))
            found.add(f'{slug}-{seen[slug]}' if seen[slug] else slug)
            seen[slug] += 1
    return frozenset(found)


def local_links(path):
    """(line number, target) for each relative link in a Markdown or HTML file."""
    text = read(path)
    if path.endswith('.html'):
        lines = enumerate(text.split('\n'), 1)
        found = [(n, t) for n, line in lines for t in _HTML_LINK_RE.findall(line)]
    else:
        found = []
        for number, line in prose_lines(text):
            prose = _INLINE_CODE_RE.sub('', line)
            found += [(number, t) for t in _MD_LINK_RE.findall(prose)]
            found += [(number, t) for t in _HTML_LINK_RE.findall(prose)]
    return [(n, t) for n, t in found if not _EXTERNAL_RE.match(t)]


def broken_links(path):
    """(line number, target) for each relative link whose file or anchor is missing."""
    broken = []
    for number, target in local_links(path):
        file_part, _, fragment = target.partition('#')
        target_path = path
        if file_part:
            target_path = os.path.normpath(
                os.path.join(os.path.dirname(path), unquote(file_part)))
        if not os.path.exists(target_path):
            broken.append((number, target))
        elif (fragment and target_path.endswith(('.md', '.html'))
              and unquote(fragment) not in anchors(target_path)):
            broken.append((number, target))
    return broken


def markdown_table(text, header):
    """Rows (lists of cells) of the Markdown table whose header row starts with header."""
    lines = text.split('\n')
    start = next(i for i, line in enumerate(lines) if line.startswith(header))
    rows = []
    for line in lines[start + 2:]:
        if not line.startswith('|'):
            break
        rows.append([cell.strip() for cell in re.split(r'(?<!\\)\|', line.strip())[1:-1]])
    return rows


class LinkCheckerTest(unittest.TestCase):
    """The helpers above, so the link tests cannot pass vacuously."""

    def write(self, directory, name, lines):
        path = os.path.join(directory, name)
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(lines) + '\n')
        return path

    def test_github_slugs(self):
        cases = {
            'Salesforce Safety: Static Review Only': 'salesforce-safety-static-review-only',
            'The LWC-Apex Contract': 'the-lwc-apex-contract',
            '`@AuraEnabled` Methods': 'auraenabled-methods',
            'Phase 1: Context Gathering (2-3 minutes)': 'phase-1-context-gathering-2-3-minutes',
            'SOQL & SOSL': 'soql--sosl',
            '&#128640; Installation': '-installation',
            '[Deployment Impact](metadata.md) Notes': 'deployment-impact-notes',
            'Änderungen prüfen': 'änderungen-prüfen',
            'snake_case Names': 'snake_case-names',
        }
        for heading, expected in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(github_slug(heading), expected)

    def test_markdown_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, 'guide.md', [
                '# Guide', '## Deployment Impact', '## Notes', '## Notes',
                '<a id="custom"></a>', '```', '## Not A Heading', '```',
            ])
            index = self.write(tmp, 'index.md', [
                '# Index',
                '[ok](guide.md) and [ok](guide.md#deployment-impact)',
                '[ok](guide.md#notes-1) and [ok](guide.md#custom)',
                '[ok](#index) and [ok](./sub/../guide.md "Title")',
                '[external](https://example.com/missing.md) [mail](mailto:dev@example.com)',
                '`[inline code](missing-inline.md)`',
                '```markdown',
                '[fenced code](missing-fenced.md)',
                '```',
                '[missing](missing.md)',
                '[missing](guide.md#nope) and [missing](guide.md#not-a-heading)',
                '[missing](#nope) and <a href="missing.html">html</a>',
            ])
            self.assertEqual(broken_links(index), [
                (10, 'missing.md'), (11, 'guide.md#nope'), (11, 'guide.md#not-a-heading'),
                (12, '#nope'), (12, 'missing.html'),
            ])

    def test_html_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, 'guide.md', ['# Guide'])
            page = self.write(tmp, 'page.html', [
                '<a href="guide.md#guide">guide</a> <a href="https://example.com">x</a>',
                '<section id="top"><a href="#top">top</a></section>',
                '<a href="#gone">gone</a>',
                '<img src="logo.png">',
            ])
            self.assertEqual(broken_links(page), [(3, '#gone'), (4, 'logo.png')])

    def test_frontmatter_parser(self):
        fields = parse_frontmatter('\n'.join([
            '---', 'name: demo', '', 'description: |', '  First line.', '', '  Second line.',
            'allowed-tools:', '  - Read', '  - Bash(git diff *)', '---', '# Body',
        ]))
        self.assertEqual(fields, {
            'name': 'demo',
            'description': 'First line.\n\nSecond line.\n',
            'allowed-tools': ['Read', 'Bash(git diff *)'],
        })
        for text in ('# No frontmatter', '---\nname: demo\n', '---\n  - orphan item\n---'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_frontmatter(text)

    def test_markdown_table(self):
        text = '\n'.join(['| A | B |', '|---|---|', '| `x \\| y` | 1 |', '| z | 2 |', '', '| q |'])
        self.assertEqual(markdown_table(text, '| A |'), [['`x \\| y`', '1'], ['z', '2']])


# ═══════════════════════════════════════════════════════════════
# SKILL.md frontmatter
# ═══════════════════════════════════════════════════════════════

class FrontmatterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fields = parse_frontmatter(read(SKILL_MD))

    def test_name_is_sf_code_review(self):
        name = self.fields['name']
        self.assertEqual(name, SKILL_NAME)
        self.assertEqual(os.path.basename(SKILL_ROOT), name)
        self.assertRegex(name, r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
        self.assertNotRegex(name, r'anthropic|claude')

    def test_frontmatter_keys_are_known(self):
        # Claude Code ignores an unknown key without an error, so a typo such as
        # "contex: fork" would silently run the review in the author's context.
        self.assertLessEqual(set(self.fields), KNOWN_FRONTMATTER_KEYS)

    def test_runs_in_a_blocking_fork(self):
        # The review runs in a fresh subagent that never sees the conversation
        # that wrote the code, and the invoking turn waits for its report.
        self.assertEqual(self.fields['context'], 'fork')
        self.assertEqual(self.fields['agent'], 'general-purpose')
        self.assertEqual(self.fields['background'], 'false')
        self.assertEqual(self.fields['effort'], 'xhigh')
        self.assertNotIn('model', self.fields)

    def test_install_paths_match_name(self):
        # Claude Code (.claude/skills) and Codex (.agents/skills) find a skill by
        # its folder, which must carry the skill's name.
        text = read(README)
        claude = re.findall(r'\.claude[/\\]skills[/\\]([\w-]+)', text)
        codex = re.findall(r'\.agents[/\\]skills[/\\]([\w-]+)', text)
        self.assertTrue(claude)
        self.assertTrue(codex)
        self.assertEqual(set(claude) | set(codex), {SKILL_NAME})

    def test_description(self):
        description = self.fields['description'].strip()
        self.assertTrue(description)
        self.assertLessEqual(len(description), 1024)
        self.assertNotRegex(description, r'<[^>]+>')  # no XML tags

    def test_description_is_a_lean_trigger(self):
        # The description sits in every session's skill listing: keep it to what
        # the skill covers and when to use it. Rules live in the body.
        description = ' '.join(self.fields['description'].split())
        self.assertLessEqual(len(description), 700)
        self.assertTrue(description.startswith('Code review for Salesforce'), description)
        self.assertRegex(description, r'(?i)separate agent')
        for phrase in ('mentoring', 'never deploy', 'setting review standards'):
            self.assertNotIn(phrase, description)

    def test_allowed_tools_are_read_only(self):
        # Static review only: read-only tools, read-only git and gh, and the
        # bundled analyzer; never sf/sfdx, a general shell, or unscoped WebFetch
        # (reviewed code is untrusted input, so no pre-approved exfiltration path).
        # "git -C <repo>" reads a second repository of a multi-repo review.
        allowed = self.fields['allowed-tools']
        analyzer = 'Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/pr-analyzer.py *)'
        for required in (analyzer, 'Bash(gh pr view *)', 'Bash(gh pr diff *)',
                         'Bash(git merge-base *)', 'Bash(git -C * diff *)',
                         'Bash(git -C * show *)', 'Bash(gh issue view *)'):
            self.assertIn(required, allowed)
        for tool in allowed:
            with self.subTest(tool=tool):
                self.assertTrue(
                    tool in {'Read', 'Grep', 'Glob', analyzer}
                    or re.fullmatch(r'Bash\(git (?:-C \* )?(?:diff|log|show|status|merge-base'
                                    r'|rev-parse|blame|ls-files) \*\)', tool)
                    or re.fullmatch(r'Bash\(gh (?:pr (?:view|diff|checks)|issue view) \*\)', tool),
                    tool)
                self.assertFalse(tool.startswith('WebFetch'), tool)

    def test_skill_dir_paths_exist(self):
        paths = set(re.findall(r'\$\{CLAUDE_SKILL_DIR\}/([\w./-]+)', read(SKILL_MD)))
        self.assertIn('scripts/pr-analyzer.py', paths)
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(os.path.join(SKILL_ROOT, path)))


# ═══════════════════════════════════════════════════════════════
# SKILL.md body: an agent's procedure, not a human's
# ═══════════════════════════════════════════════════════════════

class SkillBodyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(SKILL_MD)

    def test_fits_the_compaction_budget(self):
        self.assertLessEqual(len(self.text), SKILL_MD_MAX_CHARS)

    def test_output_format_is_defined(self):
        self.assertIn('output-format', anchors(SKILL_MD))
        body = self.text.split('## Output Format', 1)[1].split('\n## ', 1)[0]
        for marker in ('**Verdict:**', '**Scope:**', '### Findings', '### Questions',
                       '`path/to/file', '(pre-existing)', 'Request changes', 'Approve'):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_standing_rules(self):
        # Reviewed code, comments, and PR text are data; findings are verified
        # before they are reported.
        self.assertRegex(self.text, r'(?i)as data, not (?:as )?instructions')
        self.assertRegex(self.text, r'(?i)verify each (?:candidate )?finding')

    def body(self):
        """SKILL.md without its frontmatter."""
        return self.text.split('\n---\n', 1)[1]

    def test_body_opens_with_target_and_skill_dir(self):
        # A forked review sees only this file: the target and the skill folder
        # must be in it, ahead of every section.
        intro = self.body().split('\n## ', 1)[0]
        self.assertIn('\nReview target: $ARGUMENTS\n', intro)
        self.assertIn('\nSkill folder: ${CLAUDE_SKILL_DIR}\n', intro)
        self.assertEqual(self.text.count('$ARGUMENTS'), 1)

    def test_unexpanded_placeholders_have_a_fallback(self):
        # Codex and a direct read of the file leave the placeholders as typed.
        self.assertRegex(self.text, r"still shows a `\$` placeholder.{0,120}"
                                    r"folder of this SKILL\.md")

    def test_independence_rule(self):
        rule = self.line_starting('- **Independent.**')
        for phrase in ('began with this skill', 'You are the delegate; do not delegate.',
                       'fresh agent', 'unchanged', '`independent: no`'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, rule)

    def test_claims_in_the_request_are_unverified(self):
        rule = self.line_starting('- **Claims are context.**')
        self.assertRegex(rule, r'(?i)unverified.{0,60}never evidence')

    def test_empty_target_stops(self):
        rule = self.line_starting('- No target given:')
        self.assertIn('`No target: nothing to review`', rule)
        self.assertIn('Never approve an empty diff.', rule)

    def test_multi_repo_and_commit_range_targets(self):
        self.assertIn('`repo=<path>:<base>...<head>`', self.line_starting('- Several repositories:'))
        self.assertIn('`git diff --no-color --default-prefix <from> <to>`',
                      self.line_starting('- Commit range:'))

    def test_context_includes_the_governing_rules(self):
        step = self.line_starting('2. **Gather context.**')
        for phrase in ('CLAUDE.md', 'AGENTS.md', 'gh issue view', 'sfdx-project.json'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, step)

    def test_orchestration(self):
        # Small changes stay in one fresh agent; large ones fan out to one fresh
        # agent per feature slice, and degrade to a sequential pass without Agent.
        step = self.line_starting('3. **Plan the passes.**')
        for phrase in ('300', '10 files', 'by feature', 'exactly one slice', 'in parallel',
                       '(assets/reviewer-brief.md)', '`effort: xhigh`', '`parallel: no`'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, step)

    def test_every_angle_is_named_in_skill_md(self):
        # A one-line list of every angle keeps a skipped angle visible.
        angles = re.findall(r'^### (.+)$', read(ANGLES), re.MULTILINE)
        self.assertGreaterEqual(len(angles), 16)
        listed = self.line_starting('Angles:').lower()
        for angle in angles:
            with self.subTest(angle=angle):
                self.assertIn(angle.lower(), listed)

    def test_merge_does_not_drop_and_sweep_runs(self):
        step = self.line_starting('6. **Merge and sweep.**')
        self.assertRegex(step, r'(?i)without dropping')
        self.assertIn('(assets/review-angles.md#gap-sweep)', step)
        self.assertRegex(step, r'(?i)contracts between slices')
        self.assertRegex(step, r'(?i)zero new findings is a valid result')

    def test_verification_drops_only_with_a_quoted_guard(self):
        self.assertNotIn("Drop what doesn't hold", self.text)
        step = self.line_starting('7. **Verify each candidate finding**')
        self.assertRegex(step, r'(?i)drop a candidate only when you can quote')
        self.assertIn('`file:line`', step)
        self.assertIn('`Confidence: high`', step)
        for verdict in ('CONFIRMED', 'REFUTED', 'UNDECIDABLE', 'blind'):
            with self.subTest(verdict=verdict):
                self.assertIn(verdict, step)

    def test_questions_only_for_facts_outside_the_repo(self):
        step = self.line_starting('7. **Verify each candidate finding**')
        self.assertRegex(step, r'(?i)under Questions only when the deciding fact lives '
                               r'outside the repository')

    def test_soft_floor_reruns_sweep_once(self):
        step = self.line_starting('8. **Report**')
        self.assertRegex(step, r'(?i)fewer than 5 findings on more than 100 reviewable lines'
                               r'.{0,40}gap sweep once more')

    def test_no_nit_cap(self):
        # Every issue is reported, ranked; a cap hides real ones.
        for path in (SKILL_MD, README):
            with self.subTest(path=rel(path)):
                nit_rows = [line for line in read(path).split('\n') if 'nit`' in line or '[nit]' in line]
                self.assertTrue(nit_rows)
                for row in nit_rows:
                    self.assertNotIn('at most', row)

    def test_output_has_confidence_independence_coverage(self):
        body = self.text.split('## Output Format', 1)[1].split('\n## ', 1)[0]
        for marker in ('Independent review from a separate agent. Relay it unchanged.',
                       'independent: yes | no', 'parallel: yes | no', 'not reviewed:',
                       'Confidence: high | medium', '### Outside this change',
                       'Outside this change never changes the verdict'):
            with self.subTest(marker=marker):
                self.assertIn(marker, body)

    def test_salesforce_investigation_moved(self):
        # The eight Salesforce steps live with the other angles, so a reviewer of
        # a non-Salesforce slice skips them and SKILL.md keeps its budget.
        self.assertNotIn('Investigate the change the way', self.text)
        self.assertIn('(assets/review-angles.md#salesforce-investigation)', self.text)
        steps = re.findall(r'^\d\. \*\*(.+?)\.\*\*',
                           read(ANGLES).split('## Salesforce Investigation', 1)[1], re.MULTILINE)
        self.assertEqual(steps, ['Context', 'Entry points', 'Limits at bulk volume', 'Data access',
                                 'UI layer', 'Automation overlap', 'Tests',
                                 'Metadata and deployment'])

    def test_no_human_process_content(self):
        for pattern in (r'\(\d+-\d+ minutes\)', r'(?i)offer to pair', r'(?i)ask to split',
                        r'(?i)question approach', '🎉', r'(?i)\[praise\]'):
            with self.subTest(pattern=pattern):
                self.assertNotRegex(self.text, pattern)

    def test_diff_commands_survive_user_git_config(self):
        # color.ui=always and diff.mnemonicPrefix/noprefix change what git prints
        commands = re.findall(r'`(git diff [^`]*)`', self.text)
        self.assertTrue(any('| python3 ${CLAUDE_SKILL_DIR}/scripts/pr-analyzer.py' in c
                            for c in commands), commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertIn('--no-color', command)
                self.assertIn('--default-prefix', command)
        # Uncommitted work: tracked changes against HEAD, and untracked files
        self.assertIn('`git diff --no-color --default-prefix HEAD`', self.text)
        self.assertIn('git status --porcelain', self.text)

    def line_starting(self, prefix):
        """The one SKILL.md line that starts with prefix, leading spaces ignored."""
        found = [line for line in self.text.split('\n') if line.lstrip().startswith(prefix)]
        self.assertEqual(len(found), 1, prefix)
        return found[0]

    def test_s1_reports_only_what_the_change_touches(self):
        # An older problem is a finding only when the change makes it reachable or
        # worse, as the guides say; its severity is no way back in. Other older
        # problems in the code the review read are listed apart, never scanned for.
        rule = self.line_starting('- **Review the change.**')
        self.assertNotIn('🔴', rule)
        self.assertRegex(rule, r'(?i)changed lines')
        self.assertRegex(rule, r'(?i)reachable or worse.{0,40}"\(pre-existing\)"')
        self.assertRegex(rule, r'(?i)other older problems.{0,80}"Outside this change"')
        self.assertRegex(rule, r'(?i)never scan unchanged files')

    def test_s2_branch_diffs_use_three_dots(self):
        # Two dots also show what the target gained since the fork, reversed.
        for command in re.findall(r'`(git diff [^`]*)`', self.text):
            with self.subTest(command=command):
                self.assertNotRegex(command, r'(?<!\.)\.\.(?!\.)')
        branch = self.line_starting('- Branch:')
        self.assertIn('`git diff --no-color --default-prefix <base>...HEAD`', branch)
        self.assertIn('`origin/<target>...origin/<source>`', branch)

    def test_s2_review_reads_a_line_range_per_hunk(self):
        review = self.line_starting('5. **Find candidates**')
        self.assertRegex(review, r'(?i)enclosing function or block.{0,40}line range')
        self.assertRegex(review, r'(?i)never the whole file')
        self.assertRegex(review, r'(?i)Flow, LWC, Aura.{0,60}element around the hunk')

    def test_review_step_traces_callers_and_mirrors(self):
        # Most real defects sit outside the hunk: in a caller, in the code the
        # change copies, in a rule file, or in what the change removed.
        self.assertNotIn('Follow callers only when', self.text)
        review = self.line_starting('5. **Find candidates**')
        for phrase in ('callers and callees', 'mirrors or claims parity with',
                       'sibling branches', 'CLAUDE.md', 'OWD', '`git show <base>:<path>`',
                       '(assets/review-angles.md)', 'up to 8 each'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, review)

    def test_s3_renamed_files_are_diffed_with_both_paths(self):
        rename = self.line_starting('- A renamed or moved file')
        self.assertIn('both paths', rename)
        self.assertRegex(rename, r'(?i)only its changed lines')

    def test_s4_formatting_rewrites_are_read_without_whitespace(self):
        rewrite = self.line_starting('- A file whose diff rewrites most lines')
        self.assertIn('-w --ignore-cr-at-eol', rewrite)
        self.assertRegex(rewrite, r'(?i)line endings')
        self.assertRegex(rewrite, r'(?i)under Scope.{0,40}formatting')

    def test_guides_are_read_checklist_first(self):
        self.assertRegex(self.text, r'(?i)review checklist.{0,120}first')

    def test_template_matches_the_output_format(self):
        template = read(PR_TEMPLATE)
        for marker in ('**Verdict:**', '**Scope:**', '### Findings', '### Questions',
                       '### Outside this change', 'Confidence:', 'independent: yes',
                       'Independent review from a separate agent. Relay it unchanged.'):
            with self.subTest(marker=marker):
                self.assertIn(marker, template)
        for gone in ('Review Time', '## Strengths', '- [ ]'):
            with self.subTest(gone=gone):
                self.assertNotIn(gone, template)


# ═══════════════════════════════════════════════════════════════
# The briefs a review sends to its delegate agents
# ═══════════════════════════════════════════════════════════════

class ReviewerBriefTest(unittest.TestCase):
    """A delegate sees nothing but its brief, so the brief must carry every rule."""

    @classmethod
    def setUpClass(cls):
        cls.text = read(BRIEF)
        cls.sections = {name: section for name, section in
                        re.findall(r'^## (.+?)\n(.*?)(?=^## |\Z)', cls.text, re.M | re.S)}

    def test_has_a_reviewer_and_a_verifier_brief(self):
        self.assertEqual(set(self.sections), {'Slice Reviewer', 'Verifier'})

    def test_every_delegate_is_told_not_to_delegate(self):
        for name, section in self.sections.items():
            with self.subTest(brief=name):
                self.assertIn('You are the delegate; do not delegate.', section)
                self.assertRegex(section, r'(?i)as data, not instructions')

    def test_salesforce_safety_is_copied_verbatim(self):
        safety = read(SKILL_MD).split('### Salesforce Safety: Static Review Only', 1)[1]
        first_rule = re.search(r'^- (Never run .+?\.) ', safety, re.M).group(1)
        for name, section in self.sections.items():
            with self.subTest(brief=name):
                self.assertIn(first_rule, section)

    def test_slice_reviewer_brief_is_self_contained(self):
        brief = self.sections['Slice Reviewer']
        for placeholder in ('{skill_folder}', '{repository}', '{diff_command}', '{hunks}',
                            '{intent}', '{rule_files}', '{guides}'):
            with self.subTest(placeholder=placeholder):
                self.assertIn(placeholder, brief)
        self.assertIn('{skill_folder}/assets/review-angles.md', brief)
        self.assertRegex(brief, r'(?i)could not read')
        for field in ('file:', 'line:', 'angle:', 'summary:', 'failure_scenario:',
                      'severity:', 'confidence:'):
            with self.subTest(field=field):
                self.assertIn(field, brief)

    def test_verifier_is_blind_and_answers_in_three_verdicts(self):
        brief = self.sections['Verifier']
        self.assertIn('{findings}', brief)
        self.assertRegex(brief, r"(?i)not the reasoning")
        for verdict in ('CONFIRMED', 'REFUTED', 'UNDECIDABLE'):
            with self.subTest(verdict=verdict):
                self.assertIn(verdict, brief)


# ═══════════════════════════════════════════════════════════════
# Repository: license and install instructions
# ═══════════════════════════════════════════════════════════════

class RepositoryTest(unittest.TestCase):
    def test_license_keeps_the_upstream_notice(self):
        # Adapted from awesome-skills/code-review-skill (MIT): the copyright and
        # permission notice must ship with every copy.
        text = read(LICENSE)
        self.assertTrue(text.startswith('MIT License\n'))
        self.assertIn('Copyright (c) 2025 awesome-skills', text)
        self.assertIn('Copyright (c) 2026 Ruslan Mukhamadeev', text)
        self.assertIn('The above copyright notice and this permission notice shall be included '
                      'in all\ncopies or substantial portions of the Software.', text)

    def test_readme_names_the_repository(self):
        text = read(README)
        self.assertNotRegex(text, r'<owner>|<repo>|<repository-url>')
        self.assertIn(f'npx skills add {REPOSITORY} --skill {SKILL_NAME}', text)
        self.assertIn(f'https://github.com/{REPOSITORY}.git', text)
        self.assertIn('LICENSE', text)
        self.assertNotIn('Do not nest', text)

    def test_old_name_is_gone(self):
        files = [SKILL_MD, README, INDEX_HTML, os.path.join(_HERE, 'pr-analyzer.py')]
        files += skill_files('.md')
        if REPO_ROOT:
            files.append(os.path.join(REPO_ROOT, 'README.md'))
        for path in sorted(set(files)):
            with self.subTest(path=path):
                self.assertNotRegex(read(path), _OLD_NAME_RE)

    @needs_repo_root
    def test_skill_lives_under_skills_dir(self):
        self.assertFalse(os.path.exists(os.path.join(REPO_ROOT, 'SKILL.md')))
        self.assertEqual(rel(_SKILLS_DIR), '..')

    @needs_repo_root
    def test_license_copies_identical(self):
        self.assertEqual(read(os.path.join(REPO_ROOT, 'LICENSE')), read(LICENSE))

    @needs_repo_root
    def test_root_readme_lists_every_skill(self):
        text = read(os.path.join(REPO_ROOT, 'README.md'))
        names = sorted(d for d in os.listdir(_SKILLS_DIR)
                       if os.path.isfile(os.path.join(_SKILLS_DIR, d, 'SKILL.md')))
        self.assertIn(SKILL_NAME, names)
        for name in names:
            with self.subTest(skill=name):
                fields = parse_frontmatter(read(os.path.join(_SKILLS_DIR, name, 'SKILL.md')))
                self.assertEqual(fields['name'], name)
                self.assertIn(f'(skills/{name}/)', text)
                self.assertIn(f'--skill {name}', text)

    @needs_repo_root
    def test_coveragerc_points_at_the_skill(self):
        config = configparser.ConfigParser()
        config.read(os.path.join(REPO_ROOT, '.coveragerc'))
        source = config['run']['source']
        self.assertEqual(os.path.normpath(os.path.join(REPO_ROOT, source)), _HERE)

    @needs_repo_root
    def test_test_commands_name_existing_paths(self):
        # The test and coverage commands run from the repository root.
        for path in (README, os.path.join(REPO_ROOT, 'README.md')):
            commands = re.findall(r'unittest discover -s ([\w./-]+)', read(path))
            with self.subTest(readme=path):
                self.assertTrue(commands)
                for directory in commands:
                    self.assertTrue(os.path.isdir(os.path.join(REPO_ROOT, directory)), directory)

    @needs_repo_root
    def test_root_readme_links_resolve(self):
        self.assertEqual(broken_links(os.path.join(REPO_ROOT, 'README.md')), [])


# ═══════════════════════════════════════════════════════════════
# Links and guide registration
# ═══════════════════════════════════════════════════════════════

class LinksTest(unittest.TestCase):
    def test_every_local_link_resolves(self):
        files = skill_files('.md', '.html')
        self.assertIn(SKILL_MD, files)
        self.assertIn(INDEX_HTML, files)
        broken = {rel(path): links for path in files if (links := broken_links(path))}
        self.assertEqual(broken, {})

    def test_every_guide_is_registered(self):
        # README: "Register new guides in SKILL.md, this README, and index.html."
        # A guide SKILL.md does not link is never loaded.
        skill_targets = {os.path.normpath(t.partition('#')[0]) for _, t in local_links(SKILL_MD)}
        for path in skill_files('.md'):
            relative = rel(path)
            if not relative.startswith(('reference/', 'assets/')):
                continue
            with self.subTest(guide=relative):
                self.assertIn(os.path.normpath(relative), skill_targets)
                if relative.startswith('reference/'):
                    name = rf'(?<![\w-]){re.escape(os.path.basename(path))}'
                    self.assertRegex(read(README), name)
                    self.assertRegex(read(INDEX_HTML), name)


# ═══════════════════════════════════════════════════════════════
# SKILL.md <-> scripts/pr-analyzer.py
# ═══════════════════════════════════════════════════════════════

# One sample per path pattern in SKILL.md's "Use this path when ..." sentence
DETECTION_SAMPLES = {
    'sfdx-project.json': 'sfdx-project.json',
    '*.cls': SF + 'classes/AccountService.cls',
    '*.trigger': SF + 'triggers/AccountTrigger.trigger',
    '*.apex': 'scripts/apex/seed.apex',
    '*.soql': 'scripts/soql/openOpportunities.soql',
    '*.page': SF + 'pages/AccountPage.page',
    '*.component': SF + 'components/AccountHeader.component',
    '*-meta.xml': SF + 'objects/Account/fields/Tier__c.field-meta.xml',
    'lwc/**': SF + 'lwc/accountList/accountList.js',
    'aura/**': SF + 'aura/AccountCard/AccountCard.cmp',
    'manifest/*.xml': 'manifest/package.xml',
    'destructiveChanges*.xml': 'destructiveChangesPost.xml',
}

# Samples per row of the Salesforce routing table, keyed by the start of the
# row's "Changed files" cell
ROUTING_SAMPLES = {
    '`classes/*.cls`': (SF + 'classes/AccountService.cls', 'scripts/apex/seed.apex'),
    '`triggers/*.trigger`': (SF + 'triggers/AccountTrigger.trigger',),
    'Apex test classes': (SF + 'classes/AccountServiceTest.cls',),
    '`*.soql`': ('scripts/soql/openOpportunities.soql',),
    '`lwc/<bundle>/*`': (SF + 'lwc/accountList/accountList.js',),
    '`aura/<bundle>/*`': (SF + 'aura/AccountCard/AccountCardController.js',),
    '`*.page`': (SF + 'pages/AccountPage.page', SF + 'components/AccountHeader.component'),
    '`*.flow-meta.xml`': (SF + 'flows/Account_Update.flow-meta.xml',
                          SF + 'flowDefinitions/Account_Update.flowDefinition-meta.xml',
                          SF + 'flowtests/Account_Update_Test.flowtest-meta.xml'),
    'Permission sets': tuple(SF + path for path in (
        'permissionsets/Sales.permissionset-meta.xml',
        'permissionsetgroups/Sales_Bundle.permissionsetgroup-meta.xml',
        'profiles/Admin.profile-meta.xml',
        'sharingRules/Account.sharingRules-meta.xml',
        'objects/Invoice__c/Invoice__c.object-meta.xml',
        'objects/Account/fields/Tier__c.field-meta.xml',
        'objects/Account/validationRules/Tier_Required.validationRule-meta.xml',
        'namedCredentials/Billing.namedCredential-meta.xml',
        'externalCredentials/Billing.externalCredential-meta.xml',
        'remoteSiteSettings/Billing.remoteSite-meta.xml',
        'cspTrustedSites/Cdn.cspTrustedSite-meta.xml',
        'connectedApps/Portal.connectedApp-meta.xml',
        'customMetadata/Feature_Flag.Checkout.md-meta.xml',
        'labels/CustomLabels.labels-meta.xml',
    )),
    '`sfdx-project.json`': ('sfdx-project.json', '.forceignore', 'manifest/package.xml',
                            'destructiveChanges.xml'),
    'Only `*-meta.xml` apiVersion changes': (
        SF + 'classes/AccountService.cls-meta.xml',
        SF + 'triggers/AccountTrigger.trigger-meta.xml',
    ),
}


class AnalyzerContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_text = read(SKILL_MD)

    def test_recommended_guides_exist_and_are_linked(self):
        skill_targets = {os.path.normpath(t.partition('#')[0]) for _, t in local_links(SKILL_MD)}
        for guide in pr_analyzer.GUIDE_ORDER:
            with self.subTest(guide=guide):
                self.assertTrue(os.path.isfile(os.path.join(SKILL_ROOT, guide)))
                self.assertIn(os.path.normpath(guide), skill_targets)

    def test_review_path_named_by_the_analyzer_exists(self):
        suggestions = pr_analyzer.generate_suggestions([file_stats('sfdx-project.json')], 0.1, [])
        self.assertIn('follow the Salesforce Review Path in SKILL.md', suggestions[0])
        self.assertIn('salesforce-review-path', anchors(SKILL_MD))

    def test_paths_listed_in_skill_md_are_flagged(self):
        # "Use this path when ... the diff touches ... (the analyzer flags these too)"
        sentence = next(line for line in self.skill_text.split('\n')
                        if line.startswith('Use this path when'))
        self.assertIn('(the analyzer flags these too)', sentence)
        self.assertEqual(set(re.findall(r'`([^`]+)`', sentence)), set(DETECTION_SAMPLES))
        for pattern, path in DETECTION_SAMPLES.items():
            with self.subTest(pattern=pattern):
                files = [file_stats(path)]
                suggestions = pr_analyzer.generate_suggestions(files, 0.1, [])
                self.assertTrue(any(s.startswith('Salesforce change: ') for s in suggestions))
                self.assertIn(pr_analyzer.GUIDE_SF_PLATFORM, pr_analyzer.recommend_guides(files))

    def test_routing_table_matches_recommended_guides(self):
        rows = markdown_table(self.skill_text, '| Changed files | Load |')
        self.assertEqual(len(rows), len(ROUTING_SAMPLES))
        for changed, load, _ in rows:
            keys = [key for key in ROUTING_SAMPLES if changed.startswith(key)]
            self.assertEqual(len(keys), 1, f'no single sample set for the row {changed!r}')
            guides = {link.partition('#')[0] for link in re.findall(r'\]\(([^)]+)\)', load)}
            self.assertTrue(guides, load)
            for path in ROUTING_SAMPLES[keys[0]]:
                with self.subTest(row=keys[0], path=path):
                    recommended = pr_analyzer.recommend_guides([file_stats(path)])
                    # The platform guide is always loaded first
                    self.assertEqual(recommended[0], pr_analyzer.GUIDE_SF_PLATFORM)
                    self.assertLessEqual(guides, set(recommended))


if __name__ == '__main__':
    unittest.main()
