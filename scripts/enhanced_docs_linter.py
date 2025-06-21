#!/usr/bin/env python3
"""
Enhanced documentation linter with advanced format checks.

This linter provides comprehensive checks for documentation quality,
format consistency, and API documentation completeness.
"""

import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class DocstringIssue:
    """Represents a documentation issue found by the linter."""

    file_path: str
    line_number: int
    issue_type: str
    message: str
    severity: str = "error"  # error, warning, info


class EnhancedDocsLinter:
    """Enhanced documentation linter with comprehensive checks."""

    def __init__(self):
        self.issues: List[DocstringIssue] = []
        self.stats = {
            "files_checked": 0,
            "docstrings_found": 0,
            "api_routes_found": 0,
            "curl_examples_found": 0,
            "sphinx_compliant": 0,
        }

        # Patterns for various checks
        self.russian_pattern = re.compile(r"[а-яё]", re.IGNORECASE)
        self.sphinx_sections = [
            "Args:",
            "Arguments:",
            "Parameters:",
            "Returns:",
            "Return:",
            "Yields:",
            "Raises:",
            "Note:",
            "Example:",
            "Examples:",
        ]
        self.api_sections = ["Args:", "Returns:", "Raises:", "Example:"]
        self.curl_pattern = re.compile(r"```bash.*?curl.*?```", re.DOTALL)
        self.response_pattern = re.compile(r"Response:\s*```json.*?```", re.DOTALL)

    def check_file(self, file_path: Path) -> bool:
        """Check a single Python file for documentation issues."""
        self.stats["files_checked"] += 1

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)

            # Check module docstring
            module_docstring = ast.get_docstring(tree)
            if module_docstring:
                self._check_module_docstring(module_docstring, str(file_path))

            # Check all functions and classes
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self._check_function_docstring(node, str(file_path), content)
                elif isinstance(node, ast.ClassDef):
                    self._check_class_docstring(node, str(file_path))

            return (
                len([issue for issue in self.issues if issue.file_path == str(file_path) and issue.severity == "error"])
                == 0
            )

        except Exception as e:
            self.issues.append(
                DocstringIssue(
                    file_path=str(file_path),
                    line_number=0,
                    issue_type="parse_error",
                    message=f"Failed to parse file: {e}",
                    severity="error",
                )
            )
            return False

    def _check_module_docstring(self, docstring: str, file_path: str):
        """Check module-level docstring."""
        self.stats["docstrings_found"] += 1

        # Check for Russian text
        if self.russian_pattern.search(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=1,
                    issue_type="language",
                    message="Russian text found in module docstring. Use English for API modules.",
                    severity="error",
                )
            )

        # Check for module docstring structure
        if self._is_api_file(file_path):
            self._check_api_module_docstring(docstring, file_path)

    def _check_function_docstring(self, node: ast.FunctionDef, file_path: str, content: str):
        """Check function/method docstring."""
        docstring = ast.get_docstring(node)
        if not docstring:
            if self._is_public_function(node, file_path):
                self.issues.append(
                    DocstringIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="missing_docstring",
                        message=f"Public function '{node.name}' missing docstring",
                        severity="warning",
                    )
                )
            return

        self.stats["docstrings_found"] += 1

        # Check for Russian text
        if self.russian_pattern.search(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    issue_type="language",
                    message=f"Russian text in docstring for '{node.name}'. Use English for API functions.",
                    severity="error",
                )
            )

        # Check if this is an API route
        if self._is_api_route(node, content):
            self.stats["api_routes_found"] += 1
            self._check_api_route_docstring(docstring, node.name, file_path, node.lineno)

        # Check Sphinx format for API files
        if self._is_api_file(file_path):
            self._check_sphinx_format(docstring, node.name, file_path, node.lineno)

    def _check_class_docstring(self, node: ast.ClassDef, file_path: str):
        """Check class docstring."""
        docstring = ast.get_docstring(node)
        if not docstring:
            if self._is_public_class(node):
                self.issues.append(
                    DocstringIssue(
                        file_path=file_path,
                        line_number=node.lineno,
                        issue_type="missing_docstring",
                        message=f"Public class '{node.name}' missing docstring",
                        severity="warning",
                    )
                )
            return

        self.stats["docstrings_found"] += 1

        # Check for Russian text
        if self.russian_pattern.search(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=node.lineno,
                    issue_type="language",
                    message=f"Russian text in docstring for class '{node.name}'. Use English for API classes.",
                    severity="error",
                )
            )

        # Check class docstring structure
        if self._is_api_file(file_path):
            self._check_class_docstring_structure(docstring, node.name, file_path, node.lineno)

    def _check_api_module_docstring(self, docstring: str, file_path: str):
        """Check API module docstring structure."""
        if not self._has_example_section(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=1,
                    issue_type="missing_example",
                    message="API module docstring should include usage examples",
                    severity="warning",
                )
            )

    def _check_api_route_docstring(self, docstring: str, func_name: str, file_path: str, line_number: int):
        """Check API route docstring for completeness."""

        # Check for required sections
        missing_sections = []
        for section in self.api_sections:
            if section not in docstring:
                missing_sections.append(section)

        if missing_sections:
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=line_number,
                    issue_type="missing_sections",
                    message=f"API route '{func_name}' missing sections: {', '.join(missing_sections)}",
                    severity="error",
                )
            )

        # Check for curl examples
        if not self.curl_pattern.search(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=line_number,
                    issue_type="missing_curl",
                    message=f"API route '{func_name}' missing curl example",
                    severity="error",
                )
            )
        else:
            self.stats["curl_examples_found"] += 1

        # Check for response examples
        if not self.response_pattern.search(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=line_number,
                    issue_type="missing_response",
                    message=f"API route '{func_name}' missing response example",
                    severity="warning",
                )
            )

    def _check_sphinx_format(self, docstring: str, name: str, file_path: str, line_number: int):
        """Check if docstring follows Sphinx format."""

        # Skip simple one-liners
        if len(docstring.strip().split("\n")) <= 1:
            return

        has_sphinx_sections = any(section in docstring for section in self.sphinx_sections)

        if has_sphinx_sections:
            self.stats["sphinx_compliant"] += 1

            # Check section formatting
            self._check_section_formatting(docstring, name, file_path, line_number)
        else:
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=line_number,
                    issue_type="format",
                    message=f"Function '{name}' docstring should use Sphinx format with sections",
                    severity="warning",
                )
            )

    def _check_section_formatting(self, docstring: str, name: str, file_path: str, line_number: int):
        """Check formatting of Sphinx sections."""

        # Check Args section formatting
        if "Args:" in docstring:
            args_match = re.search(r"Args:\s*\n(.*?)(?=\n\s*\w+:|$)", docstring, re.DOTALL)
            if args_match:
                args_content = args_match.group(1)
                if not re.search(r"\s+\w+\s*\([^)]+\):\s*", args_content):
                    self.issues.append(
                        DocstringIssue(
                            file_path=file_path,
                            line_number=line_number,
                            issue_type="format",
                            message=f"Args section in '{name}' should follow format: 'param (type): description'",
                            severity="warning",
                        )
                    )

        # Check Returns section formatting
        if "Returns:" in docstring:
            returns_match = re.search(r"Returns:\s*\n(.*?)(?=\n\s*\w+:|$)", docstring, re.DOTALL)
            if returns_match:
                returns_content = returns_match.group(1).strip()
                if not re.search(r"\s*\w+.*?:", returns_content):
                    self.issues.append(
                        DocstringIssue(
                            file_path=file_path,
                            line_number=line_number,
                            issue_type="format",
                            message=f"Returns section in '{name}' should specify return type",
                            severity="info",
                        )
                    )

    def _check_class_docstring_structure(self, docstring: str, class_name: str, file_path: str, line_number: int):
        """Check class docstring structure."""

        # Check for Attributes section in classes with attributes
        if "class" in file_path and not self._has_attributes_section(docstring):
            self.issues.append(
                DocstringIssue(
                    file_path=file_path,
                    line_number=line_number,
                    issue_type="missing_attributes",
                    message=f"Class '{class_name}' should document its attributes",
                    severity="info",
                )
            )

    def _is_api_file(self, file_path: str) -> bool:
        """Check if file is an API module."""
        return any(
            pattern in file_path
            for pattern in [
                "/api/",
                "/routes/",
                "/endpoints/",
                "/models/",
                "/schemas/",
                "/services/",
                "/repo/",
                "/core/",
                "/tools/",
            ]
        )

    def _is_api_route(self, node: ast.FunctionDef, content: str) -> bool:
        """Check if function is an API route."""
        # Look for decorator patterns
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Attribute):
                if hasattr(decorator.value, "id") and decorator.value.id == "router":
                    return True
            elif isinstance(decorator, ast.Call):
                if (
                    isinstance(decorator.func, ast.Attribute)
                    and hasattr(decorator.func.value, "id")
                    and decorator.func.value.id == "router"
                ):
                    return True
        return False

    def _is_public_function(self, node: ast.FunctionDef, file_path: str) -> bool:
        """Check if function should have documentation."""
        return not node.name.startswith("_") and self._is_api_file(file_path) and node.name not in ["main", "cli"]

    def _is_public_class(self, node: ast.ClassDef) -> bool:
        """Check if class should have documentation."""
        return not node.name.startswith("_")

    def _has_example_section(self, docstring: str) -> bool:
        """Check if docstring has example section."""
        return any(pattern in docstring for pattern in ["Example:", "Examples:", ">>> "])

    def _has_attributes_section(self, docstring: str) -> bool:
        """Check if docstring has attributes section."""
        return "Attributes:" in docstring

    def generate_report(self) -> str:
        """Generate comprehensive report."""
        report = []
        report.append("=" * 70)
        report.append("ENHANCED DOCUMENTATION LINTER REPORT")
        report.append("=" * 70)

        # Statistics
        report.append("\n📊 STATISTICS:")
        report.append(f"Files checked: {self.stats['files_checked']}")
        report.append(f"Docstrings found: {self.stats['docstrings_found']}")
        report.append(f"API routes found: {self.stats['api_routes_found']}")
        report.append(f"Curl examples found: {self.stats['curl_examples_found']}")
        report.append(f"Sphinx compliant: {self.stats['sphinx_compliant']}")

        if self.stats["api_routes_found"] > 0:
            curl_coverage = (self.stats["curl_examples_found"] / self.stats["api_routes_found"]) * 100
            report.append(f"Curl example coverage: {curl_coverage:.1f}%")

        # Issues by type
        issue_types = {}
        for issue in self.issues:
            if issue.issue_type not in issue_types:
                issue_types[issue.issue_type] = []
            issue_types[issue.issue_type].append(issue)

        if issue_types:
            report.append("\n🚨 ISSUES BY TYPE:")
            for issue_type, issues in issue_types.items():
                errors = len([i for i in issues if i.severity == "error"])
                warnings = len([i for i in issues if i.severity == "warning"])
                info = len([i for i in issues if i.severity == "info"])
                report.append(f"{issue_type}: {errors} errors, {warnings} warnings, {info} info")

        # Detailed issues
        if self.issues:
            report.append("\n📋 DETAILED ISSUES:")

            # Group by severity
            errors = [i for i in self.issues if i.severity == "error"]
            warnings = [i for i in self.issues if i.severity == "warning"]
            info = [i for i in self.issues if i.severity == "info"]

            for severity, issues in [("ERROR", errors), ("WARNING", warnings), ("INFO", info)]:
                if issues:
                    report.append(f"\n{severity}S:")
                    for issue in issues:
                        report.append(f"  {issue.file_path}:{issue.line_number}: {issue.message}")
        else:
            report.append("\n✅ No issues found!")

        # Recommendations
        report.append("\n💡 RECOMMENDATIONS:")
        if self.stats["curl_examples_found"] < self.stats["api_routes_found"]:
            report.append("- Add curl examples to API route docstrings")
        if self.stats["sphinx_compliant"] < self.stats["docstrings_found"]:
            report.append("- Convert more docstrings to Sphinx format")
        report.append("- Use templates from docs/docstring_templates.md")
        report.append("- Run 'make check-docstrings' before committing")

        return "\n".join(report)


def main():
    """Main function for command line usage."""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_docs_linter.py <file1> [file2] ...")
        print("       python enhanced_docs_linter.py src/")
        sys.exit(1)

    linter = EnhancedDocsLinter()
    files_to_check = []

    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file() and path.suffix == ".py":
            files_to_check.append(path)
        elif path.is_dir():
            files_to_check.extend(path.rglob("*.py"))

    # Filter files
    api_files = []
    for file_path in files_to_check:
        # Skip test files, migrations, etc.
        if any(
            pattern in str(file_path)
            for pattern in ["/tests/", "/migrations/", "/__pycache__/", "test_", "_test.py", "/venv/", "/.venv/"]
        ):
            continue

        # Skip simple files
        if file_path.name in ["__init__.py", "main.py", "cli.py"]:
            continue

        api_files.append(file_path)

    if not api_files:
        print("No relevant Python files found to check.")
        sys.exit(0)

    print(f"Checking {len(api_files)} files...")

    all_passed = True
    for file_path in api_files:
        if not linter.check_file(file_path):
            all_passed = False

    # Generate and print report
    report = linter.generate_report()
    print(report)

    # Exit with error code if there are errors
    error_count = len([i for i in linter.issues if i.severity == "error"])
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
