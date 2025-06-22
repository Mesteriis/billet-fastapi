"""
Utility functions for autogen.

This module provides helper functions for configuration, naming conventions,
and file operations.
"""

import re
import tomllib
from pathlib import Path
from typing import Any, Dict

import tomli_w


def validate_app_name(app_name: str) -> bool:
    """
    Validate application name format.

    Args:
        app_name: Application name to validate

    Returns:
        True if name is valid, False otherwise
    """
    if not app_name:
        return False

    # Check if name is lowercase and uses underscores
    if not app_name.replace("_", "").islower():
        return False

    # Check if name doesn't start with number
    if app_name[0].isdigit():
        return False

    # Check for reserved Python keywords
    reserved_words = {
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
    }

    if app_name in reserved_words:
        return False

    return True


def generate_model_name(app_name: str) -> str:
    """
    Generate model class name from app name (singular, PascalCase).

    Args:
        app_name: Application name (plural, snake_case)

    Returns:
        Model class name (singular, PascalCase)
    """
    # Simple singularization (remove 's' if it ends with 's')
    if app_name.endswith("s") and len(app_name) > 1:
        singular = app_name[:-1]
    else:
        singular = app_name

    # Convert to PascalCase
    return "".join(word.capitalize() for word in singular.split("_"))


def snake_case_to_pascal_case(snake_str: str) -> str:
    """
    Convert snake_case to PascalCase.

    Args:
        snake_str: String in snake_case

    Returns:
        String in PascalCase
    """
    return "".join(word.capitalize() for word in snake_str.split("_"))


def snake_case_to_camel_case(snake_str: str) -> str:
    """
    Convert snake_case to camelCase.

    Args:
        snake_str: String in snake_case

    Returns:
        String in camelCase
    """
    components = snake_str.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


def pascal_case_to_snake_case(pascal_str: str) -> str:
    """
    Convert PascalCase to snake_case.

    Args:
        pascal_str: String in PascalCase

    Returns:
        String in snake_case
    """
    # Add underscores before uppercase letters (except the first one)
    snake_str = re.sub(r"(?<!^)(?=[A-Z])", "_", pascal_str)
    return snake_str.lower()


def get_app_config(app_path: Path) -> Dict[str, Any] | None:
    """
    Load app configuration from app_config.toml.

    Args:
        app_path: Path to application directory

    Returns:
        Configuration dictionary or None if file doesn't exist
    """
    config_file = app_path / "app_config.toml"

    if not config_file.exists():
        return None

    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return None


def update_pyproject_config(app_name: str, app_config: Dict[str, Any]) -> bool:
    """
    Update pyproject.toml with app metadata.

    Args:
        app_name: Application name
        app_config: Application configuration

    Returns:
        True if successful, False otherwise
    """
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        return False

    try:
        # Read existing pyproject.toml
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Add/update autogen section
        if "autogen" not in data:
            data["autogen"] = {}

        data["autogen"][app_name] = {
            "level": app_config["app"]["level"],
            "template_version": "1.0",
            "autogen_version": "0.1.0",
            "api_prefix": app_config["api"]["prefix"],
        }

        # Write back
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(data, f)

        return True

    except Exception:
        return False


def create_backup(file_path: Path, backup_suffix: str = ".bak") -> Path | None:
    """
    Create backup of a file.

    Args:
        file_path: Path to file to backup
        backup_suffix: Suffix for backup file

    Returns:
        Path to backup file or None if failed
    """
    if not file_path.exists():
        return None

    backup_path = file_path.with_suffix(file_path.suffix + backup_suffix)

    try:
        backup_path.write_bytes(file_path.read_bytes())
        return backup_path
    except Exception:
        return None


def ensure_directory(directory: Path) -> bool:
    """
    Ensure directory exists, create if necessary.

    Args:
        directory: Directory path

    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def safe_filename(filename: str) -> str:
    """
    Make filename safe for filesystem.

    Args:
        filename: Original filename

    Returns:
        Safe filename
    """
    # Replace unsafe characters with underscores
    safe_chars = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove extra underscores
    safe_chars = re.sub(r"_+", "_", safe_chars)
    # Strip leading/trailing underscores and dots
    return safe_chars.strip("_.")


def pluralize_simple(word: str) -> str:
    """
    Simple pluralization (add 's' if doesn't end with 's').

    Args:
        word: Word to pluralize

    Returns:
        Pluralized word
    """
    if word.endswith("s"):
        return word
    return word + "s"


def singularize_simple(word: str) -> str:
    """
    Simple singularization (remove 's' if ends with 's').

    Args:
        word: Word to singularize

    Returns:
        Singularized word
    """
    if word.endswith("s") and len(word) > 1:
        return word[:-1]
    return word
