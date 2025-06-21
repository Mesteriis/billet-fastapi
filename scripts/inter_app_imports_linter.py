#!/usr/bin/env python3
"""
Inter-App Imports Linter.

Проверяет правила импортов между приложениями в папке apps/:
- ❌ Запрещает прямые импорты между приложениями вне TYPE_CHECKING
- ✅ Разрешает импорты интерфейсов (apps.*.interfaces)
- ✅ Разрешает импорты в TYPE_CHECKING блоках
- ✅ Разрешает импорты из shared модулей
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Any, Iterator, NamedTuple


class ImportViolation(NamedTuple):
    """Нарушение правил импорта."""

    file_path: str
    line_number: int
    column: int
    import_module: str
    violation_type: str
    suggestion: str


class InterAppImportsChecker(ast.NodeVisitor):
    """
    AST visitor для проверки импортов между приложениями.
    """

    def __init__(self, file_path: str, config: dict[str, Any] | None = None):
        self.file_path = file_path
        self.violations: list[ImportViolation] = []
        self.in_type_checking = False
        self.type_checking_depth = 0
        self.config = config or {}

        # Паттерны для проверки
        self.apps_import_pattern = re.compile(r"^apps\.([^.]+)\.(.+)$")
        self.interfaces_pattern = re.compile(r"^apps\.([^.]+)\.interfaces")

        # Получаем список разрешенных путей для импортов
        self.allowed_shared_imports = self._get_allowed_shared_imports()

    def _get_allowed_shared_imports(self) -> list[str]:
        """Получить список разрешенных путей для импортов из конфигурации."""
        shared_imports = self.config.get("allow_shared_imports", [])

        # Поддержка старого формата (boolean) для обратной совместимости
        if isinstance(shared_imports, bool):
            if shared_imports:
                return ["apps.shared"]  # Значение по умолчанию
            else:
                return []

        # Новый формат - список путей
        if isinstance(shared_imports, list):
            return shared_imports

        # Значение по умолчанию если конфигурация некорректна
        return ["apps.shared"]

    def _is_allowed_shared_import(self, module_name: str) -> bool:
        """Проверить разрешен ли импорт из shared модуля."""
        for allowed_path in self.allowed_shared_imports:
            if module_name.startswith(allowed_path + ".") or module_name == allowed_path:
                return True
        return False

    def visit_If(self, node: ast.If) -> None:
        """Обработка if блоков для определения TYPE_CHECKING."""
        # Проверяем if TYPE_CHECKING:
        if self._is_type_checking_block(node):
            self.in_type_checking = True
            self.type_checking_depth += 1

            # Посещаем дочерние узлы
            for child in ast.iter_child_nodes(node):
                self.visit(child)

            self.type_checking_depth -= 1
            if self.type_checking_depth == 0:
                self.in_type_checking = False
        else:
            # Обычный if блок
            self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Обработка import statements."""
        for alias in node.names:
            self._check_import(module_name=alias.name, node=node, import_type="import")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Обработка from ... import statements."""
        if node.module:
            self._check_import(module_name=node.module, node=node, import_type="from_import")

    def _is_type_checking_block(self, node: ast.If) -> bool:
        """Проверить является ли блок TYPE_CHECKING."""
        if isinstance(node.test, ast.Name):
            return node.test.id == "TYPE_CHECKING"
        elif isinstance(node.test, ast.Attribute):
            # typing.TYPE_CHECKING
            if (
                isinstance(node.test.value, ast.Name)
                and node.test.value.id == "typing"
                and node.test.attr == "TYPE_CHECKING"
            ):
                return True
        return False

    def _check_import(self, module_name: str, node: ast.AST, import_type: str) -> None:
        """Проверить импорт на соответствие правилам."""
        # Проверяем является ли это импортом из apps.*
        apps_match = self.apps_import_pattern.match(module_name)
        if not apps_match:
            return  # Не импорт из apps, пропускаем

        app_name, module_path = apps_match.groups()

        # Правило 1: Импорты из разрешенных shared модулей разрешены
        if self._is_allowed_shared_import(module_name):
            return

        # Правило 2: Импорты интерфейсов всегда разрешены
        if self.interfaces_pattern.match(module_name):
            return

        # Правило 3: Импорты в TYPE_CHECKING блоках разрешены
        if self.in_type_checking:
            return

        # Правило 4: Импорты внутри того же приложения разрешены
        current_app = self._get_current_app_name()
        if current_app == app_name:
            return

        # Нарушение найдено!
        violation_type = "direct_inter_app_import"
        suggestion = self._generate_suggestion(module_name, app_name, module_path)

        # Безопасное получение номера строки и колонки
        line_number = getattr(node, "lineno", 1)
        column = getattr(node, "col_offset", 0)

        self.violations.append(
            ImportViolation(
                file_path=self.file_path,
                line_number=line_number,
                column=column,
                import_module=module_name,
                violation_type=violation_type,
                suggestion=suggestion,
            )
        )

    def _get_current_app_name(self) -> str | None:
        """Получить имя текущего приложения из пути файла."""
        path_parts = Path(self.file_path).parts
        try:
            apps_index = path_parts.index("apps")
            if apps_index + 1 < len(path_parts):
                return path_parts[apps_index + 1]
        except ValueError:
            pass
        return None

    def _generate_suggestion(self, module_name: str, app_name: str, module_path: str) -> str:
        """Сгенерировать предложение по исправлению."""
        # Показываем примеры разрешенных путей из конфигурации
        allowed_examples = (
            ", ".join(self.allowed_shared_imports[:3]) if self.allowed_shared_imports else "core, constants"
        )

        if "models" in module_path or "schemas" in module_path:
            return f"Use interface: from apps.{app_name}.interfaces import [InterfaceName]"
        elif "services" in module_path:
            return f"Move to TYPE_CHECKING: if TYPE_CHECKING:\\n    from {module_name} import ..."
        else:
            return f"Consider: 1) interface from apps.{app_name}.interfaces, 2) TYPE_CHECKING block, or 3) allowed shared paths: {allowed_examples}"


class InterAppImportsLinter:
    """
    Основной класс линтера.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.total_files = 0
        self.total_violations = 0

    def check_file(self, file_path: str) -> list[ImportViolation]:
        """Проверить один файл."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)
            checker = InterAppImportsChecker(file_path, self.config)
            checker.visit(tree)

            return checker.violations

        except SyntaxError as e:
            print(f"⚠️  Syntax error in {file_path}:{e.lineno}: {e.msg}")
            return []
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return []

    def check_directory(self, directory: str) -> Iterator[ImportViolation]:
        """Проверить все Python файлы в директории."""
        path = Path(directory)

        # Находим все .py файлы
        python_files = list(path.rglob("*.py"))
        self.total_files = len(python_files)

        for file_path in python_files:
            # Пропускаем __pycache__ и .venv
            if "__pycache__" in str(file_path) or ".venv" in str(file_path):
                continue

            violations = self.check_file(str(file_path))
            for violation in violations:
                yield violation

    def format_violation(self, violation: ImportViolation) -> str:
        """Форматировать нарушение для вывода."""
        return (
            f"{violation.file_path}:{violation.line_number}:{violation.column}: "
            f"❌ Direct inter-app import: {violation.import_module}\n"
            f"    💡 Suggestion: {violation.suggestion}"
        )

    def run(self, paths: list[str], fix: bool = False) -> int:
        """Запустить линтер."""
        all_violations = []

        for path in paths:
            if Path(path).is_file():
                violations = self.check_file(path)
                all_violations.extend(violations)
            else:
                violations = list(self.check_directory(path))
                all_violations.extend(violations)

        self.total_violations = len(all_violations)

        # Выводим результаты
        if all_violations:
            print("🔍 Inter-App Import Violations Found:\n")

            # Группируем по файлам
            violations_by_file = {}
            for violation in all_violations:
                if violation.file_path not in violations_by_file:
                    violations_by_file[violation.file_path] = []
                violations_by_file[violation.file_path].append(violation)

            # Выводим по файлам
            for file_path, violations in violations_by_file.items():
                print(f"📄 {file_path}:")
                for violation in violations:
                    print(f"  Line {violation.line_number}: {violation.import_module}")
                    print(f"    💡 {violation.suggestion}")
                print()

            print(f"❌ Found {self.total_violations} violations in {len(violations_by_file)} files")

            # Общие рекомендации
            print("\n📋 Quick Fix Guide:")
            print("  1. ✅ Use interfaces: from apps.users.interfaces import UserIdentity")
            print("  2. ✅ Use TYPE_CHECKING: if TYPE_CHECKING: from apps.users.models import User")

            # Показываем примеры разрешенных путей из конфигурации
            allowed_paths = self.config.get("allow_shared_imports", ["apps.shared", "core", "constants"])
            if isinstance(allowed_paths, list) and allowed_paths:
                example_path = allowed_paths[0]
                print(f"  3. ✅ Allowed shared paths: from {example_path} import ...")
            else:
                print("  3. ✅ Shared modules: from core import ... (check config)")

            return 1  # Exit code 1 = есть нарушения
        else:
            print(f"✅ No inter-app import violations found! Checked {self.total_files} files.")
            return 0  # Exit code 0 = нет нарушений


def load_config() -> dict[str, Any]:
    """Загрузить конфигурацию из pyproject.toml."""
    try:
        import tomllib
    except ImportError:
        return {}  # Если tomllib недоступен, используем пустую конфигурацию

    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        return data.get("tool", {}).get("inter_app_imports_linter", {})
    except FileNotFoundError:
        return {}


def main() -> int:
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Inter-App Imports Linter - проверка импортов между приложениями")
    parser.add_argument("paths", nargs="*", default=["src/apps"], help="Пути для проверки (по умолчанию: src/apps)")
    parser.add_argument("--fix", action="store_true", help="Автоматически исправить нарушения (пока не реализовано)")
    parser.add_argument("--config", help="Путь к файлу конфигурации")
    parser.add_argument("--verbose", "-v", action="store_true", help="Подробный вывод")

    args = parser.parse_args()

    # Загружаем конфигурацию
    config = load_config()

    # Создаем и запускаем линтер
    linter = InterAppImportsLinter(config)

    if args.verbose:
        print(f"🔍 Checking paths: {args.paths}")
        print(f"📋 Config: {config}")

    return linter.run(args.paths, fix=args.fix)


if __name__ == "__main__":
    sys.exit(main())
