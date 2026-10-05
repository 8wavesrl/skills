---
name: de-slopify
description: Find the tells that make a UI look AI-generated (gradient and glow buttons, emoji as icons, glassmorphism, purple and indigo accents, decorative orbs, cards inside cards, side borders, chart library defaults, scattered spacing, padded copy) and replace them with precise, element-by-element fixes whose values come from the project's design system or the user's own choices, never from a house taste. A bundled read-only script lists the mechanical candidates with file and line; the render is judged for layout, hierarchy and density. Nothing changes before the user approves the plan. Use when the user says a page, component or HTML artifact looks vibecoded, generic, templated or like AI slop, asks to de-slop or polish an agent-generated UI ("de-slopify", "deslop", "sembra fatto con l'AI", "togli l'effetto AI", "rendilo meno generico", "sembra vibecoded"), or before shipping a UI an agent generated.
---

# De-slopify

Slop is UI generated without decisions: real components and patterns, combined by default
instead of by intent. People recognize it at a glance, and "make it look less AI" is a gamble:
it names no element, so the result depends on what the agent happens to notice, it often swaps
one default for another, and nobody can review the change before it lands. What works reliably
is the reverse. Name each tell, then give one precise instruction per element: what goes, what
replaces it, the exact value. This skill does both, and takes every value from the project. A
trendy font or grain on every surface, chosen by the agent, is the next slop.

## Step 0: scope and level

State in one line what is being de-slopped (a page, a component, a one-off HTML artifact, the
whole app) and which level applies:

| Level | When | The values come from |
|---|---|---|
| Clean up | the structure holds, the tells are on the surface | the design system; without one, the anchors the user gives (palette, typeface, icon set) |
| Define the aesthetic | a one-off artifact with no design system | a reference: an image the user owns or may use, or a named style |
| Design it | a product or a site with no design behind it | a design (Figma, a designer). Say so: polishing does not get there |

A design system shows in the script's header (packages, token definitions) and in the
project's AGENTS.md. When a skill documents it (for @volverjs, the volverjs-style and
volverjs-ui-vue skills), load it before writing any fix: guessed class names and tokens are
wrong in ways that look right. A skill can be wrong too: when a prop or class it names does not
render as described, the library's source and types decide.

Inside a product, the finished pages next to the one in scope are the reference: the same
title, the same tile, the same list. Read two or three of them before judging, and match them
before inventing anything.

## 1. See it

Judge the render, not the code alone. Use the project's way to look at the running app (a
screenshot script, Storybook, the dev server in a headless browser); without one, ask the user
for screenshots. Both themes when the app has a dark mode, and a phone width for pages meant
for phones. Check that the capture covers the whole page: an app that scrolls inside a
container shows only the first screen, so use a taller window. Charts and tooltips need their
hover and focus states captured too. Keep the "before" files: they are the comparison at the
end.

## 2. Run the measurable checks

```bash
python3 <this skill's directory>/scripts/scan.py <the folders or files in scope>
```

Point it at the UI code in scope, the whole frontend for an app-wide pass. The report tags each
candidate `strong` (the pattern rarely survives a design decision), `review` (legitimate in some
contexts) and closes with measures: how many distinct literal radii, shadows, font sizes and
spacings the code uses instead of a scale. Token definitions (custom properties, SCSS
variables, theme files) are the system and never count as tells. Palette and effect classes are
checked only in Tailwind and UnoCSS projects; uppercase eyebrows and text size classes in every
project. A purple token that is a Tailwind default is reported as a
default; purple literals in a project whose tokens are purple are reported as the brand typed by
hand.

In a project with a design system an agent tends to use the tokens, so the scan often comes back
nearly empty: what is left are the decisions, and they show only in the render. Then the plan
comes from step 3, and success is measured on the screenshots, not on the count.

## 3. Judge what the script cannot see

Read [references/tells.md](references/tells.md), then look at the render for:

1. **Density and verbosity.** Helper text that repeats the label, stats nobody asked for, the
   same number shown twice, badges that carry no state, a subtitle under every title. Strip
   first: removing usually does more than restyling.
2. **Hierarchy.** One primary action per view. Three colored buttons of equal weight are no
   hierarchy; a destructive action looks destructive.
3. **Layout.** Everything centered, a column of identical cards, the three equal feature
   columns, every section boxed.
4. **Containers.** A card inside a card, a card around one control, border, shadow and tinted
   background on the same box.
5. **Decoration without a job.** Orbs, rings, sparkles, floating icons, gradients that carry no
   meaning, an icon in a tinted square next to every label.
6. **Type.** The default font at default sizes, no scale, weight as the only hierarchy, a size
   or an uppercase eyebrow no other page uses.
7. **Copy and sample data.** The cliches the script found, exclamation marks, "Oops", John Doe,
   99.9% and +40% everywhere.
8. **Charts.** The library palette and gridlines, a legend that repeats the title, series
   colors unrelated to the product's semantic colors. A chart drawn by hand in SVG or canvas
   gets the same look: the script recognises charts only by their library imports.

## 4. Verify every candidate

Open each one in context and drop what has a job: a fade that masks a scroll edge, a spinner, a
status dot that pulses, a blur behind a modal, a literal a chart library needs as a hex (there
the fix reads the token at runtime, it does not remove the color). Keep the evidence for what
stays: a file and line, or a region of a screenshot.

## 5. Write the plan

One row per element, removals first, then specifications. Each row names the element, the
tell, the change and the exact value: a token name, a component and modifier, or a value the
user gave. The shape that works, after the article's own prompt:

> Card on /dashboard: remove the drop shadow and the 2px outline. Buttons: the system's
> primary button, flat, no icon. Remove the five emoji (listed). Remove the line "use the
> arrows to navigate". Title: the display type token.

- **The system wins.** A literal becomes the token that means it (color, spacing, radius,
  shadow, type step); a hand-styled element becomes the system component with a modifier.
- **No system, no anchors: ask, do not invent.** Offer two or three concrete options (a
  palette in hex, a typeface from a free library, an icon set) or ask for a reference image.
  One decision from the user beats a fashionable default from the agent.
- **Subtract before you substitute.** A removed gradient needs nothing in its place.
- **Keep what works.** Behaviour, states (loading, empty, error, focus) and accessibility
  (contrast in both themes, focus ring, reduced motion) come out at least as good.
- **References are the user's to give.** Their own images, licensed sources or a named public
  style; never a living designer's work fed in for replication.

## 6. Report, then wait

Show the before screenshots, the scan summary (count per tell) and the plan as a table:
element, tell, change, value, evidence. Ask which rows to apply. Change nothing in this step.

## 7. Apply, then show the difference

- Anchored edits, element by element. No global search and replace: the same pattern often
  plays different roles, and a blanket rewrite breaks one of them silently.
- Run the project's checks (lint, typecheck, build) and its visual check.
- Render the same pages in the same themes, put before and after side by side, run the scan
  again and give the counts before and after. Say which checks ran and which were skipped.

## Rules

- Diagnose against the project, never against a taste list: house favourites become the next
  default.
- Read-only until the user approves the plan.
- Every finding cites evidence: a file and line, or a region of a screenshot.
- "Make it look less AI" is not a plan. When another agent or model does the edits, hand it the
  plan, not the slogan.

Based on Maya Brennan, [How to de-slopify your designs](https://uxdesign.cc/how-to-de-slopify-your-designs-4c40c57c1dc9)
(UX Collective, 2026). The catalog in references/ is written anew from its "anatomy of slop".
