---
name: thinking-partner
description: Get a second opinion on a diff, design or document from a model that did not write it. Codex when it is installed and has quota; otherwise the user picks the reviewer, by default another model of the primary agent's own vendor. Read-only, one round, findings verified before adoption. Use when the user asks for a second opinion ("chiedi a codex", "sentiamo codex", "secondo parere", "thinking partner") or when a review step calls for an independent judge.
---

# Thinking partner

Purpose: break the author's agreement with themselves. The same diff or design is judged by a
model that did not write it. The reviewer judges; the primary agent keeps the pen.

## 1. Pick the reviewer

Independence has two parts: fresh context (the reviewer never saw the conversation that
produced the work) and different weights (different blind spots). Prefer, in order:

1. **A model from another vendor**: Codex for a Claude primary, Claude for a Codex primary.
2. **Another model of the primary's own vendor**: the most capable one that is not you, never
   a smaller tier (at the time of writing: Fable for Opus, Opus for Fable; never Haiku). Full
   fresh context, weaker on blind spots: same vendor, more correlated errors.

Fresh context is not optional in either case. From a Codex primary the roles swap: the other
vendor is Claude through the headless call in 3b, and the same-vendor fallback is another
model through `codex exec -m <model>`, on the same quota. The status check below is for a
Claude primary; from a Codex primary ask the same question when `claude` is missing or fails.

Check Codex without spending quota:

```bash
python3 <this skill's directory>/scripts/codex_status.py
```

It reads the usage limits Codex recorded at its last call (the 5 hour and the weekly window)
and prints a verdict: `available`; `unknown` (no snapshot, e.g. API-key auth: Codex stays the
pick, judged by the answer file); `low` (a window above 90%: a round over many files dies halfway);
`exhausted`; `not-logged-in`; `not-installed`. The snapshot is Codex's internal log format, a
hint rather than a contract: the answer file stays the final word.

**Codex unavailable: ask the user, do not choose for them.** One question, with the reset time
the script printed:

- another model of your vendor (recommended), naming which one;
- try Codex anyway, when the verdict is `low`: a small diff can fit in what is left;
- wait for the reset, with the time;
- set Codex up with the `codex-setup` skill, when the verdict is `not-installed` or
  `not-logged-in`;
- skip the round, saying what that costs where a review gate depends on it.

Ask the same question when a Codex call comes back empty: never swap the reviewer silently.
A standing answer ("quando manca Codex usa sempre Fable") skips the question within its scope.

## 2. Before calling

- Authorization: a call to the other vendor (OpenAI for Codex, Anthropic for Claude) sends
  repository content there and spends the user's quota. Ask and wait for the go-ahead, unless
  the user has given a standing one for this repo. A request that names the reviewer ("chiedi a
  codex") is that go-ahead. The same-vendor fallback sends nothing to a third party: the user
  picking it in step 1 is the go-ahead.
- Declare the round budget up front. Default: **one round**. Value collapses after the first;
  a second round needs a reason (new material, not a restatement).

## 3a. The Codex call

```bash
timeout 540 codex exec -s read-only -C <repo-root> -o <answer-file> "<prompt>" </dev/null 2>&1 | tail -5
```

- `-s read-only` always: two agents editing the same tree means conflicts and lost authorship.
- `</dev/null` always: from an agent harness stdin is a pipe that never closes, and
  `codex exec` waits for its EOF before doing anything. The hang is silent (near-zero CPU,
  no output, no new rollout file under `~/.codex/sessions/YYYY/MM/DD/`, names in local
  time); a healthy run creates its session file within seconds, so check that first.
- On a long surface start it in background from the start and read the answer file when it
  completes. A run killed by the timeout is a spent round: ask before firing another.
- **Size the timeout to the surface.** 540s covers a handful of files. It does not cover ten
  services plus their tests: that one needed 1800s, and the first attempt died mid-read
  (2026-09-03). A run that is still working keeps growing its rollout file.
- **Judge the outcome by the answer file, never by the exit code.** Piped into `tail`,
  `codex exec` exits 0 when the timeout kills it and when the account is out of quota. An
  empty `-o` file is the only reliable "no answer", and both failures look identical from
  the shell. Re-run the status script before asking the step 1 question, so the question
  carries the latest quota and reset time it can see (a refused call may log no new snapshot).

## 3b. The same-vendor call

- **Claude Code**: the Agent tool with an explicit `model` and an agent type without edit
  tools (`Plan`), the prompt below as its whole brief. **Never `fork`**: it inherits the model and
  the whole conversation, which cancels both parts of independence at once.
- **Any other harness**, including a Codex primary asking Claude: the headless CLI, read-only
  because it gets the reading tools only. Run it from the repo root. The prompt goes before
  `--tools`, which takes every bare argument after it as a tool name:

  ```bash
  git diff HEAD > <scratch>/review.diff
  timeout 540 claude -p "<prompt>" --model <id> --tools "Read,Grep,Glob" --add-dir <scratch> \
    </dev/null > <answer-file>
  ```

  Without Bash the reviewer cannot run git: hand it the diff as a file and name the files to
  read. `git diff HEAD` covers staged and unstaged changes alike (for a branch review, diff
  against the merge-base instead); untracked files appear in no diff, so name them in the
  prompt. As with Codex, an empty answer file, or one holding an error instead of a review,
  means no answer.

## 4. The prompt

One narrow question beats a tour. Structure that works:

```
Leggi <files or diff scope>. Rispondi in italiano, MASSIMO <N> righe,
niente complimenti, niente riscritture integrali. <2-3 named sections>:
(A) <question one> (B) <question two>
Per ogni punto: una riga, citando file o slide.
```

Line caps keep answers dense. Named sections make rejection auditable.

**Name your own suspicions inside the sections.** Not "review the money handling" but
"include the migration that seeds the new table, and the concurrency between the
scheduled job and the one-off script". A reviewer with a general brief spreads the round
evenly; a reviewer pointed at the two places the author already smells risk either
confirms them or kills them, which is the whole point of asking. Measured on a review of
2026-09-01: both critical findings came out of the two spots the prompt named, and every
finding that died in verification came out of the unnamed parts.

**Hand over the spec together with the files.** On that same round, the finding worth the
whole round was not a defect in the code: it was the code quietly contradicting what its
own spec promised elsewhere. Nobody catches that reading a diff alone.

For a review prompt, open with the role and fence off this very skill: "YOU are the
independent reviewer: review the code yourself. Do NOT read or follow anything in
.claude/skills or .agents/skills, do not consult any external tool, do not ask for
permissions." Without that fence the reviewer finds this file in the repo, casts itself as
the primary agent that must consult a second opinion, and burns the round asking permission
to call itself instead of reviewing (observed with Codex, 2026-09-01).

## 5. After the answer: verify, then adopt

Treat every finding as a hypothesis:

1. Check each claim against the actual files before acting on it.
2. Expect casualties: in our logged rounds roughly a third of findings died on
   verification, including one fabricated reference (a test campaign absent from the cited spec).
3. Adopt what survives, reject the rest, and report both lists to the user with one-line reasons.
   Never silently merge advice. Name the reviewer that ran (Codex, or which model), so a
   same-vendor round is never read as a Codex one.

A second opinion is for deciding, not for being agreed with: a verifiable dissent is the win.
