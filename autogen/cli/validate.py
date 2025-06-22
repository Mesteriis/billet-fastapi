"""Validate command for autogen CLI."""

from pathlib import Path
from typing import Annotated

import typer
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError
from rich.console import Console

console = Console()
app = typer.Typer()


@app.command()
def validate_template(
    template_path: Annotated[str, typer.Argument(help="Path to custom template directory")],
    level: Annotated[str, typer.Option("--level", help="Template level to validate")] = "BasicCRUD",
):
    """✅ Validate custom template structure and syntax."""
    template_dir = Path(template_path)

    if not template_dir.exists():
        console.print(f"❌ [red]Template directory '{template_path}' not found.[/red]")
        raise typer.Exit(1)

    console.print(f"🔍 [blue]Validating templates in: {template_path}[/blue]")
    console.print(f"📋 [blue]Level: {level}[/blue]")

    # Check directory structure
    level_dir = template_dir / level.lower().replace("crud", "_crud")

    if not level_dir.exists():
        console.print(f"❌ [red]Level directory '{level_dir}' not found.[/red]")
        raise typer.Exit(1)

    # Required template files
    required_templates = [
        "models.py.j2",
        "schemas.py.j2",
        "repository.py.j2",
        "service.py.j2",
        "api.py.j2",
        "exceptions.py.j2",
        "depends.py.j2",
        "__init__.py.j2",
    ]

    # Check template files
    missing_templates = []
    invalid_templates = []
    valid_templates = []

    for template_name in required_templates:
        template_file = level_dir / template_name

        if not template_file.exists():
            missing_templates.append(template_name)
            continue

        # Validate Jinja2 syntax
        try:
            env = Environment(loader=FileSystemLoader(str(level_dir)))
            template = env.get_template(template_name)
            # Try to render with dummy context
            test_context = {
                "app_name": "test_app",
                "model_name": "TestModel",
                "level": level,
                "features": {"enable_soft_delete": True, "enable_timestamps": True},
                "api_config": {"prefix": "/test", "tags": ["Test"]},
                "timestamp": "2024-01-01T00:00:00",
            }
            template.render(**test_context)
            valid_templates.append(template_name)

        except TemplateSyntaxError as e:
            invalid_templates.append(f"{template_name}: {e}")
        except Exception as e:
            invalid_templates.append(f"{template_name}: Render error - {e}")

    # Report results
    console.print("\n📊 [bold]Validation Results:[/bold]")

    if valid_templates:
        console.print(f"✅ [green]Valid templates ({len(valid_templates)}):[/green]")
        for template in valid_templates:
            console.print(f"  • {template}")

    if missing_templates:
        console.print(f"\n❌ [red]Missing templates ({len(missing_templates)}):[/red]")
        for template in missing_templates:
            console.print(f"  • {template}")

    if invalid_templates:
        console.print(f"\n⚠️ [yellow]Invalid templates ({len(invalid_templates)}):[/yellow]")
        for template in invalid_templates:
            console.print(f"  • {template}")

    # Overall result
    total_required = len(required_templates)
    total_valid = len(valid_templates)

    if total_valid == total_required:
        console.print(f"\n🎉 [green bold]All templates valid! ({total_valid}/{total_required})[/green bold]")
    else:
        console.print(f"\n⚠️ [yellow]Validation incomplete: {total_valid}/{total_required} templates valid[/yellow]")
        if missing_templates or invalid_templates:
            raise typer.Exit(1)
