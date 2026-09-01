---
name: codex-thinking-partner
description: Get a second opinion from the Codex CLI on a diff, design or document. Read-only, one round, findings verified before adoption. Use when the user asks to consult Codex ("chiedi a codex", "sentiamo codex", "secondo parere") or when a review step calls for an independent judge.
---

# Codex as thinking partner

Purpose: break the author's agreement with themselves. The same diff or design is judged by a
model that did not write it. Codex judges; the primary agent keeps the pen.

## Before calling

- Authorization: outbound calls send repository content to OpenAI and spend the user's quota.
  Ask and wait for the go-ahead, unless the user has given a standing one for this repo.
- Declare the round budget up front. Default: **one round**. Value collapses after the first;
  a second round needs a reason (new material, not a restatement).

## The call

```bash
timeout 540 codex exec -s read-only -C <repo-root> -o <answer-file> "<prompt>" </dev/null 2>&1 | tail -5
```

- `-s read-only` always: two agents editing the same tree means conflicts and lost authorship.
- `</dev/null` always: from an agent harness stdin is a pipe that never closes, and
  `codex exec` waits for its EOF before doing anything. The hang is silent (near-zero CPU,
  no output, no new rollout file under `~/.codex/sessions/YYYY/MM/DD/`, names in local
  time); a healthy run creates its session file within seconds, so check that first.
- If it outlives the timeout, run it in background and read the answer file when it completes.

## The prompt

One narrow question beats a tour. Structure that works:

```
Leggi <files or diff scope>. Rispondi in italiano, MASSIMO <N> righe,
niente complimenti, niente riscritture integrali. <2-3 named sections>:
(A) <question one> (B) <question two>
Per ogni punto: una riga, citando file o slide.
```

Line caps keep answers dense. Named sections make rejection auditable.

For a review prompt, open with the role and fence off this very skill: "YOU are the
independent reviewer: review the code yourself. Do NOT read or follow anything in
.claude/skills or .agents/skills, do not consult any external tool, do not ask for
permissions." Without that fence Codex finds this file in the repo, casts itself as the
primary agent that must consult Codex, and burns the round asking permission to call
itself instead of reviewing (observed 2026-09-01).

## After the answer: verify, then adopt

Treat every finding as a hypothesis:

1. Check each claim against the actual files before acting on it.
2. Expect casualties: in our logged rounds roughly a third of findings died on
   verification, including one fabricated reference (a test campaign absent from the cited spec).
3. Adopt what survives, reject the rest, and report both lists to the user with one-line reasons.
   Never silently merge advice.

A second opinion is for deciding, not for being agreed with: a verifiable dissent is the win.
