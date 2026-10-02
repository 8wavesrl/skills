#!/usr/bin/env python3
"""The repository's definition of done, as one read-only command.

Checks every skill's frontmatter against its folder, the README links and skills table, the
cross-references between skills, the house rule on dashes and that the bundled Python scripts
compile. Prints each problem and exits 1 if there is any.

Usage: python3 scripts/check.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / 'skills'
# Skills a SKILL.md may name that ship with the harness rather than with this repo.
BUILTIN_SKILLS = {'code-review'}
DASHES = re.compile('[—–]')
# The one place dashes may appear: the lines that state the rule against them.
DASH_RULE = '(—/–)'
SKILL_REFERENCE = re.compile(r'`([a-z0-9-]+)`\s+skill\b')


def frontmatter(text):
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(':')
        if sep and not line.startswith(' '):
            fields[key.strip()] = value.strip()
    return fields


def main():
    problems = []
    skill_dirs = sorted(p for p in SKILLS.iterdir() if (p / 'SKILL.md').is_file())
    names = {p.name for p in skill_dirs}

    for skill in skill_dirs:
        fields = frontmatter((skill / 'SKILL.md').read_text())
        if fields.get('name') != skill.name:
            problems.append(f'{skill.name}/SKILL.md: name is {fields.get("name")!r}, folder is {skill.name!r}')
        if not fields.get('description'):
            problems.append(f'{skill.name}/SKILL.md: description missing')

    readme = (ROOT / 'README.md').read_text()
    for target in re.findall(r'\]\((skills/[^)#]+)', readme):
        if not (ROOT / target).exists():
            problems.append(f'README.md: link to {target} does not resolve')
    for name in sorted(names):
        if f'[`{name}`](skills/{name}/SKILL.md)' not in readme:
            problems.append(f'README.md: skill {name} missing from the skills table')

    docs = sorted(SKILLS.rglob('*.md')) + [ROOT / n for n in ('README.md', 'AGENTS.md', 'CLAUDE.md')
                                           if (ROOT / n).exists()]
    for doc in docs:
        text = doc.read_text()
        rel = doc.relative_to(ROOT)
        for ref in sorted(set(SKILL_REFERENCE.findall(text)) - names - BUILTIN_SKILLS):
            problems.append(f'{rel}: names the `{ref}` skill, which does not exist')
        for number, line in enumerate(text.splitlines(), 1):
            if DASHES.search(line) and DASH_RULE not in line:
                problems.append(f'{rel}:{number}: em or en dash in prose')

    for script in sorted(SKILLS.glob('*/scripts/*.py')) + sorted((ROOT / 'scripts').glob('*.py')):
        try:
            compile(script.read_text(), str(script), 'exec')
        except SyntaxError as error:
            problems.append(f'{script.relative_to(ROOT)}:{error.lineno}: {error.msg}')

    for problem in problems:
        print(problem)
    print(f'{len(problems)} problem(s) across {len(skill_dirs)} skills')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
