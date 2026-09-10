# The grading page palette

Where the colour and type come from, and where they deviate. The treatment using them is
[`grading-page-treatment.md`](grading-page-treatment.md).

## Vendored from the kit, never fetched

The page carries the coilyco kit's **primitive ramps**, verbatim from `src/sass/_kit.scss` on
`coilyco-flight-deck/website`. The kit is authored as custom properties for this reason, in its own
words: the site compiles that file, and a page elsewhere inlines the same text. It vendors rather
than fetches because a shipped tool never reaches up into another repo for its runtime config, and
the absent build step is this page's safety property.

**Three layers, and nothing skips one.** Primitives are the only literal colours here. Roles
(`--ground`, `--affirm`) are `var()` onto a primitive and are all a component rule may read. A rule
may rebind a role from a primitive, as `.output` does, and may never paint one directly.
`grade/tests/test_page_tokens.py` fails on each, and runs anywhere.

Hand-copying is what went wrong before: the page sat on the retired `_vars.scss` names for months
after the kit replaced them, because nothing could tell the source had moved. `just sync-kit
../website` re-vendors and stamps the commit, `just sync-kit-check` reports drift but **skips with
no website checkout**, so the layer tests carry CI. Moving a primitive moves every role bound to it.

## The three deviations, each deliberate

* **Type is this board's own** - the kit floors text at 16px, and 105 cases do not fit a projector
  at that floor, so `--t-0` starts at `.68rem` and `--zoom` carries the room, 0.9x to 1.9x.
* **Mono is the system stack** - a second vendored face costs more than a 27% mono share earns.
* **Components are not adopted** - a card is a hairline and a 2px left rule, never a bordered
  container. A composition consumes the system, it does not join it.

## Structure, and what is measured

`--line` is the kit's quiet hairline and `--line-2` its `--k-edge`, both neutral, so the board takes
`--k-line-quiet` over the accent-coloured `--k-line`: that edge would sit 21 degrees from the deduct
verdict at one lightness. The **frame does not flip** - nav and footer hold `--k-p-850` on both
themes, the kit's rule 3, absent from the light block. Every painted role is measured live against the background it lands on, both themes, worst case
rather than a list. `.ctl[aria-pressed]` paints brand on a 16% brand wash where brand itself lands
at 4.30:1, so `--accent-on-wash` takes a brighter step: 5.56:1 ink, 6.10:1 paper, zero failures.
