"""`housecast mcpeval` - drive the loop from the command line.

The visual flow is the deliverable, and this exists beside it rather than under
it, because a run that can only be started by clicking cannot be scripted, and
the numbers a report quotes have to come from a command a reader can run.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

import click

from housecast.mcpeval import config as cfg
from housecast.mcpeval import store
from housecast.mcpeval.compare import ComparisonError, DecisionRule, compare
from housecast.mcpeval.definitions import baseline_from
from housecast.mcpeval.models import ModelConfig, probe_tool_calls
from housecast.mcpeval.run import RunConfig, execute
from housecast.mcpeval.runner import advertised_tools
from housecast.mcpeval.subject.server import SUBJECT_VERSION
from housecast.mcpeval.task import available, load_slug


def _model_config(model: str, temperature: float, seed: int | None) -> ModelConfig:
    return ModelConfig(
        base_url=cfg.model_base_url(),
        model=model,
        api_key=cfg.api_key(),
        temperature=temperature,
        seed=seed,
    )


@click.group(name="mcpeval")
def mcpeval() -> None:
    """Change a tool's description and know if it helped."""


@mcpeval.command("subject")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8931, show_default=True, type=int)
def subject_cmd(host: str, port: int) -> None:
    """Serve the subject over HTTP MCP."""
    import uvicorn

    from housecast.mcpeval.subject.server import app

    click.echo(f"subject {SUBJECT_VERSION} on http://{host}:{port}/mcp")
    uvicorn.run(app(), host=host, port=port, log_level="warning")


@mcpeval.command("tasks")
def tasks_cmd() -> None:
    """List the tasks on disk."""
    for path in available():
        task = load_slug(path.stem)
        click.echo(f"{task.slug:24} {len(task.prompts):3} prompts  {task.title}")


@mcpeval.command("preflight")
@click.option("--model", default=None)
def preflight_cmd(model: str | None) -> None:
    """One live request, before a board rather than inside one.

    A route that answers in prose scores every prompt as calling nothing, which
    reads as a catastrophic prose defect and is a transport fact.
    """
    name = model or cfg.model_name()
    click.echo(f"model    {name}")
    click.echo(f"base_url {cfg.model_base_url()}")
    click.echo(f"subject  {cfg.subject_url()}")
    verdict = asyncio.run(probe_tool_calls(_model_config(name, 0.0, 7)))
    if verdict == "ok":
        click.secho("tool_calls: structured, so a board against this route is readable", fg="green")
        return
    click.secho(f"tool_calls: {verdict}", fg="red")
    sys.exit(1)


@mcpeval.command("baseline")
@click.option("--author", default="human:unknown", show_default=True)
@click.option("--root", type=click.Path(path_type=pathlib.Path), default=None)
def baseline_cmd(author: str, root: pathlib.Path | None) -> None:
    """Capture what the subject currently advertises, as the arm everything compares to."""
    from mcp.client.client import Client

    async def go() -> None:
        async with Client(cfg.subject_url()) as subject:
            advertised = await advertised_tools(subject)
        defs = baseline_from(advertised, authored_by=author)
        path = store.save_definitions(defs, root)
        click.echo(f"baseline {defs.short()} over {len(defs.tools)} tools -> {path}")

    asyncio.run(go())


@mcpeval.command("run")
@click.option("--task", required=True)
@click.option(
    "--definitions", "definitions_path", type=click.Path(path_type=pathlib.Path), default=None
)
@click.option("--model", default=None)
@click.option("--temperature", default=0.0, show_default=True, type=float)
@click.option("--seed", default=7, show_default=True, type=int)
@click.option("--concurrency", default=8, show_default=True, type=int)
@click.option("--root", type=click.Path(path_type=pathlib.Path), default=None)
def run_cmd(
    task: str,
    definitions_path: pathlib.Path | None,
    model: str | None,
    temperature: float,
    seed: int,
    concurrency: int,
    root: pathlib.Path | None,
) -> None:
    """Run every prompt of one task against one definition set."""
    from mcp.client.client import Client

    loaded = load_slug(task)
    name = model or cfg.model_name()

    async def go() -> None:
        if definitions_path is not None:
            defs = store.load_definitions(definitions_path)
        else:
            async with Client(cfg.subject_url()) as subject:
                defs = baseline_from(await advertised_tools(subject), authored_by="human:cli")
        click.echo(
            f"{loaded.slug}: {len(loaded.prompts)} prompts, definitions {defs.short()} "
            f"({defs.label or 'unlabelled'}), model {name}, concurrency {concurrency}"
        )

        def progress(done: int, total: int, trial: object) -> None:
            click.echo(f"  {done}/{total}", nl=False)
            click.echo("\r", nl=False)

        run = await execute(
            loaded,
            defs,
            RunConfig(
                subject_url=cfg.subject_url(),
                model=_model_config(name, temperature, seed),
                concurrency=concurrency,
                subject_version=SUBJECT_VERSION,
            ),
            on_progress=progress,
        )
        store.save_definitions(defs, root)
        path = store.save_run(run, root)
        mean = run.mean_score
        click.echo(
            f"{run.run_id}: {len(run.scored)} scored, {len(run.errored)} transport-errored, "
            f"mean {mean:.3f} in {run.duration_seconds:.1f}s -> {path}"
            if mean is not None
            else f"{run.run_id}: nothing scored -> {path}"
        )

    asyncio.run(go())


@mcpeval.command("compare")
@click.argument("before", type=click.Path(path_type=pathlib.Path))
@click.argument("after", type=click.Path(path_type=pathlib.Path))
@click.option("--regression-threshold", default=0.25, show_default=True, type=float)
@click.option("--max-regressions", default=None, type=int)
@click.option("--json", "as_json", is_flag=True)
def compare_cmd(
    before: pathlib.Path,
    after: pathlib.Path,
    regression_threshold: float,
    max_regressions: int | None,
    as_json: bool,
) -> None:
    """Pair two runs of one task, prompt to prompt. Never two averages."""
    rule = DecisionRule(regression_threshold=regression_threshold, max_regressions=max_regressions)
    try:
        report = compare(store.load_run(before), store.load_run(after), rule)
    except ComparisonError as exc:
        click.secho(str(exc), fg="red")
        sys.exit(2)
    click.echo(json.dumps(report.as_dict(), indent=2) if as_json else report.render())


@mcpeval.command("runs")
@click.option("--root", type=click.Path(path_type=pathlib.Path), default=None)
def runs_cmd(root: pathlib.Path | None) -> None:
    """Every run on disk, newest last."""
    for path in store.runs(root):
        run = store.load_run(path)
        mean = run.mean_score
        click.echo(
            f"{run.run_id}  {run.task:20} {run.definition_digest[7:19]}  "
            f"{run.definition_label or '-':16} mean={mean:.3f}  {run.started_at}"
            if mean is not None
            else f"{run.run_id}  {run.task:20} nothing scored  {run.started_at}"
        )


@mcpeval.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8932, show_default=True, type=int)
@click.option("--root", type=click.Path(path_type=pathlib.Path), default=None)
def serve_cmd(host: str, port: int, root: pathlib.Path | None) -> None:
    """The visual flow: task, run, triaged queue, prose editor, comparison."""
    import uvicorn

    from housecast.mcpeval.page.server import build_app

    click.echo(f"the loop on http://{host}:{port}/")
    uvicorn.run(build_app(root), host=host, port=port, log_level="warning")
