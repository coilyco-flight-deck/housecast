"""Human annotation loop. One challenge per screen, one keystroke per decision.

Annotations are appended after every decision, so an interrupted session keeps
everything already annotated.
"""

from __future__ import annotations

import sys
import termios
import time
import tty
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from housecast.grade.io import save_annotations
from housecast.grade.schema import (
    AGENT_COMPOSE,
    DEDUCTIONS,
    LABEL_SETS,
    Annotation,
    DatasetEntry,
    Fit,
    Profile,
    Verdict,
    annotation_order,
    pair_results,
)

LABEL_HELP = {
    Verdict.PASS: "pass",
    Verdict.FAIL: "fail",
    Fit.FIT: "fit",
    Fit.UNDECIDED: "undecided",
    Fit.NO_FIT: "does not fit",
}

TYPE_STYLES = ("bright_cyan", "bright_magenta", "bright_yellow", "bright_green", "bright_blue")


def read_key() -> str:
    """Single keypress without a newline, so annotation stays one stroke."""
    if not sys.stdin.isatty():
        return sys.stdin.read(1) or "q"
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def style_for(profile: Profile, test_type: str) -> str:
    return TYPE_STYLES[profile.rank(test_type) % len(TYPE_STYLES)]


def entity_header(console: Console, roster: dict[str, Any], entity: str) -> None:
    """Printed once per entity, so the charter is loaded rather than implied.

    The roster is a projection the deployment composes, because owns, defers,
    and traits are its words. This layer renders lines rather than reading a
    shape it would then have to know. See docs/grading.md.
    """
    spec = roster.get("entities", {}).get(entity)
    if not spec:
        return
    lines = [f"[bold]{spec.get('display_name', entity)}[/bold]  {spec.get('purpose', '')}"]
    lines.extend(str(note) for note in spec.get("notes", []))
    console.print(Panel("\n".join(lines), border_style="bright_white", title="entity"))


def render(
    console: Console,
    entry: DatasetEntry,
    position: int,
    total: int,
    started: float,
    profile: Profile,
    roster: dict[str, Any] | None = None,
) -> None:
    challenge = entry.challenge
    style = style_for(profile, challenge.test_type)
    console.clear()
    if roster:
        entity_header(console, roster, challenge.entity)

    header = Table.grid(padding=(0, 2))
    header.add_column(style="bold")
    header.add_column()
    header.add_row("challenge", f"[bold]{challenge.id}[/bold]")
    header.add_row("entity", challenge.entity)
    header.add_row("test type", f"[{style}]{challenge.test_type}[/]")
    if challenge.attribute:
        half = f" ({challenge.half.value})" if challenge.half else ""
        header.add_row("attribute", f"{challenge.attribute}{half}")
    header.add_row("progress", progress(position, total, started))
    console.print(header)
    console.print()

    console.print(Panel(challenge.prompt or "", title="prompt", border_style="dim"))
    words = len(entry.output.split())
    console.print(
        Panel(
            entry.output,
            title=f"output ({words} words, cap {challenge.word_cap(profile)})",
            border_style=style,
        )
    )
    console.print(Panel(challenge.target or "", title="target", border_style="green"))

    keys = LABEL_SETS[challenge.label_set(profile)]
    hints = "    ".join(f"[bold]{key}[/bold] {LABEL_HELP[label]}" for key, label in keys.items())
    console.print(f"{hints}    [bold]s[/bold] skip    [bold]q[/bold] quit")


def ask(console: Console, label: str, hint: str) -> str:
    """Styled prompt printed first, then a bare readline.

    console.input hands readline a prompt carrying ANSI colour codes, readline
    miscounts the cursor column, and an answer long enough to wrap overwrites
    itself. An empty prompt leaves readline nothing to miscount.
    """
    console.print(f"[bold]{label}[/bold] ({hint})")
    return input("> ").strip()


def collect_evidence(console: Console, output: str) -> tuple[str, str]:
    """RULERS anchors a deduction to a verbatim span, verified against the output."""
    critique = ask(console, "critique", "what it did wrong")
    while True:
        evidence = ask(console, "evidence", "verbatim quote, blank to skip")
        if not evidence or evidence.lower() in output.lower():
            return critique, evidence
        console.print("[red]not found verbatim in the output[/red]")


def annotate_session(
    dataset: list[DatasetEntry],
    annotations: dict[str, Annotation],
    out: Path,
    profile: Profile = AGENT_COMPOSE,
    roster: dict[str, Any] | None = None,
) -> bool:
    """Returns False when the annotator quit before finishing."""
    console = Console()
    entity_order = list(roster.get("entity_order", [])) if roster else None
    pending = [
        entry
        for entry in annotation_order(dataset, profile, entity_order)
        if entry.id not in annotations
    ]
    started = time.monotonic()

    for index, entry in enumerate(pending, start=1):
        keys = LABEL_SETS[entry.challenge.label_set(profile)]
        while True:
            render(console, entry, index, len(pending), started, profile, roster)
            key = read_key().lower()
            if key == "q":
                return False
            if key == "s":
                break
            if key in keys:
                label = keys[key]
                critique, evidence = "", ""
                if label in DEDUCTIONS:
                    console.print()
                    critique, evidence = collect_evidence(console, entry.output)
                annotations[entry.id] = Annotation(
                    id=entry.id, label=label, critique=critique, evidence=evidence
                )
                save_annotations(out, annotations)
                break
    return True


def summarize(
    console: Console, dataset: list[DatasetEntry], annotations: dict[str, Annotation]
) -> None:
    pairs = pair_results(dataset, annotations)
    if pairs:
        table = Table(title="boundary pairs, the scoring unit")
        for column in ("pair", "entity", "attribute", "result"):
            table.add_column(column)
        for pair in pairs:
            if not pair.complete:
                result = "[yellow]incomplete[/yellow]"
            elif pair.passed:
                result = "[green]pass[/green]"
            else:
                result = "[red]fail[/red]"
            table.add_row(pair.pair_id, pair.entity, pair.attribute, result)
        console.print(table)

    # Only this dataset's ids. An annotations file outlives a case rename, so
    # counting the whole file reports more grades than there are cases.
    ids = {entry.id for entry in dataset}
    current = {key: value for key, value in annotations.items() if key in ids}
    counts: dict[str, int] = {}
    for annotation in current.values():
        counts[annotation.label.value] = counts.get(annotation.label.value, 0) + 1
    console.print(
        f"\nannotated {len(current)} of {len(dataset)}: "
        + ", ".join(f"{value} {key}" for key, value in sorted(counts.items()))
    )
    if stale := len(annotations) - len(current):
        console.print(f"[yellow]{stale} annotations are for ids not in this dataset[/yellow]")


def progress(position: int, total: int, started: float) -> str:
    elapsed = time.monotonic() - started
    if position <= 1:
        return f"{position}/{total}"
    rate = elapsed / (position - 1)
    remaining = rate * (total - position + 1)
    return f"{position}/{total}  {elapsed / 60:.0f}m elapsed  ~{remaining / 60:.0f}m left"
