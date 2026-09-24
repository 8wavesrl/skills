#!/usr/bin/env python3
"""Read-only audit of a project's agent configuration.

Prints a Markdown report of the measurable findings: context files, installed skills and
their lock, real skill and MCP usage from Claude Code transcripts, the memory index and the
settings. It never writes, moves or deletes anything.

Usage: python3 audit.py [--repo PATH] [--days N] [--json]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOME = Path.home()
CLAUDE_HOME = Path(os.environ.get('CLAUDE_CONFIG_DIR') or HOME / '.claude')
CLAUDE_PROJECTS = CLAUDE_HOME / 'projects'
CONTEXT_FILE_NAMES = ('CLAUDE.md', 'CLAUDE.local.md', 'AGENTS.md', 'GEMINI.md')
CONTEXT_LINE_BUDGET = 200
# Share of content words two bullets must have in common to read as the same rule: tuned so
# a paraphrase is caught and two rules on neighbouring topics are not.
SIMILAR_RULE_THRESHOLD = 0.25
PROJECT_SKILL_DIRS = ('.agents/skills', '.claude/skills')
GLOBAL_SKILL_DIRS = (HOME / '.agents' / 'skills', CLAUDE_HOME / 'skills')
# A description that claims every task, not one that is emphatic about its own domain
# ("ANY class name in a project that uses X" is scoped and does not match)
BROAD_TRIGGER = re.compile(
    r'\b(?:any|every|all)\s+(?:coding\s+|programming\s+|development\s+)?(?:tasks?|requests?|prompts?)\b',
    re.I,
)
CLOSED_MARKER = re.compile(r'\b(RESOLVED|CLOSED|FIXED|MITIGATED|DONE|CHIUSO|RISOLTO)\b')
OPEN_MARKER = re.compile(r'\b(OPEN|APERTO)\b')
MARKDOWN_LINK = re.compile(r'\[[^\]]*\]\(([^)\s]+)\)')
BACKTICK_TOKEN = re.compile(r'`([a-z0-9][a-z0-9:-]*)`')
SKILL_WORD = re.compile(r'\bskills?\b', re.I)
SLASH_COMMAND = re.compile(r'<command-name>/?([\w:.-]+)</command-name>')
SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', '.nx', '.next', 'coverage'}


class Report:
    """Collects findings by section, each tagged fix, review or info."""

    def __init__(self):
        self.sections = defaultdict(list)

    def add(self, section, level, text):
        self.sections[section].append({'level': level, 'text': text})

    def counts(self):
        return Counter(f['level'] for items in self.sections.values() for f in items)


def sha(path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


def read_text(path):
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def frontmatter_description(skill_md):
    """Returns the description field of a SKILL.md, folded scalars joined into one line."""
    text = read_text(skill_md)
    match = re.match(r'---\n(.*?)\n---', text, re.S)
    if not match:
        return ''
    lines, collecting = [], False
    for line in match.group(1).splitlines():
        if line.startswith('description:'):
            collecting = True
            lines.append(line[len('description:'):])
            continue
        if collecting and re.match(r'^[A-Za-z][\w-]*:', line):
            break
        if collecting:
            lines.append(line)
    text = ' '.join(part.strip() for part in lines).strip()
    return re.sub(r'^[>|][-+]?\s*', '', text).strip().strip('"\'')


def repo_files(repo, names):
    """Tracked files with one of the given basenames, falling back to a walk outside git."""
    try:
        out = subprocess.run(
            ['git', '-C', str(repo), 'ls-files', '--cached', '--others', '--exclude-standard'],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        return [repo / f for f in out if Path(f).name in names]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            found += [Path(root) / f for f in files if f in names]
        return found


def scan_skill_dir(directory, scope):
    """One record per skill folder or link in a skills directory."""
    skills = {}
    if not directory.is_dir():
        return skills
    for entry in sorted(directory.iterdir()):
        if entry.name.startswith('.'):
            continue
        skill_md = entry / 'SKILL.md'
        broken = entry.is_symlink() and not entry.exists()
        if not broken and not skill_md.is_file():
            continue
        skills[entry.name] = {
            'name': entry.name,
            'scope': scope,
            'dir': str(directory),
            'link': entry.is_symlink(),
            'target': os.path.realpath(entry),
            'broken': broken,
            'hash': None if broken else sha(skill_md),
            'mtime': None if broken else datetime.fromtimestamp(skill_md.stat().st_mtime).date().isoformat(),
            'description': '' if broken else frontmatter_description(skill_md),
        }
    return skills


def other_skill_names():
    """Skill names available from claude.ai sync and plugins, for reference checks only."""
    names = set()
    for base in (CLAUDE_HOME / 'skills' / 'synced', CLAUDE_HOME / 'plugins'):
        if base.is_dir():
            for skill_md in base.rglob('SKILL.md'):
                names.add(skill_md.parent.name)
    return names


def project_key(repo):
    return re.sub(r'[^A-Za-z0-9]', '-', str(repo.resolve()))


def settings_paths(repo):
    """Claude Code settings from the lowest to the highest precedence."""
    return [CLAUDE_HOME / 'settings.json', repo / '.claude' / 'settings.json', repo / '.claude' / 'settings.local.json']


def plugin_skills(repo):
    """Skill name to the enabled plugins that provide it, as `plugin@marketplace`."""
    enabled = {}
    for path in settings_paths(repo):
        enabled.update((read_json(path) or {}).get('enabledPlugins') or {})
    installed = (read_json(CLAUDE_HOME / 'plugins' / 'installed_plugins.json') or {}).get('plugins') or {}
    provided = defaultdict(list)
    for plugin, installs in installed.items():
        if not enabled.get(plugin):
            continue
        for install in installs:
            skills_dir = Path(install.get('installPath', '')) / 'skills'
            if skills_dir.is_dir():
                for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
                    provided[skill_md.parent.name].append(plugin)
    return provided


# Context files ------------------------------------------------------------------------------

def audit_context_files(repo, report, known_skills):
    """Checks every context file; returns the project's own, the global one excluded."""
    project_files = sorted(set(repo_files(repo, CONTEXT_FILE_NAMES)))
    global_md = CLAUDE_HOME / 'CLAUDE.md'
    files = project_files + ([global_md] if global_md.is_file() else [])
    if not files:
        report.add('Context files', 'info', 'No CLAUDE.md, AGENTS.md or GEMINI.md found.')
        return []
    for path in files:
        check_context_file(path, repo, report, known_skills)
    check_similar_rules(files, repo, report)
    return project_files


def check_context_file(path, repo, report, known_skills):
    lines = read_text(path).splitlines()
    label = display(path, repo)
    loaded = len(lines)
    for line in lines:
        imported = re.match(r'^@(\S+)\s*$', line)
        if not imported or path.name not in ('CLAUDE.md', 'CLAUDE.local.md'):
            continue
        target = (path.parent / imported.group(1)).expanduser()
        if not target.is_file():
            report.add('Context files', 'fix', f'`{label}` imports `@{imported.group(1)}`, which does not exist.')
        else:
            loaded += len(read_text(target).splitlines())
    level = 'review' if loaded > CONTEXT_LINE_BUDGET else 'info'
    extra = f' ({loaded} with its imports)' if loaded != len(lines) else ''
    report.add('Context files', level, f'`{label}`: {len(lines)} lines{extra}, budget {CONTEXT_LINE_BUDGET}.')
    for number, line in enumerate(lines, 1):
        for link in MARKDOWN_LINK.findall(line):
            if re.match(r'^(https?:|mailto:|#)', link):
                continue
            target = link.split('#')[0]
            if target and not (path.parent / target).exists() and not (repo / target).exists():
                report.add('Context files', 'fix', f'`{label}:{number}` links `{link}`, which does not exist.')
        if SKILL_WORD.search(line):
            for token in BACKTICK_TOKEN.findall(line):
                base = token.split(':')[-1]
                if '-' in base and base not in known_skills and not base.endswith('-lock'):
                    report.add(
                        'Context files', 'review',
                        f'`{label}:{number}` names the skill `{token}`, not installed in any scope '
                        '(a built-in skill would explain it).',
                    )


def rule_units(path):
    """Bullets and paragraphs of a Markdown file, each with its set of content words."""
    units = []
    for block in re.split(r'\n(?=\s*[-*] |\s*\d+\. )|\n\s*\n', read_text(path)):
        text = ' '.join(block.split())
        if len(text) < 60 or text[0] in '#|`':
            continue
        units.append((text, set(re.findall(r'[a-z][a-z-]{3,}', text.lower()))))
    return units


def check_similar_rules(files, repo, report):
    """Flags the same rule stated in two context files, which will drift apart."""
    units = {path: rule_units(path) for path in files}
    for index, first in enumerate(files):
        for second in files[index + 1:]:
            for text_a, words_a in units[first]:
                for text_b, words_b in units[second]:
                    overlap = len(words_a & words_b) / max(1, len(words_a | words_b))
                    if overlap >= SIMILAR_RULE_THRESHOLD:
                        report.add(
                            'Context files', 'review',
                            f'Same rule in two files: `{display(first, repo)}` "{text_a[:70]}..." and '
                            f'`{display(second, repo)}` "{text_b[:70]}...".',
                        )


def dependency_versions(repo):
    """Major version of each dependency, installed version first, declared range second."""
    versions = {}
    for manifest in repo_files(repo, ('package.json',)):
        data = read_json(manifest) or {}
        for field in ('dependencies', 'devDependencies', 'peerDependencies'):
            for name, spec in (data.get(field) or {}).items():
                major = re.search(r'\d+', str(spec))
                if major and name not in versions:
                    versions[name] = int(major.group())
        manager = re.match(r'(\w+)@(\d+)', data.get('packageManager') or '')
        if manager:
            versions[manager.group(1)] = int(manager.group(2))
    for name in list(versions):
        installed = read_json(repo / 'node_modules' / name / 'package.json')
        if installed and re.match(r'\d+', str(installed.get('version', ''))):
            versions[name] = int(re.match(r'\d+', installed['version']).group())
    return versions


def audit_version_claims(repo, files, report):
    versions = {n: v for n, v in dependency_versions(repo).items() if not n.startswith('@')}
    if not versions:
        return
    for path in files:
        for number, line in enumerate(read_text(path).splitlines(), 1):
            for name, actual in versions.items():
                pattern = r'(?<![\w/@.-])' + re.escape(name) + r'\s+v?(\d+)(?:\.\d+)*(\+)?(?![\w.])'
                for claimed, plus in re.findall(pattern, line, re.I):
                    claimed = int(claimed)
                    stale = actual < claimed if plus else actual != claimed
                    if stale:
                        report.add(
                            'Context files', 'fix',
                            f'`{display(path, repo)}:{number}` says {name} {claimed}{plus}, '
                            f'the project uses {name} {actual}.',
                        )


# Skills -------------------------------------------------------------------------------------

def audit_skills(repo, report):
    project = {d: scan_skill_dir(repo / d, 'project') for d in PROJECT_SKILL_DIRS}
    global_ = {str(d): scan_skill_dir(d, 'global') for d in GLOBAL_SKILL_DIRS}
    project_names = set().union(*[set(s) for s in project.values()])
    global_all = {}
    for skills in global_.values():
        for name, record in skills.items():
            global_all.setdefault(name, record)

    lock_path = repo / 'skills-lock.json'
    lock = (read_json(lock_path) or {}).get('skills', {}) if lock_path.is_file() else None
    if lock is not None:
        for name in sorted(set(lock) - project_names):
            report.add(
                'Skills', 'fix',
                f'`{name}` is declared in `skills-lock.json` but not installed: restore it with '
                '`npx skills experimental_install` or drop it with `npx skills remove`.',
            )
        for name in sorted(project_names - set(lock)):
            report.add('Skills', 'review', f'`{name}` is installed in the project but absent from `skills-lock.json`: nobody manages it.')
    elif project_names:
        report.add('Skills', 'info', 'Project skills are installed without a `skills-lock.json`: teammates cannot reproduce them.')

    agents_dir, claude_dir = (project[d] for d in PROJECT_SKILL_DIRS)
    if agents_dir and claude_dir:
        for name in sorted(set(claude_dir) - set(agents_dir)):
            report.add('Skills', 'review', f'`{name}` is in `.claude/skills` only: the other agents do not see it.')
        for name in sorted(set(agents_dir) - set(claude_dir)):
            report.add('Skills', 'review', f'`{name}` is in `.agents/skills` only: Claude Code does not see it.')

    for skills in list(project.values()) + list(global_.values()):
        for record in skills.values():
            if record['broken']:
                report.add('Skills', 'fix', f'`{record["name"]}` in `{record["dir"]}` is a broken link to `{record["target"]}`.')

    for name in sorted(project_names & set(global_all)):
        local = next(s[name] for s in project.values() if name in s)
        remote = global_all[name]
        if local['hash'] == remote['hash']:
            report.add('Skills', 'info', f'`{name}` is installed both in the project and globally, same content.')
        elif local['target'] != remote['target']:
            report.add(
                'Skills', 'fix',
                f'`{name}` has two different versions: project `{local["mtime"]}`, global `{remote["mtime"]}`. '
                'Only one should stay.',
            )

    visible = {}
    for record in list(claude_dir.values()) + list(global_.get(str(CLAUDE_HOME / 'skills'), {}).values()):
        visible.setdefault(record['name'], record)
    for record in visible.values():
        description = record['description']
        if len(description) > 1024:
            report.add('Skills', 'review', f'`{record["name"]}` has a {len(description)}-character description (the limit is 1024).')
        broad = sorted(set(BROAD_TRIGGER.findall(description)))
        if broad:
            report.add('Skills', 'review', f'`{record["name"]}` claims a broad trigger ({", ".join(broad)}): it competes with every other skill.')
        kept_back = re.match(r'(.+)-(v\d+|legacy|old)$', record['name'])
        if kept_back and kept_back.group(1) in visible:
            report.add('Skills', 'review', f'`{record["name"]}` is a kept-back version of `{kept_back.group(1)}`.')
    from_plugins = plugin_skills(repo)
    for name, plugins in sorted(from_plugins.items()):
        sources = ', '.join(f'`{p.split("@")[0]}:{name}` from `{p}`' for p in plugins)
        if name in visible:
            report.add(
                'Skills', 'fix',
                f'`{name}` is listed twice: installed on its own and as {sources}. Remove the '
                'standalone copy for Claude Code (`npx skills remove <name> -a claude-code`).',
            )
        elif len(plugins) > 1:
            report.add('Skills', 'fix', f'`{name}` comes from several plugins: {sources}.')
    total = sum(len(r['description']) for r in visible.values())
    report.add(
        'Skills', 'info',
        f'{len(visible)} standalone skills and {len(from_plugins)} plugin skills visible to Claude Code, '
        f'{total} characters of standalone descriptions in every session.',
    )

    global_lock = (read_json(HOME / '.agents' / '.skill-lock.json') or {}).get('skills', {})
    by_source = Counter(entry.get('source', '?') for entry in global_lock.values())
    for source, count in by_source.most_common():
        if count >= 5:
            report.add(
                'Skills', 'review',
                f'{count} global skills in `~/.agents/.skill-lock.json` come from `{source}`, likely '
                'installed in one go: check each one is wanted.',
            )
    return visible, project_names


# Usage --------------------------------------------------------------------------------------

def audit_usage(repo, days, visible, report):
    if not CLAUDE_PROJECTS.is_dir():
        report.add('Usage', 'info', 'No Claude Code transcripts found: usage cannot be measured.')
        return
    key = project_key(repo)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    skill_here, skill_elsewhere, mcp_here = Counter(), Counter(), Counter()
    earliest = None
    for transcript in CLAUDE_PROJECTS.rglob('*.jsonl'):
        if datetime.fromtimestamp(transcript.stat().st_mtime, timezone.utc) < cutoff:
            continue
        top = transcript.relative_to(CLAUDE_PROJECTS).parts[0]
        here = top == key or top.startswith(key + '-')
        with open(transcript, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                if '"Skill"' not in line and 'command-name' not in line and 'mcp__' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                stamp = entry.get('timestamp')
                if stamp:
                    when = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                    if when < cutoff:
                        continue
                    earliest = min(earliest or when, when)
                message = entry.get('message')
                if not isinstance(message, dict):
                    continue
                content = message.get('content')
                used = []
                if isinstance(content, str):
                    used += [c.split(':')[-1] for c in SLASH_COMMAND.findall(content)]
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict):
                        continue
                    if block.get('type') == 'text':
                        used += [c.split(':')[-1] for c in SLASH_COMMAND.findall(block.get('text', ''))]
                    if block.get('type') != 'tool_use':
                        continue
                    name = block.get('name', '')
                    if name == 'Skill':
                        used.append(str((block.get('input') or {}).get('skill', '')).split(':')[-1])
                    elif name.startswith('mcp__') and here:
                        mcp_here[name.split('__')[1]] += 1
                for skill in used:
                    (skill_here if here else skill_elsewhere)[skill] += 1
    window = f'since {earliest.date().isoformat()}' if earliest else f'in the last {days} days'
    report.add('Usage', 'info', f'Skill invocations and slash commands from Claude Code transcripts, {window}.')
    unused = []
    for name in sorted(visible):
        uses_here, uses_elsewhere = skill_here[name], skill_elsewhere[name]
        if uses_here or uses_elsewhere:
            report.add('Usage', 'info', f'`{name}`: {uses_here} here, {uses_elsewhere} in other projects.')
        else:
            unused.append(name)
    if unused:
        report.add('Usage', 'review', 'Never used: ' + ', '.join(f'`{n}`' for n in unused) + '.')

    servers = set(((read_json(repo / '.mcp.json') or {}).get('mcpServers') or {}).keys())
    for server in sorted(servers):
        # Tool names carry the server name with anything outside [A-Za-z0-9_-] replaced
        uses = mcp_here[re.sub(r'[^A-Za-z0-9_-]', '_', server)]
        report.add('Usage', 'review' if not uses else 'info', f'MCP server `{server}` (from `.mcp.json`): {uses} tool calls here.')


# Memory and settings ------------------------------------------------------------------------

def audit_memory(repo, report):
    memory = CLAUDE_PROJECTS / project_key(repo) / 'memory'
    index = memory / 'MEMORY.md'
    if not index.is_file():
        report.add('Memory', 'info', 'No auto-memory index for this project.')
        return
    lines = read_text(index).splitlines()
    linked = set(re.findall(r'\]\(([^)]+?\.md)\)', read_text(index)))
    for name in sorted(linked):
        if not (memory / name).is_file():
            report.add('Memory', 'fix', f'`MEMORY.md` points to `{name}`, which does not exist.')
    for path in sorted(memory.glob('*.md')):
        if path.name != 'MEMORY.md' and path.name not in linked:
            report.add('Memory', 'review', f'`{path.name}` is not listed in `MEMORY.md`, so it is never recalled.')
    report.add('Memory', 'info', f'`MEMORY.md` is loaded in every session: {len(lines)} lines, {len(read_text(index))} characters.')
    for line in lines:
        target = re.search(r'\]\(([^)]+?\.md)\)', line)
        if target and CLOSED_MARKER.search(line) and not OPEN_MARKER.search(line):
            report.add('Memory', 'review', f'`{target.group(1)}` is marked closed: shorten it or keep only the playbook.')
        if target and len(line) > 300:
            report.add(
                'Memory', 'review',
                f'The index line for `{target.group(1)}` has {len(line)} characters: the index carries '
                'a hook, the file the detail.',
            )


def audit_settings(repo, report):
    paths = settings_paths(repo)
    hooks_total = 0
    for path in paths:
        data = read_json(path)
        if data is None:
            continue
        label = display(path, repo)
        hooks = data.get('hooks') or {}
        for event, groups in hooks.items():
            for group in groups or []:
                for hook in group.get('hooks', []):
                    hooks_total += 1
                    timeout = hook.get('timeout')
                    note = f', timeout {timeout}s' if timeout else ''
                    report.add('Settings', 'info', f'`{label}`: {event} hook `{str(hook.get("command", ""))[:80]}`{note}.')
        plugins = [p for p, on in (data.get('enabledPlugins') or {}).items() if on]
        if plugins:
            report.add('Settings', 'info', f'`{label}` enables plugins: ' + ', '.join(f'`{p}`' for p in plugins) + '.')
        allow = (data.get('permissions') or {}).get('allow') or []
        deny = (data.get('permissions') or {}).get('deny') or []
        if allow or deny:
            report.add('Settings', 'info', f'`{label}`: {len(allow)} allow and {len(deny)} deny rules.')
    if not hooks_total:
        report.add('Settings', 'review', 'No hooks in any scope: every hard constraint lives in prose the model may skip.')


def display(path, repo):
    path = Path(path)
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path).replace(str(HOME), '~')


def render(report, repo):
    counts = report.counts()
    out = [
        f'# Agent configuration audit: {repo.name}',
        '',
        f'{counts["fix"]} to fix, {counts["review"]} to review, {counts["info"]} for information.',
    ]
    for section in ('Context files', 'Skills', 'Usage', 'Memory', 'Settings'):
        items = report.sections.get(section)
        if not items:
            continue
        out += ['', f'## {section}', '']
        order = {'fix': 0, 'review': 1, 'info': 2}
        for item in sorted(items, key=lambda i: order[i['level']]):
            out.append(f'- **{item["level"]}** {item["text"]}')
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', default='.', help='project root (default: current directory)')
    parser.add_argument('--days', type=int, default=30, help='usage window in days (default: 30)')
    parser.add_argument('--json', action='store_true', help='print the findings as JSON')
    args = parser.parse_args()
    repo = Path(args.repo).expanduser().resolve()
    report = Report()

    visible, project_names = audit_skills(repo, report)
    known = set(visible) | project_names | other_skill_names()
    for directory in GLOBAL_SKILL_DIRS:
        known |= set(scan_skill_dir(directory, 'global'))
    files = audit_context_files(repo, report, known)
    audit_version_claims(repo, files, report)
    audit_usage(repo, args.days, visible, report)
    audit_memory(repo, report)
    audit_settings(repo, report)

    if args.json:
        json.dump(report.sections, sys.stdout, indent=2)
        print()
    else:
        sys.stdout.write(render(report, repo))


if __name__ == '__main__':
    main()
