# The grading page

`housecast/grade/page/index.html` renders a committed run and is what `serve
--static` mounts: one file, no build step, nothing resolving a hostname.

## What you see

The board opens on the cases, not on a control panel. A run that has never been
graded is the ordinary first load rather than an error, so 91 ungraded cases is
what the page is designed around, and every slot reads as a slot waiting for a
decision. On a narrow screen the map and the controls fold behind one
disclosure, so the first thing on a phone is a case.

The rail carries the run name, how much is graded, and the board map: one cell
per case, entity-major, in the order the cases appear beside it, so the map is
progress, navigation, and the result heatmap at once.

## The card is the pair, not the case

A boundary challenge has two halves: the in-half asks for something the entity
owns, the out-half asks for something it does not, and a pair scores only when
both are graded. So the card holds both halves side by side. An entity that says
yes to everything passes every in-half and fails every out-half, and that shape
is only visible when the two responses sit adjacent.

The header restates both halves and then names what they say together.

* `in pass // out pass` - the boundary holds
* `in fail // out pass` - refuses work it owns
* `in pass // out fail` - takes work it does not own
* `in fail // out fail` - misses both ways

That is a restatement and never a new rule, and the halves stay on screen beside
it so it is checkable against its own data. Role-fit and personality cases carry
no pair and render as single cards.

## See also

* [`grading-page-treatment.md`](grading-page-treatment.md) - colour and type.
* [`grading-page-delivery.md`](grading-page-delivery.md) - payloads and the test.
