# The room's pages

The three pages [`room.md`](room.md) serves from `housecast/room/page/`, with no build step.

## One room, three readers

* `/` is the attendee page on a phone: the info page, then submit plus the live leaderboard, then grade, the split, and closing, whichever phase the presenter set.
* `/screen` is shared into the call and lands on the public recording. It reads `?view=screen`, so no prompt text reaches it until the presenter picks one. In closing it counts failing grades rather than printing their reasons, because the reasons are attendee-typed.
* `/present` is the presenter's. A token in `#token=` is taken once and dropped from the address.

## Why it looks like this

The presenter's session flow deck is the visual reference, so the pages take its dark slate, IBM Plex Sans, and each subject's fixed colour and emblem rather than the kit's purple. A subject is always its emblem, name, and colour together, never hue alone. Divergence bars are neutral because rose means FAIL.

The shared screen scales type off the short side of the window, since the projector's aspect is unknown.

## Working on them

`?demo=holding|submissions|grading|split|closing|flow` renders any page from a scripted room in the contract's shapes, marked "demo data", with no server. A page redraws each second for its timers and only rewrites markup that changed, so a half-typed reason survives and a screen reader is not re-announced.
