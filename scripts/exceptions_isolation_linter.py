#!/usr/bin/env python3
"""
Exceptions isolation linter.

This linter ensures proper isolation of exceptions across applications and layers:
1. App isolation: Auth modules can only use Auth exceptions, Users modules can only use Users exceptions
2. Layer isolation: API layer uses APIException, Service layer uses ServiceException, etc.
3. Standard exceptions blocking: Prevents use of standard Python exceptions in favor of custom ones
4. Import validation: Ensures proper exception imports and usage

Usage:
    python scripts/exceptions_isolation_linter.py
    python scripts/exceptions_isolation_linter.py --fix
    python scripts/exceptions_isolation_linter.py --check-only src/apps/auth/
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, List, NamedTuple


class ViolationError(NamedTuple):
    """Exception isolation violation."""

    file_path: str
    line_number: int
    column: int
    violation_type: str
    message: str
    severity: str


class ExceptionsIsolationLinter:
    """
    Linter for checking exception isolation across applications and layers.

    Validates:
    - Application isolation (auth vs users vs core)
    - Layer isolation (api vs service vs repo vs depends)
    - Standard exception usage blocking
    - Proper import patterns
    """

    # Standard exceptions that should not be used directly
    FORBIDDEN_STANDARD_EXCEPTIONS = {
        "Exception",
        "ValueError",
        "TypeError",
        "RuntimeError",
        "AttributeError",
        "KeyError",
        "IndexError",
        "NotImplementedError",
        "ImportError",
        "IOError",
        "OSError",
        "ConnectionError",
        "HTTPException",  # Should use app-specific API exceptions instead
    }

    # Required exception patterns for each layer
    LAYER_PATTERNS = {
        "api": ["APIException", "AppException", "Error", "HTTPException"],
        "services": ["ServiceException", "AppException", "Error"],
        "repo": ["RepoException", "AppException", "Error"],
        "depends": ["DependsException", "AppException", "Error"],
    }

    # Application prefixes
    APP_PREFIXES = {
        "auth": "Auth",
        "users": "Users",
        "core": "Core",
    }

    def __init__(self, fix_mode: bool = False):
        self.fix_mode = fix_mode
        self.violations: List[ViolationError] = []

    def lint_file(self, file_path: Path) -> List[ViolationError]:
        """
        Lint a single Python file for exception isolation violations.

        Args:
            file_path: Path to the Python file to lint

        Returns:
            List of violation errors found
        """
        if not file_path.suffix == ".py":
            return []

        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)

            # Reset violations for this file
            self.violations = []

            # Check different types of violations
            self._check_raise_statements(tree, file_path, content)
            self._check_exception_imports(tree, file_path, content)
            self._check_exception_inheritance(tree, file_path, content)
            self._check_layer_isolation(tree, file_path, content)
            self._check_app_isolation(tree, file_path, content)

            return self.violations

        except Exception as e:
            return [
                ViolationError(
                    file_path=str(file_path),
                    line_number=0,
                    column=0,
                    violation_type="PARSE_ERROR",
                    message=f"Failed to parse file: {e}",
                    severity="ERROR",
                )
            ]

    def _check_raise_statements(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check raise statements for forbidden standard exceptions."""

        class RaiseVisitor(ast.NodeVisitor):
            def __init__(self, linter):
                self.linter = linter

            def visit_Raise(self, node: ast.Raise) -> None:
                if node.exc:
                    if isinstance(node.exc, ast.Call):
                        # raise Exception(message)
                        if isinstance(node.exc.func, ast.Name):
                            exc_name = node.exc.func.id
                            if exc_name in self.linter.FORBIDDEN_STANDARD_EXCEPTIONS:
                                self.linter.violations.append(
                                    ViolationError(
                                        file_path=str(file_path),
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        violation_type="FORBIDDEN_STANDARD_EXCEPTION",
                                        message=f"Use of forbidden standard exception: {exc_name}",
                                        severity="ERROR",
                                    )
                                )
                    elif isinstance(node.exc, ast.Name):
                        # raise exception_instance
                        exc_name = node.exc.id
                        if exc_name in self.linter.FORBIDDEN_STANDARD_EXCEPTIONS:
                            self.linter.violations.append(
                                ViolationError(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    column=node.col_offset,
                                    violation_type="FORBIDDEN_STANDARD_EXCEPTION",
                                    message=f"Use of forbidden standard exception: {exc_name}",
                                    severity="ERROR",
                                )
                            )

                self.generic_visit(node)

        visitor = RaiseVisitor(self)
        visitor.visit(tree)

    def _check_exception_imports(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check exception imports for proper patterns."""

        class ImportVisitor(ast.NodeVisitor):
            def __init__(self, linter):
                self.linter = linter

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                if node.module and "fastapi" in node.module:
                    for alias in node.names or []:
                        if alias.name == "HTTPException":
                            # Check if this is in an API layer file
                            if not self._is_api_layer_file(file_path):
                                self.linter.violations.append(
                                    ViolationError(
                                        file_path=str(file_path),
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        violation_type="LAYER_VIOLATION",
                                        message="HTTPException should only be imported in API layer",
                                        severity="WARNING",
                                    )
                                )

                self.generic_visit(node)

            def _is_api_layer_file(self, file_path: Path) -> bool:
                """Check if file is in API layer or Core infrastructure."""
                path_str = str(file_path)
                return (
                    "/api/" in path_str
                    or file_path.name.endswith("_routes.py")
                    or "/core/" in path_str  # Allow HTTPException in Core infrastructure
                )

        visitor = ImportVisitor(self)
        visitor.visit(tree)

    def _check_exception_inheritance(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check that custom exceptions inherit from proper base classes."""

        class ClassVisitor(ast.NodeVisitor):
            def __init__(self, linter):
                self.linter = linter

            def visit_ClassDef(self, node: ast.ClassDef) -> None:
                if node.name.endswith("Exception") or node.name.endswith("Error"):
                    if not self._has_proper_inheritance(node):
                        self.linter.violations.append(
                            ViolationError(
                                file_path=str(file_path),
                                line_number=node.lineno,
                                column=node.col_offset,
                                violation_type="INHERITANCE_VIOLATION",
                                message=f"Exception class {node.name} should inherit from proper base exception",
                                severity="WARNING",
                            )
                        )

                self.generic_visit(node)

            def _has_proper_inheritance(self, node: ast.ClassDef) -> bool:
                """Check if exception class has proper inheritance."""
                if not node.bases:
                    return False

                for base in node.bases:
                    if isinstance(base, ast.Name):
                        base_name = base.id
                        # Check for proper base exceptions
                        if any(
                            pattern in base_name
                            for pattern in [
                                "APIException",
                                "ServiceException",
                                "RepoException",
                                "DependsException",
                                "AppException",
                                "Exception",  # Standard Python Exception is acceptable
                                "BaseException",  # BaseException is also acceptable
                                "Error",  # Classes ending with Error are acceptable
                                "ServiceError",  # Intermediate service error classes
                                "RepoError",  # Intermediate repo error classes
                                "ValidationError",  # Validation errors
                                "BackupError",  # Backup errors
                                "MigrationError",  # Migration errors
                            ]
                        ):
                            return True

                return False

        visitor = ClassVisitor(self)
        visitor.visit(tree)

    def _check_layer_isolation(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check that layers use appropriate exception types."""
        layer = self._detect_layer(file_path)
        if not layer:
            return

        required_patterns = self.LAYER_PATTERNS.get(layer, [])
        if not required_patterns:
            return

        # Check raise statements in this layer
        class LayerRaiseVisitor(ast.NodeVisitor):
            def __init__(self, linter, required_patterns):
                self.linter = linter
                self.required_patterns = required_patterns

            def visit_Raise(self, node: ast.Raise) -> None:
                if node.exc and isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        exc_name = node.exc.func.id
                        if (exc_name.endswith("Exception") or exc_name.endswith("Error")) and not any(
                            pattern in exc_name for pattern in self.required_patterns
                        ):
                            self.linter.violations.append(
                                ViolationError(
                                    file_path=str(file_path),
                                    line_number=node.lineno,
                                    column=node.col_offset,
                                    violation_type="LAYER_ISOLATION_VIOLATION",
                                    message=f"Layer '{layer}' should use exceptions containing {required_patterns}",
                                    severity="WARNING",
                                )
                            )

                self.generic_visit(node)

        visitor = LayerRaiseVisitor(self, required_patterns)
        visitor.visit(tree)

    def _check_app_isolation(self, tree: ast.AST, file_path: Path, content: str) -> None:
        """Check that applications use only their own exceptions."""
        app = self._detect_app(file_path)
        if not app:
            return

        app_prefix = self.APP_PREFIXES.get(app)
        if not app_prefix:
            return

        # Check raise statements for cross-app usage
        class AppRaiseVisitor(ast.NodeVisitor):
            def __init__(self, linter, app_prefix, current_app):
                self.linter = linter
                self.app_prefix = app_prefix
                self.current_app = current_app

            def visit_Raise(self, node: ast.Raise) -> None:
                if node.exc and isinstance(node.exc, ast.Call):
                    if isinstance(node.exc.func, ast.Name):
                        exc_name = node.exc.func.id

                        # Check for cross-app usage
                        for other_app, other_prefix in self.linter.APP_PREFIXES.items():
                            if other_app != self.current_app and exc_name.startswith(other_prefix):
                                self.linter.violations.append(
                                    ViolationError(
                                        file_path=str(file_path),
                                        line_number=node.lineno,
                                        column=node.col_offset,
                                        violation_type="APP_ISOLATION_VIOLATION",
                                        message=f"App '{self.current_app}' cannot use '{other_app}' exceptions: {exc_name}",
                                        severity="ERROR",
                                    )
                                )

                self.generic_visit(node)

        visitor = AppRaiseVisitor(self, app_prefix, app)
        visitor.visit(tree)

    def _detect_layer(self, file_path: Path) -> str | None:
        """Detect the architectural layer from file path."""
        path_str = str(file_path)

        if "/api/" in path_str or path_str.endswith("_routes.py"):
            return "api"
        elif "/services/" in path_str or path_str.endswith("_service.py"):
            return "services"
        elif "/repo/" in path_str or path_str.endswith("_repo.py"):
            return "repo"
        elif "/depends/" in path_str or path_str.endswith("_depends.py"):
            return "depends"

        return None

    def _detect_app(self, file_path: Path) -> str | None:
        """Detect the application from file path."""
        path_str = str(file_path)

        if "/apps/auth/" in path_str:
            return "auth"
        elif "/apps/users/" in path_str:
            return "users"
        elif "/core/" in path_str:
            return "core"

        return None


def main():
    """Main entry point for the linter."""
    parser = argparse.ArgumentParser(description="Exception isolation linter")
    parser.add_argument("paths", nargs="*", help="Paths to lint (default: src/)")
    parser.add_argument("--fix", action="store_true", help="Auto-fix violations where possible")
    parser.add_argument("--check-only", action="store_true", help="Only check, do not fix")
    parser.add_argument(
        "--severity", choices=["ERROR", "WARNING", "INFO"], default="WARNING", help="Minimum severity level to report"
    )

    args = parser.parse_args()

    # Default to src/ if no paths provided
    paths = args.paths or ["src/"]

    linter = ExceptionsIsolationLinter(fix_mode=args.fix and not args.check_only)
    total_violations = 0

    for path_str in paths:
        path = Path(path_str)

        if path.is_file():
            files = [path] if path.suffix == ".py" else []
        else:
            files = list(path.rglob("*.py"))

        for file_path in files:
            violations = linter.lint_file(file_path)

            # Filter by severity
            filtered_violations = [
                v for v in violations if _severity_level(v.severity) >= _severity_level(args.severity)
            ]

            if filtered_violations:
                print(f"\n{file_path}:")
                for violation in filtered_violations:
                    print(
                        f"  {violation.line_number}:{violation.column} "
                        f"{violation.severity}: {violation.violation_type} - {violation.message}"
                    )

                total_violations += len(filtered_violations)

    print(f"\nTotal violations found: {total_violations}")

    if total_violations > 0:
        sys.exit(1)
    else:
        print("✅ No exception isolation violations found!")
        sys.exit(0)


def _severity_level(severity: str) -> int:
    """Convert severity string to numeric level."""
    levels = {"INFO": 1, "WARNING": 2, "ERROR": 3}
    return levels.get(severity, 2)


if __name__ == "__main__":
    main()
