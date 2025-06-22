"""
Interactive mode implementation.

Provides user-friendly interactive CLI for generating applications.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def interactive_command():
    """
    🎯 Interactive mode for application generation.

    Guides user through the process of creating applications step by step.
    """
    console.print(
        Panel(
            Text("🚀 Welcome to Autogen Interactive Mode!", justify="center", style="bold blue")
            + Text("\n\n[dim]This wizard will guide you through creating enterprise-grade FastAPI applications[/dim]"),
            title="Autogen Interactive",
            border_style="cyan",
        )
    )

    # Show available levels
    _show_levels_info()

    # Get application details
    app_name = _get_app_name()
    level = _get_app_level()

    # Show summary
    _show_summary(app_name, level)

    # Confirm and create
    if Confirm.ask("Continue with app creation?", default=True):
        _create_app_interactive(app_name, level)
    else:
        console.print("[yellow]Operation cancelled[/yellow]")


def _show_levels_info():
    """Show information about available application levels."""
    table = Table(title="📊 Available Application Levels")

    table.add_column("Level", style="cyan", no_wrap=True)
    table.add_column("Features", style="green")
    table.add_column("DI System", style="blue")
    table.add_column("Test Files", style="magenta")

    table.add_row("BasicCRUD", "CRUD operations\nSimple filters\n5 exceptions", "FastAPI Depends", "7 test files")

    table.add_row(
        "Advanced",
        "40+ filter operators\nFulltext search\nAggregations\nInterfaces",
        "Auto-register DI\ntyping.Protocol",
        "9 test files",
    )

    table.add_row(
        "Enterprise",
        "Caching (Redis/Memory)\nBulk operations\nEvent system\nMonitoring",
        "DI Container\nUnit of Work",
        "11 test files",
    )

    console.print(table)
    console.print()


def _get_app_name() -> str:
    """Get and validate application name."""
    while True:
        app_name = Prompt.ask("[cyan]Enter application name[/cyan]", default="products").strip().lower()

        if _validate_app_name(app_name):
            break
        else:
            console.print(
                "[red]❌ Invalid name![/red] "
                "[dim]Use lowercase, snake_case, plural (e.g., 'products', 'user_profiles')[/dim]"
            )

    return app_name


def _get_app_level() -> str:
    """Get application level."""
    levels = ["BasicCRUD", "Advanced", "Enterprise"]

    console.print("\n[cyan]Choose application level:[/cyan]")
    for i, level in enumerate(levels, 1):
        console.print(f"  {i}. {level}")

    while True:
        choice = Prompt.ask("Enter choice (1-3)", choices=["1", "2", "3"], default="1")

        return levels[int(choice) - 1]


def _show_summary(app_name: str, level: str):
    """Show creation summary."""
    table = Table(title="📋 Creation Summary")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("App Name", app_name)
    table.add_row("Level", level)
    table.add_row("Directory", f"src/apps/{app_name}/")

    # Show what will be created
    files_to_create = [
        "📁 Basic structure",
        "🗄️ Model stub",
        "⚙️ Configuration (app_config.toml)",
        "📖 README with instructions",
    ]

    table.add_row("Will Create", "\n".join(files_to_create))

    console.print()
    console.print(table)
    console.print()


def _create_app_interactive(app_name: str, level: str):
    """Create application in interactive mode."""
    from .start import startapp_command

    try:
        # Use the existing startapp command
        console.print(f"[blue]Creating app '{app_name}' with level '{level}'...[/blue]")
        startapp_command(app_name, force=False)

        # Update config with selected level
        _update_app_config(app_name, level)

        console.print(
            Panel(
                f"[green]✅ App '{app_name}' created successfully![/green]\n\n"
                f"[dim]Next steps:[/dim]\n"
                f"1. Edit the model in [blue]src/apps/{app_name}/models/{app_name}_models.py[/blue]\n"
                f"2. Run [bold cyan]autogen initapp {app_name}[/bold cyan] to generate components",
                title="🎉 Success",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to create app: {e}[/red]")


def _update_app_config(app_name: str, level: str):
    """Update app_config.toml with selected level."""
    import tomllib
    from pathlib import Path

    import tomli_w

    config_file = Path(f"src/apps/{app_name}/app_config.toml")

    try:
        # Read existing config
        with open(config_file, "rb") as f:
            config = tomllib.load(f)

        # Update level
        config["app"]["level"] = level

        # Update features based on level
        if level == "Enterprise":
            config["features"]["enable_caching"] = True
            config["features"]["enable_events"] = True
            config["features"]["enable_monitoring"] = True
        elif level == "Advanced":
            config["features"]["enable_caching"] = False
            config["features"]["enable_events"] = False
            config["features"]["enable_monitoring"] = False

        # Write back
        with open(config_file, "wb") as f:
            tomli_w.dump(config, f)

    except Exception as e:
        console.print(f"[yellow]⚠️ Could not update config: {e}[/yellow]")


def _validate_app_name(app_name: str) -> bool:
    """Validate application name format."""
    if not app_name:
        return False

    # Check if name is lowercase and uses underscores
    if not app_name.replace("_", "").islower():
        return False

    # Check if name doesn't start with number
    if app_name[0].isdigit():
        return False

    # Check for reserved Python keywords
    reserved_words = [
        "and",
        "as",
        "assert",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "exec",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "not",
        "or",
        "pass",
        "print",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    ]

    if app_name in reserved_words:
        return False

    return True
