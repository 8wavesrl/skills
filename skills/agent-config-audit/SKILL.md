---
name: agent-config-audit
description: Audit what a project's coding agents load (CLAUDE.md, AGENTS.md, installed skills and their lock, MCP servers, hooks, auto-memory) and propose what to fix, prune or hand over to lint, tests and hooks. A bundled read-only script measures lock drift, duplicate or stale skills, real skill usage from Claude Code transcripts, broken references, outdated version claims and rules repeated across files; the judgment checks cover prose a tool should enforce and content the model reads better from the code. Nothing changes before the user decides. Use when the user asks to audit or clean up the agent setup ("audit agent files", "doctor", "pulizia skill", "stato di salute della configurazione"), after installing a batch of skills, or when instructions seem ignored and skills fire at the wrong time.
---

# Agent configuration audit

Instructions age. Models and harnesses improve, the codebase moves, and a rule written after
one bad afternoon stays forever while adherence to the whole file drops. This audit measures
what the agents load, checks it against the files, and proposes a leaner setup whose hard
constraints are enforced by tools rather than prose. It never deletes on its own.

## Step 0: scope

State in one line: the project root, the agents in use (which of `.claude/`, `.agents/`,
`.codex/`, `.cursor/` exist) and whether a `skills-lock.json` manages the project skills.

## 1. Archive first

Snapshot what the audit may touch, so a restore costs one command. Skill folders are usually
git-ignored, so git alone does not cover them. Tell the user where the archive is.

```bash
backup=~/.claude/backups/agent-config-$(date +%F) && mkdir -p "$backup"
key=$(pwd | sed 's/[^A-Za-z0-9]/-/g')
(cd ~ && tar -czf "$backup/global.tar.gz" $(ls -d .claude/skills .agents/skills \
  .agents/.skill-lock.json .claude/CLAUDE.md ".claude/projects/$key/memory" 2>/dev/null))
tar -czf "$backup/project.tar.gz" $(ls -d .claude .agents skills-lock.json CLAUDE.md AGENTS.md 2>/dev/null)
```

## 2. Run the measurable checks

```bash
python3 <this skill's directory>/scripts/audit.py --repo . --days 30
```

The report tags each finding `fix` (verifiably wrong: a broken link, a lock entry not
installed, two versions of one skill), `review` (needs judgment) or `info`. It covers context
file size with imports, links and skill names that do not resolve, version claims that no
longer match the manifests, rules repeated across files, lock and mirror drift, the same skill
in two scopes or both standalone and inside a Claude Code plugin, broad trigger claims, bulk
installs from one source, usage per skill and per MCP server, the memory index, and hooks. It
honours `CLAUDE_CONFIG_DIR`.

Usage comes from Claude Code transcripts only, kept about 30 days by default. Zero uses is a
signal, not proof: an installer skill is rarely used and still earns its place. In Claude Code,
`/skill-doctor` (v2.1.252 and later) shows each skill's context cost and use as well: quote it
when available, the script covers what it does not (other agents, locks, context files).

## 3. Judgment checks

Read every context file in full, then:

1. **Prose a tool should enforce.** For each rule, ask whether a linter, formatter, type
   check, test, hook or permission can enforce it; [references/enforceable-rules.md](references/enforceable-rules.md)
   maps the common ones. Check whether it is already on (`npx eslint --print-config <file>`).
   If it is off, measure the violations before proposing it: an autofix across a hundred
   files is the user's scope decision. Once a tool enforces the rule, the prose goes; the part
   the tool cannot say (the reason, the trap) stays.
2. **Claims about the setup.** Every sentence that states a fact about the configuration (a
   skill is or is not in the lock, a file lives in a folder, a command does something) is
   checked against the files. A stale claim misleads more than a missing one.
3. **What the code already says.** Directory trees, architecture summaries, dependency lists
   and generic clean-code advice are candidates to cut: agents answer more questions from the
   source than from a summary of it. Keep what the code does not say: the commands that verify
   work, the slow or dangerous operations, the boundaries, the traps that already cost a bug.
4. **One audience, one copy.** For each pair of similar rules the script flags, keep the copy
   the widest audience reads. A personal global rule repeated in the team's AGENTS.md can be
   legitimate (teammates do not have the global file); two files loaded in the same session
   that say the same thing are not.
5. **Overlapping skills.** Group the skills by domain and read the ones you judge. Two skills
   for one job, a skill that pushes a style against the project's design system, a skill whose
   description claims every task: propose one owner per domain, backed by the usage numbers.
6. **Hard constraints as prose.** A rule whose violation is expensive (never run X directly,
   never commit Y) belongs in a hook or a permission deny as well as in the text.
7. **Memory.** Entries marked closed, entries that contradict an instruction file, and entries
   that are team knowledge and belong in the repo.

## 4. Report, then wait

One table, most important first: finding, evidence (`file:line`, a count, a command output),
proposed action, how to undo it. Keep what is wrong apart from what is a choice, and ask which
rows to apply. Change nothing in this step.

## 5. Apply what the user approved

- Lock-managed skills change through their tool, never by hand in the folders:
  `npx skills remove <name>` in the project, `-g` for a global one, `-a <agent>` to drop one
  agent's link and keep the skill for the others. A lock entry declared but not installed goes
  with the same command, or comes back with `npx skills experimental_install`.
- A skill a Claude Code plugin already provides loses its standalone copy for Claude only
  (`-a claude-code`): plugins are Claude-only, the other agents keep the CLI install.
- A new lint rule: add it, autofix, then run the project's type check, tests and build. An
  autofix that rewrites imports can break code the linter cannot see.
- Edit context files with anchored edits and read every change back from the file.
- Run the script again and show what changed.

## 6. Test without (optional)

For a skill or rule whose value is in doubt, run one real task without it (restore from the
archive afterwards). Outcomes vary between runs, so repeat when the decision matters. If the
agent fails exactly the way the skill was written to prevent, the skill stays.

## Rules

- Read-only until the user decides. Never delete a skill, a memory or a rule on your own.
- Archive before the first change.
- Every proposal cites evidence: a file and line, a count, a command output.
- Suggest a cadence: every few weeks, and after installing a batch of skills.

Based on Addy Osmani, [Audit your agent files](https://addyosmani.com/blog/audit-your-agent-files/).
