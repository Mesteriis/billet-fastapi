"""
CLI команды для генерации тестовых компонентов FastAPI приложений.

Этот модуль предоставляет:
- Генерацию фабрик для тестов
- Генерацию фикстур
- Создание базовых тестовых файлов
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from autogen.core.generators import AppGenerator, GenerationConfig

console = Console()

# Create tests CLI app
tests = typer.Typer(help="🧪 Генерация тестовых компонентов.")


@tests.command()
def factories(
    app_name: str = typer.Argument(help="Имя приложения"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Показать что будет сгенерировано"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Перезаписать существующие файлы"),
):
    """
    🏭 Генерация фабрик и фикстур для тестов.

    Создает тестовые компоненты для указанного приложения:
    - Фабрики для создания тестовых данных
    - Фикстуры для pytest
    - Базовую конфигурацию для тестов

    Примеры:
        autogen tests factories users
        autogen tests factories products --dry-run
        autogen tests factories orders --overwrite
    """
    try:
        console.print(f"🧪 Генерация тестовых компонентов для приложения: [bold]{app_name}[/bold]")

        # Проверяем существование приложения
        app_dir = Path(f"src/apps/{app_name}")
        if not app_dir.exists():
            console.print(f"❌ Приложение {app_name} не найдено в src/apps/", style="red")
            console.print("💡 Используйте 'autogen startapp' для создания нового приложения", style="blue")
            raise typer.Abort()

        # Создаем конфигурацию на основе существующего приложения
        config = create_config_from_existing_app(app_name)

        # Генерируем тестовые компоненты
        generator = AppGenerator()
        results = generator.generate_test_factories(config, dry_run=dry_run, overwrite=overwrite)

        # Отображаем результаты
        display_generation_results(results, dry_run)

    except Exception as e:
        console.print(f"❌ Ошибка генерации тестовых компонентов: {e}", style="red")
        raise typer.Abort()


@tests.command()
def coverage(
    app_name: str = typer.Argument(help="Имя приложения"),
    test_type: str = typer.Option("unit", help="Тип тестов (unit/integration/e2e)"),
    coverage_target: int = typer.Option(80, help="Целевое покрытие тестов (%)"),
):
    """
    📊 Анализ покрытия тестов приложения.

    Анализирует текущее покрытие тестов и предлагает улучшения:
    - Текущий процент покрытия
    - Непокрытые функции и классы
    - Рекомендации по улучшению

    Примеры:
        autogen tests coverage users
        autogen tests coverage products --test-type integration
        autogen tests coverage orders --coverage-target 90
    """
    try:
        console.print(f"📊 Анализ покрытия тестов для: [bold]{app_name}[/bold]")

        # Проверяем существование тестов
        tests_dir = Path(f"tests/apps/{app_name}")
        if not tests_dir.exists():
            console.print(f"⚠️ Тесты для приложения {app_name} не найдены", style="yellow")
            console.print("💡 Используйте 'autogen tests factories' для создания тестовых компонентов", style="blue")
            return

        # Запускаем анализ покрытия
        coverage_results = analyze_app_coverage(app_name, test_type, coverage_target)
        display_coverage_results(coverage_results)

    except Exception as e:
        console.print(f"❌ Ошибка анализа покрытия: {e}", style="red")
        raise typer.Abort()


def create_config_from_existing_app(app_name: str) -> GenerationConfig:
    """Создает конфигурацию на основе существующего приложения."""
    app_dir = Path(f"src/apps/{app_name}")

    # Ищем модель
    models_dir = app_dir / "models"
    model_files = list(models_dir.glob("*_models.py")) if models_dir.exists() else []

    if model_files:
        model_file = model_files[0]
        model_name = model_file.stem.replace("_models", "").title()
        table_name = model_file.stem.replace("_models", "")
    else:
        model_name = app_name.title()
        table_name = app_name.lower()

    # Определяем уровень сложности по существующим файлам
    level = "BasicCRUD"
    if (app_dir / "middleware").exists():
        level = "Advanced"
    if (app_dir / "cache").exists() or (app_dir / "events").exists():
        level = "Enterprise"

    return GenerationConfig(
        app_name=app_name,
        model_name=model_name,
        table_name=table_name,
        level=level,
        features={"testing": True, "factories": True, "fixtures": True},
        testing_config={"coverage_target": 80, "use_factories": True},
    )


def analyze_app_coverage(app_name: str, test_type: str, coverage_target: int) -> dict:
    """Анализирует покрытие тестов приложения."""
    import json
    import subprocess
    import sys

    try:
        # Запускаем pytest с покрытием
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            f"tests/apps/{app_name}",
            f"--cov=src/apps/{app_name}",
            "--cov-report=json",
            "--cov-report=term-missing",
            "--quiet",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        # Парсим результаты
        coverage_json = Path("coverage.json")
        if coverage_json.exists():
            with open(coverage_json) as f:
                coverage_data = json.load(f)
            coverage_percent = coverage_data.get("totals", {}).get("percent_covered", 0)
        else:
            coverage_percent = 0

        return {
            "app_name": app_name,
            "test_type": test_type,
            "coverage_percent": coverage_percent,
            "coverage_target": coverage_target,
            "success": result.returncode == 0,
            "output": result.stdout,
            "meets_target": coverage_percent >= coverage_target,
        }

    except Exception as e:
        return {
            "app_name": app_name,
            "test_type": test_type,
            "coverage_percent": 0,
            "coverage_target": coverage_target,
            "success": False,
            "error": str(e),
            "meets_target": False,
        }


def display_generation_results(results: dict, dry_run: bool):
    """Отображает результаты генерации тестовых компонентов."""
    if dry_run:
        console.print("\n🔍 Предварительный просмотр генерации:")

        table = Table(title="Файлы для генерации")
        table.add_column("Файл", style="cyan")
        table.add_column("Описание", style="blue")
        table.add_column("Существует", style="yellow")

        for file_info in results.get("files_to_generate", []):
            exists_status = "✅ Да" if file_info.get("exists", False) else "❌ Нет"
            table.add_row(file_info.get("file", ""), file_info.get("description", ""), exists_status)

        console.print(table)

    else:
        status = results.get("status", "unknown")
        app_name = results.get("app_name", "")

        if status == "success":
            console.print(f"✅ Тестовые компоненты для [bold]{app_name}[/bold] успешно созданы!", style="green")

            # Созданные фабрики
            factories = results.get("factories_created", [])
            if factories:
                console.print(f"\n🏭 Созданные фабрики ({len(factories)}):")
                for factory in factories:
                    console.print(f"  • {Path(factory).name}", style="green")

            # Созданные фикстуры
            fixtures = results.get("fixtures_created", [])
            if fixtures:
                console.print(f"\n🔧 Созданные фикстуры ({len(fixtures)}):")
                for fixture in fixtures:
                    console.print(f"  • {Path(fixture).name}", style="blue")

        elif status == "failed":
            console.print(f"❌ Не удалось создать тестовые компоненты для {app_name}", style="red")
            errors = results.get("errors", [])
            if errors:
                console.print("\nОшибки:")
                for error in errors:
                    console.print(f"  • {error}", style="red")

        # Пропущенные файлы
        skipped = results.get("files_skipped", [])
        if skipped:
            console.print(f"\n⚠️ Пропущенные файлы ({len(skipped)}):")
            for file in skipped:
                console.print(f"  • {Path(file).name} (уже существует)", style="yellow")
            console.print("💡 Используйте --overwrite для перезаписи", style="blue")


def display_coverage_results(results: dict):
    """Отображает результаты анализа покрытия."""
    app_name = results.get("app_name", "")
    coverage_percent = results.get("coverage_percent", 0)
    coverage_target = results.get("coverage_target", 80)
    meets_target = results.get("meets_target", False)

    # Определяем цвет и статус
    if meets_target:
        color = "green"
        status = "✅ Отлично"
    elif coverage_percent >= coverage_target * 0.8:
        color = "yellow"
        status = "⚠️ Удовлетворительно"
    else:
        color = "red"
        status = "❌ Требует внимания"

    panel = Panel(
        f"**Приложение:** {app_name}\n"
        f"**Текущее покрытие:** {coverage_percent:.1f}%\n"
        f"**Целевое покрытие:** {coverage_target}%\n"
        f"**Статус:** {status}",
        title="📊 Отчет о покрытии тестов",
        border_style=color,
    )

    console.print(panel)

    # Рекомендации
    if not meets_target:
        console.print("\n💡 Рекомендации:")
        console.print(f"  • Добавьте тесты для увеличения покрытия на {coverage_target - coverage_percent:.1f}%")
        console.print("  • Сосредоточьтесь на тестировании бизнес-логики")
        console.print("  • Добавьте интеграционные тесты для API")


if __name__ == "__main__":
    tests()
