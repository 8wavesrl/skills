---
name: codex-setup
description: Install, authenticate and smoke-test the OpenAI Codex CLI so it can serve as a read-only second opinion. Use when codex is missing (command not found), on a new machine or project, or when the user asks to install, set up or initialize Codex.
---

# Codex setup

Goal: a working `codex` binary, authenticated, proven with one read-only call. Codex here is a
reviewer, not a second author: nothing in this setup grants it write access.

## 1. Check what is already there

```bash
codex --version && codex login status
```

If both succeed, skip to the smoke test. `codex doctor` diagnoses a broken install.

## 2. Install

```bash
npm install -g @openai/codex
```

Requires Node 18+. After install re-run `codex --version`.

## 3. Authenticate

Two options, pick with the user (it is their account and their quota):

- ChatGPT account (OAuth, opens a browser): `codex login`
- API key, without ever pasting it in a command line or chat:
  `printenv OPENAI_API_KEY | codex login --with-api-key`

Verify with `codex login status`. Never ask the user to paste the key into the conversation.

## 4. Smoke test, read-only

```bash
codex exec -s read-only --ephemeral --skip-git-repo-check "Reply with exactly: OK"
```

Expect `OK` in the final message. `--ephemeral` keeps the test out of session history.

## Defaults that matter

- Every advisory call uses `-s read-only`: Codex judges, the primary agent writes.
- Calls spend the user's quota and send repository content to OpenAI: get the user's go-ahead
  before the first call in a project, and respect whatever standing rule they set.
- Long runs: wrap in a timeout or run in background; capture the final answer with
  `-o <file>` (`--output-last-message`) instead of scraping the log.
- User config lives in `~/.codex/config.toml`; do not edit it without being asked.

For how to actually consult it, see the `codex-thinking-partner` skill.
