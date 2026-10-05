# The tells of AI slop

Each tell: what it looks like, when it is legitimate, the check that finds it (a `scan.py` check
name, a measure, or judgment on the render) and the shape of a precise fix. A tell is a pattern
used by default; the same pattern chosen on purpose, and expressed through the design system,
is a decision.

## Color

**Default AI accent** (`ai-palette`). Purple and indigo gradients and accents, or the newer
muted amber and terracotta on cream. Legitimate when it is the brand, expressed through tokens.
Fix: the brand token, one accent per view, semantic colors (success, warning, danger) for
status only.

**Framework defaults typed by hand** (`framework-default-color`). Tailwind's 500 and 600 steps
as hex literals: a color nobody chose. Fix: the token that means it.

**Chart library defaults** (`chart-default-palette`, `chart-unstyled`). Chart.js blue and pink,
the Recharts example purple, ECharts, D3 category10. Fix: map each series to a product color
or a semantic one, grey for "other", fewer colors than series when the series are many. When
the library needs a hex, read the token at runtime (`getComputedStyle`) instead of copying it.

**Colors outside the system** (`off-system-color`). A literal where a token exists. Fix: the
token that means it; when none fits, the user decides whether the system gains one.

**Neon on dark** (`glow`). Saturated glows and glowing borders on a near-black surface. Fix: the
dark theme's surface and border tokens, no glow.

## Depth and effects

**Gradient and glow buttons** (`gradient-control`, `glow`). Fix: the system's primary button,
flat, no colored shadow.

**Gradient text** (`gradient-text`). Fix: the heading color token; emphasis comes from size and
weight.

**Heavy shadows and thick outlines** (`heavy-shadow`, the shadow measure, judgment for
outlines). Fix: the system's elevation tokens, and one way to separate a surface (a border, a
shadow or a tonal background), not all three.

**Glassmorphism** (`glass`). Translucent panels over a blurred backdrop. A blur behind a modal
can be a deliberate choice. Fix: an opaque surface token.

**Decorative orbs** (`blob`, `gradient-decorative`). Blurred blobs and mesh gradients behind the
content. Fix: remove them. If the page needs presence, a real image or the brand's own graphic
element.

**Floating animations** (`float-animation`, the reduced-motion measure). Icons that bob, cards
that drift, sparkles. Spinners, skeletons and status pulses have a job. Fix: remove; motion
answers a user action, and honours `prefers-reduced-motion`.

## Shape and structure

**Rounded everything** (the radius measures). Pills and large radii on every box and control.
Fix: the system's radius scale, tighter on small controls than on containers.

**Side borders on everything** (`side-border`). A thick colored left border on alerts, cards,
list items. Quotes and a severity cue the alert component defines are legitimate. Fix: the
system's alert or callout component, or nothing.

**Elements wrapped in cards** (`nested-cards`, judgment). Every section boxed, cards inside
cards, a card around a single control. Fix: remove the inner container and group with spacing
and headings.

**Inconsistent spacing** (the spacing measures). Many distinct literal values, values off the
4px grid, the same gap expressed three ways. Fix: the spacing tokens.

**Boring layouts** (judgment). Everything centered, one column of identical blocks, three equal
feature columns. Fix: a grid with one focal point, reading content aligned left. When the page
needs a real composition, this is the "define the aesthetic" or "design it" level: ask for a
reference.

**No visual hierarchy** (judgment). Several primary-looking buttons, every element at the same
weight. Fix: one primary action per view, secondary and quiet variants for the rest,
destructive actions styled as such.

**No organic or textured shapes** (judgment). Only rounded rectangles and flat fills. A product
UI is right to be plain. For an expressive artifact: an illustration, photo or pattern the user
owns. Generators reproduce digital styles far better than organic ones, so a hand-made asset
from the user beats a generated one.

## Content

**Emoji as icons** (`emoji-icon`). Rockets, sparkles and checkmarks in headings, buttons and
labels. Emoji are legitimate as user content (chat, reactions). Fix: named icons from the
project's set, or nothing.

**Basic fonts** (the font-family measure). The default font at default sizes, no scale. Fix:
the system's type tokens. Without a system, the user picks a typeface (offer two or three free
ones) and a scale of three to five steps.

**Eyebrows and icon chips** (`eyebrow`, the text size measure, judgment for chips). A small
uppercase, letter-spaced label above every heading; an icon in a tinted rounded square next to
every label or number. Fix: remove them, or use the label style the sibling pages already use.

**Verbose and dense** (judgment). Helper text that repeats the label, subtitles under every
title, metric chips nobody asked for. Fix: remove; the label carries the meaning.

**Marketing cliches** (`copy-cliche`). Elevate, seamless, unleash, supercharge, "Oops!". Fix:
plain, specific words and the product's own nouns.

**Placeholder realism** (judgment). John Doe, Acme, 99.9%, +40% on every tile, lorem ipsum.
Fix: realistic sample data, or real data.
