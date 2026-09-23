---
name: changelog
description: Add user-facing release notes, one file per version, folding them into the pending version when the latest one has not shipped yet. Works in the language the user asks for and in whatever changelog folder the project uses (docs/changelog/ by default). Use when the user asks for a changelog entry or release notes ("changelog", "note di rilascio", "release notes"), or when user-facing work is being closed.
---

# Release notes

Each version has one file `<changelog>/<version>.md`. A version is shipped once its release
tag exists; until then its file is pending and collects every new bullet.

## Step 0: resolve path, language and versioning

Do this once per task, before touching any file, and state the result to the user in one line
(e.g. "Changelog in `docs/changelog/`, lingua: italiano, versioning GitVersion (minor su main)").

**Changelog folder** (`<changelog>`), first match wins:

1. A path the user named in the request.
2. A path recorded in the project's `CLAUDE.md` / `AGENTS.md`.
3. An existing folder among `docs/changelog/`, `changelog/`, `docs/release-notes/`,
   `release-notes/`. If several exist, ask which one.
4. None exists: propose `docs/changelog/` and create it only after the user agrees. If the
   project keeps a single `CHANGELOG.md` instead, say so and ask whether to follow that file's
   format (add the bullets under its unreleased section) rather than introduce a folder.

In a monorepo, prefer the folder closest to the package the change touches, if it has one.

**Project rules win.** If `<changelog>/_TEMPLATE.md` or `<changelog>/README.md` exist, read
them: they override this file where they diverge (frontmatter, headings, tone). The bundled
templates are only a fallback.

**Language**, first match wins:

1. The language the user asked for explicitly ("scrivile in inglese", "in German").
2. The language of the latest version files in `<changelog>`: readers see one changelog, so
   follow the folder and mention it if it differs from the conversation.
3. The language the user is writing in.

The language governs the title, the bullets and the section headings. Frontmatter keys
(`version`, `date`, `title`) and version numbers never change.

**Versioning scheme**, first match wins:

1. `GitVersion.yml` at the repo root: read the increment configured for the current branch
   (e.g. `main` bumps the minor, `hotfix/*` the patch).
2. Release tags only: infer the usual bump from the last few tags.
3. A version in the manifest (`package.json`, `*.csproj`, `pyproject.toml`, `Cargo.toml`):
   use that as the next version if it is ahead of the latest tag.
4. None of the above, or not sure: ask the user for the version number.

## 1. Find the target file

1. `git fetch --tags`, then read the latest release tag:
   `git tag -l --sort=-v:refname | grep -E '^v?[0-9]+\.[0-9]+\.[0-9]+$' | head -1`.
   Ignore non-SemVer tags (e.g. `product-clone`). Keep the project's prefix convention
   (`v1.2.0` vs `1.2.0`) in mind when comparing, but file names carry the bare number.
2. List the version files in `<changelog>` (skip `_TEMPLATE.md` and `README.md`).
3. If a file has a version **greater** than the latest tag, it is still pending: add the new
   bullets to that file and stop looking.
4. Otherwise create the next version with the scheme from step 0 (e.g. minor bump:
   `0.224.0` becomes `0.225.0`). If unsure, ask the user.

## 2. Write the entry

Start from the project's `<changelog>/_TEMPLATE.md`. If there is none, use the bundled
[templates/release.it.md](templates/release.it.md) or
[templates/release.en.md](templates/release.en.md); for any other language translate the
English one.

- Frontmatter has only `version`, `date` (today, `YYYY-MM-DD`) and `title`. When folding into
  a pending file, update `date` to today and adjust `title` if the new bullets change its
  meaning.
- Bullets are written for the customer in the resolved language: what changes for the person
  using the product, not how it was implemented. No commit messages, file names, ticket ids or
  technical jargon. Use the product name the existing notes use.
- One bullet per visible change; merge bullets that describe the same feature, including with
  bullets already in a pending file.
- Optional `###` section headings only when the release groups several areas.
- One language per file. Do not mix languages with the bullets already there.
- No em dashes or en dashes: use a colon, parentheses, a comma or a new sentence.
- Skip purely internal work (refactoring, CI, docs, dependency bumps) unless it changes
  something the user sees.

## 3. Source of the bullets

Base the bullets on the actual changes: the conversation, the related spec (see the `new-spec`
skill), or `git log <latest tag>..HEAD` on the current branch. Show the bullets to the user
before writing them if the scope is not obvious.
