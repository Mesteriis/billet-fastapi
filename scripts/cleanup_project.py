#!/usr/bin/env python3
"""
Скрипт для очистки проекта от временных файлов и мусора.

БЕЗОПАСНО удаляет только мусор:
- .benchmarks/ - файлы бенчмарков
- reports/ - отчеты (кроме важных)
- htmlcov/ - отчеты покрытия HTML
- .coverage* - файлы покрытия
- .pytest_cache/ - кеш pytest (включая в src/, tests/)
- .mypy_cache/ - кеш mypy (включая в src/, tests/)
- __pycache__/ - кеш Python (включая в src/, tests/)
- *.pyc, *.pyo - скомпилированные Python файлы (ВЕЗДЕ)
- coverage.xml, *.log - отчеты и логи (включая в src/)
- .DS_Store - файлы macOS (ВЕЗДЕ)
- Thumbs.db - файлы Windows (ВЕЗДЕ)
- *.tmp, *.temp - временные файлы (ВЕЗДЕ)
- .tox/ - tox окружения
- .ruff_cache/, .black_cache/ - кеш линтеров

НЕ УДАЛЯЕТ важные файлы:
- .venv/, venv/, env/ - виртуальные окружения
- node_modules/ - зависимости Node.js
- dist/, build/ - артефакты сборки
- *.py - исходный код Python (в src/, tests/, docs/)
- .git/ - репозиторий Git

НОВОЕ: Теперь ищет мусор И В ЗАЩИЩЕННЫХ ДИРЕКТОРИЯХ (src/, tests/, docs/)!
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
            ".benchmarks",  # Директория бенчмарков
            "htmlcov",  # HTML отчеты покрытия
            ".pytest_cache",  # Кеш pytest
            ".mypy_cache",  # Кеш mypy
            "__pycache__",  # Кеш Python
            ".tox",  # Tox окружения
            ".coverage_html",  # HTML покрытие
            ".ruff_cache",  # Кеш Ruff
            ".black_cache",  # Кеш Black
            ".hypothesis",  # Hypothesis кеш
            ".cache",  # Общий кеш
        }

        self.file_patterns_to_remove = {
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".coverage*",
            "coverage.xml",  # Coverage XML отчет в корне
            "coverage.json",  # Coverage JSON отчет
            "junit.xml",  # JUnit XML отчет
            "test-results.xml",  # Результаты тестов XML
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

    def is_cache_directory(self, path: Path) -> bool:
        """Проверить, является ли путь кеш-директорией, которую можно удалить даже внутри защищенных директорий."""
        cache_directories = {
            ".mypy_cache",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".black_cache",
            ".hypothesis",
            ".cache",
        }
        return path.name in cache_directories

    def should_remove_file(self, file_path: Path) -> bool:
        """Определить, нужно ли удалить файл."""
        # Проверяем, не является ли сам файл защищенным
        if file_path.name in self.protected_files:
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

    def is_safe_to_remove_in_protected_dir(self, file_path: Path) -> bool:
        """Проверить, безопасно ли удалить файл в защищенной директории."""
        # Только определенные типы мусорных файлов можно удалять в защищенных директориях
        safe_patterns = {
            "*.pyc",
            "*.pyo",
            "*.pyd",  # Скомпилированные Python файлы
            ".coverage*",
            "coverage.xml",
            "coverage.json",  # Отчеты покрытия
            "junit.xml",
            "test-results.xml",  # XML отчеты тестов
            "*.tmp",
            "*.temp",  # Временные файлы
            "*.log",  # Лог файлы
            ".DS_Store",
            "Thumbs.db",  # Системные файлы
            "*.orig",
            "*.rej",  # Файлы патчей
            "*.swp",
            "*.swo",
            "*~",  # Временные файлы редакторов
        }

        # Проверяем безопасные паттерны
        for pattern in safe_patterns:
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

                # Проверяем: либо директория не защищена, либо это кеш-директория
                should_remove = dir_name in self.directories_to_remove and (
                    not self.is_protected(dir_path) or self.is_cache_directory(dir_path)
                )

                if should_remove:
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

            # Проверяем, находимся ли в защищенной директории
            in_protected_dir = any(protected in root_path.parts for protected in self.protected_directories)

            for file_name in files:
                file_path = root_path / file_name

                # Определяем, можно ли удалить файл
                should_remove = False
                if in_protected_dir:
                    # В защищенной директории удаляем только безопасные мусорные файлы
                    should_remove = self.is_safe_to_remove_in_protected_dir(file_path)
                else:
                    # В обычных директориях используем стандартную логику
                    should_remove = self.should_remove_file(file_path)

                if should_remove:
                    try:
                        size = file_path.stat().st_size

                        if self.verbose:
                            protection_note = " [protected dir]" if in_protected_dir else ""
                            print(
                                f"📄 Удаляем файл: {file_path.relative_to(self.project_root)}{protection_note} ({self.format_size(size)})"
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
