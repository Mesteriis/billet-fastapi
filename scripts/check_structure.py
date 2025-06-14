#!/usr/bin/env python3
"""
Скрипт для проверки структуры проекта.
Используется в pre-commit хуках.
"""

import os
import sys
from pathlib import Path


def check_project_structure():
    """Проверка базовой структуры проекта."""
    project_root = Path(__file__).parent.parent
    errors = []

    # Обязательные директории
    required_dirs = ["src", "tests", "migrations", "src/apps", "src/core", "tests/factories", "tests/mocking"]

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            errors.append(f"❌ Отсутствует обязательная директория: {dir_path}")

    # Обязательные файлы
    required_files = ["pyproject.toml", "src/__init__.py", "tests/__init__.py", "conftest.py"]

    for file_path in required_files:
        full_path = project_root / file_path
        if not full_path.exists():
            errors.append(f"❌ Отсутствует обязательный файл: {file_path}")

    # Проверка __init__.py в пакетах
    src_dirs = []
    for root, dirs, files in os.walk(project_root / "src"):
        # Пропускаем __pycache__ и .git
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        if dirs:  # Если есть подпапки, значит это пакет
            src_dirs.append(Path(root))

    for src_dir in src_dirs:
        init_file = src_dir / "__init__.py"
        if not init_file.exists():
            rel_path = src_dir.relative_to(project_root)
            errors.append(f"❌ Отсутствует __init__.py в пакете: {rel_path}")

    # Проверка импортов в __init__.py файлах
    for init_file in project_root.rglob("*/__init__.py"):
        if "src" in str(init_file):
            try:
                with open(init_file, encoding="utf-8") as f:
                    content = f.read()
                    # Проверяем, что нет относительных импортов верхнего уровня
                    if "from .." in content and init_file.name != "__init__.py":
                        rel_path = init_file.relative_to(project_root)
                        errors.append(f"⚠️  Подозрительный относительный импорт в: {rel_path}")
            except Exception:
                pass

    # Результат
    if errors:
        print("🔍 Проверка структуры проекта:")
        for error in errors:
            print(error)
        return False
    else:
        print("✅ Структура проекта корректна")
        return True


if __name__ == "__main__":
    success = check_project_structure()
    sys.exit(0 if success else 1)
