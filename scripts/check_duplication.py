#!/usr/bin/env python3
"""
Скрипт для обнаружения дублирования кода в проекте.
Использует несколько подходов для выявления потенциальных дублей.
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Настройки для анализа
MIN_LINES_FOR_DUPLICATE = 7  # Минимум строк для считания дубликатом
IGNORE_PATTERNS = [
    r"^\s*#.*$",  # Комментарии
    r'^\s*""".*?""".*$',  # Докстринги
    r"^\s*$",  # Пустые строки
    r"^\s*import\s+.*$",  # Импорты
    r"^\s*from\s+.*import.*$",  # From импорты
]

EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "htmlcov",
    "node_modules",
    ".venv",
    "venv",
    "migrations",
    "reports",
    "docs",
    "examples",
}

EXCLUDE_FILES = {"__init__.py", "conftest.py", "test_*.py", "*_test.py"}


class CodeDuplicationDetector:
    """Детектор дублирования кода."""

    def __init__(self, root_path: str, min_lines: int = MIN_LINES_FOR_DUPLICATE):
        self.root_path = Path(root_path)
        self.min_lines = min_lines
        self.ignore_patterns = [re.compile(pattern) for pattern in IGNORE_PATTERNS]

    def should_ignore_line(self, line: str) -> bool:
        """Проверяет, следует ли игнорировать строку."""
        return any(pattern.match(line) for pattern in self.ignore_patterns)

    def normalize_line(self, line: str) -> str:
        """Нормализует строку для сравнения."""
        # Убираем лишние пробелы
        line = re.sub(r"\s+", " ", line.strip())
        # Заменяем переменные на плейсхолдеры (упрощенно)
        line = re.sub(r"\b\w+\b", "VAR", line)
        return line

    def get_python_files(self) -> List[Path]:
        """Получает список Python файлов для анализа."""
        python_files = []

        for root, dirs, files in os.walk(self.root_path):
            # Исключаем определенные директории
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file

                    # Проверяем исключения файлов
                    should_exclude = any(file_path.match(pattern) for pattern in EXCLUDE_FILES)

                    if not should_exclude:
                        python_files.append(file_path)

        return python_files

    def get_file_lines(self, file_path: Path) -> List[str]:
        """Читает и обрабатывает строки файла."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = []
                for line_num, line in enumerate(f, 1):
                    if not self.should_ignore_line(line):
                        normalized = self.normalize_line(line)
                        if normalized:  # Не пустая после нормализации
                            lines.append((line_num, line.rstrip(), normalized))
                return lines
        except Exception as e:
            print(f"Ошибка чтения файла {file_path}: {e}")
            return []

    def find_exact_duplicates(self) -> Dict[str, List[Tuple[Path, int, int]]]:
        """Находит точные дубликаты блоков кода."""
        print("🔍 Поиск точных дубликатов...")

        duplicates = defaultdict(list)
        files = self.get_python_files()

        # Группируем файлы по хешам блоков
        for file_path in files:
            lines = self.get_file_lines(file_path)

            # Создаем скользящее окно для блоков кода
            for i in range(len(lines) - self.min_lines + 1):
                block_lines = lines[i : i + self.min_lines]

                # Создаем хеш блока на основе нормализованных строк
                block_text = "\n".join(norm_line for _, _, norm_line in block_lines)
                block_hash = hashlib.md5(block_text.encode()).hexdigest()

                start_line = block_lines[0][0]
                end_line = block_lines[-1][0]

                duplicates[block_hash].append((file_path, start_line, end_line))

        # Фильтруем только дубликаты (более одного вхождения)
        return {h: locations for h, locations in duplicates.items() if len(locations) > 1}

    def find_similar_functions(self) -> List[Tuple[str, List[Tuple[Path, int]]]]:
        """Находит похожие функции."""
        print("🔍 Поиск похожих функций...")

        functions = defaultdict(list)
        files = self.get_python_files()

        for file_path in files:
            content = self.get_file_content(file_path)
            if not content:
                continue

            # Ищем определения функций
            function_pattern = re.compile(r"^(\s*)def\s+(\w+)\s*\([^)]*\):", re.MULTILINE)

            for match in function_pattern.finditer(content):
                func_name = match.group(2)
                start_line = content[: match.start()].count("\n") + 1

                # Группируем по имени функции
                functions[func_name].append((file_path, start_line))

        # Возвращаем функции с одинаковыми именами в разных файлах
        similar = []
        for func_name, locations in functions.items():
            if len(locations) > 1:
                # Проверяем, что это разные файлы
                unique_files = {loc[0] for loc in locations}
                if len(unique_files) > 1:
                    similar.append((func_name, locations))

        return similar

    def get_file_content(self, file_path: Path) -> str:
        """Получает содержимое файла."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def check_architectural_violations(self) -> List[str]:
        """Проверяет нарушения архитектуры (перекрестные импорты)."""
        print("🔍 Проверка архитектурных нарушений...")

        violations = []

        # Правила архитектуры
        rules = {
            "messaging": ["streaming"],  # messaging не должен импортировать streaming
            "streaming": ["messaging"],  # streaming не должен импортировать messaging (кроме core)
        }

        files = self.get_python_files()

        for file_path in files:
            content = self.get_file_content(file_path)
            if not content:
                continue

            # Определяем модуль файла
            parts = file_path.parts
            if "src" in parts:
                try:
                    src_index = parts.index("src")
                    if src_index + 1 < len(parts):
                        module = parts[src_index + 1]
                    else:
                        continue
                except (ValueError, IndexError):
                    continue
            else:
                continue

            # Проверяем импорты
            import_pattern = re.compile(r"^(?:from\s+(\w+)|import\s+(\w+))", re.MULTILINE)

            for match in import_pattern.finditer(content):
                imported_module = match.group(1) or match.group(2)

                if module in rules and imported_module in rules[module]:
                    violations.append(f"❌ {file_path}: модуль '{module}' не должен импортировать '{imported_module}'")

        return violations

    def run_pylint_similarity_check(self) -> str:
        """Запускает pylint для проверки схожести кода."""
        print("🔍 Запуск pylint для проверки схожести...")

        try:
            cmd = ["pylint", "--disable=all", "--enable=duplicate-code", "src/"]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root_path)
            return result.stdout
        except Exception as e:
            return f"Ошибка запуска pylint: {e}"

    def generate_report(self) -> str:
        """Генерирует отчет об обнаруженном дублировании."""
        report = []
        report.append("# 📊 Отчет об анализе дублирования кода\n")

        # Точные дубликаты
        duplicates = self.find_exact_duplicates()
        report.append(f"## 🔍 Точные дубликаты (найдено: {len(duplicates)})\n")

        if duplicates:
            for i, (block_hash, locations) in enumerate(duplicates.items(), 1):
                if len(locations) > 1:
                    report.append(f"### Дубликат #{i}")
                    report.append(f"**Найдено в {len(locations)} местах:**")
                    for file_path, start_line, end_line in locations:
                        rel_path = file_path.relative_to(self.root_path)
                        report.append(f"- `{rel_path}:{start_line}-{end_line}`")
                    report.append("")
        else:
            report.append("✅ Точных дубликатов не найдено!\n")

        # Похожие функции
        similar_functions = self.find_similar_functions()
        report.append(f"## 🔧 Похожие функции (найдено: {len(similar_functions)})\n")

        if similar_functions:
            for func_name, locations in similar_functions:
                report.append(f"### Функция: `{func_name}`")
                report.append("**Найдена в:**")
                for file_path, line_num in locations:
                    rel_path = file_path.relative_to(self.root_path)
                    report.append(f"- `{rel_path}:{line_num}`")
                report.append("")
        else:
            report.append("✅ Дублированных функций не найдено!\n")

        # Архитектурные нарушения
        violations = self.check_architectural_violations()
        report.append(f"## 🏗️ Архитектурные нарушения (найдено: {len(violations)})\n")

        if violations:
            for violation in violations:
                report.append(f"- {violation}")
            report.append("")
        else:
            report.append("✅ Архитектурных нарушений не найдено!\n")

        # Pylint схожесть
        pylint_output = self.run_pylint_similarity_check()
        report.append("## 🐍 Pylint Similarity Check\n")
        report.append("```")
        report.append(pylint_output)
        report.append("```\n")

        return "\n".join(report)


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description="Анализ дублирования кода")
    parser.add_argument("--path", "-p", default=".", help="Путь к проекту")
    parser.add_argument(
        "--min-lines",
        "-m",
        type=int,
        default=MIN_LINES_FOR_DUPLICATE,
        help="Минимальное количество строк для дубликата",
    )
    parser.add_argument("--output", "-o", help="Файл для сохранения отчета")

    args = parser.parse_args()

    detector = CodeDuplicationDetector(args.path, args.min_lines)
    report = detector.generate_report()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"📄 Отчет сохранен в: {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
