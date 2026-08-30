# The grading page palette

Where the page's colour and type come from, and the three places they deviate. The treatment that
uses them is [`grading-page-treatment.md`](grading-page-treatment.md).


The site publishes a token set under its `.docs` scope, and these are those names and those values:
`--umbra` `#16121f` ground, `--penumbra` `#211c33`, `--sink`
`#0d0a14` for a well, `--ink` `#e6e2f2`, `--bright` `#ffffff`, `--quiet`
`#9aabc4`, plus `--mint`, `--amber`, `--coral`, `--sage` `#93b7a4`, `--peri`
`#a9aad0`, and the two hairlines `--edge` and `--edge-soft`. Note `--quiet` is a cool blue-grey rather
than a tint of the accent. Naming them as the
site names them is what lets a value be traced back to `site.css` rather than re-derived.

**The structure matters more than the palette, and it is hairlines and
left-rules rather than boxes.** `.docs__body h2` separates on a `border-top`,
`pre` carries a 2px `--mint` rule over `--sink`, `blockquote` a 2px `--amber`
one, and every rail list a 1px `--edge-soft`. So a card here is a hairline above and a 2px rule at
the left, the current one turning accent, and never a bordered container with a filled header.

Labels follow `.label` and `.docs__shelf`: mono, `.68rem`, weight 700,
`.16em` tracking, uppercase, in `--quiet`. Focus follows the site's own ring,
amber at 3px with a 3px offset, on controls only. **Put that ring on the card itself and it draws
the box this whole treatment removes**, which is worth knowing before someone tries it again.

The board is measured against the site rather than described as matching it. The same probe over
both pages compares mono share, white use, the spacing scale, and the largest type. Against the
docs page the board now runs 51.2px to its 51.2px, 8 distinct gaps to its 8, and 27% mono to its
11%.

**27% is the floor the card's own labels set.** What remains is the response label, the in and out
tags, the case ids, the entity and the crumbs, and 63 cards multiply every one. The prompt and the
pass criterion dropped their labels for that reason; the response kept its own, because the well
alone does not announce it on a fast scan.

Two things the site does that this page does not. Its `data-band` idiom swaps ground colour per
full-bleed section, and a single-scroll board has no section breaks to hang that on. Its prose caps
at `68ch`, and the pair card is deliberately two columns wide, which is the one place the board's
job argues with the site's layout.
