---
name: full-review
description: Full-diff review before commit, no regressions, readable, maintainable, DRY, pre-existing bugs flagged and fixed, the project's checks run, and a model that did not write the code consulted read-only as independent verifier (Codex, or the user's pick when Codex is unavailable). Use when the user asks for the review ("fai la review", "lancia la review", "full review", review before commit or PR).
---

# Full review

The team's canonical review prompt, turned into procedure: no regressions, readable,
maintainable, DRY, pre-existing defects fixed too, an independent model as verifier. This
skill replaces typing that prompt; do not paste it on top.

## 1. Collect the diff

```bash
git status --short && git diff HEAD --stat
```

The stat shows where the weight is before you spend context on it. `git diff HEAD` covers
staged and unstaged changes alike; for a branch review, diff against the merge-base of the
target branch instead.

Leave out of the diff, and out of the reading, what nobody reviews line by line: lockfiles,
generated code, build output, migration snapshots, recorded fixtures. A lockfile diff alone
can run to thousands of lines. Exclude them with pathspecs (`*` crosses folders):

```bash
git diff HEAD -- . ':!pnpm-lock.yaml' ':!*_snapshot.json' ':!dist/'
```

Note only that they changed and whether that is expected: a lockfile that moved with no
manifest change, or a manifest change with no lockfile, is a finding.

Read every other touched file in full, not just the hunks: regressions live in the callers,
not in the diff. Untracked files (`??` in the status) appear in no diff: read those in full
too.

## 2. Review

Do it yourself, in this context, without spawning reviewer subagents. You read every touched
file in step 1; a fan-out of agents rereading the same files on your own model multiplies the
cost without adding a perspective. The one extra model this review pays for is the
independent verifier in step 5.

**Claude Code's built-in `code-review` only on request.** It fans out parallel reviewer
agents, more at each level (`max` starts many), and can drain the user's usage in minutes. Run
it only when the user asks for it in this review, with an explicit level (without one it
reuses whatever level the user typed last): the one they name, otherwise `low`, the cheapest.
On a security or data-protection change you may offer it in one line and wait for the answer;
never start it unasked. Never with `--fix` (its findings are hypotheses: you check them
against the files before step 3 fixes them) or `--comment` (it posts on the PR). It does not
replace step 5.

Four questions per file. They reach where a diff review does not: callers three folders away
and pre-existing defects in the touched areas.

- **Regressions**: who calls this? Which contract, test or serialized shape changed meaning?
  What broke three folders away that no local test covers?
- **Readable**: will the next person understand this without the conversation that produced it?
- **DRY**: did this change introduce a second copy of logic that already exists? Search before
  assuming it did not.
- **Pre-existing defects** in the touched areas: fix them, do not sidestep them. If one is out
  of scope, say why and record it where the project keeps its traps (or as a spec), so it
  becomes work instead of folklore.

## 3. Fix what you found

Fix your own findings and the pre-existing defects now, before the checks and before the
verifier. The verifier then reads the code that will be committed, spends its one round on
what you missed instead of rediscovering what you already knew, and sees your fixes, which
otherwise nobody would review. Keep a list as you go, one line per finding (file, defect,
fix): step 5 hands it to the verifier and step 6 reports it.

**An unverified fix is not a fix.** Measured on 2026-09-13: a finding about a sync that kept an
expired cursor for ever was fixed by a script that then stopped on a later anchor and saved
nothing. The report said the finding was closed, the file had never changed, and the next
round found the same defect untouched. Read every fix back from the file that holds it (grep
for the line you believe you wrote) before writing it down as fixed. A finding marked fixed
with nothing behind it is worse than one left open, because it is the one nobody looks at
again.

## 4. Run the project's definition of done

Every check the project defines, all of them, before claiming done: typically tests,
typecheck and lint. The list belongs in the repo's agent entry file (`AGENTS.md` or
equivalent); if it is missing there, ask for it and suggest writing it down. Where unit
tests mock the real thing (raw SQL, migrations, bundling), add a check against the real
local database or the production build. Where the project defines a scoped form of its
checks (`nx affected`, a workspace filter), use it; do not invent a narrower scope the project
does not define.

Send each check's output to a file and read the summary and the failures, not the whole log:
a full test run pasted into the conversation can cost more context than the review itself.

```bash
<check> > <scratch>/<check>.log 2>&1; echo "exit $?"; tail -30 <scratch>/<check>.log
```

Judge by the exit code, then grep the log for the failing cases. Do not pipe the check
straight into `tail`: the pipe reports `tail`'s exit code, not the check's.

## 5. The independent verifier

Consult a second model on the diff as it stands after step 3, following the `thinking-partner`
skill: the other vendor when it is available (Codex from a Claude primary), otherwise the
reviewer the user picks there. Read-only, one round, narrow prompt, with the step 1 exclusions
applied to the diff it receives. Put your step 3 list in the prompt and ask it to check that
those fixes are complete rather than report the defects again. Verify each of its findings
against the files, adopt what survives, reject the rest with reasons.

**Size the round to the diff.** On a trivial diff (copy, docs, comments, formatting, a single
config value), recommend skipping the round before starting it, even under a standing
go-ahead: one line, the user decides. Never recommend skipping on a security or
data-protection change.

**On a security or data-protection change this step gates the commit**, not the PR and not the
release. Measured on 2026-09-03, on a phase that closed five tenant-boundary defects: the round
was skipped because the account had hit its usage limit, the work shipped that evening, and the
round the next day found two GDPR erasures the phase had left half closed, plus two queries its
own fix had missed in the very file it was correcting. The author had read those files three
times. Waiting for the quota to reset would have cost an afternoon; not waiting put incomplete
erasures in production. This does not contradict step 6: the agent still does not commit on its
own, it means the round is not something to catch up on afterwards. When Codex is out on such
a change, say in the `thinking-partner` question that this round gates the commit: a
same-vendor round satisfies the gate, skipping means no commit until a round has run.

**Pull on the mild findings first.** The two findings that paid for their whole round that day
both arrived phrased as nuance rather than as defects. "This measures reachability, not the
exact charge" turned out to mean the script asked its question by a cursor while both programs
that act on the answer ask by a marker. A reviewer who did not write the code states things
carefully; establishing the severity is your job, not theirs.

## 6. Close

- Fix what survived the verifier, read each fix back as in step 3, and re-run the checks a fix
  could have invalidated.
- Report: findings fixed (yours from step 3, the verifier's from here), findings rejected
  (yours, the verifier's, `code-review`'s if it ran) with one-line reasons, which model
  verified or who decided to skip the round, checks output as it is. A skipped check is
  reported as skipped, never implied as passed.
- Do not commit: commits happen only when the user asks.
