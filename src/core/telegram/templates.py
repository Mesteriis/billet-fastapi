"""Система шаблонов для Telegram сообщений."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape
from pydantic import Field

from tools.pydantic import BaseModel as BaseConfigModel


class MessageTemplate(BaseConfigModel):
    """Шаблон сообщения."""

    name: str = Field(..., description="Имя шаблона")
    template: str = Field(..., description="Содержимое шаблона")
    description: str | None = Field(default=None, description="Описание шаблона")
    variables: dict[str, Any] = Field(default_factory=dict, description="Переменные по умолчанию")
    parse_mode: str | None = Field(default="HTML", description="Режим парсинга")

    def render(self, **kwargs) -> str:
        """Рендер шаблона с переданными переменными."""
        # Объединяем переменные по умолчанию с переданными
        context = {**self.variables, **kwargs}

        # Создаем Jinja2 шаблон
        template = Template(self.template)
        return template.render(**context)


class TemplateManager:
    """Менеджер шаблонов сообщений."""

    def __init__(self, templates_dir: str | Path = "telegram/templates", auto_reload: bool = False):
        """
        Инициализация менеджера шаблонов.

        Args:
            templates_dir: Директория с шаблонами
            auto_reload: Автоперезагрузка шаблонов
        """
        self.templates_dir = Path(templates_dir)
        self.auto_reload = auto_reload

        # Создаем директорию если не существует
        self.templates_dir.mkdir(parents=True, exist_ok=True)

        # Настраиваем Jinja2 окружение
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            auto_reload=auto_reload,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Кеш шаблонов
        self._templates_cache: dict[str, MessageTemplate] = {}

        # Загружаем шаблоны при инициализации
        self._load_templates()

    def _load_templates(self) -> None:
        """Загрузка всех шаблонов из директории."""
        self._templates_cache.clear()

        # Загружаем .j2 файлы как шаблоны
        for template_file in self.templates_dir.glob("*.j2"):
            try:
                template_name = template_file.stem
                template_content = template_file.read_text(encoding="utf-8")

                # Ищем метаданные в комментариях
                metadata = self._parse_template_metadata(template_content)

                template = MessageTemplate(name=template_name, template=template_content, **metadata)

                self._templates_cache[template_name] = template

            except Exception as e:
                print(f"Ошибка загрузки шаблона {template_file}: {e}")

    def _parse_template_metadata(self, content: str) -> dict[str, Any]:
        """Парсинг метаданных из комментариев шаблона."""
        metadata = {}
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("{#") and line.endswith("#}"):
                # Извлекаем метаданные из комментариев
                # Формат: {# key: value #}
                meta_content = line[2:-2].strip()
                if ":" in meta_content:
                    key, value = meta_content.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if key == "description":
                        metadata["description"] = value
                    elif key == "parse_mode":
                        metadata["parse_mode"] = value
                    elif key == "variables":
                        # Парсинг переменных как JSON
                        try:
                            import json

                            metadata["variables"] = json.loads(value)
                        except:
                            pass

        return metadata

    def get_template(self, name: str) -> MessageTemplate | None:
        """Получить шаблон по имени."""
        if self.auto_reload:
            self._load_templates()

        return self._templates_cache.get(name)

    def render_template(self, name: str, **kwargs) -> str | None:
        """Рендер шаблона по имени."""
        template = self.get_template(name)
        if template:
            return template.render(**kwargs)
        return None

    def add_template(self, template: MessageTemplate) -> None:
        """Добавить шаблон в кеш."""
        self._templates_cache[template.name] = template

    def remove_template(self, name: str) -> bool:
        """Удалить шаблон из кеша."""
        if name in self._templates_cache:
            del self._templates_cache[name]
            return True
        return False

    def list_templates(self) -> list[str]:
        """Получить список всех шаблонов."""
        if self.auto_reload:
            self._load_templates()

        return list(self._templates_cache.keys())

    def save_template_to_file(self, template: MessageTemplate) -> bool:
        """Сохранить шаблон в файл."""
        try:
            template_file = self.templates_dir / f"{template.name}.j2"

            # Добавляем метаданные в комментарии
            content_lines = []

            if template.description:
                content_lines.append(f"{{# description: {template.description} #}}")

            if template.parse_mode and template.parse_mode != "HTML":
                content_lines.append(f"{{# parse_mode: {template.parse_mode} #}}")

            if template.variables:
                import json

                variables_json = json.dumps(template.variables, ensure_ascii=False)
                content_lines.append(f"{{# variables: {variables_json} #}}")

            content_lines.append("")
            content_lines.append(template.template)

            template_file.write_text("\n".join(content_lines), encoding="utf-8")

            # Обновляем кеш
            self._templates_cache[template.name] = template

            return True

        except Exception as e:
            print(f"Ошибка сохранения шаблона {template.name}: {e}")
            return False

    def create_default_templates(self) -> None:
        """Создать шаблоны по умолчанию."""
        default_templates = [
            MessageTemplate(
                name="welcome",
                template="👋 Привет, {{ user.first_name }}!\n\nДобро пожаловать в бота!",
                description="Приветственное сообщение",
                variables={"user": {"first_name": "Пользователь"}},
            ),
            MessageTemplate(
                name="help",
                template="""📖 <b>Справка по командам:</b>

{% for command in commands %}
• {{ command.command }} - {{ command.description }}
{% endfor %}

Для получения подробной информации используйте /help <команда>""",
                description="Справка по командам",
                variables={"commands": []},
            ),
            MessageTemplate(
                name="error",
                template="❌ <b>Ошибка:</b> {{ error_message }}",
                description="Сообщение об ошибке",
                variables={"error_message": "Неизвестная ошибка"},
            ),
            MessageTemplate(
                name="success",
                template="✅ {{ message }}",
                description="Сообщение об успехе",
                variables={"message": "Операция выполнена успешно"},
            ),
            MessageTemplate(
                name="loading",
                template="⏳ {{ message|default('Загрузка...') }}",
                description="Сообщение о загрузке",
                variables={},
            ),
            MessageTemplate(
                name="admin_only",
                template="🔒 Эта команда доступна только администраторам.",
                description="Сообщение о недостаточных правах",
            ),
        ]

        for template in default_templates:
            if not self.get_template(template.name):
                self.save_template_to_file(template)


# Глобальный менеджер шаблонов
_template_manager: TemplateManager | None = None


def get_template_manager() -> TemplateManager:
    """Получить глобальный менеджер шаблонов."""
    global _template_manager
    if _template_manager is None:
        from .config import TelegramBotsConfig

        config = TelegramBotsConfig()
        _template_manager = TemplateManager(
            templates_dir=config.TELEGRAM_TEMPLATES_DIR, auto_reload=config.TELEGRAM_TEMPLATES_AUTO_RELOAD
        )
    return _template_manager


def render_template(name: str, **kwargs) -> str | None:
    """Быстрый рендер шаблона."""
    return get_template_manager().render_template(name, **kwargs)
