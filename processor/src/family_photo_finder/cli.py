"""Click-based command-line interface."""

from __future__ import annotations

import json
import shutil
import webbrowser
from pathlib import Path

import click
from rich.panel import Panel

from .config import Config, Paths, default_processor_root
from .deploy import deploy_to_website
from .drive import MissingCredentialsError
from .logging_utils import get_console, get_logger, setup_logging
from .pipeline import run_pipeline
from .site import SiteBuilder
from .state import PipelineState

logger = get_logger(__name__)


SETUP_INSTRUCTIONS = """\
[bold]Google Drive credentials are required.[/bold]

The processor uses the official Google Drive API. Follow these steps once:

  [bold cyan]1.[/bold cyan] Create or pick a Google Cloud project:
     [link=https://console.cloud.google.com/projectcreate]https://console.cloud.google.com/projectcreate[/link]

  [bold cyan]2.[/bold cyan] Enable the [bold]Google Drive API[/bold]:
     [link=https://console.cloud.google.com/apis/library/drive.googleapis.com]https://console.cloud.google.com/apis/library/drive.googleapis.com[/link]
     -> click [bold]Enable[/bold].

  [bold cyan]3.[/bold cyan] Configure the OAuth consent screen (External + Testing is fine):
     [link=https://console.cloud.google.com/apis/credentials/consent]https://console.cloud.google.com/apis/credentials/consent[/link]
     Add your own Google account as a test user.

  [bold cyan]4.[/bold cyan] Create credentials:
     [link=https://console.cloud.google.com/apis/credentials]https://console.cloud.google.com/apis/credentials[/link]
     -> [bold]Create Credentials -> OAuth client ID -> Desktop app[/bold].

  [bold cyan]5.[/bold cyan] Download the JSON and save it as:
     [bold yellow]{credentials_path}[/bold yellow]

  [bold cyan]6.[/bold cyan] Rerun your command. A browser will open once for consent and
     a refresh token is written to [bold]token.json[/bold] so future runs are silent.

Only the read-only scope [italic]drive.readonly[/italic] is requested.
"""


def _render_missing_credentials(credentials_path: Path) -> None:
    console = get_console()
    body = SETUP_INSTRUCTIONS.format(credentials_path=credentials_path)
    console.print(
        Panel(
            body,
            title="[bold red]Missing credentials.json[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )


def _load_context(config_path: Path, verbose: bool) -> tuple[Config, Paths]:
    setup_logging(verbose=verbose)
    processor_root = default_processor_root()
    paths = Paths.from_processor_root(processor_root)
    paths.ensure()
    config = Config.load(config_path)
    return config, paths


@click.group(
    invoke_without_command=True,
    help=(
        "Family Function Photo Finder — turn a Google Drive folder into a "
        "static photo-finder website."
    ),
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Path to config.yaml (defaults to processor/config.yaml).",
)
@click.option(
    "--folder-url",
    "folder_url",
    default=None,
    help=(
        "Shorthand: when provided without a subcommand, runs the full pipeline. "
        "Equivalent to `process --folder-url URL`."
    ),
)
@click.option("-v", "--verbose", is_flag=True, help="Verbose logging.")
@click.pass_context
def cli(
    ctx: click.Context,
    config_path: Path | None,
    folder_url: str | None,
    verbose: bool,
) -> None:
    if config_path is None:
        config_path = default_processor_root() / "config.yaml"
    config, paths = _load_context(config_path, verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["paths"] = paths

    if ctx.invoked_subcommand is None:
        if folder_url is None and not config.google_drive_folder:
            click.echo(ctx.get_help())
            return
        ctx.invoke(process, folder_url=folder_url, concurrency=None, keep_cache=False)


@cli.command(help="Run the full pipeline: download -> detect -> cluster -> thumbnails.")
@click.option(
    "--folder-url",
    "folder_url",
    default=None,
    help="Google Drive folder URL or ID (overrides config.yaml).",
)
@click.option(
    "--concurrency",
    type=int,
    default=None,
    help=(
        "Parallel Drive downloads. Default 4. Drop to 1-2 on a flaky "
        "network (corporate VPN, weak Wi-Fi)."
    ),
)
@click.option(
    "--keep-cache",
    is_flag=True,
    help="Do not delete processor/cache/ after processing (debugging only).",
)
@click.pass_context
def process(
    ctx: click.Context,
    folder_url: str | None,
    concurrency: int | None,
    keep_cache: bool,
) -> None:
    config: Config = ctx.obj["config"]
    paths: Paths = ctx.obj["paths"]
    console = get_console()

    target_url = folder_url or config.google_drive_folder
    if not target_url:
        raise click.UsageError(
            "Provide --folder-url or set google_drive_folder in config.yaml."
        )

    console.rule(f"[bold]Processing {config.event_title}[/bold]")
    try:
        summary = run_pipeline(
            config=config,
            paths=paths,
            folder_url=target_url,
            skip_cleanup=keep_cache,
            concurrency=concurrency,
        )
    except MissingCredentialsError as exc:
        _render_missing_credentials(exc.credentials_path)
        raise click.exceptions.Exit(code=2) from None
    console.rule("[bold green]Done[/bold green]")
    console.print(
        f"Photos: [bold]{summary.photo_count}[/bold]   "
        f"Faces: [bold]{summary.face_count}[/bold]   "
        f"Clusters: [bold]{summary.cluster_count}[/bold]"
    )
    console.print(
        f"Open the review UI:  [cyan]uv run photo-finder review[/cyan]"
    )


@cli.command(help="Open the static review UI for naming clusters.")
@click.option("--no-open", is_flag=True, help="Print the path instead of opening it.")
@click.pass_context
def review(ctx: click.Context, no_open: bool) -> None:
    paths: Paths = ctx.obj["paths"]
    target = paths.review_dir / "index.html"
    if not target.exists():
        raise click.UsageError(
            f"{target} not found. Run `photo-finder process` first."
        )

    console = get_console()
    console.print(f"Review UI: [cyan]{target}[/cyan]")
    console.print(
        "Type names, click [bold]Export labels.json[/bold], then save it next to "
        f"[cyan]{paths.state_dir / 'labels.json'}[/cyan]."
    )

    if no_open:
        return
    try:
        webbrowser.open(target.as_uri())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not auto-open review UI: %s", exc)


@cli.command("generate-site", help="Build website-data/people.json.")
@click.option(
    "--labels",
    "labels_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Optional labels.json exported from the review UI. Defaults to "
        "processor/state/labels.json."
    ),
)
@click.pass_context
def generate_site(ctx: click.Context, labels_path: Path | None) -> None:
    config: Config = ctx.obj["config"]
    paths: Paths = ctx.obj["paths"]
    state = PipelineState(paths.state_dir)

    photos = state.load_photos()
    faces = state.load_faces()
    clusters = state.load_clusters()
    if not photos or not clusters:
        raise click.UsageError(
            "No pipeline state found. Run `photo-finder process` first."
        )

    labels = state.load_labels()
    if labels_path is not None:
        if not labels_path.exists():
            raise click.UsageError(f"labels file not found: {labels_path}")
        with labels_path.open("r", encoding="utf-8") as fh:
            labels = json.load(fh)
        state.save_labels(labels)

    builder = SiteBuilder(config)
    target = builder.build(photos, faces, clusters, labels, paths.site_data_dir)
    get_console().print(f"Wrote [cyan]{target}[/cyan]")


@cli.command(help="Copy generated assets into website/public/data/.")
@click.pass_context
def deploy(ctx: click.Context) -> None:
    paths: Paths = ctx.obj["paths"]
    deploy_to_website(paths)
    get_console().print(
        f"Assets ready at [cyan]{paths.website_public_data_dir}[/cyan]. "
        "Run [bold]npm run build[/bold] inside ../website to ship the site."
    )


@cli.command(help="Print step-by-step Google Drive credential setup instructions.")
@click.pass_context
def setup(ctx: click.Context) -> None:
    paths: Paths = ctx.obj["paths"]
    _render_missing_credentials(paths.processor_root / "credentials.json")


@cli.command("import-labels", help="Import a labels.json exported by the review UI.")
@click.argument(
    "labels_file", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.pass_context
def import_labels(ctx: click.Context, labels_file: Path) -> None:
    paths: Paths = ctx.obj["paths"]
    state = PipelineState(paths.state_dir)
    target = state.labels_path
    shutil.copyfile(labels_file, target)
    get_console().print(f"Imported labels into [cyan]{target}[/cyan].")


if __name__ == "__main__":
    cli(obj={})
