#!/usr/bin/env python3
"""
Скрипт для проверки соблюдения архитектурных правил проекта.
"""

import re
import sys
from pathlib import Path
from typing import List, Set


class ArchitectureChecker:
    """Проверяет соблюдение архитектурных правил."""

    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.violations = []

        # Правила архитектуры
        self.rules = {
            # messaging не должен импортировать streaming
            "messaging": {
                "forbidden_imports": ["streaming"],
                "description": "messaging модуль не должен импортировать streaming",
            },
            # streaming не должен импортировать messaging (кроме разрешенных)
            "streaming": {
                "forbidden_imports": ["messaging"],
                "allowed_exceptions": ["messaging.core", "messaging.models"],
                "description": "streaming модуль не должен импортировать messaging (кроме core и models)",
            },
            # apps не должны импортировать друг друга напрямую
            "apps": {
                "forbidden_cross_imports": True,
                "description": "apps не должны импортировать друг друга напрямую",
            },
        }

    def get_python_files(self) -> List[Path]:
        """Получает список Python файлов в src/."""
        src_path = self.root_path / "src"
        if not src_path.exists():
            return []

        python_files = []
        for file_path in src_path.rglob("*.py"):
            # Исключаем тесты и миграции
            if any(part in file_path.parts for part in ["test", "migration", "__pycache__"]):
                continue
            python_files.append(file_path)

        return python_files

    def get_file_imports(self, file_path: Path) -> Set[str]:
        """Извлекает импорты из файла."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return set()

        imports = set()

        # Паттерны для поиска импортов
        patterns = [
            r"^from\s+(\w+(?:\.\w+)*)",  # from module import ...
            r"^import\s+(\w+(?:\.\w+)*)",  # import module
        ]

        for line in content.splitlines():
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    module = match.group(1)
                    # Берем только первую часть модуля
                    top_level = module.split(".")[0]
                    imports.add(top_level)

        return imports

    def get_module_from_path(self, file_path: Path) -> str:
        """Определяет модуль по пути файла."""
        parts = file_path.parts
        if "src" not in parts:
            return ""

        try:
            src_index = parts.index("src")
            if src_index + 1 < len(parts):
                return parts[src_index + 1]
        except ValueError:
            pass

        return ""

    def check_forbidden_imports(self):
        """Проверяет запрещенные импорты."""
        python_files = self.get_python_files()

        for file_path in python_files:
            module = self.get_module_from_path(file_path)
            if not module or module not in self.rules:
                continue

            rule = self.rules[module]
            if "forbidden_imports" not in rule:
                continue

            imports = self.get_file_imports(file_path)
            forbidden = set(rule["forbidden_imports"])

            # Проверяем исключения
            allowed_exceptions = set(rule.get("allowed_exceptions", []))

            violations = imports & forbidden
            for violation in violations:
                # Проверяем, есть ли это нарушение в исключениях
                is_allowed = any(exc.startswith(f"{violation}.") for exc in allowed_exceptions)

                if not is_allowed:
                    rel_path = file_path.relative_to(self.root_path)
                    self.violations.append(f"❌ {rel_path}: {rule['description']} (импортирует {violation})")

    def check_apps_cross_imports(self):
        """Проверяет перекрестные импорты между apps."""
        src_path = self.root_path / "src" / "apps"
        if not src_path.exists():
            return

        # Получаем список всех apps
        apps = [d.name for d in src_path.iterdir() if d.is_dir() and not d.name.startswith("_")]

        for app_dir in src_path.iterdir():
            if not app_dir.is_dir() or app_dir.name.startswith("_"):
                continue

            app_name = app_dir.name
            other_apps = [app for app in apps if app != app_name]

            # Проверяем файлы в этом app
            for file_path in app_dir.rglob("*.py"):
                if "__pycache__" in file_path.parts:
                    continue

                imports = self.get_file_imports(file_path)

                # Ищем импорты других apps
                for other_app in other_apps:
                    if other_app in imports:
                        rel_path = file_path.relative_to(self.root_path)
                        self.violations.append(
                            f"❌ {rel_path}: app '{app_name}' не должен импортировать app '{other_app}' напрямую"
                        )

    def check_circular_imports(self):
        """Проверяет циклические импорты (упрощенная версия)."""
        python_files = self.get_python_files()
        import_graph = {}

        # Строим граф импортов
        for file_path in python_files:
            module_name = str(file_path.relative_to(self.root_path / "src")).replace("/", ".").replace(".py", "")
            imports = self.get_file_imports(file_path)
            import_graph[module_name] = imports

        # Простая проверка на циклы (можно улучшить)
        for module, imports in import_graph.items():
            for imported in imports:
                if imported in import_graph and module.split(".")[0] in import_graph[imported]:
                    self.violations.append(f"⚠️  Возможен циклический импорт между {module} и {imported}")

    def check_all(self) -> List[str]:
        """Проводит все проверки архитектуры."""
        print("🏗️  Проверка архитектурных правил...")

        self.check_forbidden_imports()
        self.check_apps_cross_imports()
        self.check_circular_imports()

        return self.violations


def main():
    """Главная функция."""
    root_path = Path(".")
    checker = ArchitectureChecker(root_path)
    violations = checker.check_all()

    if violations:
        print("\n❌ Обнаружены нарушения архитектурных правил:")
        for violation in violations:
            print(f"  {violation}")
        print(f"\nВсего нарушений: {len(violations)}")
        sys.exit(1)
    else:
        print("✅ Архитектурные правила соблюдены!")
        sys.exit(0)


if __name__ == "__main__":
    main()
