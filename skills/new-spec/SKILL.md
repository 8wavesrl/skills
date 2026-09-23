---
name: new-spec
description: Create, update, release or archive a feature spec and keep the project roadmap in sync. Works in the language the user asks for and in whatever specs folder the project uses (docs/specs/ by default). Use when the user asks to write a new spec, update a spec's status, release a spec (move to released/) or archive one ("nuova spec", "scrivi una spec", "rilascia la spec", "archivia la spec").
---

# Specs lifecycle

A spec lives in one of three folders, and only the active ones appear in the roadmap.

| Folder | Content | Status |
|---|---|---|
| `<specs>/` (root) | active specs | draft, or partial with what is done |
| `<specs>/released/` | fully shipped | released |
| `<specs>/archived/` | obsolete or superseded | keep the last status, add a line on why |

## Step 0: resolve paths and language

Do this once per task, before touching any file, and state the result to the user in one line
(e.g. "Spec in `docs/specs/`, roadmap `docs/ROADMAP.md`, lingua: italiano").

**Specs folder** (`<specs>`), first match wins:

1. A path the user named in the request.
2. A path recorded in the project's `CLAUDE.md` / `AGENTS.md`.
3. An existing folder among `docs/specs/`, `specs/`, `doc/specs/`, `documentation/specs/`.
   If several exist, ask which one.
4. None exists: propose `docs/specs/` and create it only after the user agrees.

In a monorepo, prefer the folder closest to the package the feature touches, if it has one.

**Roadmap**: the file the specs README links to; otherwise `ROADMAP.md` in the parent of
`<specs>` (e.g. `docs/ROADMAP.md`), then at the repo root. If there is none, do not create one
unprompted: ask once, and if the user declines skip every roadmap step below.

**Project rules win.** If `<specs>/README.md` or `<specs>/_TEMPLATE.md` exist, read both: they
override this file where they diverge (sections, status values, naming). The bundled templates
are only a fallback.

**Language**, first match wins:

1. The language the user asked for explicitly ("scrivila in inglese", "in French").
2. The language of the specs already in `<specs>` (read one or two headers). A project mixing
   languages within one spec is worse than one written in the "wrong" language, so follow the
   folder and mention it if it differs from the conversation.
3. The language the user is writing in.

The language governs prose, headings, header labels, status values, file names and the roadmap
cells. Identifiers, file paths, APIs, commands and product names stay as they are. Folder
names `released/` and `archived/` never change.

## Localized vocabulary

Use these exact strings for Italian and English. For any other language translate them once,
reuse the same wording everywhere, and match any wording already present in the project.

| Key | Italiano | English |
|---|---|---|
| Header: status | `Stato` | `Status` |
| Header: date | `Data` | `Date` |
| Header: scope | `Ambito` | `Scope` |
| Header: related | `Spec collegate` | `Related specs` |
| No related specs | `Nessuna` | `None` |
| Draft | `Bozza (non implementata)` | `Draft (not implemented)` |
| Partial | `Parziale (<cosa è fatto>)` | `Partial (<what is done>)` |
| Released | `Rilasciata` | `Released` |
| Archived because | `Archiviata: <motivo>` | `Archived: <reason>` |
| Sections | `Panoramica`, `Obiettivi e non-obiettivi`, `Design`, `Fasi di rilascio` | `Overview`, `Goals and non-goals`, `Design`, `Rollout phases` |
| Roadmap columns | `Spec`, `Ondata`, `Effort`, `Dipendenze`, `Stato` | `Spec`, `Wave`, `Effort`, `Dependencies`, `Status` |
| Roadmap short status | `Bozza`, `Parziale` | `Draft`, `Partial` |
| To be defined | `da definire` | `TBD` |
| Empty roadmap | `Al momento non ci sono spec attive.` | `There are no active specs at the moment.` |

## New spec

1. Pick a kebab-case file name in the spec's language describing the feature
   (`scadenze-dismesse.md`, `retired-deadlines.md`). Check that no spec on a similar topic
   already exists in any of the three folders: if one does, propose updating it instead.
2. Start from the project's `<specs>/_TEMPLATE.md`. If there is none, use the bundled
   [templates/spec.it.md](templates/spec.it.md) or [templates/spec.en.md](templates/spec.en.md);
   for any other language translate the English one with the vocabulary above. Write the copy
   to `<specs>/<name>.md` and fill the four-line header:
   - status: draft
   - date: today, `YYYY-MM-DD`
   - scope: one or two lines on what the spec introduces
   - related specs: relative links with the relationship, or the "none" word
3. Remove the HTML comment with the conventions from the copy.
4. Write the four sections in the chosen language. In `Design` list the exact paths of the
   files to create or modify: check them in the codebase, do not guess.
5. Add a row to the roadmap table:
   `| [<Title>](<relative path to the spec>) | <wave> | <effort> | <dependencies> | <draft> |`.
   The link is relative to the roadmap file, not to the repo root. If the table still holds the
   empty placeholder row `| | | | | |` and the empty-roadmap sentence, remove both. Ask the user
   for wave and effort when they are not clear from the conversation; write the "to be defined"
   word rather than invent.

## Status update

Set the header status to partial, saying what is done, and update the status cell of its
roadmap row.

## Release (spec fully implemented)

1. `git mv <specs>/<name>.md <specs>/released/<name>.md` (create `released/` if missing).
2. Set the status to released.
3. Fix relative links: inside the moved file (one more `../`) and in every file pointing to it
   (other specs, the roadmap, READMEs). Grep the repo for the file name to find them.
4. Remove its row from the roadmap. If the table is now empty, restore the placeholder row and
   the empty-roadmap sentence.
5. User-facing work also needs a release note: use the `changelog` skill, in the same
   language as the existing release notes.

## Archive (superseded or dropped)

Same as release, but into `<specs>/archived/`, and without changing the status. Add a line
under the header block with the reason and, if any, the spec that supersedes it, e.g.
`> **Archiviata**: superata da [nuova-spec.md](../nuova-spec.md).`

## Writing rules

- One language per spec, the one resolved in step 0. Do not switch mid-document.
- No em dashes or en dashes: use a colon, parentheses, a comma or a new sentence.
- Always move files with `git mv`, never delete and recreate.
- Before closing, grep for every link you added or changed and check that the target exists
  at the resolved path.
