# The grading page

`housecast/grade/page/index.html` renders a committed run and is what `serve
--static` mounts: one file, no build step, nothing resolving a hostname.

## What you see

The board opens on the cases, not on a control panel. A run that has never been graded is the ordinary first load rather than an error, so 91 ungraded
cases is what the page is designed around, and every slot reads as a slot waiting for a decision. On a narrow screen the map and the controls fold
behind one disclosure, so the first thing on a phone is a case. A card is addressable: `?card=7` is the seventh card, matching the counter and
rewritten as you move, and `?case=<id>` takes a case or a pair id and survives a reorder that a position does not.

The rail carries the run name, how much is graded, and the board map: one cell
per case, grouped by entity with a tally each, so the map is
progress, navigation, and the result heatmap at once.

## The card is the pair, not the case

A paired challenge has two halves: the in-half asks for the case the rule
covers, the out-half asks for the neighbouring case it must not cover, and a pair scores only when
both are graded. So the card holds both halves side by side. An entity that says
yes to everything passes every in-half and fails every out-half, and that shape
is only visible when the two responses sit adjacent.

The header restates both halves and then names what they say together, in the
words the profile gives each outcome (`pass/pass`, `fail/pass`, `pass/fail`,
`fail/fail`). The page holds no wording of its own.
That is a restatement and never a new rule, and the halves stay on screen beside
it so it is checkable against its own data. A case that carries
no pair renders as a single card.

## See also

* [`grading-page-treatment.md`](grading-page-treatment.md) - color and type.
* [`grading-page-delivery.md`](grading-page-delivery.md) - payloads and the test.
