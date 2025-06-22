"""
Initapp command implementation.

Generates full application components based on configuration.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

console = Console()


def initapp_command(
    app_name: Annotated[str, typer.Argument(help="Application name to initialize")],
    level: Annotated[str, typer.Option("--level", help="App level (BasicCRUD/Advanced/Enterprise)")] = "",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be generated")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing files")] = False,
    strategy: Annotated[str, typer.Option("--strategy", help="Merge strategy (safe/regenerate/interactive)")] = "safe",
    backup: Annotated[bool, typer.Option("--backup", help="Create backup before changes")] = False,
    template_dir: Annotated[str, typer.Option("--template-dir", help="Custom template directory")] = "",
):
    """
    ⚡ Generate full application components.

    Generates all components based on app_config.toml:
    - Models, schemas, repository, service, API routes
    - Exception hierarchy with rich traceback
    - Full test suite with factories and E2E tests
    - Automatic Alembic migration
    - pyproject.toml metadata update
    """

    # Проверка существования приложения
    app_path = Path(f"src/apps/{app_name}")
    if not app_path.exists():
        console.print(f"[red]❌ App '{app_name}' not found[/red]")
        console.print(f"[dim]Run 'autogen startapp {app_name}' first[/dim]")
        raise typer.Exit(1)

    # Проверка конфигурации
    config_file = app_path / "app_config.toml"
    if not config_file.exists():
        console.print(f"[red]❌ Configuration file not found: {config_file}[/red]")
        raise typer.Exit(1)

    try:
        if dry_run:
            console.print(
                Panel(
                    f"[yellow]🔍 DRY RUN MODE[/yellow]\n"
                    f"Would generate components for: [bold]{app_name}[/bold]\n"
                    f"Level: {level or 'from config'}\n"
                    f"Strategy: {strategy}\n"
                    f"Template dir: {template_dir or 'default'}\n"
                    f"Backup: {'yes' if backup else 'no'}",
                    title="Dry Run",
                    border_style="yellow",
                )
            )
        else:
            console.print(f"[yellow]⚠️ initapp command not fully implemented yet[/yellow]")
            console.print(f"[dim]Working on: {app_name}, level: {level or 'auto-detect'}[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Failed to initialize app: {e}[/red]")
        raise typer.Exit(1)
