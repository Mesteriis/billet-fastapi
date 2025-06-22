"""
Main CLI application for Autogen.

Simplified single-version approach with v1.0.0 Complete templates.
"""

import typer
from typing_extensions import Annotated

from .init import initapp_command
from .interactive import interactive_command
from .list import list_apps
from .migrate import migrate_app
from .start import startapp_command
from .tests import tests
from .validate import validate_template

# Create main CLI application
app = typer.Typer(
    name="autogen",
    help="🚀 FastAPI Application Generator (v1.0.0 Complete)",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Add all commands
app.command(name="startapp", help="🆕 Create a new FastAPI application structure.")(startapp_command)
app.command(name="initapp", help="⚡ Initialize application with templates.")(initapp_command)
app.command(name="list", help="📋 List all applications in the project.")(list_apps)
app.command(name="migrate", help="🔄 Migrate application to newer structure.")(migrate_app)
app.command(name="interactive", help="🤖 Interactive application wizard.")(interactive_command)
app.command(name="validate-template", help="✅ Validate custom template structure.")(validate_template)

# Add test generation commands
app.add_typer(tests, name="tests", help="🧪 Generate and manage test components.")


@app.callback()
def main(
    version: Annotated[bool, typer.Option("--version", "-v", help="Show version information")] = False,
):
    """
    🚀 FastAPI Application Generator (v1.0.0 Complete)

    Generate production-ready FastAPI applications with:
    - BasicCRUD: Standard CRUD operations
    - Advanced: + Search, monitoring, health checks
    - Enterprise: + Caching, events, performance tracking

    Test Components:
    - Generate factories and fixtures
    - Analyze test coverage
    - Create test templates

    Examples:
        autogen startapp myapp
        autogen initapp myapp --level Advanced
        autogen tests factories users
        autogen tests coverage products
        autogen list
    """
    if version:
        import typer

        typer.echo("Autogen CLI v1.0.0 Complete")
        typer.echo("Single-version FastAPI application generator")
        typer.echo("Supports: BasicCRUD, Advanced, Enterprise levels")
        typer.echo("Features: App generation, test factories, coverage analysis")
        raise typer.Exit()


if __name__ == "__main__":
    app()
