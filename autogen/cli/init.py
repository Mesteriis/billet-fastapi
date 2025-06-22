"""
Application initialization commands.

This module provides the initapp command for initializing existing FastAPI applications
with generated templates.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing_extensions import Annotated

from autogen.core.generators import AppGenerator, GenerationConfig

console = Console()


def initapp_command(
    app_name: Annotated[str, typer.Argument(help="Application name to initialize")],
    level: Annotated[str, typer.Option("--level", help="App level (BasicCRUD/Advanced/Enterprise)")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be generated")] = False,
    overwrite: Annotated[bool, typer.Option("--overwrite", help="Overwrite existing files")] = False,
    strategy: Annotated[str, typer.Option("--strategy", help="Merge strategy (safe/regenerate/interactive)")] = "safe",
    backup: Annotated[bool, typer.Option("--backup", help="Create backup before changes")] = False,
    template_dir: Annotated[str, typer.Option("--template-dir", help="Custom template directory")] = "",
):
    """
    Initialize existing FastAPI application with templates.

    This command generates all necessary files for an existing application
    based on its configuration and specified level.

    Examples:
        autogen initapp myapp --level BasicCRUD
        autogen initapp myapp --level Advanced --dry-run
        autogen initapp myapp --level Enterprise --overwrite
    """
    # Validate app exists
    app_path = Path(f"src/apps/{app_name}")
    if not app_path.exists():
        console.print(f"❌ [red]Application '{app_name}' not found. Use 'autogen startapp' first.[/red]")
        raise typer.Exit(1)

    # Check for config file
    config_file = app_path / "app_config.toml"
    if not config_file.exists():
        console.print(f"❌ [red]Configuration file not found: {config_file}[/red]")
        raise typer.Exit(1)

    try:
        # Load configuration (always v1)
        config = GenerationConfig.from_toml_file(config_file)

        # Override level if provided
        if level:
            config.level = level

        # Initialize generator
        generator = AppGenerator(template_dir) if template_dir else AppGenerator()

        if dry_run:
            console.print(f"🔍 [cyan]Dry run for {config.level} app: {app_name}[/cyan]")
            result = generator.generate_app(config, dry_run=True)
            _show_dry_run_results(result)
        else:
            console.print(f"🚀 Generating {config.level} app: {app_name}")
            result = generator.generate_app(config, overwrite=overwrite, backup=backup)
            _show_generation_results(result)

    except Exception as e:
        console.print(f"❌ [red]Generation failed: {str(e)}[/red]")
        raise typer.Exit(1)


def _show_generation_results(result: dict):
    """Display generation results."""
    status = result["status"]

    if status == "success":
        console.print(
            Panel(
                f"[bold]✅ SUCCESS[/bold]\n"
                f"App: {result['app_name']} ({result['level']})\n"
                f"Files created: {len(result['files_created'])}\n"
                f"Files skipped: {len(result['files_skipped'])}\n"
                f"Errors: {len(result['errors'])}",
                title="Generation Results",
                border_style="green",
            )
        )
    elif status == "partial_success":
        console.print(
            Panel(
                f"[bold]⚠️ PARTIAL SUCCESS[/bold]\n"
                f"App: {result['app_name']} ({result['level']})\n"
                f"Files created: {len(result['files_created'])}\n"
                f"Files skipped: {len(result['files_skipped'])}\n"
                f"Errors: {len(result['errors'])}",
                title="Generation Results",
                border_style="yellow",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold]❌ FAILED[/bold]\n"
                f"App: {result['app_name']} ({result['level']})\n"
                f"Files created: {len(result['files_created'])}\n"
                f"Files skipped: {len(result['files_skipped'])}\n"
                f"Errors: {len(result['errors'])}",
                title="Generation Results",
                border_style="red",
            )
        )

    # Show created files
    if result["files_created"]:
        console.print("\n[bold green]✅ Files Created:[/bold green]")
        for file_path in result["files_created"]:
            console.print(f"  + {file_path}")

    # Show skipped files
    if result["files_skipped"]:
        console.print("\n[bold yellow]⏭️ Files Skipped:[/bold yellow]")
        for file_path in result["files_skipped"]:
            console.print(f"  - {file_path}")

    # Show errors
    if result["errors"]:
        console.print("\n[bold red]❌ Errors:[/bold red]")
        for error in result["errors"]:
            console.print(f"  ✗ {error}")

    # Show next steps
    if result["status"] in ["success", "partial_success"]:
        console.print(
            Panel(
                f"Next steps:\n"
                f"1. Review generated files in src/apps/{result['app_name']}/\n"
                f"2. Create database migration: make migrate-create\n"
                f"3. Apply migration: make migrate-up\n"
                f"4. Run tests: pytest tests/apps/{result['app_name']}/\n"
                f"5. Register router in src/apps/api_router.py",
                title="What's Next?",
                border_style="cyan",
            )
        )

    # Show version
    if result.get("version"):
        console.print(
            Panel(
                f"[bold]Version:[/bold] {result['version']} (Complete)",
                title="Template Version",
                border_style="cyan",
            )
        )


def _show_dry_run_results(result: dict):
    """Display dry run results."""
    console.print(
        Panel(
            f"[bold]App:[/bold] {result['app_name']}\n"
            f"[bold]Level:[/bold] {result['level']}\n"
            f"[bold]Version:[/bold] {result['version']}\n"
            f"[bold]Model:[/bold] {result['model_name']}\n"
            f"[bold]Files to generate:[/bold] {len(result['files_to_generate'])}",
            title="🔍 Dry Run Results",
            border_style="cyan",
        )
    )

    # Show files table
    table = Table(title="Files to Generate", show_header=True, header_style="bold magenta")
    table.add_column("Template", style="cyan")
    table.add_column("Output", style="green")
    table.add_column("Exists", style="yellow")

    for file_info in result["files_to_generate"]:
        exists_status = "✅ Yes" if file_info["exists"] else "❌ No"
        table.add_row(file_info["template"], file_info["output"], exists_status)

    console.print(table)

    # Show features panel
    _create_features_panel(result["features"])


def _create_features_panel(features: dict):
    """Create and display features panel."""
    enabled_features = [name for name, enabled in features.items() if enabled]
    disabled_features = [name for name, enabled in features.items() if not enabled]

    features_text = ""
    if enabled_features:
        features_text += "[bold green]Enabled:[/bold green]\n"
        for feature in enabled_features:
            features_text += f"  ✅ {feature}\n"

    if disabled_features:
        features_text += "\n[bold red]Disabled:[/bold red]\n"
        for feature in disabled_features:
            features_text += f"  ❌ {feature}\n"

    console.print(
        Panel(
            features_text.strip(),
            title="🎯 Features Configuration",
            border_style="blue",
        )
    )
