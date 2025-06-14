"""Базовые обработчики команд Telegram ботов."""

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from ..decorators import callback_handler, command, get_command_registry, message_handler, rate_limit
from ..templates import render_template


@command("start", description="Запуск бота")
@rate_limit(calls=3, period=60)
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    user = message.from_user
    if user is None:
        await message.answer("❌ Не удалось получить информацию о пользователе")
        return

    response = render_template(
        "welcome",
        user={"first_name": user.first_name, "last_name": user.last_name, "username": user.username, "id": user.id},
    )

    if response:
        await message.answer(response)
    else:
        await message.answer(f"👋 Привет, {user.first_name}!\n\nДобро пожаловать в бота!")


@command("help", description="Справка по командам")
@rate_limit(calls=5, period=60)
async def cmd_help(message: Message):
    """Обработчик команды /help."""
    registry = get_command_registry()
    commands_info = registry.get_commands_info()

    response = render_template("help", commands=commands_info)

    if response:
        await message.answer(response)
    else:
        help_text = "📖 <b>Доступные команды:</b>\n\n"
        for cmd_info in commands_info:
            help_text += f"• {cmd_info['command']} - {cmd_info['description']}\n"

        await message.answer(help_text, parse_mode="HTML")


@command("info", description="Информация о боте")
async def cmd_info(message: Message):
    """Обработчик команды /info."""
    from ...core.config import get_settings

    settings = get_settings()

    info_text = f"""🤖 <b>Информация о боте</b>

📍 <b>Проект:</b> {settings.PROJECT_NAME}
📝 <b>Описание:</b> {settings.PROJECT_DESCRIPTION}
🔢 <b>Версия:</b> {settings.VERSION}

👤 <b>Пользователь:</b> {message.from_user.first_name if message.from_user else "Неизвестно"}
🆔 <b>ID:</b> <code>{message.from_user.id if message.from_user else "Неизвестно"}</code>
💬 <b>Чат:</b> {message.chat.type}"""

    await message.answer(info_text, parse_mode="HTML")


@command("status", description="Статус системы")
@rate_limit(calls=2, period=120)
async def cmd_status(message: Message):
    """Обработчик команды /status."""
    import datetime

    import psutil

    # Системная информация
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())

    status_text = f"""📊 <b>Статус системы</b>

🖥 <b>CPU:</b> {cpu_percent}%
🧠 <b>RAM:</b> {memory.percent}% ({memory.used // 1024 // 1024} MB / {memory.total // 1024 // 1024} MB)
💾 <b>Диск:</b> {disk.percent}% ({disk.used // 1024 // 1024 // 1024} GB / {disk.total // 1024 // 1024 // 1024} GB)
⏰ <b>Uptime:</b> {str(uptime).split(".")[0]}"""

    await message.answer(status_text, parse_mode="HTML")


@command("ping", description="Проверка отклика")
async def cmd_ping(message: Message):
    """Обработчик команды /ping."""
    import time

    start_time = time.time()

    sent_message = await message.answer("🏓 Pong!")

    end_time = time.time()
    response_time = round((end_time - start_time) * 1000, 2)

    await sent_message.edit_text(f"🏓 Pong! Время отклика: {response_time} мс")


@command("echo", description="Повторить сообщение")
async def cmd_echo(message: Message):
    """Обработчик команды /echo."""
    # Получаем текст после команды
    command_text = message.text or ""
    if " " in command_text:
        echo_text = command_text.split(" ", 1)[1]
        await message.answer(f"🔄 {echo_text}")
    else:
        await message.answer("💭 Напишите что-то после команды /echo")


@command("templates", description="Список доступных шаблонов")
async def cmd_templates(message: Message):
    """Обработчик команды /templates."""
    from ..templates import get_template_manager

    template_manager = get_template_manager()
    templates = template_manager.list_templates()

    if templates:
        template_text = "📋 <b>Доступные шаблоны:</b>\n\n"
        for template_name in templates:
            template = template_manager.get_template(template_name)
            if template:
                description = template.description or "Без описания"
                template_text += f"• <code>{template_name}</code> - {description}\n"

        await message.answer(template_text, parse_mode="HTML")
    else:
        await message.answer("📋 Шаблоны не найдены")


@command("keyboard", description="Показать клавиатуру")
async def cmd_keyboard(message: Message):
    """Обработчик команды /keyboard с inline клавиатурой."""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="answer_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="answer_no"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Информация", callback_data="show_info"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings"),
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh")],
        ]
    )

    await message.answer("⌨️ Выберите опцию:", reply_markup=keyboard)


# Обработчики callback queries
@callback_handler("answer_yes")
async def callback_answer_yes(callback: CallbackQuery):
    """Обработчик нажатия 'Да'."""
    await callback.answer("✅ Вы выбрали: Да")
    if (
        callback.message
        and isinstance(callback.message, Message)
        and hasattr(callback.message, "edit_text")
        and callable(getattr(callback.message, "edit_text", None))
    ):
        await callback.message.edit_text("✅ Ответ: Да")


@callback_handler("answer_no")
async def callback_answer_no(callback: CallbackQuery):
    """Обработчик нажатия 'Нет'."""
    await callback.answer("❌ Вы выбрали: Нет")
    if (
        callback.message
        and isinstance(callback.message, Message)
        and hasattr(callback.message, "edit_text")
        and callable(getattr(callback.message, "edit_text", None))
    ):
        await callback.message.edit_text("❌ Ответ: Нет")


@callback_handler("show_info")
async def callback_show_info(callback: CallbackQuery):
    """Обработчик показа информации."""
    info_text = """ℹ️ <b>Информация</b>

Это пример inline клавиатуры в Telegram боте.
Вы можете создавать различные кнопки для взаимодействия с пользователями."""

    await callback.answer()
    if (
        callback.message
        and isinstance(callback.message, Message)
        and hasattr(callback.message, "edit_text")
        and callable(getattr(callback.message, "edit_text", None))
    ):
        await callback.message.edit_text(info_text, parse_mode="HTML")


@callback_handler("show_settings")
async def callback_show_settings(callback: CallbackQuery):
    """Обработчик показа настроек."""
    settings_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔔 Уведомления", callback_data="toggle_notifications"),
                InlineKeyboardButton(text="🌙 Тема", callback_data="toggle_theme"),
            ],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")],
        ]
    )

    await callback.answer()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            "⚙️ <b>Настройки</b>\n\nВыберите параметр для изменения:", parse_mode="HTML", reply_markup=settings_keyboard
        )


@callback_handler("refresh")
async def callback_refresh(callback: CallbackQuery):
    """Обработчик обновления."""
    await callback.answer("🔄 Обновлено!", show_alert=True)

    # Возвращаем исходную клавиатуру
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="answer_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="answer_no"),
            ],
            [
                InlineKeyboardButton(text="ℹ️ Информация", callback_data="show_info"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings"),
            ],
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh")],
        ]
    )

    await callback.message.edit_text("⌨️ Выберите опцию:", reply_markup=keyboard)


# Обработчик всех остальных сообщений
@message_handler(content_types=["text"])
async def handle_text_message(message: Message):
    """Обработчик текстовых сообщений."""
    # Игнорируем команды, они обрабатываются отдельно
    if message.text and message.text.startswith("/"):
        return

    # Простой эхо-ответ
    response = f"💬 Вы написали: {message.text}"
    await message.answer(response)


# Обработчики других типов контента
@message_handler(content_types=["photo"])
async def handle_photo(message: Message):
    """Обработчик фотографий."""
    await message.answer("📸 Получена фотография! Спасибо за изображение.")


@message_handler(content_types=["document"])
async def handle_document(message: Message):
    """Обработчик документов."""
    doc_name = message.document.file_name if message.document else "файл"
    await message.answer(f"📄 Получен документ: {doc_name}")


@message_handler(content_types=["voice"])
async def handle_voice(message: Message):
    """Обработчик голосовых сообщений."""
    await message.answer("🎤 Получено голосовое сообщение!")


@message_handler(content_types=["sticker"])
async def handle_sticker(message: Message):
    """Обработчик стикеров."""
    await message.answer("😊 Классный стикер!")


def register_basic_handlers():
    """Регистрация базовых обработчиков."""
    # Все обработчики регистрируются автоматически при импорте
    # благодаря декораторам
    pass
