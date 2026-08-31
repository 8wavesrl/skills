---
name: review-with-codex
description: Full-diff review before commit, no regressions, readable, maintainable, DRY, pre-existing bugs flagged and fixed, with Codex consulted read-only as an independent verifier. Use when the user asks for the review ("fai la review", "lancia la review", review before commit or PR).
---

# Review with Codex

The team's canonical review prompt, turned into procedure: no regressions, readable,
maintainable, DRY, pre-existing defects fixed too, Codex as independent verifier. This skill
replaces typing that prompt; do not paste it on top.

## 1. Collect the whole diff

```bash
git status --short && git diff && git diff --staged
```

For a branch review, diff against the merge-base of the target branch instead. Read every
touched file in full, not just the hunks: regressions live in the callers, not in the diff.

## 2. Review, four questions per file

- **Regressions**: who calls this? Which contract, test or serialized shape changed meaning?
  What broke three folders away that no local test covers?
- **Readable**: will the next person understand this without the conversation that produced it?
- **DRY**: did this change introduce a second copy of logic that already exists? Search before
  assuming it did not.
- **Pre-existing defects** in the touched areas: fix them, do not sidestep them. If one is out
  of scope, say why and record it where the project keeps its traps (or as a spec), so it
  becomes work instead of folklore.

## 3. Run the project's definition of done

Every check the project defines, all of them, before claiming done: typically tests,
typecheck and lint. The list belongs in the repo's agent entry file (`AGENTS.md` or
equivalent); if it is missing there, ask for it and suggest writing it down. Where unit
tests mock the real thing (raw SQL, migrations, bundling), add a check against the real
local database or the production build.

## 4. The independent verifier

Consult Codex on the same diff following the `codex-thinking-partner` skill: read-only, one
round, narrow prompt. Verify each of its findings against the files, adopt what survives,
reject the rest with reasons.

## 5. Close

- Fix what survived review, re-run the checks that a fix could have invalidated.
- Report: findings fixed, findings rejected (yours and Codex's) with one-line reasons, checks
  output as it is. A skipped check is reported as skipped, never implied as passed.
- Do not commit: commits happen only when the user asks.
