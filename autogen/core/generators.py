"""
Application generators.

This module provides the main AppGenerator class for creating FastAPI applications.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader, select_autoescape


@dataclass
class GenerationConfig:
    """Configuration for application generation."""

    app_name: str
    level: str  # "BasicCRUD", "Advanced", "Enterprise"
    model_name: str
    table_name: str
    features: Dict[str, bool]
    api_config: Dict[str, Any]
    testing_config: Dict[str, Any]

    @classmethod
    def from_toml_file(cls, config_path: Path) -> "GenerationConfig":
        """Load configuration from TOML file."""
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        return cls(
            app_name=config_path.parent.name,
            level=data["app"]["level"],
            model_name=data["app"]["name"],
            table_name=data["database"]["table_name"],
            features=data["features"],
            api_config=data["api"],
            testing_config=data["testing"],
        )


class AppGenerator:
    """
    Main application generator.

    Generates FastAPI applications with different complexity levels:
    - BasicCRUD: Simple CRUD with FastAPI Depends
    - Advanced: + Filtering, search, aggregations
    - Enterprise: + Caching, events, monitoring
    """

    def __init__(self, template_dir: str = ""):
        """Initialize generator with template directory."""
        self.template_dir = Path(template_dir) if template_dir else self._get_default_template_dir()
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)), autoescape=select_autoescape(["html", "xml"])
        )

    def generate_app(
        self, config: GenerationConfig, dry_run: bool = False, overwrite: bool = False, backup: bool = False
    ) -> Dict[str, Any]:
        """
        Generate complete application.

        Args:
            config: Generation configuration
            dry_run: Only show what would be generated
            overwrite: Overwrite existing files
            backup: Create backup before changes

        Returns:
            Dictionary with generation results
        """

        if dry_run:
            return self._dry_run_generation(config)

        # Actual generation logic will be implemented here
        return {"status": "not_implemented", "message": "Full generation not yet implemented", "config": config}

    def _dry_run_generation(self, config: GenerationConfig) -> Dict[str, Any]:
        """Show what would be generated without creating files."""
        files_to_generate = self._get_files_for_level(config.level)

        return {
            "status": "dry_run",
            "app_name": config.app_name,
            "level": config.level,
            "files_to_generate": files_to_generate,
            "template_dir": str(self.template_dir),
        }

    def _get_files_for_level(self, level: str) -> List[str]:
        """Get list of files to generate for given level."""
        base_files = [
            "models/{app_name}_models.py",
            "schemas/{app_name}_schemas.py",
            "repo/{app_name}_repo.py",
            "services/{app_name}_service.py",
            "api/{app_name}_routes.py",
            "exceptions.py",
            "interfaces.py",
            "depends/repositories.py",
            "depends/services.py",
        ]

        test_files = [
            "tests/test_{app_name}_models.py",
            "tests/test_{app_name}_repo.py",
            "tests/test_{app_name}_service.py",
            "tests/test_{app_name}_api.py",
            "tests/conftest.py",
            "tests/factories.py",
            "tests/e2e/test_{app_name}_crud_e2e.py",
        ]

        if level in ["Advanced", "Enterprise"]:
            test_files.extend(
                [
                    "tests/test_{app_name}_advanced.py",
                    "tests/test_{app_name}_integration.py",
                ]
            )

        if level == "Enterprise":
            base_files.extend(
                [
                    "services/{app_name}_cache_service.py",
                    "services/{app_name}_event_service.py",
                ]
            )
            test_files.extend(
                [
                    "tests/test_{app_name}_cache.py",
                    "tests/test_{app_name}_events.py",
                ]
            )

        return base_files + test_files

    def _get_default_template_dir(self) -> Path:
        """Get default template directory."""
        # Look for templates in the autogen package
        current_dir = Path(__file__).parent.parent
        return current_dir / "templates"
