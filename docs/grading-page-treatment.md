# The grading page, colour and type

How [`grading-page.md`](grading-page.md) treats evidence, verdicts, and scale. The values
themselves are coilysiren.me's own, in [`grading-page-palette.md`](grading-page-palette.md).

## Evidence and critique share one purple

Purple carries structure and the evidence span and is never a verdict, so a verdict never reads as
an accent and an accent never reads as a verdict.

The highlighted span and the critique below it are the same purple, which is the whole claim: this
span is why that sentence was written. Nothing draws a line between them, because a line is
geometry that breaks on reflow and colour is not.

`evidence` was checked verbatim against `output` when recorded, so a match is
expected. The page matches again rather than trusting, and says so in the card when it fails,
because a highlight that silently misses is worse than one that reports it. Empty `evidence`
renders the critique with no highlight, and a graded case with no critique says so rather than
showing an empty block.

## Verdicts never rely on hue alone

Each verdict carries a glyph, a word, and a colour, the colour weakest of the three. Pass and fit
take teal, fail and does-not-fit rose, undecided amber, an ungraded slot a dashed outline. Measured
live in the rendered page, every painted text role clears WCAG AA in both themes.

The kit's registers retired the 21-degree coral/amber near-miss and **took amber off focus**: a
focused card used to recolour its entity label to the hue meaning UNDECIDED. Focus and current-ness
are structure and take purple, so amber only means undecided now. Each chapter carries its agent
and an element glyph from `roster.yaml`, the glyph doing what a colour would: the kit holds no
spare hue, the warm ones being verdict-locked and there being no blue at all.

## Scale and keyboard

`j` and `k` move between cards, `g` and `G` jump to the ends, `+` and `-` move
the type scale, `t` switches theme, `f` cycles the filter. Focus follows the card, so the keyboard
and the pointer land in the same place.

The scale runs 0.9x to 1.9x off one `--zoom` token on the root, which is the projector solve: at
1.9x a response reads at 32px, pair card intact, no sideways scroll.
