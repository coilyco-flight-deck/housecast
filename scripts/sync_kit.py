"""Re-vendor the coilyco kit's primitive ramps into the grading page.

The page carries no build step on purpose, so the kit's primitives are pasted
into it rather than imported. That is the supported shape - the kit is authored
as custom properties precisely so "a page elsewhere inlines the same text" - but
a hand-copied palette drifts silently, and this one did: it sat on _vars.scss
names for months after the kit replaced them.

So the copy is mechanical and checkable. `--check` is the drift gate and needs
a website checkout to compare against; with none present it skips rather than
failing, because housecast must build without one.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

PAGE = Path(__file__).resolve().parent.parent / "housecast/grade/page/index.html"
KIT_REL = "src/sass/_kit.scss"

DECL = re.compile(r"^\s*(--k-[a-z0-9-]+):\s*([^;]+);", re.MULTILINE)
VENDOR_BLOCK = re.compile(
    r"(/\* -- layer 1: kit primitives\. Vendored\. Do not hand-edit; re-vendor\. -- \*/\n)(.*?)(\n\n  /\* -- layer 2)",
    re.DOTALL,
)


def kit_primitives(kit_path: Path) -> dict[str, str]:
    """Every --k-* literal the kit declares on :root, before the ground blocks."""
    text = kit_path.read_text(encoding="utf-8")
    root = text.split(":root {", 1)[1].split("\n}", 1)[0]
    return {m.group(1): m.group(2).strip() for m in DECL.finditer(root)}


def vendored(page_text: str) -> dict[str, str]:
    m = VENDOR_BLOCK.search(page_text)
    if not m:
        sys.exit("could not find the vendored primitive block in the page")
    return {d.group(1): d.group(2).strip() for d in DECL.finditer(m.group(2))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("website", nargs="?", help="path to a coilyco website checkout")
    ap.add_argument("--check", action="store_true", help="report drift, write nothing")
    args = ap.parse_args()

    site = Path(args.website).expanduser() if args.website else None
    if site is None or not (site / KIT_REL).is_file():
        where = f"{site}/{KIT_REL}" if site else "no path given"
        if args.check:
            print(f"sync-kit: no website checkout to compare against ({where}); skipped")
            return 0
        sys.exit(f"sync-kit: need a website checkout carrying {KIT_REL} ({where})")

    kit = kit_primitives(site / KIT_REL)
    page_text = PAGE.read_text(encoding="utf-8")
    have = vendored(page_text)

    missing = sorted(n for n in have if n not in kit)
    drifted = sorted((n, have[n], kit[n]) for n in have if n in kit and have[n] != kit[n])

    sha = subprocess.run(
        ["git", "-C", str(site), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip() or "unknown"

    if missing:
        print("sync-kit: vendored names the kit no longer declares:")
        for n in missing:
            print(f"  {n}")
    if drifted:
        print(f"sync-kit: {len(drifted)} primitive(s) drifted from the kit at {sha}:")
        for n, mine, theirs in drifted:
            print(f"  {n}: page has {mine}, kit has {theirs}")
    if not missing and not drifted:
        print(f"sync-kit: {len(have)} vendored primitives match the kit at {sha}")
        return 0

    if args.check:
        print("\nRe-vendor with `just sync-kit <website>`, then re-derive: moving a")
        print("primitive moves every role bound to it, so re-run the contrast matrix")
        print("on BOTH grounds before believing the page still passes.")
        return 1

    if drifted:
        new = page_text
        for n, mine, theirs in drifted:
            new = re.sub(rf"(^\s*{re.escape(n)}:\s*)[^;]+;", rf"\g<1>{theirs};", new, count=1, flags=re.MULTILINE)
        new = re.sub(r"(website@)[0-9a-f]+", rf"\g<1>{sha}", new, count=1)
        PAGE.write_text(new, encoding="utf-8")
        print(f"\nrewrote {len(drifted)} primitive(s) and stamped website@{sha}")
        print("now re-derive: the roles bound to those primitives have all moved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
