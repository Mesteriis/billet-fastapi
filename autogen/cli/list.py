"""
List command for autogen CLI.
"""

import tomllib
from pathlib import Path
from typing import Any, Dict, List

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

app = typer.Typer()


@app.command()
def list_apps():
    """📋 List all generated applications with their configurations."""
    apps_dir = Path("src/apps")

    if not apps_dir.exists():
        console.print("❌ [red]No apps directory found. Run from project root.[/red]")
        raise typer.Exit(1)

    # Find all applications
    applications = []
    for app_path in apps_dir.iterdir():
        if app_path.is_dir() and not app_path.name.startswith("_"):
            app_info = _get_app_info(app_path)
            if app_info:
                applications.append(app_info)

    if not applications:
        console.print("📭 [yellow]No applications found.[/yellow]")
        return

    # Display applications table
    _display_apps_table(applications)

    # Display summary
    _display_summary(applications)


def _get_app_info(app_path: Path) -> Dict[str, Any] | None:
    """Get information about an application."""
    try:
        config_file = app_path / "app_config.toml"

        # Basic info
        app_info = {
            "name": app_path.name,
            "path": str(app_path),
            "level": "Unknown",
            "status": "Unknown",
            "files_count": 0,
            "has_config": config_file.exists(),
            "has_models": (app_path / "models").exists(),
            "has_api": (app_path / "api").exists(),
            "has_tests": (app_path / "tests").exists(),
        }

        # Read configuration if exists
        if config_file.exists():
            try:
                with open(config_file, "rb") as f:
                    config = tomllib.load(f)
                app_info["level"] = config.get("app", {}).get("level", "Unknown")
                app_info["description"] = config.get("app", {}).get("description", "No description")

                # Features info
                features = config.get("features", {})
                app_info["features"] = {
                    "soft_delete": features.get("enable_soft_delete", False),
                    "timestamps": features.get("enable_timestamps", False),
                    "pagination": features.get("enable_pagination", False),
                    "caching": features.get("enable_caching", False),
                    "events": features.get("enable_events", False),
                }

            except Exception as e:
                app_info["config_error"] = str(e)

        # Count files
        app_info["files_count"] = len([f for f in app_path.rglob("*.py") if f.is_file()])

        # Determine status
        if app_info["has_config"] and app_info["has_models"] and app_info["has_api"]:
            app_info["status"] = "✅ Complete"
        elif app_info["has_config"]:
            app_info["status"] = "🚧 Partial"
        else:
            app_info["status"] = "📝 Basic"

        return app_info

    except Exception as e:
        console.print(f"⚠️ [yellow]Error reading {app_path.name}: {e}[/yellow]")
        return None


def _display_apps_table(applications: List[Dict[str, Any]]):
    """Display applications in a table."""
    table = Table(title="🏗️ FastAPI Applications", show_header=True, header_style="bold blue")

    table.add_column("Application", style="green", width=20)
    table.add_column("Level", style="cyan", width=12)
    table.add_column("Status", style="yellow", width=12)
    table.add_column("Files", justify="right", style="magenta", width=8)
    table.add_column("Features", style="dim", width=25)
    table.add_column("Description", style="dim")

    for app in sorted(applications, key=lambda x: x["name"]):
        # Format features
        features_str = ""
        if "features" in app:
            enabled_features = [k for k, v in app["features"].items() if v]
            features_str = ", ".join(enabled_features[:3])
            if len(enabled_features) > 3:
                features_str += f", +{len(enabled_features) - 3} more"

        table.add_row(
            app["name"],
            app["level"],
            app["status"],
            str(app["files_count"]),
            features_str,
            app.get("description", "No description")[:50] + ("..." if len(app.get("description", "")) > 50 else ""),
        )

    console.print(table)


def _display_summary(applications: List[Dict[str, Any]]):
    """Display summary information."""
    total_apps = len(applications)
    levels = {}
    statuses = {}
    total_files = 0

    for app in applications:
        # Count by level
        level = app["level"]
        levels[level] = levels.get(level, 0) + 1

        # Count by status
        status = app["status"]
        statuses[status] = statuses.get(status, 0) + 1

        # Total files
        total_files += app["files_count"]

    # Create summary panels
    summary_text = f"""
📊 **Total Applications:** {total_apps}
📁 **Total Files:** {total_files}
📈 **Average Files per App:** {total_files // total_apps if total_apps > 0 else 0}

**By Level:**
{chr(10).join(f"  • {level}: {count}" for level, count in levels.items())}

**By Status:**
{chr(10).join(f"  • {status}: {count}" for status, count in statuses.items())}
    """

    console.print(Panel(summary_text, title="📈 Summary", border_style="blue"))
