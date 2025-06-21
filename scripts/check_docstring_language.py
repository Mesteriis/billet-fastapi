#!/usr/bin/env python3
"""
Docstring language checker for pre-commit hooks.

This script checks that docstrings in API modules and library modules
are written in English and follow Sphinx format.
"""

import ast
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

# Russian words that should not appear in API docstrings
RUSSIAN_PATTERNS = [
    r"\b(?:получить|создать|обновить|удалить|проверить|вернуть|выполнить)\b",
    r"\b(?:пользователь|админ|модератор|система|данные|файл|список)\b",
    r"\b(?:для|через|при|без|после|перед|над|под|между|около)\b",
    r"\b(?:если|то|иначе|когда|где|что|как|почему|зачем)\b",
    r"\b(?:и|или|не|да|нет|можно|нужно|должен|может)\b",
    r"[а-яё]",  # Any Cyrillic characters
]

# Required Sphinx sections for API modules
REQUIRED_SPHINX_SECTIONS = ["Args:", "Returns:", "Example:"]

# Directories that should have English docstrings
API_DIRECTORIES = [
    "src/apps/*/api/",
    "src/apps/*/models/",
    "src/apps/*/services/",
    "src/apps/*/repo/",
    "src/core/",
    "src/tools/",
]

# Directories to exclude from checking
EXCLUDE_DIRECTORIES = [
    "tests/",
    "migrations/",
    "scripts/",
    "__pycache__/",
    ".git/",
]


class DocstringChecker:
    """Checks docstrings for language and format compliance."""

    def __init__(self):
        self.errors: List[Tuple[str, int, str]] = []
        self.russian_pattern = re.compile("|".join(RUSSIAN_PATTERNS), re.IGNORECASE)

    def check_file(self, file_path: Path) -> bool:
        """
        Check a single Python file for docstring compliance.

        Args:
            file_path: Path to the Python file to check

        Returns:
            bool: True if file passes all checks, False otherwise
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Check module docstring
            if ast.get_docstring(tree):
                self._check_docstring(ast.get_docstring(tree), str(file_path), 1, "module")

            # Check class and function docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        self._check_docstring(docstring, str(file_path), node.lineno, node.name)

            return len(self.errors) == 0

        except Exception as e:
            self.errors.append((str(file_path), 0, f"Failed to parse file: {e}"))
            return False

    def _check_docstring(self, docstring: str, file_path: str, line_no: int, name: str):
        """Check individual docstring for compliance."""

        # Check for Russian text
        if self.russian_pattern.search(docstring):
            self.errors.append(
                (
                    file_path,
                    line_no,
                    f"Russian text found in docstring for '{name}'. API docstrings must be in English.",
                )
            )

        # For API modules, check Sphinx format
        if self._is_api_module(file_path):
            self._check_sphinx_format(docstring, file_path, line_no, name)

    def _is_api_module(self, file_path: str) -> bool:
        """Check if file is in API directory."""
        return any(
            "/api/" in file_path
            or "/models/" in file_path
            or "/services/" in file_path
            or "/repo/" in file_path
            or "/core/" in file_path
            or "/tools/" in file_path
            for pattern in API_DIRECTORIES
        )

    def _check_sphinx_format(self, docstring: str, file_path: str, line_no: int, name: str):
        """Check if docstring follows Sphinx format."""

        # Skip simple one-line docstrings
        if len(docstring.split("\n")) <= 1:
            return

        # Check for required sections in function docstrings
        if "def " in name or "async def" in name:
            missing_sections = []
            for section in REQUIRED_SPHINX_SECTIONS:
                if section not in docstring:
                    missing_sections.append(section)

            if missing_sections:
                self.errors.append(
                    (file_path, line_no, f"Missing Sphinx sections in '{name}': {', '.join(missing_sections)}")
                )


def should_check_file(file_path: Path) -> bool:
    """Determine if file should be checked."""

    # Only check Python files
    if file_path.suffix != ".py":
        return False

    # Skip excluded directories
    for exclude_dir in EXCLUDE_DIRECTORIES:
        if exclude_dir in str(file_path):
            return False

    # Skip __init__.py files (usually just exports)
    if file_path.name == "__init__.py":
        return False

    # Skip main.py and cli.py (entry points)
    if file_path.name in ["main.py", "cli.py"]:
        return False

    return True


def main():
    """Main function for command line usage."""

    if len(sys.argv) < 2:
        print("Usage: python check_docstring_language.py <file1> [file2] ...")
        sys.exit(1)

    checker = DocstringChecker()
    all_passed = True

    for file_arg in sys.argv[1:]:
        file_path = Path(file_arg)

        if not file_path.exists():
            print(f"File not found: {file_path}")
            all_passed = False
            continue

        if not should_check_file(file_path):
            continue

        if not checker.check_file(file_path):
            all_passed = False

    # Print errors
    if checker.errors:
        print("Docstring language/format errors found:")
        for file_path, line_no, error in checker.errors:
            print(f"{file_path}:{line_no}: {error}")
        print(f"\nTotal errors: {len(checker.errors)}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
