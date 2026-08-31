# Eight Wave agent skills

Portable skills for coding agents (Claude Code and compatible), extracted from the Eight Wave
engineering workflow. They encode one rule: **Codex judges, your primary agent writes.**
Read-only, one declared round, and every finding verified against the files before adoption.

## Skills

| Skill | What it does |
|---|---|
| [`codex-setup`](skills/codex-setup/SKILL.md) | Install, authenticate and smoke-test the OpenAI Codex CLI, read-only by default |
| [`codex-thinking-partner`](skills/codex-thinking-partner/SKILL.md) | A second opinion on a diff, design or document: one round, verified, adopted or rejected with reasons |
| [`review-with-codex`](skills/review-with-codex/SKILL.md) | Full-diff pre-commit review (regressions, readability, DRY, pre-existing defects) with Codex as independent verifier |

## Install

Copy the folders you want into your project's skills directory:

```bash
git clone --depth 1 https://github.com/8wavesrl/skills /tmp/8wave-skills
cp -R /tmp/8wave-skills/skills/review-with-codex .claude/skills/review-with-codex
```

Or pin them with the skills sync tooling of your choice; the layout is the conventional
`skills/<name>/SKILL.md`.

## Prerequisites

- The [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`) with an
  account or API key. `codex-setup` walks through it.
- Outbound calls send repository content to OpenAI and spend the account's quota: the skills
  ask for the user's go-ahead accordingly.

## License

MIT, copyright 8 wave S.r.l.
