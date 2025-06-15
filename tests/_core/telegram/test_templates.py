"""Тесты для системы шаблонов Telegram ботов."""

import shutil
import tempfile
from pathlib import Path

import pytest

from core.telegram.templates import MessageTemplate, TemplateManager


class TestMessageTemplate:
    """Тесты для класса MessageTemplate."""

    def test_basic_template(self):
        """Тест базового шаблона."""
        template = MessageTemplate(name="test", template="Hello, {{ name }}!")

        assert template.name == "test"
        assert template.template == "Hello, {{ name }}!"
        assert template.description is None
        assert template.parse_mode == "HTML"

    def test_template_render(self):
        """Тест рендеринга шаблона."""
        template = MessageTemplate(
            name="greeting", template="Hello, {{ name }}! Welcome to {{ app_name }}.", variables={"app_name": "MyBot"}
        )

        result = template.render(name="John")
        assert result == "Hello, John! Welcome to MyBot."

    def test_template_render_with_defaults(self):
        """Тест рендеринга с переменными по умолчанию."""
        template = MessageTemplate(
            name="greeting",
            template="Hello, {{ name }}! Status: {{ status }}",
            variables={"status": "active", "name": "Guest"},
        )

        # Используем переменные по умолчанию
        result1 = template.render()
        assert result1 == "Hello, Guest! Status: active"

        # Переопределяем переменные
        result2 = template.render(name="John", status="inactive")
        assert result2 == "Hello, John! Status: inactive"

    def test_complex_template(self):
        """Тест сложного шаблона с циклами."""
        template = MessageTemplate(
            name="list",
            template="""Items:
{% for item in items %}
- {{ item.name }}: {{ item.price }}
{% endfor %}
Total: {{ total }}""",
        )

        result = template.render(
            items=[{"name": "Apple", "price": "$1"}, {"name": "Banana", "price": "$2"}], total="$3"
        )

        expected = """Items:

- Apple: $1

- Banana: $2

Total: $3"""
        assert result == expected


class TestTemplateManager:
    """Тесты для класса TemplateManager."""

    @pytest.fixture
    def temp_dir(self):
        """Создаем временную директорию для тестов."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    def test_manager_initialization(self, temp_dir):
        """Тест инициализации менеджера."""
        manager = TemplateManager(templates_dir=temp_dir)

        assert manager.templates_dir == temp_dir
        assert manager.auto_reload is False
        assert isinstance(manager._templates_cache, dict)

    def test_add_and_get_template(self, temp_dir):
        """Тест добавления и получения шаблона."""
        manager = TemplateManager(templates_dir=temp_dir)

        template = MessageTemplate(name="test_template", template="Hello, {{ name }}!")

        manager.add_template(template)

        retrieved = manager.get_template("test_template")
        assert retrieved is not None
        assert retrieved.name == "test_template"
        assert retrieved.template == "Hello, {{ name }}!"

    def test_render_template(self, temp_dir):
        """Тест рендеринга шаблона через менеджер."""
        manager = TemplateManager(templates_dir=temp_dir)

        template = MessageTemplate(name="greeting", template="Hello, {{ name }}!")

        manager.add_template(template)

        result = manager.render_template("greeting", name="World")
        assert result == "Hello, World!"

        # Несуществующий шаблон
        result = manager.render_template("nonexistent", name="World")
        assert result is None

    def test_list_templates(self, temp_dir):
        """Тест получения списка шаблонов."""
        manager = TemplateManager(templates_dir=temp_dir)

        templates = [
            MessageTemplate(name="template1", template="Template 1"),
            MessageTemplate(name="template2", template="Template 2"),
            MessageTemplate(name="template3", template="Template 3"),
        ]

        for template in templates:
            manager.add_template(template)

        template_list = manager.list_templates()
        assert len(template_list) == 3
        assert "template1" in template_list
        assert "template2" in template_list
        assert "template3" in template_list

    def test_remove_template(self, temp_dir):
        """Тест удаления шаблона."""
        manager = TemplateManager(templates_dir=temp_dir)

        template = MessageTemplate(name="test_template", template="Hello, {{ name }}!")

        manager.add_template(template)
        assert manager.get_template("test_template") is not None

        # Удаляем шаблон
        result = manager.remove_template("test_template")
        assert result is True
        assert manager.get_template("test_template") is None

        # Попытка удалить несуществующий шаблон
        result = manager.remove_template("nonexistent")
        assert result is False

    def test_save_template_to_file(self, temp_dir):
        """Тест сохранения шаблона в файл."""
        manager = TemplateManager(templates_dir=temp_dir)

        template = MessageTemplate(
            name="file_template", template="Hello, {{ name }}!", description="Test template", parse_mode="Markdown"
        )

        result = manager.save_template_to_file(template)
        assert result is True

        # Проверяем, что файл создан
        template_file = temp_dir / "file_template.j2"
        assert template_file.exists()

        # Проверяем содержимое файла
        content = template_file.read_text(encoding="utf-8")
        assert "description: Test template" in content
        assert "parse_mode: Markdown" in content
        assert "Hello, {{ name }}!" in content

    def test_load_templates_from_files(self, temp_dir):
        """Тест загрузки шаблонов из файлов."""
        # Создаем тестовый файл шаблона
        template_file = temp_dir / "test_template.j2"
        template_content = """{# description: Test template #}
{# parse_mode: HTML #}

Hello, {{ name }}! Welcome to our bot."""

        template_file.write_text(template_content, encoding="utf-8")

        # Создаем менеджер и загружаем шаблоны
        manager = TemplateManager(templates_dir=temp_dir)

        # Проверяем, что шаблон загружен
        template = manager.get_template("test_template")
        assert template is not None
        assert template.name == "test_template"
        assert template.description == "Test template"
        assert template.parse_mode == "HTML"
        assert "Hello, {{ name }}!" in template.template

    def test_metadata_parsing(self, temp_dir):
        """Тест парсинга метаданных из комментариев."""
        manager = TemplateManager(templates_dir=temp_dir)

        content = """{# description: Welcome message #}
{# parse_mode: Markdown #}
{# variables: {"default_name": "Guest"} #}

Welcome, {{ name|default(default_name) }}!"""

        metadata = manager._parse_template_metadata(content)

        assert metadata["description"] == "Welcome message"
        assert metadata["parse_mode"] == "Markdown"
        assert metadata["variables"]["default_name"] == "Guest"

    def test_create_default_templates(self, temp_dir):
        """Тест создания шаблонов по умолчанию."""
        manager = TemplateManager(templates_dir=temp_dir)

        # Убеждаемся, что нет шаблонов
        assert len(manager.list_templates()) == 0

        # Создаем шаблоны по умолчанию
        manager.create_default_templates()

        # Проверяем, что шаблоны созданы
        templates = manager.list_templates()
        assert len(templates) > 0

        # Проверяем конкретные шаблоны
        assert "welcome" in templates
        assert "help" in templates
        assert "error" in templates

        # Проверяем один из шаблонов
        welcome_template = manager.get_template("welcome")
        assert welcome_template is not None
        assert "Добро пожаловать" in welcome_template.template


@pytest.mark.asyncio
class TestTemplateManagerAsync:
    """Асинхронные тесты для TemplateManager."""

    async def test_concurrent_template_access(self, temp_dir=None):
        """Тест одновременного доступа к шаблонам."""
        import asyncio

        if temp_dir is None:
            temp_dir = Path(tempfile.mkdtemp())

        manager = TemplateManager(templates_dir=temp_dir)

        # Добавляем тестовый шаблон
        template = MessageTemplate(name="concurrent_test", template="Hello, {{ name }}!")
        manager.add_template(template)

        # Функция для одновременного рендеринга
        async def render_template(name_suffix):
            await asyncio.sleep(0.01)  # Небольшая задержка
            return manager.render_template("concurrent_test", name=f"User{name_suffix}")

        # Запускаем несколько задач одновременно
        tasks = [render_template(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # Проверяем результаты
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == f"Hello, User{i}!"

        # Очищаем временную директорию
        if temp_dir:
            shutil.rmtree(temp_dir)
