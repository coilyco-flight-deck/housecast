# The grading page palette

Where the page's colour and type come from, and the three places they deviate.
The treatment that uses them is [`grading-page-treatment.md`](grading-page-treatment.md).

The first cut authored a palette for the grading task and never derived it from
Kai's site, so the page read as a different product: system sans against the
site's Roboto, rounded corners against its square ones, and a neon purple
against its muted ones. The tokens are now the site's, read off its `_vars.scss`
and confirmed against its rendered computed styles.

Ground `#211c33`, surfaces stepping up through `#29243f` to `#3e375d`, the shape
motif tiled at 960px, Roboto embedded as woff2, and every corner square. The
verdict hues are the site's own warm set: sage for pass, coral for fail, and its
focus amber for undecided.

**Two values are lifted rather than copied.** Sage and the accent purple are
Kai's hues and saturations at a higher value, because her mid-value accents were
authored against a light content panel and this page sits them on the dark
ground. Both were lifted only until they cleared AA, and the hue and saturation
are untouched.

**The assets sit beside the page rather than inside it.** Embedding Roboto as a
base64 data URI worked and was reverted: a random 32-character run inside the
woff2 matched a secret detector, and the only ways past that are excluding this
file from the scan, which is precisely the file a leaked payload would land in,
or hoping the next font revision does not collide. Both are worse than a
sibling file. `serve` and `present` mount the page's directory, so the relative
URLs resolve for every mode except a sealed `file://` artifact, which needs the
inlining tracked at `#8`. `LICENSE-FONTS` carries the SIL Open Font License that
redistribution requires.

**Coral and the focus amber sit 21 degrees apart**, which is the one place the
site's palette is weaker than an authored one. It is accepted rather than
corrected because colour is the weakest of the three verdict signals and the
costly confusion, pass against fail, is 130 degrees apart.
