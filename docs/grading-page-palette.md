# The grading page palette

Where the page's colour and type come from, and the three places they deviate. The treatment that
uses them is [`grading-page-treatment.md`](grading-page-treatment.md).

The first cut authored a palette for the grading task and never derived it from Kai's site, so the
page read as a different product: system sans against the site's Roboto, rounded corners against
its square ones, and a neon purple against its muted ones. The tokens are now the site's, read off
its `_vars.scss` and confirmed against its rendered computed styles.

The site publishes a token set under its `.docs` scope, and these are those names and those values:
`--umbra` `#16121f` ground, `--penumbra` `#211c33`, `--sink`
`#0d0a14` for a well, `--ink` `#e6e2f2`, `--bright` `#ffffff`, `--quiet`
`#9aabc4`, plus `--mint`, `--amber`, `--coral`, `--sage` `#93b7a4`, `--peri`
`#a9aad0`, and the two hairlines `--edge` and `--edge-soft`. Naming them as the
site names them is what lets a value be traced back to `site.css` rather than re-derived.

**`--quiet` is a cool blue-grey rather than a purple**, which two earlier passes
guessed wrong. The site's muted text is not a tint of its accent.

**The structure matters more than the palette, and it is hairlines and
left-rules rather than boxes.** `.docs__body h2` separates on a `border-top`,
`pre` carries a 2px `--mint` rule over `--sink`, `blockquote` a 2px `--amber`
one, and every rail list a 1px `--edge-soft`. So a card here is a hairline above and a 2px rule at
the left, the current one turning accent, and never a bordered container with a filled header.

Labels follow `.label` and `.docs__shelf`: mono, `.68rem`, weight 700,
`.16em` tracking, uppercase, in `--quiet`. Focus follows the site's own ring,
amber at 3px with a 3px offset, on controls only. **Put that ring on the card itself and it draws
the box this whole treatment removes**, which is worth knowing before someone tries it again.

Two things the site does that this page does not. Its `data-band` idiom swaps ground colour per
full-bleed section, and a single-scroll board has no section breaks to hang that on. Its prose caps
at `68ch`, and the pair card is deliberately two columns wide, which is the one place the board's
job argues with the site's layout.

**Coral and the focus amber sit 21 degrees apart**, the one place the site's palette is weaker than
an authored one. Accepted rather than corrected, because colour is the weakest of the three verdict
signals and the costly confusion, pass against fail, is 130 degrees apart.
