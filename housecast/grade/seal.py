"""Write an export into a copy of the page, so it renders from a file path.

The page ships with `null` in its slot and stays that way. Sealing produces a
new file somewhere else, because a committed payload is a record of somebody's
board and the tracked page is not where one lives. See docs/grading-page.md.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from housecast.grade.export import ExportRefusedError

SLOT_OPEN = '<script type="application/json" id="embedded-export">'
SLOT_CLOSE = "</script>"

PAGE = Path(__file__).parent / "page" / "index.html"

# Referenced beside the page, never inlined into it: base64 in a committed file
# once matched trufflehog as a Box key. See docs/grading-page-delivery.md.
ASSETS = (
    "roboto-latin-400-normal.woff2",
    "roboto-latin-700-normal.woff2",
    "background-shapes.svg",
)


def _data_uri(asset: Path) -> str:
    """base64 for the fonts, percent-encoded for the SVG, which is smaller as text."""
    if asset.suffix == ".svg":
        return "data:image/svg+xml," + quote(asset.read_text(encoding="utf-8"))
    return "data:font/woff2;base64," + base64.b64encode(asset.read_bytes()).decode("ascii")


def inline_assets(page: str, assets_dir: Path) -> str:
    """Fold the sibling fonts and motif into the page, so a file:// copy carries them."""
    for name in ASSETS:
        reference = f'url("{name}")'
        if reference not in page:
            raise ExportRefusedError(
                f"the page no longer references {name}, so sealing it is a lie"
            )
        asset = assets_dir / name
        if not asset.is_file():
            raise ExportRefusedError(
                f"{name} is missing beside the page, so the seal would lose it"
            )
        page = page.replace(reference, f'url("{_data_uri(asset)}")')
    return page


def seal(page: str, payload: dict[str, Any]) -> str:
    """Replace the slot's contents, leaving every other byte of the page alone."""
    start = page.find(SLOT_OPEN)
    if start < 0:
        raise ExportRefusedError(f"the page carries no {SLOT_OPEN!r} slot to seal into")
    opened = start + len(SLOT_OPEN)
    closed = page.find(SLOT_CLOSE, opened)
    if closed < 0:
        raise ExportRefusedError("the page's embedded-export slot is never closed")

    body = json.dumps(payload, separators=(",", ":"))
    # `</script>` inside the JSON would close the slot early and drop the rest
    # of the payload into the document as markup.
    if SLOT_CLOSE in body.lower():
        raise ExportRefusedError("the payload contains a closing script tag, which would break out")
    return page[:opened] + body + page[closed:]


def seal_to(out: Path, payload: dict[str, Any], page_path: Path = PAGE) -> Path:
    """Always writes a copy. Refuses to overwrite the page it read."""
    page_path = page_path.resolve()
    if out.resolve() == page_path:
        raise ExportRefusedError(
            "refusing to seal over the page itself, because the tracked file holds null"
        )
    sealed = seal(page_path.read_text(encoding="utf-8"), payload)
    out.write_text(inline_assets(sealed, page_path.parent), encoding="utf-8")
    return out
