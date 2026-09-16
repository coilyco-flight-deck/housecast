"""Record the MCP loop page as a demo video, unattended.

Drives a running `just mcpeval-serve` through one full iteration (baseline,
run, read, edit, rerun, blind judgement, reveal) with Playwright's own video
capture, then has ffmpeg speed up the stretches spent waiting on the model.
The page makes real model calls, so the numbers in the video are a live run
rather than a replay, and two recordings will not show the same scores.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import time

from playwright.sync_api import Page, sync_playwright

EDIT_TOOL = "media_analyze"
EDIT_LABEL = "narrow media_analyze so it stops winning transcription"
EDIT_PROSE = (
    "Return technical metadata for a media file: duration, dimensions, and whether an "
    "audio track is present. It does NOT return speech, transcripts, subtitles or any "
    "spoken content. To get the words out of a file, use media_transcribe instead."
)
RUN_TIMEOUT_MS = 300_000


class Clock:
    """Wall-clock marks relative to the page opening, so waits map onto the video."""

    def __init__(self) -> None:
        self.start = time.monotonic()
        self.waits: list[tuple[float, float]] = []

    def now(self) -> float:
        return time.monotonic() - self.start

    def wait(self, fn) -> None:
        begin = self.now()
        fn()
        self.waits.append((begin, self.now()))


def run_and_wait(page: Page, clock: Clock, click: str) -> None:
    # A run is finished when #go re-enables and the run header names a new run.
    before = page.text_content("#run-meta") or ""
    page.click(click)
    clock.wait(
        lambda: page.wait_for_function(
            "prev => !document.getElementById('go').disabled"
            " && document.getElementById('run-meta').textContent !== prev",
            arg=before,
            timeout=RUN_TIMEOUT_MS,
        )
    )


def drive(page: Page, url: str, clock: Clock, pause: float) -> None:
    page.goto(url)
    page.wait_for_function("document.getElementById('env').textContent.length > 0")
    page.wait_for_timeout(pause * 1000)

    page.click("#baseline")
    page.wait_for_selector("#p-edit:not(.hidden)")
    page.wait_for_timeout(pause * 1000)

    run_and_wait(page, clock, "#go")
    page.wait_for_timeout(pause * 1000)

    rows = page.locator(".qrow")
    for i in range(min(rows.count(), 2)):
        rows.nth(i).scroll_into_view_if_needed()
        rows.nth(i).click()
        page.wait_for_timeout(pause * 1000)
        rows.nth(i).click()

    page.locator("#p-edit").scroll_into_view_if_needed()
    page.select_option("#tool", EDIT_TOOL)
    page.wait_for_timeout(pause * 500)
    page.fill("#prose", "")
    page.type("#prose", EDIT_PROSE, delay=12)
    page.type("#label", EDIT_LABEL, delay=20)
    page.wait_for_selector("#save:not([disabled])")
    page.wait_for_timeout(pause * 1000)

    run_and_wait(page, clock, "#save")

    clock.wait(lambda: page.wait_for_selector("#p-compare:not(.hidden) button[data-v]", timeout=60_000))
    page.locator("#p-compare").scroll_into_view_if_needed()
    page.wait_for_timeout(pause * 1500)
    page.click("#p-compare button[data-v='b']")
    page.wait_for_selector("#p-compare .verdict")
    page.locator("#p-compare .verdict").scroll_into_view_if_needed()
    page.wait_for_timeout(pause * 3000)


def speed_filter(duration: float, waits: list[tuple[float, float]], factor: float) -> str:
    """One ffmpeg filtergraph: normal speed between waits, `factor` inside them."""
    segments: list[tuple[float, float, float]] = []
    cursor = 0.0
    for begin, end in waits:
        if begin > cursor:
            segments.append((cursor, begin, 1.0))
        segments.append((begin, end, factor))
        cursor = end
    if cursor < duration:
        segments.append((cursor, duration, 1.0))
    parts = []
    for i, (a, b, k) in enumerate(segments):
        parts.append(f"[0:v]trim=start={a:.3f}:end={b:.3f},setpts=(PTS-STARTPTS)/{k}[s{i}]")
    joined = "".join(f"[s{i}]" for i in range(len(segments)))
    parts.append(f"{joined}concat=n={len(segments)}:v=1:a=0,fps=30[out]")
    return ";".join(parts)


def probe_duration(path: pathlib.Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8932/")
    parser.add_argument("--out", type=pathlib.Path, required=True)
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--pause", type=float, default=1.2, help="seconds held on each beat")
    parser.add_argument("--wait-speed", type=float, default=8.0)
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--channel", default="chrome", help="installed browser, so no Playwright download")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    raw_dir = args.out / "raw"
    shutil.rmtree(raw_dir, ignore_errors=True)
    size = {"width": args.width, "height": args.height}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=args.channel or None, headless=not args.headed)
        context = browser.new_context(viewport=size, record_video_dir=str(raw_dir), record_video_size=size)
        page = context.new_page()
        clock = Clock()
        try:
            drive(page, args.url, clock, args.pause)
        finally:
            page.screenshot(path=str(args.out / "final.png"), full_page=True)
            video = pathlib.Path(page.video.path())
            context.close()
            browser.close()

    raw = args.out / "raw.webm"
    video.replace(raw)
    shutil.rmtree(raw_dir, ignore_errors=True)
    duration = probe_duration(raw)
    (args.out / "waits.json").write_text(json.dumps({"duration": duration, "waits": clock.waits}, indent=2))

    mp4 = args.out / "demo.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw),
         "-filter_complex", speed_filter(duration, clock.waits, args.wait_speed),
         "-map", "[out]", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(mp4)],
        check=True,
    )
    gif = args.out / "demo.gif"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf",
         "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer",
         str(gif)],
        check=True,
    )
    print(f"raw {duration:.1f}s, {len(clock.waits)} waits sped {args.wait_speed}x -> {mp4} and {gif}")


if __name__ == "__main__":
    main()
