# Eight Wave agent skills

Portable skills for coding agents, published with `npx skills add 8wavesrl/skills` and synced
to claude.ai as the `eightwave` plugin. Everything under `skills/` ships to other projects:
what you write there is read by agents you will never see, so it has to stand on its own.

## Layout

- `skills/<name>/SKILL.md`: frontmatter `name` equal to the folder, and a `description` that
  says what the skill does and when to use it, trigger phrases included.
- Bundled scripts in `skills/<name>/scripts/`, invoked from the skill as
  `python3 <this skill's directory>/scripts/<script>.py`: read-only, standard library only.
- Templates and references next to the skill that uses them.

## Conventions

- English for everything in the repo. Italian trigger phrases inside a `description` are fine:
  they are what users type.
- No em or en dashes in prose: use a colon, parentheses, a comma or a new sentence.
- "Eight Wave" in prose; "8 wave S.r.l." only as the legal name (LICENSE, copyright line).
- Renaming a skill breaks every lock that pins the old name: add the pair to "Renamed skills"
  in the README, with the date.

## Definition of done

```bash
python3 scripts/check.py
```

It checks frontmatter against folders, README links and the skills table, the skills each
SKILL.md names, dashes, and that the bundled scripts compile. There are no unit tests: a change
to a bundled script is done when it has run on real data and on fixtures for its edge cases
(build them in a temporary directory, never in the repo).
