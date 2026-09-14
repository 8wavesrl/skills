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

**On a security or data-protection change this step gates the commit**, not the PR and not the
release. Measured on 2026-09-03, on a phase that closed five tenant-boundary defects: the round
was skipped because the account had hit its usage limit, the work shipped that evening, and the
round the next day found two GDPR erasures the phase had left half closed, plus two queries its
own fix had missed in the very file it was correcting. The author had read those files three
times. Waiting for the quota to reset would have cost an afternoon; not waiting put incomplete
erasures in production. This does not contradict step 5: the agent still does not commit on its
own, it means the round is not something to catch up on afterwards.

**Pull on the mild findings first.** The two findings that paid for their whole round that day
both arrived phrased as nuance rather than as defects. "This measures reachability, not the
exact charge" turned out to mean the script asked its question by a cursor while both programs
that act on the answer ask by a marker. A reviewer who did not write the code states things
carefully; establishing the severity is your job, not theirs.

## 5. Close

- Fix what survived review, re-run the checks that a fix could have invalidated.
- Report: findings fixed, findings rejected (yours and Codex's) with one-line reasons, checks
  output as it is. A skipped check is reported as skipped, never implied as passed.
- Do not commit: commits happen only when the user asks.

**An unverified fix is not a fix.** Measured on 2026-09-13: a finding about a sync that kept an
expired cursor for ever was fixed during this very step by a script that then stopped on a
later anchor and saved nothing. The report said the finding was closed, the file had never
changed, and the next round found the same defect untouched. Read every fix back from the file
that holds it (grep for the line you believe you wrote) before writing it down as fixed. A
finding marked fixed with nothing behind it is worse than one left open, because it is the one
nobody looks at again.
