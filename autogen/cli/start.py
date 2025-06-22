"""
Startapp command implementation.

Creates basic application structure with model stub and configuration.
"""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from typing_extensions import Annotated

console = Console()


def startapp_command(
    app_name: Annotated[str, typer.Argument(help="Application name (plural, snake_case)")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing app")] = False,
):
    """
    🏗️ Create basic application structure.

    Creates:
    - src/apps/{app_name}/ directory structure
    - Basic model with fields stub
    - app_config.toml with default settings
    - README.md with setup instructions
    """

    # Валидация имени приложения
    if not _validate_app_name(app_name):
        console.print(f"[red]❌ Invalid app name: {app_name}[/red]")
        console.print("[dim]App name should be lowercase, snake_case, plural (e.g., 'products', 'user_profiles')[/dim]")
        raise typer.Exit(1)

    app_path = Path(f"src/apps/{app_name}")

    # Проверка существования
    if app_path.exists() and not force:
        console.print(f"[red]❌ App '{app_name}' already exists[/red]")
        console.print(f"[dim]Use --force to overwrite or choose a different name[/dim]")
        raise typer.Exit(1)

    try:
        # Создание структуры директорий
        _create_app_structure(app_path)

        # Создание файлов
        _create_model_file(app_path, app_name)
        _create_config_file(app_path, app_name)
        _create_readme_file(app_path, app_name)

        console.print(
            Panel(
                f"[green]✅ Successfully created app '[bold]{app_name}[/bold]'[/green]\n\n"
                f"[dim]Next steps:[/dim]\n"
                f"1. Edit [blue]src/apps/{app_name}/models/{app_name}_models.py[/blue]\n"
                f"2. Configure [blue]src/apps/{app_name}/app_config.toml[/blue]\n"
                f"3. Run [bold cyan]autogen initapp {app_name}[/bold cyan]",
                title="🎉 App Created",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(f"[red]❌ Failed to create app: {e}[/red]")
        raise typer.Exit(1)


def _validate_app_name(app_name: str) -> bool:
    """Validate application name format."""
    if not app_name:
        return False

    # Check if name is lowercase and uses underscores
    if not app_name.replace("_", "").islower():
        return False

    # Check if name doesn't start with number
    if app_name[0].isdigit():
        return False

    # Check for reserved Python keywords
    reserved_words = [
        "and",
        "as",
        "assert",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "exec",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "not",
        "or",
        "pass",
        "print",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
    ]

    if app_name in reserved_words:
        return False

    return True


def _create_app_structure(app_path: Path) -> None:
    """Create basic directory structure."""
    directories = [
        app_path,
        app_path / "models",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)

    # Create __init__.py files
    (app_path / "__init__.py").write_text('"""Generated app."""\n')
    (app_path / "models" / "__init__.py").write_text('"""Models module."""\n')


def _create_model_file(app_path: Path, app_name: str) -> None:
    """Create model stub file."""
    model_name = _generate_model_name(app_name)

    model_content = f'''"""
{model_name} model definition.

This is a generated model stub. Add your fields here.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.base.models import BaseModel


class {model_name}(BaseModel):
    """
    {model_name} model.

    TODO: Add your fields here
    Example:
        name: Mapped[str] = mapped_column(String(255), nullable=False)
        description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
        price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
        is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    """

    # Add your fields here
    name: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        comment="{model_name} name"
    )

    def __repr__(self) -> str:
        return f"<{model_name}(id={{self.id}}, name='{{self.name}}')>"
'''

    model_file = app_path / "models" / f"{app_name}_models.py"
    model_file.write_text(model_content)


def _create_config_file(app_path: Path, app_name: str) -> None:
    """Create app_config.toml file."""
    model_name = _generate_model_name(app_name)

    config_content = f'''[app]
# Уровень приложения: "BasicCRUD", "Advanced", "Enterprise"
level = "BasicCRUD"
name = "{model_name}"
description = "{model_name} application"

[database]
# Настройки таблицы
table_name = "{app_name}"
schema = "public"

[features]
# Включить/выключить функции
enable_soft_delete = true
enable_timestamps = true
enable_pagination = true
enable_caching = false  # Только для Enterprise
enable_events = false   # Только для Enterprise
enable_monitoring = false  # Только для Enterprise

[exceptions]
# Настройки системы исключений
enable_rich_traceback = true  # Rich traceback для красивых ошибок
enable_error_codes = true     # Уникальные коды ошибок
enable_detailed_context = true  # Детальный контекст в исключениях
log_exceptions = true         # Логирование исключений

[api]
# Настройки API
prefix = "/{app_name.replace("_", "-")}"
tags = ["{model_name}"]
include_in_schema = true

[testing]
# Настройки тестирования
generate_factories = true
generate_fixtures = true
test_coverage_target = 80
'''

    config_file = app_path / "app_config.toml"
    config_file.write_text(config_content)


def _create_readme_file(app_path: Path, app_name: str) -> None:
    """Create README.md file."""
    model_name = _generate_model_name(app_name)

    readme_content = f"""# {model_name} Application

## Настройка

1. **Отредактируйте модель** в `models/{app_name}_models.py`
   - Добавьте нужные поля
   - Настройте валидацию и индексы

2. **Выберите уровень приложения** в `app_config.toml`
   - **BasicCRUD**: Простые CRUD операции
   - **Advanced**: + Расширенная фильтрация, поиск, агрегации
   - **Enterprise**: + Кэширование, bulk операции, события

3. **Запустите генерацию** компонентов:
   ```bash
   autogen initapp {app_name}
   ```

## Уровни приложения

### BasicCRUD
- Основные CRUD операции
- Простые фильтры
- FastAPI Depends DI
- 5 исключений + rich traceback

### Advanced  
- Расширенная фильтрация (40+ операторов)
- Полнотекстовый поиск PostgreSQL
- Курсорная пагинация
- Агрегации и сложные запросы
- Автоматическая регистрация DI
- typing.Protocol интерфейсы

### Enterprise
- Кэширование (Redis/Memory)
- Bulk операции с батчингом
- Система событий
- Unit of Work паттерн
- Полный DI контейнер
- Мониторинг и метрики

## Структура

После выполнения `autogen initapp {app_name}` будет создана полная структура:

- Модели и Pydantic схемы
- Репозиторий с выбранным уровнем функций
- Сервис с бизнес-логикой
- API routes с документацией
- Система исключений с rich traceback
- Полный набор тестов + фабрики + E2E
- Автоматические Alembic миграции
"""

    readme_file = app_path / "README.md"
    readme_file.write_text(readme_content)


def _generate_model_name(app_name: str) -> str:
    """Generate model class name from app name (singular, PascalCase)."""
    # Simple singularization (remove 's' if it ends with 's')
    if app_name.endswith("s") and len(app_name) > 1:
        singular = app_name[:-1]
    else:
        singular = app_name

    # Convert to PascalCase
    return "".join(word.capitalize() for word in singular.split("_"))
