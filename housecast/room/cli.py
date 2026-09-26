"""`housecast room serve`: run one room from a subjects file and a restart log."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

import click

from housecast.room.models import Settings
from housecast.room.server import DEFAULT_PORT, serve
from housecast.room.store import Room
from housecast.room.subjects import load_subjects


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def room() -> None:
    """The live room: intake, fan-out, divergence, restart log."""


@room.command(name="serve")
@click.option(
    "--subjects", "subjects_path", type=click.Path(exists=True, path_type=Path), required=True
)
@click.option(
    "--log",
    "log_path",
    type=click.Path(path_type=Path),
    required=True,
    help="append-only restart log; replayed on start",
)
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=DEFAULT_PORT, show_default=True)
@click.option(
    "--proxy",
    envvar="ROOM_PROXY",
    default="http://ser8:8080",
    show_default=True,
    help="OpenAI-compatible proxy base URL",
)
@click.option(
    "--model", envvar="ROOM_MODEL", default="evaluation/deepseek-v4-pro", show_default=True
)
@click.option("--jev-model", envvar="ROOM_JEV_MODEL", default="jev-1.13.0", show_default=True)
@click.option(
    "--rate-seconds", default=20.0, show_default=True, help="one prompt per client per window"
)
@click.option(
    "--address-burst",
    default=30,
    show_default=True,
    help="prompts per address per window; the ceiling on minted device tokens",
)
@click.option(
    "--devices-per-address",
    default=100,
    show_default=True,
    help="distinct grading devices per address per round",
)
def serve_cmd(
    subjects_path: Path,
    log_path: Path,
    host: str,
    port: int,
    proxy: str,
    model: str,
    jev_model: str,
    rate_seconds: float,
    address_burst: int,
    devices_per_address: int,
) -> None:
    """Serve the room. ROOM_CONTROL_TOKEN gates the presenter controls."""
    subjects = load_subjects(subjects_path)
    state = Room(subjects=subjects, log_path=log_path)
    state.load()
    token = os.environ.get("ROOM_CONTROL_TOKEN") or secrets.token_urlsafe(9)
    if "ROOM_CONTROL_TOKEN" not in os.environ:
        click.echo(f"control token: {token}", err=True)
    cfg = Settings(
        proxy=proxy.rstrip("/"),
        model=model,
        jev_model=jev_model,
        key=os.environ.get("ROOM_PROXY_KEY"),
    )
    click.echo(f"room: {len(subjects)} subjects, rev {state.rev}, http://{host}:{port}", err=True)
    serve(state, cfg, token, host, port, rate_seconds, address_burst, devices_per_address)
