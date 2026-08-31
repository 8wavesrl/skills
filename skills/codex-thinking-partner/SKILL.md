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
timeout 540 codex exec -s read-only -C <repo-root> -o <answer-file> "<prompt>" 2>&1 | tail -5
```

- `-s read-only` always: two agents editing the same tree means conflicts and lost authorship.
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

## After the answer: verify, then adopt

Treat every finding as a hypothesis:

1. Check each claim against the actual files before acting on it.
2. Expect casualties: in our logged rounds roughly a third of findings died on
   verification, including one fabricated reference (a test campaign absent from the cited spec).
3. Adopt what survives, reject the rest, and report both lists to the user with one-line reasons.
   Never silently merge advice.

A second opinion is for deciding, not for being agreed with: a verifiable dissent is the win.
