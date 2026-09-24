# Undercurrents - the visual world

Extracted from the shipped app, not invented. Source of truth for every value below:
`web/tailwind.config.ts` (tokens) and `web/src/index.css` (base layer). A hex typed by
hand into a frame is a defect; a value that has no token is a proposal to raise, not a
literal to inline.

## Grounds and surfaces

- `bg` **#0d0710** is the page. `ink` **#08040c** is deeper still and used for insets,
  code blocks and anything that should read as cut *into* the page.
- `bgglow` **#1a0a20** lifts a region without a border.
- Surfaces are not a grey scale: a card is `bg-white/[0.02]` over the ground with a
  `border-white/10` hairline, and a tinted card swaps that for the accent's own wash.
  There is one surface level. **A card inside a card is a defect.**
- Every card carries a single top highlight line (`via-white/20` gradient hairline).
  That is the house's depth language: one hairline, no drop shadow. Borders *or*
  shadows per element, never both.

## Single theme, deliberately

Dark only. `body` is `bg-bg text-white`, and no light variant exists anywhere in `src/`.
This is a commitment, not an oversight: the product is an archive of concert photography
and night-lit data, and a light ground would fight every photograph in it. Recorded here
so no future session "adds the missing light mode".

## Accents, and what each one means

Three accents, which is one more than a created brand would allow itself. They are kept
because they carry **meaning, not decoration**:

- `violet` **#a531d6** (light `#e2a6ff`, dark `#3c0a4a`) is **prediction**. Every model
  output, probability bar and forecast wears it.
- `ember` **#e2492f** (light `#ff9270`, dark `#551408`) is **the record**: measured
  history, analysis, what actually happened.
- `amber` **#d99a3f** is the rare third, used for a single era marker and never as a
  section identity.
- `cream` **#f3dcb8** is the warm text tier for a value being read, against plain white
  for structural text.

A section never borrows the other section's accent. That rule is what lets a reader know
which half of the product they are in without reading a word.

## Type

Four faces, which Path A documents rather than trims:

- `hero` **Unbounded** - the wordmark and the landing headline only. Poster voice.
- `display` **Space Grotesk** - section titles, card headings, numerals that are read
  as figures.
- `mono` **JetBrains Mono** - legitimate only under data, measurement and captions that
  annotate a measurement. Using it to make a label look technical is a defect, and the
  shipped UI currently does this in places (see "Known debts").
- `body` **Inter** - prose.

Numerals in any table or data list take `font-variant-numeric: tabular-nums` so columns
align. Headings take `text-wrap: balance`.

## Radius, motion, browser surfaces

- Radius is a scale, not a constant: `rounded-full` for small controls only, `rounded-2xl`
  for cards, `rounded-xl` for photo chips. A pill on a large container is a defect.
- Motion is one deliberate entrance per region (`anim-fade-in-up`, staggered), ease-out,
  from a visible state, and must honour `prefers-reduced-motion`.
- The browser surfaces are already claimed and stay claimed: selection uses violet on
  ink, and the scrollbar is a violet-tinted thumb. Focus rings are the remaining gap.

## Voice

Plain, measured, and never triumphant. A number is always accompanied by what it was
measured against and how many samples it rests on. Where a model loses to its baseline,
the page says so in the same voice it uses when the model wins. No exclamation marks, no
"insights", no rounding a weak result up.

## Known debts (what a redesign should fix, not preserve)

These are shipped patterns that the craft bar names as generated-UI tells. They are
recorded here so they are fixed deliberately rather than re-copied:

1. **No icon system at all.** The app draws arrows with "→" and has no icon set. Phosphor
   is the house default when a repo has none.
2. **Charts are hand-built from divs and raw SVG.** Real charts belong to a charting
   library; hand-rolled bars are a defect when the real thing is one import away.
3. **Uppercase mono eyebrow labels above almost every heading**, which is decoration
   wearing the clothes of data.
4. **Numbered section markers 01 through 13** on the tab bar, where the order carries
   no information.
5. **The oversized-number-with-tiny-label stat hero**, repeated on most pages.
6. Numerals are not tabular, and focus-visible states are largely unstyled.
