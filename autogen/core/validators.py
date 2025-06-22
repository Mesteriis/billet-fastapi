"""
Template validators.

This module provides validation for custom templates and configurations.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError


@dataclass
class ValidationResult:
    """Result of template validation."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def add_error(self, message: str) -> None:
        """Add error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add warning message."""
        self.warnings.append(message)


class TemplateValidator:
    """
    Template validator.

    Validates custom templates against required structure and syntax.
    """

    # Required files for each level
    REQUIRED_FILES_BY_LEVEL: Dict[str, Set[str]] = {
        "BasicCRUD": {
            "models.py.j2",
            "schemas.py.j2",
            "repo.py.j2",
            "services.py.j2",
            "api.py.j2",
            "exceptions.py.j2",
            "depends.py.j2",
        },
        "Advanced": {
            "models.py.j2",
            "schemas.py.j2",
            "repo.py.j2",
            "services.py.j2",
            "api.py.j2",
            "exceptions.py.j2",
            "depends.py.j2",
            "interfaces.py.j2",
        },
        "Enterprise": {
            "models.py.j2",
            "schemas.py.j2",
            "repo.py.j2",
            "services.py.j2",
            "api.py.j2",
            "exceptions.py.j2",
            "depends.py.j2",
            "interfaces.py.j2",
            "cache_service.py.j2",
            "event_service.py.j2",
        },
    }

    # Required template variables
    REQUIRED_VARIABLES: Set[str] = {
        "app_name",
        "model_name",
        "table_name",
        "level",
        "features",
        "api_config",
    }

    def validate_template_directory(self, template_dir: Path, level: str = "BasicCRUD") -> ValidationResult:
        """
        Validate template directory structure.

        Args:
            template_dir: Path to template directory
            level: Application level to validate against

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        if not template_dir.exists():
            result.add_error(f"Template directory does not exist: {template_dir}")
            return result

        if not template_dir.is_dir():
            result.add_error(f"Template path is not a directory: {template_dir}")
            return result

        # Check required files
        self._validate_required_files(template_dir, level, result)

        # Check template syntax
        self._validate_template_syntax(template_dir, result)

        # Check template variables
        self._validate_template_variables(template_dir, result)

        return result

    def _validate_required_files(self, template_dir: Path, level: str, result: ValidationResult) -> None:
        """Validate that all required files are present."""
        required_files = self.REQUIRED_FILES_BY_LEVEL.get(level, set())

        if not required_files:
            result.add_error(f"Unknown application level: {level}")
            return

        existing_files = {f.name for f in template_dir.rglob("*.j2")}
        missing_files = required_files - existing_files

        for missing_file in missing_files:
            result.add_error(f"Missing required template file: {missing_file}")

        # Check for extra files (warnings)
        extra_files = existing_files - required_files
        for extra_file in extra_files:
            result.add_warning(f"Extra template file found: {extra_file}")

    def _validate_template_syntax(self, template_dir: Path, result: ValidationResult) -> None:
        """Validate Jinja2 template syntax."""
        try:
            env = Environment(loader=FileSystemLoader(str(template_dir)))

            for template_file in template_dir.rglob("*.j2"):
                relative_path = template_file.relative_to(template_dir)
                try:
                    env.get_template(str(relative_path))
                except TemplateSyntaxError as e:
                    result.add_error(f"Template syntax error in {relative_path}: {e}")
                except Exception as e:
                    result.add_error(f"Error loading template {relative_path}: {e}")

        except Exception as e:
            result.add_error(f"Failed to create template environment: {e}")

    def _validate_template_variables(self, template_dir: Path, result: ValidationResult) -> None:
        """Validate that templates use required variables."""
        try:
            env = Environment(loader=FileSystemLoader(str(template_dir)))

            for template_file in template_dir.rglob("*.j2"):
                relative_path = template_file.relative_to(template_dir)
                try:
                    template = env.get_template(str(relative_path))
                    # This is a basic check - in practice you'd want more sophisticated analysis
                    template_source = template_file.read_text()

                    # Check if at least some required variables are used
                    used_variables = set()
                    for var in self.REQUIRED_VARIABLES:
                        if f"{{{{{var}}}}}" in template_source or f"{{{{ {var}." in template_source:
                            used_variables.add(var)

                    if not used_variables:
                        result.add_warning(f"Template {relative_path} doesn't seem to use any required variables")

                except Exception as e:
                    # Already handled in syntax validation
                    pass

        except Exception:
            # Already handled in syntax validation
            pass

    def validate_config_file(self, config_path: Path) -> ValidationResult:
        """
        Validate app_config.toml file.

        Args:
            config_path: Path to configuration file

        Returns:
            ValidationResult with validation status and messages
        """
        result = ValidationResult(is_valid=True, errors=[], warnings=[])

        if not config_path.exists():
            result.add_error(f"Configuration file does not exist: {config_path}")
            return result

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Validate required sections
            required_sections = ["app", "database", "features", "api", "testing"]
            for section in required_sections:
                if section not in config:
                    result.add_error(f"Missing required section: [{section}]")

            # Validate app section
            if "app" in config:
                app_config = config["app"]
                if "level" not in app_config:
                    result.add_error("Missing 'level' in [app] section")
                elif app_config["level"] not in ["BasicCRUD", "Advanced", "Enterprise"]:
                    result.add_error(f"Invalid level: {app_config['level']}")

                if "name" not in app_config:
                    result.add_error("Missing 'name' in [app] section")

            # Validate features consistency
            if "features" in config and "app" in config:
                features = config["features"]
                level = config["app"].get("level", "BasicCRUD")

                if level == "BasicCRUD":
                    if features.get("enable_caching", False):
                        result.add_warning("Caching is enabled but only available in Enterprise level")
                    if features.get("enable_events", False):
                        result.add_warning("Events are enabled but only available in Enterprise level")

        except tomllib.TOMLDecodeError as e:
            result.add_error(f"Invalid TOML syntax: {e}")
        except Exception as e:
            result.add_error(f"Error reading configuration: {e}")

        return result
