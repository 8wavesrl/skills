#!/usr/bin/env python3
"""Read-only scan of a frontend for the mechanical tells of AI slop.

Prints a Markdown report of candidates, each with file:line and the code it matched, tagged
strong (the pattern rarely survives a design decision), review (legitimate in some contexts:
look at it) or info (a measure). A value defined as a design token (a CSS custom property, a
SCSS or Less variable, a theme or tokens file) is the system, not a tell: only literals used
directly are. Tailwind and UnoCSS classes are checked only when the project uses one of them.
It never writes anything.

Usage: python3 scan.py [PATH ...] [--json] [--limit N]
"""
import argparse
import colorsys
import json
import os
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

STYLE_EXT = {'.css', '.scss', '.sass', '.less', '.styl', '.pcss'}
MARKUP_EXT = {'.vue', '.html', '.htm', '.svelte', '.astro'}
JSX_EXT = {'.jsx', '.tsx'}
SCRIPT_EXT = {'.js', '.ts', '.mjs', '.cjs'} | JSX_EXT
LOCALE_EXT = {'.json', '.yaml', '.yml'} | SCRIPT_EXT
SKIP_DIRS = {'node_modules', '.git', 'dist', 'build', '.nx', '.next', '.nuxt', '.output', 'coverage',
             'vendor', '.ui-tour', 'storybook-static', '.svelte-kit', '.turbo', '.cache', 'public'}
MAX_BYTES = 400_000
KEYWORDS = {'none', '0', 'inherit', 'initial', 'unset', 'revert', 'auto'}
# Files whose literals are the palette itself: their colors are definitions, not usages.
DEFINITION_FILE = re.compile(r'(^|[/_.-])(theme|tokens?|palette|colou?rs|variables|design-system|hljs|'
                             r'highlight|prism|shiki|syntax)([/_.-]|$)|tailwind\.config|uno\.config', re.I)
LOCALE_DIR = re.compile(r'(^|/)(locales?|i18n|lang|messages|translations)(/|$)', re.I)
DESIGN_SYSTEMS = re.compile(r'"(@volverjs/style|@volverjs/ui-vue|tailwindcss|unocss|@mui/material|vuetify|'
                            r'primevue|@chakra-ui/react|antd|bootstrap|@mantine/core|quasar|element-plus|'
                            r'naive-ui|@radix-ui/themes|daisyui)"')
UTILITY_FRAMEWORK = re.compile(r'"(tailwindcss|unocss|@unocss/[\w-]+)"')

COLOR_LITERAL = re.compile(r'#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b'
                           r'|\b(?:rgba?|hsla?)\([^)]*\)')
COLOR_FUNCTION = re.compile(r'\b(?:rgba?|hsla?|oklch|oklab|lab|lch|color-mix|var)\((?:[^()]|\([^)]*\))*\)'
                            r'|#[0-9a-fA-F]{3,8}\b')
STRING_COLOR = re.compile(r'''['"`](#[0-9a-fA-F]{3,8}|(?:rgba?|hsla?)\([^)'"`]*\))['"`]''')
GRADIENT = re.compile(r'\b(?:repeating-)?(?:linear|radial|conic)-gradient\(', re.I)
ANIMATION_SAFE = re.compile(r'spin|rotat|load|skeleton|shimmer|progress|indeterminate|caret|blink|'
                            r'typing|placeholder|busy|wait|indicator|status|live|recording|listening|'
                            r'speaking|countdown|offline', re.I)
CONTROL_SELECTOR = re.compile(r'button|btn|cta|badge|chip|pill|\btag\b|\[type=.?submit', re.I)
OVERLAY_SELECTOR = re.compile(r'overlay|backdrop|mask|modal|dialog|drawer|scrim', re.I)
QUOTE_SELECTOR = re.compile(r'blockquote|quote|timeline|\bcode\b|\bpre\b', re.I)
COMMENT_LINE = re.compile(r'^\s*(//|\*|/\*|<!--|#\s)')
CHART_IMPORT = re.compile(r'''from\s+['"](chart\.js(?:/auto)?|vue-chartjs|recharts|echarts(?:/[\w/]+)?|'''
                          r'''vue-echarts|apexcharts|vue3-apexcharts|react-apexcharts|highcharts[\w/-]*|'''
                          r'''@nivo/[\w-]+|victory|@unovis/[\w-]+|d3(?:-[\w-]+)?|plotly\.js[\w-]*|'''
                          r'''react-chartjs-2)['"]''')
CHART_COLOR_KEY = re.compile(r'\b(colou?rs?|backgroundColor|borderColor|stroke|fill|palette|scheme)\b')
EMOJI = re.compile('[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF'
                   '\U0001F900-\U0001F9FF\U0001FA70-\U0001FAFF☀-⛿✀-➿'
                   '⭐⭕⬆⬇⤴⤵]')
COPY_CLICHE = re.compile(r'\b(elevat(?:e|es|ing)|seamless(?:ly)?|unleash\w*|supercharg\w*|effortless(?:ly)?|'
                         r'revolutioni[sz]\w*|game[- ]chang\w*|next[- ]gen(?:eration)?|cutting[- ]edge|'
                         r'empower\w*|delve|all[- ]in[- ]one|blazing(?:ly)?[- ]fast|at your fingertips|'
                         r'to the next level|oops)\b', re.I)
FONT_DEFINITION = re.compile(r'font-family|font-(?:sans|serif|mono|body|heading|display|base|primary)$')
SYSTEM_FONTS = {'inter', 'system-ui', '-apple-system', 'blinkmacsystemfont', 'segoe ui', 'roboto',
                'helvetica', 'helvetica neue', 'arial', 'sans-serif', 'ui-sans-serif', 'noto sans',
                'ui-serif', 'serif', 'monospace', 'ui-monospace', 'apple color emoji', 'segoe ui emoji',
                'segoe ui symbol', 'noto color emoji', 'inherit', 'initial'}
CARD_PART = re.compile(r'card(?:s\b|__|-?(?:head|foot|body|title|subtitle|content|actions|section|media|'
                       r'text|item|list|group|grid|deck|wrapper|container|meta|label|icon|image|img|link|'
                       r'badge))', re.I)

# Library defaults: a palette nobody chose. Lowercase six-digit hex.
CHART_DEFAULTS = {
    'Recharts examples': {'8884d8', '82ca9d', 'ffc658', 'ff7300'},
    'Chart.js': {'36a2eb', 'ff6384', '4bc0c0', 'ff9f40', '9966ff', 'ffcd56', 'c9cbcf'},
    'ECharts': {'5470c6', '91cc75', 'fac858', 'ee6666', '73c0de', '3ba272', 'fc8452', '9a60b4', 'ea7ccc'},
    'D3 category10 / matplotlib': {'1f77b4', 'ff7f0e', '2ca02c', 'd62728', '9467bd', '8c564b', 'e377c2',
                                   '17becf', 'bcbd22'},
    'Tableau 10': {'4e79a7', 'f28e2b', 'f28e2c', 'e15759', '76b7b2', '59a14f', 'edc948', 'edc949',
                   'af7aa1', 'ff9da7', '9c755f'},
    'Highcharts': {'2caffe', '544fc5', '00e272', 'fe6a35', '6b8abc', 'd568fb', '7cb5ec', '434348',
                   '90ed7d', 'f7a35c', '8085e9', 'f15c80', 'e4d354'},
    'ApexCharts': {'008ffb', '00e396', 'feb019', 'ff4560', '775dd0'},
}
# Tailwind's 500 and 600 steps: the colors an agent types when nobody picked any.
TAILWIND_DEFAULTS = {
    '3b82f6': 'blue-500', '2563eb': 'blue-600', '6366f1': 'indigo-500', '4f46e5': 'indigo-600',
    '8b5cf6': 'violet-500', '7c3aed': 'violet-600', 'a855f7': 'purple-500', '9333ea': 'purple-600',
    'd946ef': 'fuchsia-500', 'c026d3': 'fuchsia-600', 'ec4899': 'pink-500', 'db2777': 'pink-600',
    'ef4444': 'red-500', 'dc2626': 'red-600', 'f97316': 'orange-500', 'ea580c': 'orange-600',
    'f59e0b': 'amber-500', 'd97706': 'amber-600', 'eab308': 'yellow-500', '22c55e': 'green-500',
    '16a34a': 'green-600', '10b981': 'emerald-500', '059669': 'emerald-600', '14b8a6': 'teal-500',
    '0d9488': 'teal-600', '06b6d4': 'cyan-500', '0891b2': 'cyan-600', '0ea5e9': 'sky-500',
    '0284c7': 'sky-600',
}

UTIL = r'(?<![\w-])(?:[\w-]+:)*'
TW_PALETTE = re.compile(UTIL + r'(?:bg|text|from|via|to|border|ring|shadow|fill|stroke|outline|decoration|'
                               r'accent|caret)-(?:indigo|violet|purple|fuchsia)-\d{2,3}\b')
TW_GRADIENT = re.compile(UTIL + r'bg-(?:gradient-to|linear-to|radial|conic)(?:-[\w\[\]]+)?')
TW_GRADIENT_TEXT = re.compile(UTIL + r'bg-clip-text\b')
TW_GLASS = re.compile(UTIL + r'backdrop-blur(?:-[\w\[\]]+)?')
TW_BLOB = re.compile(UTIL + r'blur-(?:2xl|3xl|\[\d{2,}px\])')
TW_SHADOW_HEAVY = re.compile(UTIL + r'shadow-(?:xl|2xl)\b')
TW_SHADOW_COLOR = re.compile(UTIL + r'shadow-(?!xl\b|2xl\b|sm\b|md\b|lg\b|none\b|inner\b)[a-z]+-\d{2,3}'
                                    r'(?:/\d+)?|' + UTIL + r'shadow-\[0_0_[^\]]+\]')
TW_SIDE_BORDER = re.compile(UTIL + r'border-[ls]-(?:[2-8]|\[\d+px\])(?![\w-])')
TW_ANIMATION = re.compile(UTIL + r'animate-(?:bounce|ping|pulse|float\w*|wiggle)\b')
TW_ARBITRARY = re.compile(UTIL + r'(?:p[xytrblse]?|m[xytrblse]?|gap(?:-[xy])?|space-[xy]|rounded(?:-\w+)?|'
                                 r'text|w|h|top|left|right|bottom|inset)-\[\d+(?:\.\d+)?(?:px|rem)\]')
TW_RADIUS = re.compile(UTIL + r'rounded(?:-[trblse]{1,2})?(?:-(?:none|sm|md|lg|xl|2xl|3xl|full|'
                              r'\[[^\]]+\]))?(?![\w-])')
CLASS_EYEBROW = re.compile(UTIL + r'uppercase\b')
CLASS_TRACKING = re.compile(UTIL + r'tracking-(?:wide|wider|widest|\[[^\]]+\])\b')
CLASS_TEXT_SIZE = re.compile(UTIL + r'text-(?:\d{2}|xs|sm|base|lg|xl|[2-9]xl)(?![\w-])')
CONTROL_TAG = re.compile(r'<(?:button|a\s|a>|Button|router-link|RouterLink|NuxtLink|Link\s|VvButton)', re.I)

# Tell names and the sentence the report prints for each check.
CHECKS = {
    'gradient-control': 'gradient on a button, badge or call to action',
    'gradient-text': 'gradient-filled text',
    'glass': 'glassmorphism (backdrop blur)',
    'glow': 'colored glow or neon shadow',
    'blob': 'decorative blurred orb',
    'emoji-icon': 'emoji used as an icon or decoration',
    'ai-palette': 'the default AI accent: purple and indigo, or muted amber',
    'framework-default-color': 'framework default color typed as a literal',
    'chart-default-palette': 'chart library default palette',
    'gradient-decorative': 'decorative background gradient',
    'heavy-shadow': 'heavy or layered shadow',
    'side-border': 'thick side border used as an accent',
    'float-animation': 'infinite decorative animation',
    'off-system-color': 'color literal that bypasses the tokens',
    'arbitrary-value': 'arbitrary utility value outside the scale',
    'nested-cards': 'card inside a card',
    'eyebrow': 'uppercase label above a heading (eyebrow)',
    'chart-unstyled': 'chart with no color configuration',
    'copy-cliche': 'marketing cliche in UI copy',
}


class Report:
    """Collects candidates by check, each tagged strong or review, and the measures."""

    def __init__(self):
        self.header = []
        self.findings = defaultdict(list)
        self.measures = []

    def add(self, check, level, path, line, code, note=''):
        self.findings[check].append({'level': level, 'path': path, 'line': line,
                                     'code': ' '.join(code.split())[:140], 'note': note})

    def measure(self, level, text):
        self.measures.append({'level': level, 'text': text})


def parse_color(text):
    """(r, g, b, a) in 0..1 for hex, rgb() and hsl(); None for anything else."""
    text = text.strip().lower()
    if text.startswith('#'):
        digits = text[1:]
        if len(digits) in (3, 4):
            digits = ''.join(c * 2 for c in digits)
        if len(digits) not in (6, 8) or not re.fullmatch(r'[0-9a-f]+', digits):
            return None
        r, g, b = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return r, g, b, int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
    match = re.match(r'(rgba?|hsla?)\(([^)]*)\)', text)
    if not match:
        return None
    parts = [p for p in re.split(r'[\s,/]+', match.group(2).strip()) if p]
    if len(parts) < 3 or any('var(' in p or '$' in p for p in parts):
        return None

    def number(value, scale):
        try:
            if value.endswith('%'):
                return float(value[:-1]) / 100
            return float(value.removesuffix('deg')) / scale
        except ValueError:
            return None

    alpha = number(parts[3], 1) if len(parts) > 3 else 1.0
    if match.group(1).startswith('rgb'):
        rgb = [number(p, 255) for p in parts[:3]]
        return None if None in rgb or alpha is None else (*rgb, alpha)
    hue, sat, light = number(parts[0], 360), number(parts[1], 100), number(parts[2], 100)
    if None in (hue, sat, light, alpha):
        return None
    return (*colorsys.hls_to_rgb(hue % 1, light, sat), alpha)


def hue_family(rgba):
    """'purple', 'muted-warm', 'neutral' or 'other' for a parsed color."""
    hue, light, sat = colorsys.rgb_to_hls(*rgba[:3])
    hue *= 360
    if sat < 0.15 or light < 0.08 or light > 0.96:
        return 'neutral'
    if 235 <= hue <= 300 and sat >= 0.35 and 0.25 <= light <= 0.85:
        return 'purple'
    if 12 <= hue <= 45 and 0.25 <= sat <= 0.75 and 0.35 <= light <= 0.7:
        return 'muted-warm'
    return 'other'


def large_radius(value):
    """True for a radius of 16px or more, or a fully round one."""
    first = re.search(r'(\d*\.?\d+)(px|rem|em|%)', value)
    if not first:
        return False
    size, unit = float(first.group(1)), first.group(2)
    return size >= 50 if unit == '%' else size * (16 if unit in ('rem', 'em') else 1) >= 16


def hex6(rgba):
    return ''.join(f'{round(c * 255):02x}' for c in rgba[:3])


def gradients(value):
    """Each gradient call in a value, parentheses balanced."""
    calls = []
    for match in GRADIENT.finditer(value):
        depth, j = 0, match.end() - 1
        while j < len(value):
            depth += value[j] == '('
            depth -= value[j] == ')'
            if depth == 0:
                break
            j += 1
        calls.append(value[match.start():j + 1])
    return calls


def is_fade(call):
    """A plain linear gradient to transparent fades an edge; radial and repeating ones decorate."""
    if not call.lower().startswith('linear-gradient('):
        return False
    if 'transparent' in call.lower():
        return True
    return any((color := parse_color(literal)) and color[3] < 0.05 for literal in COLOR_LITERAL.findall(call))


def split_layers(value):
    layers, depth, current = [], 0, ''
    for char in value:
        depth += char == '('
        depth -= char == ')'
        if char == ',' and depth == 0:
            layers.append(current)
            current = ''
        else:
            current += char
    layers.append(current)
    return [layer.strip() for layer in layers if layer.strip()]


def classify_shadow(value):
    """('glow' | 'heavy' | None, reason) for a box-shadow, text-shadow or drop-shadow value."""
    if value.strip().lower() in ('none', 'unset', 'initial', 'inherit', '0'):
        return None, ''
    layers = [layer for layer in split_layers(value) if not layer.lstrip().startswith('inset')]
    worst = None, ''
    for layer in layers:
        literals = COLOR_LITERAL.findall(layer)
        color = parse_color(literals[0]) if literals else None
        tokenized = 'var(' in layer or '$' in layer
        numbers = [float(n) * (16 if unit in ('rem', 'em') else 1) for n, unit in
                   re.findall(r'(?<![\w.#-])(-?\d*\.?\d+)(px|rem|em)?(?![\w%.])', COLOR_FUNCTION.sub(' ', layer))]
        x, y, blur = (numbers + [0, 0, 0])[:3]
        colored = color and hue_family(color) != 'neutral' and color[3] >= 0.2
        if colored and blur >= 8:
            return 'glow', f'colored, {blur:g}px blur'
        if x == 0 and y == 0 and blur >= 12 and (colored or (tokenized and not color)):
            return 'glow', f'no offset, {blur:g}px blur'
        alpha = color[3] if color else 0.15
        if (blur >= 24 and alpha >= 0.12) or (alpha >= 0.25 and blur >= 12):
            worst = 'heavy', f'{blur:g}px blur' + (f', {color[3]:.0%} opacity' if color else '')
    opacity = sum(parse_color(c)[3] for layer in layers for c in COLOR_LITERAL.findall(layer)[:1]
                  if parse_color(c))
    if len(layers) >= 3 and worst[0] is None and opacity >= 0.3:
        worst = 'heavy', f'{len(layers)} layers, {opacity:.0%} total opacity'
    return worst


def css_declarations(text, start_line=1, definition_file=False):
    """Yield (line, selector, prop, value, is_definition) for a CSS, SCSS or Less text."""
    selectors, chunk, chunk_line, line = [], '', start_line, start_line
    i, n = 0, len(text)
    while i < n:
        char = text[i]
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            end = n if end < 0 else end + 2
            line += text.count('\n', i, end)
            i = end
            continue
        if text.startswith('//', i):
            end = text.find('\n', i)
            i = n if end < 0 else end
            continue
        if char in '"\'' or text.startswith('#{', i) or char == '(':
            if not chunk.strip():
                chunk_line = line
            if char == '(':
                depth, j = 0, i
                while j < n:
                    depth += text[j] == '('
                    depth -= text[j] == ')'
                    if depth == 0:
                        break
                    j += 1
                end = j + 1
            else:
                close = '}' if char == '#' else char
                end = text.find(close, i + 1)
                end = n if end < 0 else end + 1
            line += text.count('\n', i, end)
            chunk += text[i:end]
            i = end
            continue
        if char == '{':
            selectors.append(' '.join(chunk.split()))
            chunk = ''
        elif char in ';}':
            stripped = chunk.strip()
            if ':' in stripped and not stripped.startswith('@'):
                prop, _, value = stripped.partition(':')
                prop = prop.strip().lower()
                if re.fullmatch(r'[-$@\w]+', prop):
                    definition = definition_file or prop.startswith(('--', '$', '@'))
                    yield chunk_line, ' '.join(selectors), prop, value.strip(), definition
            if char == '}' and selectors:
                selectors.pop()
            chunk = ''
        else:
            if not chunk.strip():
                chunk_line = line
            chunk += char
        if char == '\n':
            line += 1
        i += 1


def keyframe_bodies(text):
    """{name: body} for every @keyframes block."""
    bodies = {}
    for match in re.finditer(r'@(?:-webkit-)?keyframes\s+([\w-]+)\s*\{', text):
        depth, j = 1, match.end()
        while j < len(text) and depth:
            depth += text[j] == '{'
            depth -= text[j] == '}'
            j += 1
        bodies[match.group(1)] = text[match.end():j]
    return bodies


def style_regions(path, text):
    """(start_line, css) for each stylesheet region of a file."""
    if path.suffix in STYLE_EXT:
        return [(1, text)]
    regions = []
    for match in re.finditer(r'<style\b[^>]*>(.*?)</style>', text, re.S | re.I):
        regions.append((text.count('\n', 0, match.start(1)) + 1, match.group(1)))
    for match in re.finditer(r'\sstyle="([^"]*)"', text):
        regions.append((text.count('\n', 0, match.start(1)) + 1, '_{' + match.group(1) + '}'))
    return regions


def blank(match):
    return re.sub(r'[^\n]', ' ', match.group(0))


def template_text(path, text):
    """The markup of a file with styles, comments (and scripts, outside JSX) blanked, lines kept."""
    if path.suffix not in MARKUP_EXT | JSX_EXT:
        return ''
    text = re.sub(r'<style\b.*?</style>', blank, text, flags=re.S | re.I)
    text = re.sub(r'<!--.*?-->', blank, text, flags=re.S)
    if path.suffix in MARKUP_EXT:
        text = re.sub(r'<script\b.*?</script>', blank, text, flags=re.S | re.I)
    return text


class CardNesting(HTMLParser):
    """Finds an element whose tag or class says card, inside another one."""

    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.hits = [], []

    @staticmethod
    def is_card(tag, attrs):
        classes = ' '.join(v or '' for k, v in attrs if k in ('class', 'classname', ':class')).split()
        return any('card' in token.lower() and not CARD_PART.search(token) for token in [tag, *classes])

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        card = self.is_card(tag, attrs)
        if card and any(entry[1] for entry in self.stack):
            self.hits.append((self.getpos()[0], tag))
        self.stack.append((tag, card))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def walk(root):
    """Files under root, pruning dependency and build folders before descending."""
    if root.is_file():
        yield root
        return
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for name in names:
            yield Path(folder) / name


def project_packages(roots):
    """The text of every package.json from each root up to its repository, and below it."""
    texts = []
    for root in roots:
        start = root if root.is_dir() else root.parent
        for parent in [start, *start.parents]:
            if (parent / 'package.json').is_file():
                texts.append((parent / 'package.json').read_text(errors='ignore'))
            if (parent / '.git').exists():
                break
        texts += [p.read_text(errors='ignore') for p in walk(root) if p.name == 'package.json']
    return texts


def collect_files(roots):
    files = set()
    for root in roots:
        for path in walk(root):
            if '.min.' in path.name or path.name.endswith('.d.ts'):
                continue
            locale = path.suffix in LOCALE_EXT and LOCALE_DIR.search(path.as_posix())
            if (path.suffix in STYLE_EXT | MARKUP_EXT | SCRIPT_EXT or locale) and path.stat().st_size <= MAX_BYTES:
                files.add(path)
    return sorted(files)


class Scan:
    def __init__(self, roots):
        self.report = Report()
        packages = project_packages(roots)
        self.systems = sorted({name for text in packages for name in DESIGN_SYSTEMS.findall(text)})
        self.utility = any(UTILITY_FRAMEWORK.search(text) for text in packages)
        self.files = collect_files(roots)
        self.radius, self.shadows, self.spacing, self.font_sizes = Counter(), Counter(), Counter(), Counter()
        self.fonts, self.token_uses, self.tw_radius, self.kinds = Counter(), Counter(), Counter(), Counter()
        self.large_radius = Counter()
        self.defined_families, self.purple_literals = set(), []
        self.class_sizes = Counter()
        self.definitions = 0
        self.infinite = 0
        self.reduced_motion = False

    def run(self):
        base = Path.cwd()
        for path in self.files:
            try:
                name = path.resolve().relative_to(base).as_posix()
            except ValueError:
                name = path.as_posix()
            self.file(path, name, path.read_text(errors='ignore'))
        self.summarize()
        return self.report

    def file(self, path, name, text):
        lines = text.splitlines()
        definition_file = bool(DEFINITION_FILE.search(path.as_posix()))
        locale = bool(LOCALE_DIR.search(path.as_posix())) and path.suffix in LOCALE_EXT
        kind = ('locale' if locale else 'style' if path.suffix in STYLE_EXT
                else 'markup' if path.suffix in MARKUP_EXT | JSX_EXT else 'script')
        self.kinds[kind] += 1
        self.reduced_motion |= 'prefers-reduced-motion' in text
        keyframes = keyframe_bodies(text)
        for start, css in style_regions(path, text):
            for decl in css_declarations(css, start, definition_file):
                self.declaration(name, keyframes, *decl)
        if path.suffix in SCRIPT_EXT | MARKUP_EXT and not locale:
            self.script_colors(name, text, lines, definition_file)
        markup = text if locale else template_text(path, text)
        if markup:
            self.markup(name, markup, lines, locale, path.suffix in MARKUP_EXT | JSX_EXT)

    def declaration(self, name, keyframes, line, selector, prop, value, definition):
        report = self.report
        if definition:
            self.definitions += 1
            if FONT_DEFINITION.search(prop):
                self.fonts[value] += 1
            self.define_colors(COLOR_LITERAL.findall(value), name, line, f'{prop}: {value}')
            return
        code = f'{prop}: {value}'
        tokenized = 'var(' in value or '$' in value
        if prop == 'font-family':
            self.fonts[value] += 1
        decorative = [call for call in gradients(value) if not is_fade(call)]
        if decorative and not prop.startswith(('mask', '-webkit-mask')):
            kinds = ', '.join(dict.fromkeys(call.split('(')[0] for call in decorative))
            if CONTROL_SELECTOR.search(selector):
                report.add('gradient-control', 'strong', name, line, code, f'{selector}: {kinds}')
            else:
                report.add('gradient-decorative', 'review', name, line, code, f'{selector}: {kinds}')
        if prop in ('background-clip', '-webkit-background-clip') and value.startswith('text'):
            report.add('gradient-text', 'strong', name, line, code, selector)
        if prop == 'text-transform' and value.lower() == 'uppercase' and not re.search(r'\bth\b|thead', selector):
            report.add('eyebrow', 'review', name, line, code, selector)
        if prop in ('backdrop-filter', '-webkit-backdrop-filter') and 'blur' in value:
            overlay = OVERLAY_SELECTOR.search(selector)
            report.add('glass', 'review' if overlay else 'strong', name, line, code,
                       f'{selector}, an overlay' if overlay else selector)
        if prop == 'filter':
            blur = re.search(r'blur\((\d+(?:\.\d+)?)(px|rem)\)', value)
            if blur and float(blur.group(1)) * (16 if blur.group(2) == 'rem' else 1) >= 24:
                report.add('blob', 'strong', name, line, code, selector)
            for inner in re.findall(r'drop-shadow\(((?:[^()]|\([^)]*\))*)\)', value):
                if classify_shadow(inner)[0] == 'glow':
                    report.add('glow', 'strong', name, line, code, selector)
        if prop in ('box-shadow', 'text-shadow'):
            if not tokenized and value.lower() not in KEYWORDS:
                self.shadows[' '.join(value.split())] += 1
            shadow, reason = classify_shadow(value)
            if shadow == 'glow':
                report.add('glow', 'strong', name, line, code, f'{selector}: {reason}')
            elif shadow == 'heavy':
                report.add('heavy-shadow', 'review', name, line, code, f'{selector}: {reason}')
        if prop in ('border-left', 'border-inline-start', 'border-left-width', 'border-inline-start-width'):
            width = re.search(r'(\d+(?:\.\d+)?)px', value)
            visible = 'transparent' not in value and 'none' not in value
            if width and float(width.group(1)) >= 2 and visible and not QUOTE_SELECTOR.search(selector):
                report.add('side-border', 'review', name, line, code, selector)
        if prop in ('animation', 'animation-iteration-count') and 'infinite' in value:
            body = ' '.join(keyframes.get(word, '') for word in re.findall(r'[\w-]+', value))
            spinner = 'rotate' in body and 'translate' not in body and 'scale' not in body
            if not (ANIMATION_SAFE.search(value) or ANIMATION_SAFE.search(selector) or spinner):
                self.infinite += 1
                report.add('float-animation', 'review', name, line, code, selector)
        if 'radius' in prop:
            if tokenized:
                self.token_uses['radius'] += 1
            elif value.lower() not in KEYWORDS:
                self.radius[value] += 1
                self.large_radius[large_radius(value)] += 1
        if prop == 'font-size':
            if tokenized:
                self.token_uses['font-size'] += 1
            elif value.lower() not in KEYWORDS:
                self.font_sizes[value] += 1
        if re.match(r'(padding|margin|gap|row-gap|column-gap|inset|top|right|bottom|left)\b', prop):
            self.token_uses['spacing'] += value.count('var(') + value.count('$')
            for length in re.findall(r'(?<![\w.-])(\d+(?:\.\d+)?(?:px|rem|em))\b', value):
                if not re.fullmatch(r'0(?:\.0+)?\w*|1px', length):
                    self.spacing[length] += 1
        for literal in COLOR_LITERAL.findall(value):
            color = parse_color(literal)
            if color and color[3] >= 0.05:
                self.color(name, line, code, color, literal)

    def define_colors(self, literals, name, line, code):
        """Remember the hue families the tokens define; a Tailwind purple as a token is still a default."""
        for literal in literals:
            color = parse_color(literal)
            if not color:
                continue
            family = hue_family(color)
            self.defined_families.add(family)
            library = next((lib for lib, palette in CHART_DEFAULTS.items() if hex6(color) in palette), None)
            if library:
                self.report.add('chart-default-palette', 'strong', name, line, code,
                                f'{literal}: a token set to the {library} default')
            elif family == 'purple' and hex6(color) in TAILWIND_DEFAULTS:
                self.report.add('ai-palette', 'strong', name, line, code,
                                f'{literal}: a token set to Tailwind {TAILWIND_DEFAULTS[hex6(color)]}, '
                                'a default rather than a brand')

    def color(self, name, line, code, color, literal):
        """Palette checks for one color literal used outside a token definition."""
        key = hex6(color)
        for library, palette in CHART_DEFAULTS.items():
            if key in palette:
                self.report.add('chart-default-palette', 'strong', name, line, code, f'{literal}: {library}')
                return
        family = hue_family(color)
        tailwind = f', Tailwind {TAILWIND_DEFAULTS[key]}' if key in TAILWIND_DEFAULTS else ''
        if family == 'purple':
            self.purple_literals.append(len(self.report.findings['ai-palette']))
            self.report.add('ai-palette', 'strong', name, line, code, literal + tailwind)
        elif tailwind:
            self.report.add('framework-default-color', 'strong', name, line, code, literal + tailwind)
        elif family == 'muted-warm':
            self.report.add('ai-palette', 'review', name, line, code, f'{literal}: muted amber or terracotta')
        elif family != 'neutral':
            self.report.add('off-system-color', 'review', name, line, code, literal)

    def script_colors(self, name, text, lines, definition_file):
        """Colors typed in scripts and templates: inline style objects, chart configs, props."""
        charts = CHART_IMPORT.search(text)
        unstyled = re.sub(r'<style\b.*?</style>', ' ', text[charts.end():], flags=re.S | re.I) if charts else ''
        if charts and not CHART_COLOR_KEY.search(unstyled):
            self.report.add('chart-unstyled', 'review', name, text.count('\n', 0, charts.start()) + 1,
                            charts.group(0), 'the render shows the library palette')
        in_style = False
        for number, line in enumerate(lines, 1):
            if re.search(r'<style\b', line, re.I):
                in_style = True
            if in_style:
                in_style = not re.search(r'</style>', line, re.I)
                continue
            if COMMENT_LINE.match(line):
                continue
            if definition_file:
                self.define_colors(STRING_COLOR.findall(line), name, number, line)
            else:
                for match in STRING_COLOR.finditer(line):
                    color = parse_color(match.group(1))
                    if color and color[3] >= 0.05:
                        self.color(name, number, line, color, match.group(1))
            shadow = re.search(r'''\b(?:boxShadow|textShadow)\s*:\s*['"`]([^'"`]+)''', line)
            if shadow:
                kind, reason = classify_shadow(shadow.group(1))
                if kind:
                    self.report.add('glow' if kind == 'glow' else 'heavy-shadow',
                                    'strong' if kind == 'glow' else 'review', name, number, line, reason)
            if re.search(r'''\bbackdropFilter\s*:\s*['"`][^'"`]*blur''', line):
                self.report.add('glass', 'strong', name, number, line)

    def markup(self, name, markup, lines, locale, parse_cards):
        """Emoji, copy and utility classes in templates and locale files, and card nesting."""
        report = self.report
        for number, line in enumerate(markup.splitlines(), 1):
            if not line.strip() or COMMENT_LINE.match(line):
                continue
            original = lines[number - 1] if number <= len(lines) else line
            emoji = EMOJI.findall(line)
            if emoji:
                report.add('emoji-icon', 'strong', name, number, original, ''.join(emoji))
            cliche = COPY_CLICHE.search(line)
            if cliche:
                word = re.escape(cliche.group(0))
                in_copy = locale or re.search(r'>[^<]*' + word, line) or re.search(r'''['"][^'"]*''' + word, line)
                if in_copy:
                    report.add('copy-cliche', 'review', name, number, original, cliche.group(0))
            if not locale:
                if CLASS_EYEBROW.search(line) and CLASS_TRACKING.search(line):
                    report.add('eyebrow', 'review', name, number, original, 'uppercase with letter spacing')
                for match in CLASS_TEXT_SIZE.finditer(line):
                    self.class_sizes[re.sub(r'^(?:[\w-]+:)*', '', match.group(0))] += 1
            if self.utility and not locale:
                self.utility_classes(name, number, line, original)
        if parse_cards:
            parser = CardNesting()
            try:
                parser.feed(markup)
                parser.close()
            except Exception:  # loose templates: a heuristic, never a crash
                parser.hits = []
            for number, tag in parser.hits:
                original = lines[number - 1] if number <= len(lines) else ''
                report.add('nested-cards', 'review', name, number, original, f'<{tag}> inside a card')

    def utility_classes(self, name, number, line, code):
        report = self.report
        control = bool(CONTROL_TAG.search(line))
        for match in TW_GRADIENT.finditer(line):
            report.add('gradient-control' if control else 'gradient-decorative',
                       'strong' if control else 'review', name, number, code, match.group(0))
        for pattern, check, level in ((TW_GRADIENT_TEXT, 'gradient-text', 'strong'), (TW_GLASS, 'glass', 'strong'),
                                      (TW_BLOB, 'blob', 'strong'), (TW_SHADOW_COLOR, 'glow', 'strong'),
                                      (TW_PALETTE, 'ai-palette', 'strong'),
                                      (TW_SHADOW_HEAVY, 'heavy-shadow', 'review'),
                                      (TW_SIDE_BORDER, 'side-border', 'review'),
                                      (TW_ARBITRARY, 'arbitrary-value', 'review')):
            hits = [m.group(0) for m in pattern.finditer(line)]
            if hits:
                report.add(check, level, name, number, code, ' '.join(dict.fromkeys(hits)))
        for match in TW_ANIMATION.finditer(line):
            if 'pulse' in match.group(0) and re.search(r'skeleton|loading|placeholder', line, re.I):
                continue
            self.infinite += 1
            report.add('float-animation', 'review', name, number, code, match.group(0))
        for match in TW_RADIUS.finditer(line):
            self.tw_radius[re.sub(r'^(?:[\w-]+:)*', '', match.group(0))] += 1

    def summarize(self):
        report = self.report
        if 'purple' in self.defined_families:
            # The tokens are purple themselves: a purple literal is the brand typed by hand.
            palette = report.findings['ai-palette']
            for index in sorted(self.purple_literals, reverse=True):
                finding = palette.pop(index)
                finding.update(level='review', note=finding['note'] + ': the tokens define a purple too, '
                                                                      'probably the brand typed by hand')
                report.findings['off-system-color'].insert(0, finding)
            if not palette:
                del report.findings['ai-palette']
        report.header.append(f'files scanned: {len(self.files)} ('
                             + ', '.join(f'{v} {k}' for k, v in self.kinds.most_common()) + ')')
        report.header.append('design system: ' + (', '.join(self.systems) or 'none found in package.json')
                             + f'; {self.definitions} token definitions in the scanned files; utility classes: '
                             + ('Tailwind or UnoCSS' if self.utility else 'none'))
        for label, counter, threshold, key in (('border-radius', self.radius, 4, 'radius'),
                                               ('box-shadow and text-shadow', self.shadows, 3, None),
                                               ('font-size', self.font_sizes, 6, 'font-size'),
                                               ('spacing (padding, margin, gap, inset)', self.spacing, 10, 'spacing')):
            if counter:
                top = ', '.join(f'{value[:50]} x{count}' for value, count in counter.most_common(6))
                tokens = f', {self.token_uses[key]} token uses' if key else ''
                report.measure('review' if len(counter) >= threshold else 'info',
                               f'{label}: {len(counter)} distinct literal values ({top}){tokens}')
        if self.class_sizes:
            report.measure('review' if len(self.class_sizes) >= 6 else 'info',
                           f'text size classes: {len(self.class_sizes)} distinct ('
                           + ', '.join(f'{k} x{v}' for k, v in self.class_sizes.most_common(8)) + ')')
        off_grid = sorted({v for v in self.spacing if v.endswith('px') and float(v[:-2]) > 8 and float(v[:-2]) % 4},
                          key=lambda v: float(v[:-2]))
        if len(off_grid) >= 3:
            report.measure('review', f'spacing off the 4px grid: {", ".join(off_grid[:10])}')
        total = sum(self.tw_radius.values())
        if total >= 6:
            big = sum(count for cls, count in self.tw_radius.items() if re.search(r'-(?:xl|2xl|3xl|full)$', cls))
            report.measure('review' if big / total > 0.6 else 'info',
                           f'utility radius: {big} of {total} rounded classes are xl or larger ('
                           + ', '.join(f'{k} x{v}' for k, v in self.tw_radius.most_common(4)) + ')')
        total = sum(self.large_radius.values())
        if total >= 6:
            report.measure('review' if self.large_radius[True] / total > 0.6 else 'info',
                           f'radius: {self.large_radius[True]} of {total} literal border-radius values are '
                           '16px or larger, or fully round')
        families = {f.strip().strip('\'"').lower() for value in self.fonts for f in value.split(',')}
        if not self.fonts:
            report.measure('info', 'font-family: none declared in the scanned files (it comes from a '
                                   'dependency or the browser default: check the render)')
        elif families <= SYSTEM_FONTS:
            report.measure('review', 'font-family: only system or default fonts ('
                                     + '; '.join(sorted(self.fonts)[:3]) + ')')
        if self.infinite and not self.reduced_motion:
            report.measure('review', f'{self.infinite} infinite decorative animations and no '
                                     'prefers-reduced-motion query')


def render(report, roots, limit):
    levels = Counter(f['level'] for items in report.findings.values() for f in items)
    out = [f'# De-slop scan: {", ".join(roots)}', '']
    out += [f'- {line}' for line in report.header]
    out += [f'- candidates: {levels["strong"]} strong, {levels["review"]} review', '',
            'Candidates, not verdicts: open each one in context, and look at the render before judging '
            'layout, hierarchy and density.']
    for level in ('strong', 'review'):
        checks = [(check, [f for f in items if f['level'] == level]) for check, items in report.findings.items()]
        checks = sorted(((c, f) for c, f in checks if f), key=lambda pair: (-len(pair[1]), pair[0]))
        if not checks:
            continue
        out += ['', f'## {level.capitalize()}']
        for check, items in checks:
            files = Counter(f['path'] for f in items)
            out += ['', f'### {check}: {CHECKS[check]} ({len(items)} in {len(files)} files)']
            for f in items[:limit]:
                note = f' ({f["note"]})' if f['note'] else ''
                out.append(f'- {f["path"]}:{f["line"]} `{f["code"]}`{note}')
            if len(items) > limit:
                rest = Counter(f['path'] for f in items[limit:])
                out.append(f'- ...and {len(items) - limit} more: '
                           + ', '.join(f'{p} x{c}' for p, c in rest.most_common(5)))
    if report.measures:
        out += ['', '## Measures']
        out += [f'- [{m["level"]}] {m["text"]}' for m in report.measures]
    return '\n'.join(out) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('paths', nargs='*', default=['.'], help='files or folders to scan (default: .)')
    parser.add_argument('--limit', type=int, default=12, help='candidates shown per check (default: 12)')
    parser.add_argument('--json', action='store_true', help='print the findings as JSON')
    args = parser.parse_args()
    roots = [Path(p).expanduser() for p in args.paths]
    missing = [str(p) for p in roots if not p.exists()]
    if missing:
        sys.exit(f'scan.py: not found: {", ".join(missing)}')
    report = Scan([p.resolve() for p in roots]).run()
    if args.json:
        json.dump({'header': report.header, 'findings': report.findings, 'measures': report.measures},
                  sys.stdout, indent=2)
        print()
    else:
        sys.stdout.write(render(report, args.paths, args.limit))


if __name__ == '__main__':
    main()
