"""
Main CLI entry point for autogen.

This module provides the main Typer application and command routing.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

from .init import initapp_command
from .interactive import interactive_command
from .start import startapp_command

# Создаем основное CLI приложение
app = typer.Typer(
    name="autogen",
    help="🚀 Enterprise-grade FastAPI application generator",
    rich_markup_mode="rich",
    no_args_is_help=False,
)

console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[bool, typer.Option("--version", "-v", help="Show version and exit")] = False,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Run in interactive mode")] = False,
):
    """
    🚀 Enterprise-grade FastAPI application generator.

    Generate production-ready FastAPI applications with:
    - BasicCRUD: Simple CRUD with FastAPI Depends
    - Advanced: + Search, filters, aggregations
    - Enterprise: + Caching, events, UoW, DI container
    """
    if version:
        from autogen import __version__

        console.print(
            Panel(
                f"[bold blue]Autogen[/bold blue] v{__version__}\n"
                "[dim]Enterprise-grade FastAPI application generator[/dim]",
                title="Version",
                border_style="blue",
            )
        )
        raise typer.Exit()

    if interactive:
        interactive_command()
        raise typer.Exit()

    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


# Регистрируем команды
app.command(name="startapp", help="🏗️ Create basic app structure")(startapp_command)
app.command(name="initapp", help="⚡ Generate full app components")(initapp_command)


@app.command(name="list")
def list_apps():
    """📋 List all generated applications."""
    console.print("[yellow]⚠️ Not implemented yet[/yellow]")


@app.command(name="check")
def check_app(app_name: Annotated[str, typer.Argument(help="Application name to check")]):
    """🔍 Check app compatibility and available migrations."""
    console.print(f"[yellow]⚠️ Check for {app_name} not implemented yet[/yellow]")


@app.command(name="migrate")
def migrate_app(
    app_name: Annotated[str, typer.Argument(help="Application name to migrate")],
    to_version: Annotated[str, typer.Option("--to", help="Target template version")] = "latest",
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be changed")] = False,
):
    """🔄 Migrate app to newer template version."""
    console.print(f"[yellow]⚠️ Migration for {app_name} not implemented yet[/yellow]")


@app.command(name="validate-template")
def validate_template(
    template_path: Annotated[str, typer.Argument(help="Path to custom template directory")],
    level: Annotated[str, typer.Option("--level", help="Template level to validate against")] = "BasicCRUD",
):
    """✅ Validate custom template structure."""
    console.print(f"[yellow]⚠️ Template validation not implemented yet[/yellow]")


if __name__ == "__main__":
    app()
