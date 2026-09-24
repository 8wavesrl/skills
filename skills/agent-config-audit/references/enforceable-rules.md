# Prose rules a tool can enforce

A rule stated only in a context file is a request the model may skip. When one of these shows
up in CLAUDE.md or AGENTS.md, propose the tool instead and drop the prose once it is on.

| Prose rule | Enforce with | Notes |
|---|---|---|
| Always brace `if` blocks | ESLint `curly: ['error', 'all']` | `eslint-config-prettier` turns it off: place it after the Prettier preset. `all` does not conflict with Prettier |
| Use `import type` for types | `@typescript-eslint/consistent-type-imports` | Crashes on `.vue` files with no `<script>`: exclude them. `disallowTypeAnnotations: false` if `import()` types are allowed |
| No `<style scoped>` or CSS modules in Vue | `vue/enforce-style-attribute` with `allow: ['plain']` | Removing `scoped` makes class and `@keyframes` names global: prefix them with the component block |
| Imports at the top of the file | `import/first` | Forbidding dynamic imports as well: `no-restricted-syntax` on `ImportExpression` |
| `async/await` over `.then()` | `promise/prefer-await-to-then` (eslint-plugin-promise) | |
| No stray `console.log` | `no-console` | Allow it in scripts, where stdout is the interface |
| No `any` | `@typescript-eslint/no-explicit-any`, `strict` in tsconfig | |
| Package or layer boundaries | `@nx/enforce-module-boundaries`, `no-restricted-imports` | |
| Every UI string in every locale | `@intlify/vue-i18n/no-missing-keys` and similar | |
| Formatting (indent, quotes, width) | The formatter | Never prose |
| Commit message format | commitlint in a `commit-msg` hook | |
| Never run tool X directly | Claude Code `permissions.deny`, e.g. `Bash(npx vitest:*)`, or a `PreToolUse` hook | |
| No em or en dashes in prose | A pre-commit check: `git diff --cached -U0 \| grep -nP '^\+.*[\x{2013}\x{2014}]'` | Scope it to prose files if prompts are exempt |
| Tests pass before commit | A pre-commit hook or the CI gate | |

## Measuring before proposing

- A rule that needs no type information: pass it on the command line,
  `npx eslint . --rule 'curly: [error, all]' --format json -o /tmp/probe.json`.
- A typed rule, or one that needs `files` scoping: a throwaway config that imports the
  project's one and appends the rule, deleted after the run.
- Count by `ruleId`, by file and by whether a `fix` is attached: fixable violations are one
  command, the rest are manual work to size.
