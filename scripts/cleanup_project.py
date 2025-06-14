#!/usr/bin/env python3
"""
Скрипт для очистки проекта от временных файлов и мусора.

БЕЗОПАСНО удаляет только мусор:
- .benchmarks/ - файлы бенчмарков
- reports/ - отчеты (кроме важных)
- htmlcov/ - отчеты покрытия HTML
- .coverage* - файлы покрытия
- .pytest_cache/ - кеш pytest
- .mypy_cache/ - кеш mypy
- __pycache__/ - кеш Python
- *.pyc, *.pyo - скомпилированные Python файлы
- .DS_Store - файлы macOS
- Thumbs.db - файлы Windows
- *.tmp, *.temp - временные файлы
- *.log - лог файлы (кроме важных)
- .tox/ - tox окружения
- .ruff_cache/, .black_cache/ - кеш линтеров

НЕ УДАЛЯЕТ важные файлы:
- .venv/, venv/, env/ - виртуальные окружения
- node_modules/ - зависимости Node.js
- dist/, build/ - артефакты сборки
- src/, tests/, docs/ - исходный код
- .git/ - репозиторий Git
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import List, Set


class ProjectCleaner:
    """Класс для очистки проекта от временных файлов."""

    def __init__(self, project_root: Path, dry_run: bool = False, verbose: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.verbose = verbose
        self.removed_items: List[str] = []
        self.total_size_saved = 0

        # Паттерны для удаления (только мусор, НЕ виртуальные окружения!)
        self.directories_to_remove = {
            ".benchmarks",
            "htmlcov",
            ".pytest_cache",
            ".mypy_cache",
            "__pycache__",
            ".tox",
            ".coverage_html",
            ".ruff_cache",
            ".black_cache",
        }

        self.file_patterns_to_remove = {
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".coverage*",
            "*.tmp",
            "*.temp",
            "*.log",
            ".DS_Store",
            "Thumbs.db",
            "*.orig",
            "*.rej",
            "*.swp",
            "*.swo",
            "*~",
            ".pytest_cache",
        }

        # Файлы в reports/ которые можно удалить
        self.reports_patterns = {
            "coverage.xml",
            "coverage.json",
            "junit.xml",
            "test-results.xml",
            "flake8-report.txt",
            "mypy-report.txt",
            "bandit-report.json",
            "*.html",  # HTML отчеты
            "*.xml",  # XML отчеты (кроме важных конфигов)
        }

        # Важные файлы, которые НЕ нужно удалять
        self.protected_files = {
            "README.md",
            "LICENSE",
            "pyproject.toml",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            ".gitignore",
            ".pre-commit-config.yaml",
            "Makefile",
        }

        # Важные директории, которые НЕ нужно удалять
        self.protected_directories = {
            ".git",
            "src",
            "tests",
            "docs",
            "examples",
            "migrations",
            "config",
            "scripts",
            "templates",
            "backups",  # Важные бэкапы
            ".venv",  # Виртуальное окружение
            "venv",  # Виртуальное окружение
            "env",  # Виртуальное окружение
            ".env",  # Виртуальное окружение
            "node_modules",  # Зависимости Node.js
            "dist",  # Артефакты сборки (могут быть важными)
            "build",  # Артефакты сборки (могут быть важными)
        }

    def get_directory_size(self, path: Path) -> int:
        """Получить размер директории в байтах."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    try:
                        total_size += filepath.stat().st_size
                    except (OSError, FileNotFoundError):
                        pass
        except (OSError, FileNotFoundError):
            pass
        return total_size

    def format_size(self, size_bytes: int) -> str:
        """Форматировать размер в человекочитаемый вид."""
        size_float = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size_float < 1024.0:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024.0
        return f"{size_float:.1f} TB"

    def is_protected(self, path: Path) -> bool:
        """Проверить, является ли путь защищенным от удаления."""
        # Проверяем имя файла/директории
        if path.name in self.protected_files or path.name in self.protected_directories:
            return True

        # Проверяем, находится ли в защищенной директории
        for parent in path.parents:
            if parent.name in self.protected_directories:
                return True

        return False

    def should_remove_file(self, file_path: Path) -> bool:
        """Определить, нужно ли удалить файл."""
        if self.is_protected(file_path):
            return False

        # Проверяем паттерны файлов
        for pattern in self.file_patterns_to_remove:
            if file_path.match(pattern):
                return True

        # Специальная обработка для reports/
        if "reports" in file_path.parts:
            for pattern in self.reports_patterns:
                if file_path.match(pattern):
                    return True

        return False

    def clean_directories(self) -> None:
        """Очистить директории."""
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)

            # Удаляем целые директории
            for dir_name in list(dirs):
                dir_path = root_path / dir_name

                if dir_name in self.directories_to_remove and not self.is_protected(dir_path):
                    size = self.get_directory_size(dir_path)

                    if self.verbose:
                        print(
                            f"🗂️  Удаляем директорию: {dir_path.relative_to(self.project_root)} ({self.format_size(size)})"
                        )

                    if not self.dry_run:
                        try:
                            shutil.rmtree(dir_path)
                            self.removed_items.append(f"📁 {dir_path.relative_to(self.project_root)}")
                            self.total_size_saved += size
                        except OSError as e:
                            print(f"❌ Ошибка удаления {dir_path}: {e}")
                    else:
                        self.removed_items.append(f"📁 {dir_path.relative_to(self.project_root)} (dry-run)")
                        self.total_size_saved += size

                    # Убираем из списка, чтобы не заходить внутрь
                    dirs.remove(dir_name)

    def clean_files(self) -> None:
        """Очистить отдельные файлы."""
        for root, dirs, files in os.walk(self.project_root):
            root_path = Path(root)

            # Пропускаем защищенные директории
            if any(protected in root_path.parts for protected in self.protected_directories):
                continue

            for file_name in files:
                file_path = root_path / file_name

                if self.should_remove_file(file_path):
                    try:
                        size = file_path.stat().st_size

                        if self.verbose:
                            print(
                                f"📄 Удаляем файл: {file_path.relative_to(self.project_root)} ({self.format_size(size)})"
                            )

                        if not self.dry_run:
                            file_path.unlink()
                            self.removed_items.append(f"📄 {file_path.relative_to(self.project_root)}")
                            self.total_size_saved += size
                        else:
                            self.removed_items.append(f"📄 {file_path.relative_to(self.project_root)} (dry-run)")
                            self.total_size_saved += size

                    except OSError as e:
                        if self.verbose:
                            print(f"❌ Ошибка удаления {file_path}: {e}")

    def clean_empty_directories(self) -> None:
        """Удалить пустые директории."""
        for root, dirs, files in os.walk(self.project_root, topdown=False):
            root_path = Path(root)

            # Пропускаем корневую директорию и защищенные
            if root_path == self.project_root or self.is_protected(root_path):
                continue

            try:
                # Проверяем, пустая ли директория
                if not any(root_path.iterdir()):
                    if self.verbose:
                        print(f"📂 Удаляем пустую директорию: {root_path.relative_to(self.project_root)}")

                    if not self.dry_run:
                        root_path.rmdir()
                        self.removed_items.append(f"📂 {root_path.relative_to(self.project_root)} (пустая)")
                    else:
                        self.removed_items.append(f"📂 {root_path.relative_to(self.project_root)} (пустая, dry-run)")

            except OSError:
                # Директория не пустая или ошибка доступа
                pass

    def run(self) -> bool:
        """Запустить очистку проекта."""
        print(f"🧹 Очистка проекта: {self.project_root}")

        if self.dry_run:
            print("🔍 Режим dry-run: файлы не будут удалены")

        print()

        # Очищаем директории
        self.clean_directories()

        # Очищаем файлы
        self.clean_files()

        # Удаляем пустые директории
        self.clean_empty_directories()

        # Выводим результаты
        print(f"\n📊 Результаты очистки:")
        print(f"   Удалено элементов: {len(self.removed_items)}")
        print(f"   Освобождено места: {self.format_size(self.total_size_saved)}")

        if self.verbose and self.removed_items:
            print(f"\n📋 Удаленные элементы:")
            for item in self.removed_items[:20]:  # Показываем первые 20
                print(f"   {item}")

            if len(self.removed_items) > 20:
                print(f"   ... и еще {len(self.removed_items) - 20} элементов")

        if not self.removed_items:
            print("✨ Проект уже чистый!")
            return True

        if self.dry_run:
            print("\n💡 Запустите без --dry-run для фактического удаления")
        else:
            print("\n✅ Очистка завершена!")

        return True


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(
        description="Очистка проекта от временных файлов и мусора",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python scripts/cleanup_project.py                    # Обычная очистка
  python scripts/cleanup_project.py --dry-run          # Показать что будет удалено
  python scripts/cleanup_project.py --verbose          # Подробный вывод
  python scripts/cleanup_project.py --dry-run -v       # Подробный dry-run
        """,
    )

    parser.add_argument("--dry-run", action="store_true", help="Показать что будет удалено, но не удалять фактически")

    parser.add_argument("-v", "--verbose", action="store_true", help="Подробный вывод")

    parser.add_argument(
        "--project-root", type=Path, default=Path.cwd(), help="Корневая директория проекта (по умолчанию: текущая)"
    )

    args = parser.parse_args()

    # Проверяем, что мы в корне проекта
    project_root = args.project_root.resolve()
    if not (project_root / "pyproject.toml").exists():
        print("❌ Ошибка: pyproject.toml не найден. Убедитесь, что вы в корне проекта.")
        return 1

    # Запускаем очистку
    cleaner = ProjectCleaner(project_root=project_root, dry_run=args.dry_run, verbose=args.verbose)

    try:
        success = cleaner.run()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️ Очистка прервана пользователем")
        return 1
    except Exception as e:
        print(f"❌ Ошибка при очистке: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
