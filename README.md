# Eight Wave agent skills

Portable skills for coding agents (Claude Code and compatible), extracted from the Eight Wave
engineering workflow. They encode one rule: **a model that did not write the code judges,
your primary agent writes.** Codex when it is available, otherwise the reviewer you pick.
Read-only, one declared round, and every finding verified against the files before adoption.

## Skills

| Skill | What it does |
|---|---|
| [`codex-setup`](skills/codex-setup/SKILL.md) | Install, authenticate and smoke-test the OpenAI Codex CLI, read-only by default |
| [`thinking-partner`](skills/thinking-partner/SKILL.md) | A second opinion on a diff, design or document from Codex, or from the model you pick when Codex is missing or out of quota: one round, verified, adopted or rejected with reasons |
| [`full-review`](skills/full-review/SKILL.md) | Full-diff pre-commit review (regressions, readability, DRY, pre-existing defects), Claude Code's `/code-review` as first pass where available, an independent model as verifier |
| [`new-spec`](skills/new-spec/SKILL.md) | Create, update, release or archive feature specs and keep the roadmap in sync, in any language and specs folder |
| [`changelog`](skills/changelog/SKILL.md) | User-facing release notes, one file per version, folded into the pending version until it ships |
| [`agent-config-audit`](skills/agent-config-audit/SKILL.md) | Audit what the agents load (context files, skills and their lock, MCP servers, hooks, memory), measure real usage and propose what to fix, prune or hand over to lint and hooks |
| [`de-slopify`](skills/de-slopify/SKILL.md) | Find the tells that make a UI look AI-generated and replace them with precise, element-by-element fixes drawn from the project's design system, never from a house taste |

## Install

```bash
npx skills add 8wavesrl/skills
```

The [skills CLI](https://skills.sh/8wavesrl/skills) detects the agents in your project
(Claude Code, Codex, Cursor and many more), lets you pick the skills interactively, and pins
them in `skills-lock.json`. Prefer a manual copy? The layout is the conventional
`skills/<name>/SKILL.md`:

```bash
git clone --depth 1 https://github.com/8wavesrl/skills /tmp/8wave-skills
# full-review consults thinking-partner, which brings its script along
cp -R /tmp/8wave-skills/skills/full-review /tmp/8wave-skills/skills/thinking-partner .claude/skills/
```

## Renamed skills

A lock that still pins an old name will not find it: remove the old skills and add the new
ones (add `-g` to both commands for a global install).

| Old name | New name | Since |
|---|---|---|
| `review-with-codex` | `full-review` | 2026-10-02 |
| `codex-thinking-partner` | `thinking-partner` | 2026-10-02 |

```bash
npx skills remove review-with-codex codex-thinking-partner
npx skills add 8wavesrl/skills
```

## Prerequisites

- The [Codex CLI](https://github.com/openai/codex) (`npm install -g @openai/codex`) with an
  account or API key, as the preferred reviewer. `codex-setup` walks through it. Without it,
  or out of quota, the skills ask which reviewer to use instead (by default another model of
  your agent's own vendor, in a fresh context).
- Calls to another vendor send repository content there (OpenAI for Codex, Anthropic for
  Claude) and spend that account's quota: the skills ask for the user's go-ahead accordingly.

## License

MIT, copyright 8 wave S.r.l.
