# CTI Code Review Skills

Code review skills for Claude Code and Codex. Each skill lives in its own folder under `skills/` and installs on its own.

| Skill | Covers | Install |
|---|---|---|
| [sf-code-review](skills/sf-code-review/) | Salesforce (Apex, triggers, SOQL/SOSL, LWC, Aura, Visualforce, Flows, metadata) and the JavaScript, TypeScript, Node.js, NestJS, and Python code around it. Runs as a separate agent with a clean context. | `npx skills add RAMukhamadeev1/cti-code-review-skills --skill sf-code-review` |

## Install from a local checkout

Link the skill folder, not the repository root, so `git pull` updates every link:

```bash
git clone https://github.com/RAMukhamadeev1/cti-code-review-skills.git ~/src/cti-code-review-skills

ln -s ~/src/cti-code-review-skills/skills/sf-code-review ~/.claude/skills/sf-code-review   # Claude Code
ln -s ~/src/cti-code-review-skills/skills/sf-code-review ~/.agents/skills/sf-code-review   # Codex
```

## Develop

Run the tests from the repository root (standard library only):

```bash
python3 -m unittest discover -s skills/sf-code-review/scripts
python3 -m coverage run -m unittest discover -s skills/sf-code-review/scripts && python3 -m coverage report
```

The coverage run needs `pip install coverage`; its settings are in `.coveragerc`. Notes on past changes are in [docs/](docs/). Each skill's own README has its contributing rules.

## License

MIT. See [LICENSE](LICENSE). The skills are adapted from [awesome-skills/code-review-skill](https://github.com/awesome-skills/code-review-skill) (MIT), whose notice every copy keeps.
